"""Frontend-independent runtime initialization shared by application windows."""


def initialize_runtime(self):
    """Initialize saved state and registries without building UI or starting services.

    The caller supplies the runtime mixins, including achievement normalization,
    builtin click modifiers, and _register_default_console_commands().
    Loading mods, building the frontend, and starting services remain the caller's
    responsibility. Optional pygame audio initialization matches the GTK runtime.
    """
    import os
    import sys
    import time

    from defaults import (
        BASE_CURRENCIES, BASE_UPGRADES, DEFAULT_ACHIEVEMENTS,
        DEFAULT_SETTINGS, DEFAULT_STATE,
    )
    from paths import LEGACY_SETTINGS_FILE, SETTINGS_FILE, find_app_asset
    from rpc import DEFAULT_GAME_TITLE
    from save_manager import (
        DEFAULT_SAVE_ID, DEFAULT_SAVE_NAME, build_save_slot_data,
        clone_json_data, current_save_timestamp, ensure_save_storage,
        load_json, load_legacy_counter, load_save_slot_data,
        normalize_save_kind, normalize_save_name, save_json,
        write_save_slot_data,
    )

    # ---------- load saved data ----------
    self.settings     = load_json(SETTINGS_FILE,     DEFAULT_SETTINGS,     legacy_path=LEGACY_SETTINGS_FILE)
    for k, v in DEFAULT_SETTINGS.items():
        self.settings.setdefault(k, clone_json_data(v))
    if not isinstance(self.settings.get("mod_settings"), dict):
        self.settings["mod_settings"] = {}

    self.active_save_id = ensure_save_storage(self.settings)
    active_slot = load_save_slot_data(self.active_save_id)
    if active_slot is None:
        active_slot = build_save_slot_data(
            DEFAULT_SAVE_ID,
            DEFAULT_SAVE_NAME,
            DEFAULT_STATE,
            DEFAULT_ACHIEVEMENTS,
        )
        write_save_slot_data(active_slot)
        self.active_save_id = DEFAULT_SAVE_ID
        self.settings["active_save_id"] = self.active_save_id
        save_json(SETTINGS_FILE, self.settings)

    self.active_save_name = normalize_save_name(active_slot.get("name") or DEFAULT_SAVE_NAME)
    self.active_save_kind = normalize_save_kind(active_slot.get("save_kind"))
    self.active_save_created_at = active_slot.get("created_at") or current_save_timestamp()
    self.active_save_updated_at = active_slot.get("updated_at") or self.active_save_created_at
    self.active_save_last_auto_backup_at = active_slot.get("last_auto_backup_at", 0)
    self.state = clone_json_data(active_slot.get("state", DEFAULT_STATE))
    self.achievements = clone_json_data(active_slot.get("achievements", DEFAULT_ACHIEVEMENTS))
    self.active_save_required_mods = list(active_slot.get("required_mods", []))
    self.save_namespaces = clone_json_data(active_slot.get("mod_data", {}))
    if not isinstance(self.save_namespaces, dict):
        self.save_namespaces = {}
    self.achievements = {
        k: dict(v) if isinstance(v, dict) else v
        for k, v in self.achievements.items()
    }
    had_currencies_dict = isinstance(self.state.get("currencies"), dict)

    for k, v in DEFAULT_STATE.items():
        if k not in self.state:
            self.state[k] = clone_json_data(v)
    if "upgrades_owned" not in self.state:
        self.state["upgrades_owned"] = {}

    # migrate legacy flat "flesh" float -> currencies dict
    if "flesh" in self.state and not isinstance(self.state.get("currencies"), dict):
        self.state["currencies"] = {"flesh": float(self.state.pop("flesh", 0.0))}
    if "currencies" not in self.state:
        self.state["currencies"] = {"flesh": 0.0}
    self.state["currencies"].setdefault("flesh", 0.0)

    for k, v in DEFAULT_ACHIEVEMENTS.items():
        if k not in self.achievements:
            self.achievements[k] = dict(v)
    self._normalize_achievement_sources()

    # sync flesh with the old counter file only for pre-currency saves
    if not had_currencies_dict and self.state["currencies"].get("flesh", 0.0) == 0:
        legacy = load_legacy_counter()
        if legacy > 0:
            self.state["currencies"]["flesh"] = float(legacy)

    # ---------- registries ----------
    self.currencies = dict(BASE_CURRENCIES)
    self.upgrades   = dict(BASE_UPGRADES)

    # primary currency: used for base per-click gain when mods replace vanilla flesh
    self.primary_currency = "flesh"
    self._rate_cache_dirty = True
    self._cached_cpc = {}
    self._cached_cps = {}
    self._last_stats_tab_refresh = 0.0

    # mods can override this to change the clickable image
    self.flesh_image_path = find_app_asset("flesh.png")

    # mod tab/button queues — populated during load_mods(), consumed in build_ui()
    # _pending_tabs: list of (tab_id, label, box) tuples
    # _pending_buttons: dict of tab_id -> list of (label, callback) tuples
    self._pending_tabs    = []
    self._pending_buttons = {}
    self._pending_images = {}
    self._pending_sprites = []
    self._pending_draw_layers = []
    # map of tab_id -> Gtk.Box (the page widget), filled after build_ui
    self._tab_pages = {}
    self._builtin_tab_ids = {"upgrades", "achievements", "leaderboard", "saves", "settings", "console", "stats"}
    self._mod_tab_owners = {}
    self._mod_button_widgets = []
    self._mod_image_widgets = []
    self._mod_sprites = {}
    self._next_sprite_id = 1
    self._mod_draw_layers = {}
    self._next_draw_layer_id = 1
    self._mod_currency_owners = {}
    self._mod_upgrade_owners = {}
    self._mod_paths = {}
    self.loaded_mod_ids = set()
    self.installed_mods = []
    self._current_mod_info = None
    self._active_mod_owner = None
    self.current_game_title = DEFAULT_GAME_TITLE
    self._event_hooks = {}
    self._next_event_hook_id = 1
    self._click_modifiers = {}
    self._next_click_modifier_id = 1
    self._in_save_event = False
    self._save_dirty = False
    self._save_dirty_auto_backup = False
    self._dirty_save_timer_id = None
    self._mod_timers = {}
    self._next_mod_timer_id = 1
    self.mod_apis = {}
    self.mod_api_aliases = {}
    self.console_commands = {}
    self.console_aliases = {}
    self._register_builtin_click_modifiers()
    self._register_default_console_commands()

    # mods can override this to change the click sound
    # default lookup lets users drop in their own wav, then falls back to bundled assets
    self.click_sound_path = find_app_asset("click.wav")
    self._sound_cache = {}
    self._pygame_mixer_ok = False
    try:
        import pygame.mixer
        # On Windows, SDL2 needs directsound or winmm — tell it explicitly
        if sys.platform == "win32":
            os.environ.setdefault("SDL_AUDIODRIVER", "directsound")
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=128)
        pygame.mixer.init()
        self._pygame_mixer_ok = True
        if os.path.exists(self.click_sound_path):
            self._sound_cache[self.click_sound_path] = pygame.mixer.Sound(self.click_sound_path)
    except Exception:
        pass

    self.start_time      = int(time.time())
    self.rpc_last_update = 0
    self.rpc             = None
    self.rpc_update_timer_id = None
    self.rpc_next_retry = 0.0
    self._last_sound_time = 0.0
    self._runtime_services_started = False
    self._startup_missing_save = None

