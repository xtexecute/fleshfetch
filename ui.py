import os
import sys
import time

from console_capture import ConsoleMixin
from defaults import (
    BASE_CURRENCIES,
    BASE_UPGRADES,
    DEFAULT_ACHIEVEMENTS,
    DEFAULT_SETTINGS,
    DEFAULT_STATE,
)
from game_state import GameStateMixin
from gameplay_ui import GameplayUiMixin
from gtk_compat import Gdk, Gio, Gtk
from leaderboard import LeaderboardMixin
from mod_api import ModApiMixin
from mod_manager import ModManagerMixin
from paths import LEGACY_SETTINGS_FILE, SETTINGS_FILE, find_app_asset
from rendering import ModDrawLayerHandle, ModImageHandle, ModSpriteHandle, RenderingMixin
from rpc import APP_ID, DEFAULT_GAME_TITLE, RpcMixin
from save_manager import (
    DEFAULT_SAVE_ID,
    DEFAULT_SAVE_NAME,
    SaveManagerMixin,
    build_save_slot_data,
    clone_json_data,
    current_save_timestamp,
    ensure_save_storage,
    load_json,
    load_legacy_counter,
    load_save_slot_data,
    normalize_save_kind,
    normalize_save_name,
    save_json,
    write_save_slot_data,
)
from save_ui import SaveUiMixin
from settings_ui import SettingsUiMixin
from stats_ui import StatsUiMixin
from ui_layout import UiLayoutMixin

# ---------- MAIN WINDOW ----------





class FleshClicker(
    GameStateMixin, RpcMixin, SaveManagerMixin, ModManagerMixin,
    ModApiMixin, RenderingMixin, UiLayoutMixin, GameplayUiMixin,
    SaveUiMixin, SettingsUiMixin, ConsoleMixin, StatsUiMixin,
    LeaderboardMixin, Gtk.Window,
):
    def __init__(self, app: Gtk.Application):
        super().__init__(title=DEFAULT_GAME_TITLE)
        self.set_default_size(900, 600)
        self.set_application(app)
        self.app = app
        self.connect("close-request", self.on_close_request)

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

        # ---------- CSS ----------
        css = """
        window, headerbar, .titlebar {
            background-color: #151515;
            color: #dddddd;
            border: none;
        }
        decoration {
            background-color: #151515;
            border: none;
            box-shadow: none;
        }
        .flesh-picture { border-radius: 12px; }
        @keyframes squish-anim {
            0%   { transform: scale(1.0); }
            40%  { transform: scale(0.94); }
            100% { transform: scale(1.0); }
        }
        .flesh-picture.squish {
            animation: squish-anim 100ms ease-out forwards;
        }
        .upgrade-row    { padding: 6px; }
        .achievement-row { padding: 4px; }
        .badge-unlocked { color: #a6e3a1; }
        .badge-locked   { color: #f38ba8; }
        label { color: #dddddd; }
        label.security-suspicious, .security-suspicious { color: #f9e2af; }
        label.mod-deprecation, .mod-deprecation { color: #ffff00; }
        label.security-extreme, .security-extreme { color: #ff4d6d; }
        scrolledwindow, viewport, box { background-color: #151515; }
        notebook { background-color: #151515; }
        notebook > header {
            background-color: #1a1a1a;
            border-bottom: 1px solid #333;
        }
        notebook > header > tabs > tab {
            background-color: #1a1a1a;
            color: #aaaaaa;
            padding: 4px 12px;
            border: none;
        }
        notebook > header > tabs > tab:checked {
            background-color: #252525;
            color: #ffffff;
            border-bottom: 2px solid #4a9eff;
        }
        button, button * {
            background-color: #252525;
            background-image: none;
            color: #dddddd;
            border: 1px solid #333333;
            border-radius: 4px;
            padding: 4px 8px;
            box-shadow: none;
            text-shadow: none;
        }
        button:hover, button:hover * {
            background-color: #2e2e2e;
            background-image: none;
            border-color: #404040;
        }
        button:active, button:active * {
            background-color: #1e1e1e;
            background-image: none;
        }
        button.suggested-action, button.suggested-action * {
            background-color: #1c5a8a;
            background-image: none;
            border-color: #1c5a8a;
            color: #ffffff;
        }
        button.suggested-action:hover, button.suggested-action:hover * {
            background-color: #1c6ea4;
            background-image: none;
        }
        textview, textview > text { background-color: #1a1a1a; color: #dddddd; }
        entry {
            background-color: #1a1a1a;
            color: #dddddd;
            border: 1px solid #333333;
            border-radius: 4px;
        }
        spinbutton { background-color: #1a1a1a; color: #dddddd; border: 1px solid #333333; }
        paned { background-color: #151515; }
        paned > separator { background-color: #2a2a2a; min-width: 1px; min-height: 1px; }
        scrolledwindow { border: none; outline: none; }
        scrolledwindow undershoot, scrolledwindow overshoot { background: none; }
        frame { border: none; outline: none; }
        frame > border { border: none; }
        grid { background-color: #151515; border: none; }
        notebook > stack { border: none; background-color: #151515; }
        """
        provider = Gtk.CssProvider()
        provider.load_from_string(css)
        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # load mods before building UI so they can register currencies/upgrades/textures
        self.load_mods()
        self._startup_missing_save = self._startup_missing_active_save()
        self.build_ui()
        self.update_labels()

        if self._startup_missing_save:
            self.show_startup_missing_mods_load_dialog(self._startup_missing_save)
        else:
            self._emit_event("load", {
                "save_id": self.active_save_id,
                "save_name": self.active_save_name,
                "save_kind": self.active_save_kind,
                "reason": "startup",
            })
            self.start_runtime_services()


class FleshApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.window = None

    def do_activate(self, *args):
        if not self.window:
            self.window = FleshClicker(self)
        self.window.present()


def main():
    app = FleshApp()
    app.run()
