import importlib.machinery
import importlib.util
import json
import os
import random
import shlex
import sys
import time

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, Gdk, GLib

from console_capture import (
    CONSOLE_FLUSH_INTERVAL_MS,
    CONSOLE_MAX_BUFFER_CHARS,
    _stderr_tee,
    _stdout_tee,
)
from defaults import *
from leaderboard import *
from mod_api import *
from paths import *
from rpc import *
from save_manager import *
from security import MOD_SECURITY_LEVEL_NAMES, scan_mod_security

# ---------- MAIN WINDOW ----------

class FleshClicker(Gtk.Window):
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
        # map of tab_id -> Gtk.Box (the page widget), filled after build_ui
        self._tab_pages = {}
        self.loaded_mod_ids = set()
        self.installed_mods = []
        self._current_mod_info = None
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
        except Exception as e:
            print(f"[sound] pygame init failed, using fallback: {e}")

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
                "reason": "startup",
            })
            self.start_runtime_services()

    # ---------- CURRENCY HELPERS ----------

    def get_currency(self, registry_name: str) -> float:
        return float(self.state["currencies"].get(registry_name, 0.0))

    def set_currency(self, registry_name: str, value: float):
        self.state["currencies"][registry_name] = max(0.0, float(value))
        self.mark_save_dirty(auto_backup=True)

    def add_currency(self, registry_name: str, amount: float):
        self.set_currency(registry_name, self.get_currency(registry_name) + amount)

    # legacy property for callers that need the real vanilla flesh amount
    @property
    def flesh(self) -> float:
        return self.get_currency("flesh")

    # ---------- UPGRADE HELPERS ----------

    def get_upgrade_count(self, uid: str) -> int:
        return int(self.state["upgrades_owned"].get(uid, 0))

    def set_upgrade_count(self, uid: str, value: int):
        self.state["upgrades_owned"][uid] = int(value)
        self.invalidate_rate_cache()
        self.mark_save_dirty(auto_backup=True)

    def total_upgrades_owned(self) -> int:
        return sum(self.state["upgrades_owned"].values())

    def get_upgrade_cost(self, uid: str, owned: int) -> float:
        u = self.upgrades[uid]
        return u["base_cost"] * (u["cost_mult"] ** owned)

    def invalidate_rate_cache(self):
        self._rate_cache_dirty = True

    def rebuild_rate_cache(self):
        cached_cpc = {currency: 0.0 for currency in self.currencies}
        cached_cps = {currency: 0.0 for currency in self.currencies}
        for uid in self.upgrades:
            count = self.get_upgrade_count(uid)
            if not count:
                continue
            for effect in self._get_effects(uid):
                currency = effect.get("currency", "flesh")
                cached_cpc.setdefault(currency, 0.0)
                cached_cps.setdefault(currency, 0.0)
                cached_cpc[currency] += effect.get("cpc", 0.0) * count
                cached_cps[currency] += effect.get("cps", 0.0) * count
        self._cached_cpc = cached_cpc
        self._cached_cps = cached_cps
        self._rate_cache_dirty = False

    def _ensure_rate_cache(self):
        if getattr(self, "_rate_cache_dirty", True):
            self.rebuild_rate_cache()

    def _get_effects(self, uid: str) -> list:
        """Return currency_effects list; falls back to legacy fps/fpc keys."""
        u = self.upgrades[uid]
        if "currency_effects" in u:
            return u["currency_effects"]
        effects = []
        fpc = u.get("fpc", 0.0)
        fps = u.get("fps", 0.0)
        if fpc or fps:
            effects.append({"currency": "flesh", "cpc": fpc, "cps": fps, "on_buy": 0.0})
        return effects

    def compute_cps(self, currency: str) -> float:
        """Total per-second gain for a currency from all owned upgrades."""
        self._ensure_rate_cache()
        return float(self._cached_cps.get(currency, 0.0))

    def compute_cpc(self, currency: str) -> float:
        """Total per-click gain for a currency from all owned upgrades."""
        self._ensure_rate_cache()
        return float(self._cached_cpc.get(currency, 0.0))

    def effective_fpc(self) -> float:
        base = self.state.get("flesh_per_click", 1.0)
        return base + self.compute_cpc(self.primary_currency)

    def on_filter_clicked(self, button, category_key):
        self.current_filter = category_key
        self._apply_upgrade_visibility()

    # ---------- DISCORD RPC ----------

    def _ensure_rpc_update_timer(self):
        if self.rpc_update_timer_id is None:
            self.rpc_update_timer_id = GLib.timeout_add(2000, self.tick_rpc_update)

    def _stop_rpc_update_timer(self):
        if self.rpc_update_timer_id is None:
            return
        try:
            GLib.source_remove(self.rpc_update_timer_id)
        except Exception:
            pass
        self.rpc_update_timer_id = None

    def init_rpc(self):
        if not RPC_AVAILABLE:
            return False
        try:
            self.rpc = Presence(RPC_CLIENT_ID)
            self.rpc.connect()
            self.rpc_last_update = 0
            return True
        except Exception:
            self.rpc = None
            self.rpc_next_retry = time.time() + 30
            return False

    def shutdown_rpc(self):
        self._stop_rpc_update_timer()
        if not self.rpc:
            return
        try:
            self.rpc.close()
        except Exception:
            pass
        finally:
            self.rpc = None

    def tick_rpc_update(self):
        if not self.settings.get("enable_rpc"):
            self.rpc_update_timer_id = None
            return False

        now = time.time()
        if not self.rpc:
            if RPC_AVAILABLE and now >= self.rpc_next_retry:
                self.init_rpc()
            return True

        if now - self.rpc_last_update < 10:
            return True
        self.rpc_last_update = now
        try:
            self.rpc.update(
                state="Playing Fleshfetch",
                details="Clicking the flesh",
                large_image="flesh",
                large_text=self.current_game_title,
                start=self.start_time,
            )
        except Exception:
            self.rpc = None
            self.rpc_next_retry = now + 30
        return True

    # ---------- SAVE SLOTS ----------

    def _current_required_mods(self):
        required = []
        by_id = {}
        for mod_req in getattr(self, "active_save_required_mods", []) or []:
            if isinstance(mod_req, dict):
                mod_id = str(mod_req.get("id") or "")
                if mod_id:
                    by_id[mod_id] = {
                        "id": mod_id,
                        "name": mod_req.get("name") or mod_id,
                        "version": mod_req.get("version") or "",
                    }
            elif mod_req:
                mod_id = str(mod_req)
                by_id[mod_id] = {"id": mod_id, "name": mod_id, "version": ""}

        loaded_ids = set(getattr(self, "loaded_mod_ids", set()))
        for mod_info in getattr(self, "installed_mods", []):
            mod_id = mod_info.get("id")
            if not mod_id or mod_id not in loaded_ids:
                continue
            by_id[mod_id] = {
                "id": mod_id,
                "name": mod_info.get("name") or mod_id,
                "version": mod_info.get("version") or "",
            }
        for mod_id in sorted(by_id):
            required.append(by_id[mod_id])
        return required

    def _loaded_mod_ids(self):
        return set(getattr(self, "loaded_mod_ids", set()))

    def _save_slot_missing_mods(self, slot_data: dict):
        loaded_ids = self._loaded_mod_ids()
        missing = []
        for mod_req in slot_data.get("required_mods", []) or []:
            mod_id = str(mod_req.get("id") if isinstance(mod_req, dict) else mod_req)
            if mod_id and mod_id not in loaded_ids:
                if isinstance(mod_req, dict):
                    label = mod_req.get("name") or mod_id
                    version = mod_req.get("version") or ""
                    if version:
                        label = f"{label} {version}"
                else:
                    label = mod_id
                missing.append(label)
        return missing

    def _startup_missing_active_save(self):
        slot = load_save_slot_data(self.active_save_id)
        if not slot:
            return None
        missing_mods = self._save_slot_missing_mods(slot)
        if not missing_mods:
            return None
        return {
            "save_id": normalize_save_id(slot.get("id") or self.active_save_id),
            "save_name": normalize_save_name(slot.get("name") or self.active_save_id),
            "missing_mods": missing_mods,
        }

    def start_runtime_services(self):
        if self._runtime_services_started:
            return
        self._runtime_services_started = True
        GLib.timeout_add(1000, self.on_timer_tick)

        if self.settings.get("enable_rpc"):
            self.init_rpc()
            self._ensure_rpc_update_timer()

    def _normalize_event_name(self, event_name: str) -> str:
        name = str(event_name or "").strip().lower().replace("-", "_").replace(" ", "_")
        return EVENT_ALIASES.get(name, name)

    def _current_mod_namespace(self, namespace=None) -> str:
        if namespace:
            return str(namespace).strip()
        current = getattr(self, "_current_mod_info", None)
        if current is not None and current.get("id"):
            return current["id"]
        return "__global__"

    def on_event(self, event_name: str, callback):
        event_name = self._normalize_event_name(event_name)
        if not event_name or not callable(callback):
            raise ValueError("on_event() requires an event name and callable callback")
        hook_id = self._next_event_hook_id
        self._next_event_hook_id += 1
        owner = self._current_mod_namespace()
        self._event_hooks.setdefault(event_name, []).append({
            "id": hook_id,
            "callback": callback,
            "owner": owner,
        })
        return hook_id

    def off_event(self, hook_id):
        removed = False
        for event_name in list(self._event_hooks.keys()):
            hooks = self._event_hooks[event_name]
            kept = [hook for hook in hooks if hook.get("id") != hook_id]
            if len(kept) != len(hooks):
                removed = True
            if kept:
                self._event_hooks[event_name] = kept
            else:
                self._event_hooks.pop(event_name, None)
        return removed

    def emit_event(self, event_name: str, payload=None):
        self._emit_event(event_name, payload)

    def _emit_event(self, event_name: str, payload=None):
        event_name = self._normalize_event_name(event_name)
        event_payload = dict(payload or {})
        event_payload.setdefault("event", event_name)
        event_payload.setdefault("game", self)
        hooks = list(self._event_hooks.get(event_name, []))
        for hook in hooks:
            callback = hook.get("callback")
            if not callable(callback):
                continue
            try:
                callback(event_payload)
            except Exception as exc:
                print(f"[events] Hook for '{event_name}' failed: {exc}")

    def on_flesh_clicked(self, callback):
        return self.on_event("flesh_clicked", callback)

    def on_upgrade_bought(self, callback):
        return self.on_event("upgrade_bought", callback)

    def on_bought(self, callback):
        return self.on_event("upgrade_bought", callback)

    def on_upgrade_buy(self, callback):
        return self.on_event("upgrade_bought", callback)

    def on_save(self, callback):
        return self.on_event("save", callback)

    def on_load(self, callback):
        return self.on_event("load", callback)

    def set_timer(self, seconds: float, callback, repeat=True):
        if not callable(callback):
            raise ValueError("set_timer() requires a callable callback")
        interval_ms = max(1, int(float(seconds) * 1000))
        timer_id = self._next_mod_timer_id
        self._next_mod_timer_id += 1
        owner = self._current_mod_namespace()

        def _tick():
            timer_info = self._mod_timers.get(timer_id)
            if not timer_info:
                return False
            try:
                result = callback()
            except Exception as exc:
                print(f"[timers] Timer {timer_id} from '{owner}' failed: {exc}")
                self._mod_timers.pop(timer_id, None)
                return False
            if not repeat or result is False:
                self._mod_timers.pop(timer_id, None)
                return False
            return True

        source_id = GLib.timeout_add(interval_ms, _tick)
        self._mod_timers[timer_id] = {
            "source_id": source_id,
            "owner": owner,
            "repeat": bool(repeat),
            "seconds": float(seconds),
        }
        return timer_id

    def set_timeout(self, seconds: float, callback):
        return self.set_timer(seconds, callback, repeat=False)

    def set_interval(self, seconds: float, callback):
        return self.set_timer(seconds, callback, repeat=True)

    def cancel_timer(self, timer_id):
        timer_info = self._mod_timers.pop(timer_id, None)
        if not timer_info:
            return False
        try:
            GLib.source_remove(timer_info["source_id"])
        except Exception:
            pass
        return True

    def clear_timer(self, timer_id):
        return self.cancel_timer(timer_id)

    def _make_click_modifier_key(self, modifier_id=None):
        owner = self._current_mod_namespace()
        if modifier_id is None or str(modifier_id).strip() == "":
            modifier_id = f"click_modifier_{self._next_click_modifier_id}"
            self._next_click_modifier_id += 1
        modifier_id = str(modifier_id).strip().lower().replace(" ", "_")
        if not modifier_id:
            raise ValueError("Click modifier ID must be a non-empty string")
        return owner, modifier_id, f"{owner}:{modifier_id}"

    def _normalize_probability(self, chance) -> float:
        try:
            value = float(chance)
        except (TypeError, ValueError):
            value = 0.0
        if value > 1.0:
            value /= 100.0
        return max(0.0, min(1.0, value))

    def _coerce_modifier_number(self, value, default=None):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        if number != number or number in (float("inf"), float("-inf")):
            return default
        return number

    def _set_click_gain(self, gains: dict, currency: str, amount) -> bool:
        currency = str(currency or "").strip()
        if not currency or currency not in self.currencies:
            return False
        number = self._coerce_modifier_number(amount)
        if number is None:
            return False
        old = gains.get(currency, 0.0)
        number = max(0.0, number)
        if number <= 0.0:
            gains.pop(currency, None)
        else:
            gains[currency] = number
        return old != gains.get(currency, 0.0)

    def _sanitize_click_gains(self, gains: dict) -> dict:
        clean = {}
        if not isinstance(gains, dict):
            return clean
        for currency, amount in gains.items():
            currency = str(currency or "").strip()
            if not currency or currency not in self.currencies:
                continue
            number = self._coerce_modifier_number(amount)
            if number is not None and number > 0.0:
                clean[currency] = number
        return clean

    def _click_modifier_targets(self, gains: dict, modifier_info: dict, result: dict):
        target = str(result.get("currency") or modifier_info.get("currency") or "").strip()
        if target:
            return [target]
        return list(gains.keys())

    def register_click_modifier(self, modifier_id=None, callback=None, description="", currency=None):
        """Register a callback that can adjust click gains before they are awarded.

        The callback receives a context dict with game, gains, base_gains, x, y,
        n_press, total_clicks, and vanilla_multiplier. It can return:
            number: multiply targeted gains by this amount
            dict: supports multiplier, add/bonus, amount/set, currency, gains,
                  add_gains/bonus_gains, message, and triggered

        Returning None or False leaves the click unchanged.
        """
        if callable(modifier_id) and callback is None:
            callback = modifier_id
            modifier_id = None
        if not callable(callback):
            raise ValueError("register_click_modifier() requires a callable callback")
        owner, modifier_id, key = self._make_click_modifier_key(modifier_id)
        modifier_currency = str(currency or "").strip()
        self._click_modifiers[key] = {
            "key": key,
            "id": modifier_id,
            "owner": owner,
            "callback": callback,
            "description": str(description or ""),
            "currency": modifier_currency,
        }
        return key

    def add_click_modifier(self, *args, **kwargs):
        return self.register_click_modifier(*args, **kwargs)

    def register_click_multiplier(self, modifier_id=None, chance=1.0, multiplier=2.0, currency=None, description=""):
        """Register a simple chance-based click multiplier.

        Example:
            game.register_click_multiplier("lucky_click", chance=0.1, multiplier=2.0)

        The chance can be 0.1 for 10 percent or 10 for 10 percent.
        """
        if isinstance(modifier_id, (int, float)):
            if chance != 1.0:
                multiplier = chance
            chance = modifier_id
            modifier_id = None
        chance_value = self._normalize_probability(chance)
        multiplier_value = max(0.0, self._coerce_modifier_number(multiplier, 1.0))
        if not description:
            percent = chance_value * 100.0
            description = f"{percent:g}% chance to multiply click gains by {multiplier_value:g}"

        def _click_multiplier_callback(_context):
            if chance_value <= 0.0:
                return None
            if chance_value >= 1.0 or random.random() < chance_value:
                return {
                    "triggered": True,
                    "multiplier": multiplier_value,
                    "message": description,
                }
            return None

        return self.register_click_modifier(
            modifier_id,
            _click_multiplier_callback,
            description=description,
            currency=currency,
        )

    def add_click_multiplier(self, *args, **kwargs):
        return self.register_click_multiplier(*args, **kwargs)

    def unregister_click_modifier(self, modifier_id):
        modifier_key = str(modifier_id or "").strip()
        if not modifier_key:
            return False
        owner = self._current_mod_namespace()
        candidates = [modifier_key]
        if ":" not in modifier_key:
            candidates.append(f"{owner}:{modifier_key.lower().replace(' ', '_')}")
        for candidate in candidates:
            if candidate in self._click_modifiers:
                self._click_modifiers.pop(candidate, None)
                return True
        return False

    def remove_click_modifier(self, modifier_id):
        return self.unregister_click_modifier(modifier_id)

    def get_click_modifiers(self):
        modifiers = []
        for modifier_info in self._click_modifiers.values():
            modifiers.append({
                "key": modifier_info.get("key", ""),
                "id": modifier_info.get("id", ""),
                "owner": modifier_info.get("owner", ""),
                "description": modifier_info.get("description", ""),
                "currency": modifier_info.get("currency", ""),
            })
        return modifiers

    def _register_builtin_click_modifiers(self):
        def _critical_click_modifier(_context):
            owned = self.get_upgrade_count("crit_click")
            if owned <= 0:
                return None
            chance = min(1.0, 0.05 * owned)
            if random.random() >= chance:
                return None
            return {
                "triggered": True,
                "multiplier": 2.0,
                "message": "Critical Clicks triggered",
            }

        self.register_click_modifier(
            "critical_clicks",
            _critical_click_modifier,
            description="Critical Clicks: 5% chance per owned upgrade to double click gains.",
        )

    def _apply_click_modifier_result(self, gains: dict, modifier_info: dict, result, modifier_events: list):
        if result is None or result is False:
            return
        if isinstance(result, (int, float)):
            result = {"triggered": True, "multiplier": float(result)}
        if not isinstance(result, dict):
            return
        if result.get("triggered") is False:
            return

        before = dict(gains)
        targets = self._click_modifier_targets(gains, modifier_info, result)

        explicit_gains = result.get("gains")
        if isinstance(explicit_gains, dict):
            gains.clear()
            gains.update(self._sanitize_click_gains(explicit_gains))

        for field_name in ("add_gains", "bonus_gains"):
            extra_gains = result.get(field_name)
            if not isinstance(extra_gains, dict):
                continue
            for currency, amount in extra_gains.items():
                delta = self._coerce_modifier_number(amount, 0.0)
                if delta:
                    self._set_click_gain(gains, currency, gains.get(str(currency).strip(), 0.0) + delta)

        if "multiplier" in result:
            multiplier = max(0.0, self._coerce_modifier_number(result.get("multiplier"), 1.0))
            for currency in targets:
                self._set_click_gain(gains, currency, gains.get(currency, 0.0) * multiplier)

        add_value = result.get("add", result.get("bonus", None))
        if add_value is not None:
            bonus = self._coerce_modifier_number(add_value, 0.0)
            if bonus:
                add_targets = targets
                if not add_targets and result.get("currency"):
                    add_targets = [str(result.get("currency")).strip()]
                for currency in add_targets:
                    self._set_click_gain(gains, currency, gains.get(currency, 0.0) + bonus)

        if "amount" in result or "set" in result:
            set_value = result.get("amount", result.get("set"))
            for currency in targets:
                self._set_click_gain(gains, currency, set_value)

        changed = gains != before
        if changed or result.get("triggered"):
            event_info = {
                "key": modifier_info.get("key", ""),
                "id": modifier_info.get("id", ""),
                "owner": modifier_info.get("owner", ""),
            }
            if modifier_info.get("description"):
                event_info["description"] = modifier_info["description"]
            if result.get("message"):
                event_info["message"] = str(result.get("message"))
            if result.get("currency") or modifier_info.get("currency"):
                event_info["currency"] = str(result.get("currency") or modifier_info.get("currency"))
            if "multiplier" in result:
                event_info["multiplier"] = self._coerce_modifier_number(result.get("multiplier"), 1.0)
            if add_value is not None:
                event_info["add"] = self._coerce_modifier_number(add_value, 0.0)
            modifier_events.append(event_info)

    def _apply_click_modifiers(self, gains: dict, click_context: dict):
        final_gains = self._sanitize_click_gains(gains)
        base_gains = dict(final_gains)
        modifier_events = []

        for modifier_info in list(self._click_modifiers.values()):
            callback = modifier_info.get("callback")
            if not callable(callback):
                continue
            public_modifier = {
                "key": modifier_info.get("key", ""),
                "id": modifier_info.get("id", ""),
                "owner": modifier_info.get("owner", ""),
                "description": modifier_info.get("description", ""),
                "currency": modifier_info.get("currency", ""),
            }
            context = dict(click_context)
            context.update({
                "game": self,
                "gains": dict(final_gains),
                "base_gains": dict(base_gains),
                "modifier": public_modifier,
            })
            try:
                result = callback(context)
            except Exception as exc:
                print(f"[click modifiers] Modifier '{modifier_info.get('key', '?')}' failed: {exc}")
                continue
            if result is None and isinstance(context.get("gains"), dict) and context["gains"] != final_gains:
                result = {"triggered": True, "gains": context["gains"]}
            self._apply_click_modifier_result(final_gains, modifier_info, result, modifier_events)

        return final_gains, modifier_events

    def mark_save_dirty(self, auto_backup=True):
        self._save_dirty = True
        self._save_dirty_auto_backup = bool(self._save_dirty_auto_backup or auto_backup)
        if self._dirty_save_timer_id is None:
            self._dirty_save_timer_id = GLib.timeout_add(
                SAVE_DIRTY_FLUSH_INTERVAL_MS,
                self._flush_dirty_save_from_timer,
            )

    def _flush_dirty_save_from_timer(self):
        self._dirty_save_timer_id = None
        self.flush_dirty_save()
        return False

    def flush_dirty_save(self, auto_backup=None):
        if not getattr(self, "_save_dirty", False):
            return False
        flush_auto_backup = self._save_dirty_auto_backup if auto_backup is None else bool(auto_backup)
        self._save_dirty = False
        self._save_dirty_auto_backup = False
        self.save_current_progress(auto_backup=flush_auto_backup)
        return True

    def on_close_request(self, *args):
        self.flush_dirty_save(auto_backup=True)
        return False

    def _apply_save_slot_without_presaving_current(self, slot: dict, reason="load", emit_load_event=True):
        self.active_save_id = normalize_save_id(slot["id"])
        self.active_save_name = normalize_save_name(slot.get("name") or self.active_save_id)
        self.active_save_created_at = slot.get("created_at") or current_save_timestamp()
        self.active_save_updated_at = slot.get("updated_at") or self.active_save_created_at
        self.active_save_last_auto_backup_at = slot.get("last_auto_backup_at", 0)
        self.active_save_required_mods = list(slot.get("required_mods", []))
        self.settings["active_save_id"] = self.active_save_id
        save_json(SETTINGS_FILE, self.settings)

        self.state = clone_json_data(slot.get("state", DEFAULT_STATE))
        self.achievements = clone_json_data(slot.get("achievements", DEFAULT_ACHIEVEMENTS))
        self.save_namespaces = clone_json_data(slot.get("mod_data", {}))
        if not isinstance(self.save_namespaces, dict):
            self.save_namespaces = {}
        self._normalize_progress_after_load()
        self.invalidate_rate_cache()
        self.save_current_progress(auto_backup=False)
        self.update_labels()
        self.refresh_upgrades_ui()
        self.refresh_achievements_ui()
        self.refresh_stats_tab(force=True)
        if hasattr(self, "saves_list_box"):
            self.refresh_saves_list()
        if emit_load_event:
            self._emit_event("load", {
                "save_id": self.active_save_id,
                "save_name": self.active_save_name,
                "reason": reason,
            })

    def _switch_to_startup_safe_save(self, skipped_info: dict):
        skipped_id = normalize_save_id(skipped_info.get("save_id"))
        skipped_name = normalize_save_name(skipped_info.get("save_name") or skipped_id)
        missing_text = ", ".join(skipped_info.get("missing_mods", []))
        backup_save_slot(skipped_id, reason="missingmods")

        for slot in list_save_slots():
            save_id = normalize_save_id(slot.get("id"))
            if save_id == skipped_id:
                continue
            if self._save_slot_missing_mods(slot):
                continue
            self._apply_save_slot_without_presaving_current(slot, reason="startup_fallback")
            return (
                f"Skipped save '{skipped_name}' because it requires missing mods: {missing_text}. "
                f"Loaded '{self.active_save_name}' instead."
            )

        recovery_name = "Recovery Save"
        recovery_id = make_save_id(recovery_name)
        recovery_slot = build_save_slot_data(
            recovery_id,
            recovery_name,
            DEFAULT_STATE,
            DEFAULT_ACHIEVEMENTS,
            required_mods=[],
        )
        write_save_slot_data(recovery_slot)
        self._apply_save_slot_without_presaving_current(recovery_slot, reason="startup_recovery")
        return (
            f"Skipped save '{skipped_name}' because it requires missing mods: {missing_text}. "
            "Created a clean Recovery Save instead."
        )

    def save_current_progress(self, auto_backup=True):
        previous = {
            "created_at": getattr(self, "active_save_created_at", current_save_timestamp()),
            "updated_at": getattr(self, "active_save_updated_at", current_save_timestamp()),
            "last_auto_backup_at": getattr(self, "active_save_last_auto_backup_at", 0),
            "required_mods": getattr(self, "active_save_required_mods", []),
            "mod_data": getattr(self, "save_namespaces", {}),
        }
        slot = build_save_slot_data(
            self.active_save_id,
            self.active_save_name,
            self.state,
            self.achievements,
            required_mods=self._current_required_mods(),
            mod_data=self.save_namespaces,
            previous=previous,
        )
        if auto_backup:
            maybe_auto_backup_save_slot(slot)
        write_save_slot_data(slot)
        self.active_save_name = slot["name"]
        self.active_save_created_at = slot["created_at"]
        self.active_save_updated_at = slot["updated_at"]
        self.active_save_last_auto_backup_at = slot.get("last_auto_backup_at", 0)
        self.active_save_required_mods = list(slot.get("required_mods", []))
        save_json(STATE_FILE, self.state)
        save_json(ACHIEVEMENTS_FILE, self.achievements)
        save_legacy_counter(self.state.get("currencies", {}).get("flesh", 0.0))
        if hasattr(self, "_save_dirty"):
            self._save_dirty = False
            self._save_dirty_auto_backup = False
        if hasattr(self, "_event_hooks") and not getattr(self, "_in_save_event", False):
            self._in_save_event = True
            try:
                self._emit_event("save", {
                    "save_id": self.active_save_id,
                    "save_name": self.active_save_name,
                    "slot": slot,
                    "auto_backup": bool(auto_backup),
                })
            finally:
                self._in_save_event = False

    def _normalize_progress_after_load(self):
        if not isinstance(self.state, dict):
            self.state = clone_json_data(DEFAULT_STATE)
        if not isinstance(self.achievements, dict):
            self.achievements = clone_json_data(DEFAULT_ACHIEVEMENTS)
        self.achievements = {
            k: dict(v) if isinstance(v, dict) else v
            for k, v in self.achievements.items()
        }

        for k, v in DEFAULT_STATE.items():
            if k not in self.state:
                self.state[k] = clone_json_data(v)
        if "upgrades_owned" not in self.state or not isinstance(self.state["upgrades_owned"], dict):
            self.state["upgrades_owned"] = {}
        if "flesh" in self.state and not isinstance(self.state.get("currencies"), dict):
            self.state["currencies"] = {"flesh": float(self.state.pop("flesh", 0.0))}
        if "currencies" not in self.state or not isinstance(self.state["currencies"], dict):
            self.state["currencies"] = {"flesh": 0.0}
        self.state["currencies"].setdefault("flesh", 0.0)

        for k, v in DEFAULT_ACHIEVEMENTS.items():
            if k not in self.achievements:
                self.achievements[k] = dict(v)
        self._normalize_achievement_sources()

    def _fresh_save_state(self):
        state = clone_json_data(DEFAULT_STATE)
        state["currencies"] = clone_json_data(DEFAULT_STATE.get("currencies", {"flesh": 0.0}))
        for registry_name in self.currencies:
            state["currencies"].setdefault(registry_name, 0.0)
        state["upgrades_owned"] = {}
        state["total_clicks"] = 0
        return state

    def _fresh_save_achievements(self):
        achievements = clone_json_data(DEFAULT_ACHIEVEMENTS)
        for data in achievements.values():
            if isinstance(data, dict):
                data["unlocked"] = False

        for key, data in self.achievements.items():
            if key in DEFAULT_ACHIEVEMENTS or not isinstance(data, dict):
                continue
            if not self._achievement_is_active(key, data):
                continue
            fresh_data = dict(data)
            fresh_data["unlocked"] = False
            achievements[key] = fresh_data
        return achievements

    def load_save_slot(self, save_id: str, allow_missing_mods=False):
        slot = load_save_slot_data(save_id)
        if not slot:
            return False, "Save could not be loaded."
        if normalize_save_id(slot["id"]) == self.active_save_id:
            return True, f"'{self.active_save_name}' is already active."
        missing_mods = self._save_slot_missing_mods(slot)
        if missing_mods and not allow_missing_mods:
            return False, "Missing required mods: " + ", ".join(missing_mods)

        self.save_current_progress(auto_backup=True)
        backup_save_slot(slot["id"], reason="preload")
        self.active_save_id = normalize_save_id(slot["id"])
        self.active_save_name = normalize_save_name(slot.get("name") or self.active_save_id)
        self.active_save_created_at = slot.get("created_at") or current_save_timestamp()
        self.active_save_updated_at = slot.get("updated_at") or self.active_save_created_at
        self.active_save_last_auto_backup_at = slot.get("last_auto_backup_at", 0)
        self.active_save_required_mods = list(slot.get("required_mods", []))
        self.settings["active_save_id"] = self.active_save_id
        save_json(SETTINGS_FILE, self.settings)

        self.state = clone_json_data(slot.get("state", DEFAULT_STATE))
        self.achievements = clone_json_data(slot.get("achievements", DEFAULT_ACHIEVEMENTS))
        self.save_namespaces = clone_json_data(slot.get("mod_data", {}))
        if not isinstance(self.save_namespaces, dict):
            self.save_namespaces = {}
        self._normalize_progress_after_load()
        self.invalidate_rate_cache()
        self.save_current_progress(auto_backup=False)
        self.update_labels()
        self.refresh_upgrades_ui()
        self.refresh_achievements_ui()
        self.refresh_stats_tab(force=True)
        if hasattr(self, "saves_list_box"):
            self.refresh_saves_list()
        self._emit_event("load", {
            "save_id": self.active_save_id,
            "save_name": self.active_save_name,
            "reason": "manual",
        })
        return True, f"Loaded save '{self.active_save_name}'."

    def create_save_slot(self, name: str):
        self.save_current_progress(auto_backup=True)
        save_name = normalize_save_name(name)
        save_id = make_save_id(save_name)
        fresh_state = self._fresh_save_state()
        fresh_achievements = self._fresh_save_achievements()
        slot = build_save_slot_data(
            save_id,
            save_name,
            fresh_state,
            fresh_achievements,
            required_mods=self._current_required_mods(),
            mod_data={},
        )
        write_save_slot_data(slot)
        self._apply_save_slot_without_presaving_current(slot, reason="create")
        self._emit_event("save_created", {
            "save_id": slot["id"],
            "save_name": slot["name"],
        })
        return slot

    def rename_save_slot(self, save_id: str, new_name: str):
        slot = load_save_slot_data(save_id)
        if not slot:
            return False, "Save could not be renamed."
        slot["name"] = normalize_save_name(new_name)
        slot["updated_at"] = current_save_timestamp()
        backup_save_slot(slot["id"], reason="rename")
        write_save_slot_data(slot)
        if normalize_save_id(save_id) == self.active_save_id:
            self.active_save_name = slot["name"]
            self.active_save_updated_at = slot["updated_at"]
        return True, f"Renamed save to '{slot['name']}'."

    def duplicate_save_slot(self, save_id: str):
        source_id = normalize_save_id(save_id)
        if source_id == self.active_save_id:
            self.save_current_progress(auto_backup=False)
        source = load_save_slot_data(source_id)
        if not source:
            return False, "Save could not be duplicated.", None

        source_name = normalize_save_name(source.get("name") or source_id)
        copy_name = normalize_save_name(f"Copy of {source_name}")
        copy_id = make_save_id(copy_name)
        slot = build_save_slot_data(
            copy_id,
            copy_name,
            source.get("state", DEFAULT_STATE),
            source.get("achievements", DEFAULT_ACHIEVEMENTS),
            required_mods=source.get("required_mods", []),
            mod_data=source.get("mod_data", {}),
        )
        write_save_slot_data(slot)
        return True, f"Duplicated save as '{slot['name']}'.", slot

    def delete_save_slot(self, save_id: str):
        target_id = normalize_save_id(save_id)
        if target_id == self.active_save_id:
            return False, "Load another save before deleting the active one."
        slot = load_save_slot_data(target_id)
        if not slot:
            return False, "Save could not be deleted."

        backup_save_slot(target_id, reason="predelete")
        try:
            os.unlink(save_slot_path(target_id))
        except Exception as exc:
            return False, f"Failed to delete save: {exc}"
        return True, f"Deleted save '{normalize_save_name(slot.get('name') or target_id)}'. A final backup was kept."

    def export_save_slot(self, save_id: str, export_path: str):
        target_id = normalize_save_id(save_id)
        if target_id == self.active_save_id:
            self.save_current_progress(auto_backup=False)
        slot = load_save_slot_data(target_id)
        if not slot:
            return False, "Save could not be exported."
        try:
            write_json_file(normalize_export_path(export_path), slot)
        except Exception as exc:
            return False, f"Failed to export save: {exc}"
        return True, f"Exported save '{normalize_save_name(slot.get('name') or target_id)}'."

    def import_save_slot(self, import_path: str):
        try:
            imported = read_save_slot_file(import_path)
        except Exception as exc:
            return False, f"Failed to import save: {exc}", None

        original_name = normalize_save_name(imported.get("name") or "Imported Save")
        imported_id = normalize_save_id(imported.get("id") or make_save_id(original_name))
        save_name = original_name
        if save_slot_exists(imported_id):
            save_name = normalize_save_name(f"{original_name} Imported")
            imported_id = make_save_id(save_name)

        previous = {
            "created_at": imported.get("created_at"),
            "last_auto_backup_at": imported.get("last_auto_backup_at", 0),
            "required_mods": imported.get("required_mods", []),
        }
        slot = build_save_slot_data(
            imported_id,
            save_name,
            imported.get("state", DEFAULT_STATE),
            imported.get("achievements", DEFAULT_ACHIEVEMENTS),
            required_mods=imported.get("required_mods", []),
            mod_data=imported.get("mod_data", {}),
            previous=previous,
        )
        write_save_slot_data(slot)
        return True, f"Imported save '{slot['name']}'.", slot

    def restore_save_backup(self, save_id: str, backup_path: str, allow_missing_mods=False):
        target_id = normalize_save_id(save_id)
        backup_path = os.path.abspath(str(backup_path or ""))
        allowed_backups = {os.path.abspath(path) for path in list_save_backups(target_id)}
        if backup_path not in allowed_backups:
            return False, "Selected backup could not be found."

        try:
            backup_slot = read_save_slot_file(backup_path)
        except Exception as exc:
            return False, f"Selected backup could not be read: {exc}"

        missing_mods = self._save_slot_missing_mods(backup_slot)
        if target_id == self.active_save_id and missing_mods and not allow_missing_mods:
            return False, "Restored backup needs missing mods: " + ", ".join(missing_mods)

        backup_save_slot(target_id, reason="prerestore")
        try:
            copy_file_bytes(backup_path, save_slot_path(target_id))
        except Exception as exc:
            return False, f"Failed to restore backup: {exc}"

        if target_id == self.active_save_id:
            slot = load_save_slot_data(target_id)
            if not slot:
                return False, "Restored backup could not be loaded."
            self.active_save_name = normalize_save_name(slot.get("name") or target_id)
            self.active_save_created_at = slot.get("created_at") or current_save_timestamp()
            self.active_save_updated_at = slot.get("updated_at") or self.active_save_created_at
            self.active_save_last_auto_backup_at = slot.get("last_auto_backup_at", 0)
            self.active_save_required_mods = list(slot.get("required_mods", []))
            self.state = clone_json_data(slot.get("state", DEFAULT_STATE))
            self.achievements = clone_json_data(slot.get("achievements", DEFAULT_ACHIEVEMENTS))
            self.save_namespaces = clone_json_data(slot.get("mod_data", {}))
            if not isinstance(self.save_namespaces, dict):
                self.save_namespaces = {}
            self._normalize_progress_after_load()
            self.invalidate_rate_cache()
            self.save_current_progress(auto_backup=False)
            self.update_labels()
            self.refresh_upgrades_ui()
            self.refresh_achievements_ui()
            self.refresh_stats_tab(force=True)
            self._emit_event("load", {
                "save_id": self.active_save_id,
                "save_name": self.active_save_name,
                "reason": "restore",
            })
        return True, f"Restored backup {backup_display_name(backup_path)}."

    def restore_latest_save_backup(self, save_id: str):
        latest = latest_save_backup(save_id)
        if not latest:
            return False, "No backup found for this save."
        return self.restore_save_backup(save_id, latest)

    # ---------- ACHIEVEMENT SOURCES ----------

    def _normalize_achievement_sources(self):
        dirty = False

        for key, default in DEFAULT_ACHIEVEMENTS.items():
            data = self.achievements.get(key)
            if not isinstance(data, dict):
                data = dict(default)
                self.achievements[key] = data
                dirty = True
            for field, value in default.items():
                if field not in data:
                    data[field] = value
                    dirty = True
            if data.get("source") != "builtin":
                data["source"] = "builtin"
                dirty = True
            if "mod_id" in data:
                data.pop("mod_id", None)
                dirty = True
            if "mod_name" in data:
                data.pop("mod_name", None)
                dirty = True

        for key, data in list(self.achievements.items()):
            if key in DEFAULT_ACHIEVEMENTS:
                continue
            if not isinstance(data, dict):
                self.achievements.pop(key, None)
                dirty = True
                continue
            if data.get("source") != "mod":
                data["source"] = "mod"
                dirty = True
            if not data.get("mod_id"):
                data["mod_id"] = "__unknown__"
                dirty = True
            if not data.get("mod_name"):
                data["mod_name"] = "Unknown mod"
                dirty = True
            if "unlocked" not in data:
                data["unlocked"] = False
                dirty = True

        if dirty:
            self.save_current_progress(auto_backup=False)

    def _achievement_is_active(self, key: str, data: dict) -> bool:
        if data.get("source") != "mod":
            return True
        mod_id = data.get("mod_id")
        if not mod_id:
            return False
        current = getattr(self, "_current_mod_info", None)
        if current is not None and current.get("id") == mod_id:
            return True
        return mod_id in self.loaded_mod_ids

    def _get_mod_info(self, entry: str, mod_dir: str, manifest: dict) -> dict:
        mod_name = manifest.get("name") or manifest.get("title") or entry
        game_title = manifest.get("game_title")
        if not isinstance(game_title, str):
            game_title = ""
        dependencies = normalize_mod_dependencies(
            manifest.get("dependencies")
            or manifest.get("depends")
            or manifest.get("requires_mods")
            or manifest.get("required_mods")
        )
        return {
            "id": entry,
            "name": str(mod_name),
            "version": str(manifest.get("version") or ""),
            "author": str(manifest.get("author") or ""),
            "description": str(manifest.get("description") or ""),
            "dependencies": dependencies,
            "game_title": game_title.strip(),
            "path": mod_dir,
        }

    def _read_mod_enabled(self, mod_dir: str):
        enabled_path = os.path.join(mod_dir, "enabled.txt")
        if not os.path.exists(enabled_path):
            try:
                with open(enabled_path, "w", encoding="utf-8") as f:
                    f.write("true\n")
            except Exception:
                pass

        try:
            with open(enabled_path, "r", encoding="utf-8") as f:
                text = f.read().strip().lower()
        except Exception:
            text = "true"

        return "false" not in text, enabled_path

    def _write_mod_enabled(self, mod_info: dict, enabled: bool):
        with open(mod_info["enabled_path"], "w", encoding="utf-8") as f:
            f.write("true\n" if enabled else "false\n")
        mod_info["enabled"] = enabled

    def _get_security_dismissals(self) -> dict:
        dismissals = self.settings.get("dismissed_mod_security_warnings")
        if not isinstance(dismissals, dict):
            dismissals = {}
            self.settings["dismissed_mod_security_warnings"] = dismissals
        return dismissals

    def _is_mod_security_warning_dismissed(self, mod_key: str, fingerprint: str) -> bool:
        return self._get_security_dismissals().get(mod_key) == fingerprint

    def _dismiss_mod_security_warning(self, mod_info: dict):
        dismissals = self._get_security_dismissals()
        dismissals[mod_info["title_key"]] = mod_info.get("security_fingerprint", "")
        save_json(SETTINGS_FILE, self.settings)
        mod_info["security_dismissed"] = True
        mod_info["security_blocked"] = False

    def _apply_selected_game_title(self):
        selected_mod_key = str(self.settings.get("game_title_mod_key") or "")
        selected_mod = next(
            (
                mod_info
                for mod_info in self.installed_mods
                if mod_info.get("title_key") == selected_mod_key
                and mod_info.get("enabled")
                and not mod_info.get("security_blocked")
                and mod_info.get("game_title")
            ),
            None,
        )

        if selected_mod is None:
            self.current_game_title = DEFAULT_GAME_TITLE
            if selected_mod_key:
                self.settings["game_title_mod_key"] = ""
                save_json(SETTINGS_FILE, self.settings)
        else:
            self.current_game_title = selected_mod["game_title"]

        self.set_title(self.current_game_title)

    # ---------- MOD LOADING ----------

    def load_mods(self):
        """Load folder-based mods.

        Each mod is a subfolder containing:
            mod.py          — must define register(game)
            manifest.json   — optional metadata (name, version, description)
            assets/         — optional assets folder

        Inside mod.py, MOD_DIR is pre-set to the mod's folder path so you can
        reference assets like:  os.path.join(MOD_DIR, "assets", "custom.png")
        """
        self.installed_mods = []
        self.loaded_mod_ids = set()
        for mods_root in (SYSTEM_MODS_DIR, USER_MODS_DIR):
            if not os.path.isdir(mods_root):
                continue
            for entry in sorted(os.listdir(mods_root)):
                mod_dir = os.path.join(mods_root, entry)
                if not os.path.isdir(mod_dir):
                    continue

                mod_py = os.path.join(mod_dir, "mod.py")
                if not os.path.exists(mod_py):
                    continue

                manifest = {}
                manifest_path = os.path.join(mod_dir, "manifest.json")
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, "r", encoding="utf-8") as f:
                            manifest = json.load(f)
                    except Exception:
                        pass

                mod_info = self._get_mod_info(entry, mod_dir, manifest)
                enabled, enabled_path = self._read_mod_enabled(mod_dir)
                mod_source = "system" if mods_root == SYSTEM_MODS_DIR else "user"
                mod_key = f"{mod_source}:{entry}"
                security_result = scan_mod_security(mod_dir)
                security_level = int(security_result.get("level", 0))
                security_fingerprint = str(security_result.get("fingerprint", ""))
                security_dismissed = (
                    security_level > 0
                    and self._is_mod_security_warning_dismissed(mod_key, security_fingerprint)
                )
                mod_info["enabled"] = enabled
                mod_info["enabled_path"] = enabled_path
                mod_info["security_level"] = security_level
                mod_info["security_label"] = security_result.get("label", MOD_SECURITY_LEVEL_NAMES.get(security_level, "Suspicious"))
                mod_info["security_reasons"] = list(security_result.get("reasons", []))
                mod_info["security_fingerprint"] = security_fingerprint
                mod_info["security_dismissed"] = security_dismissed
                mod_info["security_blocked"] = security_level > 0 and not security_dismissed
                mod_info["root"] = mods_root
                mod_info["title_key"] = mod_key
                if mod_info["security_blocked"]:
                    print(f"[mods] Paused '{entry}' for a Level {security_level} security warning:")
                    for reason in mod_info["security_reasons"][:5]:
                        print(f"[mods]   - {reason}")
                    if len(mod_info["security_reasons"]) > 5:
                        print(f"[mods]   - and {len(mod_info['security_reasons']) - 5} more")
                    self.installed_mods.append(mod_info)
                    continue
                if not enabled:
                    self.installed_mods.append(mod_info)
                    continue

                missing_dependencies = self._mod_dependencies_missing(mod_info)
                if missing_dependencies:
                    mod_info["dependency_blocked"] = True
                    mod_info["dependency_missing"] = missing_dependencies
                    print(f"[mods] Paused '{entry}' because required mods are missing: {', '.join(missing_dependencies)}")
                    self.installed_mods.append(mod_info)
                    continue

                self._current_mod_info = mod_info
                try:
                    loader = importlib.machinery.SourceFileLoader(entry, mod_py)
                    spec   = importlib.util.spec_from_loader(loader.name, loader)
                    mod    = importlib.util.module_from_spec(spec)
                    mod.MOD_DIR  = mod_dir
                    mod.MANIFEST = manifest
                    loader.exec_module(mod)
                    if hasattr(mod, "register"):
                        mod.register(self)
                    self.loaded_mod_ids.add(mod_info["id"])
                    self.installed_mods.append(mod_info)
                except ModDependencyError as e:
                    mod_info["dependency_blocked"] = True
                    mod_info["dependency_missing"] = list(getattr(e, "missing", []) or [str(e)])
                    print(f"[mods] Paused '{entry}' because required mods are missing: {', '.join(mod_info['dependency_missing'])}")
                    self.installed_mods.append(mod_info)
                except Exception as e:
                    print(f"[mods] Failed to load '{entry}': {e}")
                finally:
                    self._current_mod_info = None

        self._apply_selected_game_title()
        self.refresh_upgrades_ui()
        self.refresh_achievements_ui()

    # ---------- MOD API ----------

    def get_save_namespace(self, namespace=None):
        namespace = self._current_mod_namespace(namespace)
        data = self.save_namespaces.setdefault(namespace, {})
        if not isinstance(data, dict):
            data = {}
            self.save_namespaces[namespace] = data
        return data

    def set_save_namespace(self, namespace=None, data=None):
        if data is None and isinstance(namespace, dict):
            data = namespace
            namespace = None
        namespace = self._current_mod_namespace(namespace)
        self.save_namespaces[namespace] = clone_json_data(data if isinstance(data, dict) else {})
        self.mark_save_dirty(auto_backup=False)

    def get_save_data(self, namespace=None):
        return self.get_save_namespace(namespace)

    def set_save_data(self, data, namespace=None):
        self.set_save_namespace(namespace, data)

    def get_save_value(self, key: str, default=None, namespace=None):
        return self.get_save_namespace(namespace).get(key, default)

    def set_save_value(self, key: str, value, namespace=None):
        data = self.get_save_namespace(namespace)
        data[str(key)] = clone_json_data(value)
        self.mark_save_dirty(auto_backup=False)
        return value

    def delete_save_value(self, key: str, namespace=None):
        data = self.get_save_namespace(namespace)
        if str(key) in data:
            data.pop(str(key), None)
            self.mark_save_dirty(auto_backup=False)
            return True
        return False

    def get_mod_settings(self, namespace=None):
        namespace = self._current_mod_namespace(namespace)
        all_settings = self.settings.setdefault("mod_settings", {})
        if not isinstance(all_settings, dict):
            all_settings = {}
            self.settings["mod_settings"] = all_settings
        data = all_settings.setdefault(namespace, {})
        if not isinstance(data, dict):
            data = {}
            all_settings[namespace] = data
        return data

    def get_mod_setting(self, key: str, default=None, namespace=None):
        return self.get_mod_settings(namespace).get(key, default)

    def set_mod_setting(self, key: str, value, namespace=None):
        data = self.get_mod_settings(namespace)
        data[str(key)] = clone_json_data(value)
        save_json(SETTINGS_FILE, self.settings)
        return value

    def delete_mod_setting(self, key: str, namespace=None):
        data = self.get_mod_settings(namespace)
        if str(key) in data:
            data.pop(str(key), None)
            save_json(SETTINGS_FILE, self.settings)
            return True
        return False

    def get_loaded_mods(self):
        return [dict(mod_info) for mod_info in self.installed_mods if mod_info.get("id") in self.loaded_mod_ids]

    def get_installed_mods(self):
        return [dict(mod_info) for mod_info in self.installed_mods]

    def get_mod_info(self, mod_id: str):
        mod_id = normalize_mod_id(mod_id)
        for mod_info in self.installed_mods:
            if mod_info.get("id") == mod_id:
                return dict(mod_info)
        return None

    def has_mod(self, mod_id: str, min_version: str = "") -> bool:
        mod_id = normalize_mod_id(mod_id)
        for mod_info in self.installed_mods:
            if mod_info.get("id") != mod_id or mod_id not in self.loaded_mod_ids:
                continue
            return version_meets_requirement(mod_info.get("version", ""), min_version)
        return False

    def require_mod(self, mod_id: str, min_version: str = ""):
        if self.has_mod(mod_id, min_version):
            return True
        requirement = mod_id if not min_version else f"{mod_id} >= {min_version}"
        raise ModDependencyError(f"Missing required mod: {requirement}", [requirement])

    def _mod_dependencies_missing(self, mod_info: dict):
        missing = []
        for dep in mod_info.get("dependencies", []) or []:
            if dep.get("optional"):
                continue
            dep_id = normalize_mod_id(dep.get("id"))
            min_version = str(dep.get("version") or "")
            if not self.has_mod(dep_id, min_version):
                missing.append(dep_id if not min_version else f"{dep_id} >= {min_version}")
        return missing

    def register_console_command(self, name: str, callback, help_text="", aliases=None):
        command_name = str(name or "").strip().lower().lstrip("/")
        if not command_name or not callable(callback):
            raise ValueError("register_console_command() requires a name and callable callback")
        alias_list = []
        for alias in aliases or []:
            alias_name = str(alias or "").strip().lower().lstrip("/")
            if alias_name and alias_name != command_name and alias_name not in alias_list:
                alias_list.append(alias_name)
        owner = self._current_mod_namespace()
        command_info = {
            "name": command_name,
            "callback": callback,
            "help": str(help_text or ""),
            "aliases": alias_list,
            "owner": owner,
        }
        self.console_commands[command_name] = command_info
        for alias in alias_list:
            self.console_aliases[alias] = command_name
        return command_name

    def unregister_console_command(self, name: str):
        command_name = str(name or "").strip().lower().lstrip("/")
        command_name = self.console_aliases.get(command_name, command_name)
        command_info = self.console_commands.pop(command_name, None)
        if not command_info:
            return False
        for alias in command_info.get("aliases", []):
            if self.console_aliases.get(alias) == command_name:
                self.console_aliases.pop(alias, None)
        return True

    def register_currency(self, registry_name: str, display_name: str):
        """Register a new currency. Safe to call if it already exists."""
        if registry_name not in self.currencies:
            self.currencies[registry_name] = {"display_name": display_name}
        if registry_name not in self.state["currencies"]:
            self.state["currencies"][registry_name] = 0.0
        self.invalidate_rate_cache()
        self.mark_save_dirty(auto_backup=False)

    def register_upgrade(self, uid: str, data: dict):
        """Add or update an upgrade in the registry."""
        if uid in self.upgrades:
            self.upgrades[uid].update(data)
        else:
            self.upgrades[uid] = data
        self.invalidate_rate_cache()

    def register_achievement(self, key: str, data: dict):
        """Add or update an achievement."""
        existing = self.achievements.get(key, {})
        if not isinstance(existing, dict):
            existing = {}

        merged = dict(existing)
        merged.update(dict(data))
        if "unlocked" not in data:
            merged["unlocked"] = bool(existing.get("unlocked", False))

        mod_info = self._current_mod_info
        if mod_info is not None:
            merged["source"] = "mod"
            merged["mod_id"] = mod_info["id"]
            merged["mod_name"] = mod_info["name"]
        elif key in DEFAULT_ACHIEVEMENTS:
            merged["source"] = "builtin"
            merged.pop("mod_id", None)
            merged.pop("mod_name", None)
        else:
            merged.setdefault("source", "mod")
            merged.setdefault("mod_id", "__unknown__")
            merged.setdefault("mod_name", "Unknown mod")

        self.achievements[key] = merged
        self.mark_save_dirty(auto_backup=False)

    def set_flesh_image(self, path: str):
        """Override the clickable image. Call from register() before build_ui runs."""
        self.flesh_image_path = path

    def set_click_sound(self, path: str):
        """Override the click sound. Must be a .wav file.
        Can be called at any time — the new sound takes effect on the next click.

        Example:
            game.set_click_sound(os.path.join(MOD_DIR, "assets", "pop.wav"))
        """
        self.click_sound_path = path
        # pre-load into pygame cache if available so first click has no delay
        if self._pygame_mixer_ok and os.path.exists(path):
            try:
                import pygame.mixer
                if path not in self._sound_cache:
                    self._sound_cache[path] = pygame.mixer.Sound(path)
            except Exception:
                pass

    def set_game_title(self, title: str):
        """Offer a custom window title from the currently loading mod.

        Call this from register(game). The player can then select the title
        using the switch beside the mod in Settings.
        """
        mod_info = self._current_mod_info
        if mod_info is None:
            raise RuntimeError("set_game_title() must be called from a mod's register() function")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Game title must be a non-empty string")
        mod_info["game_title"] = title.strip()

    def add_tab(self, tab_id: str, label: str, page_box=None):
        """Add a custom tab to the notebook.

        tab_id   — unique string ID used to reference this tab in add_tab_button()
        label    — text shown on the tab
        page_box — optional Gtk.Box to use as the page. If None, a plain vertical
                   Box with 6px spacing is created and returned so you can append
                   widgets to it.

        Returns the Gtk.Box that is the tab's page, so you can populate it:

            box = game.add_tab("mystats", "My Stats")
            box.append(Gtk.Label(label="Hello from my mod!"))

        Can be called before or after build_ui — if the UI is already built the
        tab is added immediately, otherwise it is queued and added at build time.
        """
        if page_box is None:
            page_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            page_box.set_margin_top(4)
            page_box.set_margin_bottom(4)
            page_box.set_margin_start(4)
            page_box.set_margin_end(4)

        if hasattr(self, "notebook"):
            # UI already built — add immediately
            self.notebook.append_page(page_box, Gtk.Label(label=label))
            self._tab_pages[tab_id] = page_box
            # flush any buttons that were queued for this tab
            for btn_label, callback in self._pending_buttons.pop(tab_id, []):
                btn = Gtk.Button(label=btn_label)
                btn.connect("clicked", lambda b, cb=callback: cb(b))
                page_box.append(btn)
        else:
            self._pending_tabs.append((tab_id, label, page_box))

        return page_box

    def add_tab_button(self, tab_id: str, label: str, callback):
        """Add a button to an existing tab (built-in or mod-created).

        tab_id   — ID of the target tab. Built-in IDs are:
                   "upgrades", "achievements", "leaderboard", "saves",
                   "settings", "console", "stats"
                   Mod tab IDs are whatever string you passed to add_tab().
        label    — button text
        callback — function called when clicked. Receives the Gtk.Button as its
                   only argument.

        Can be called before or after build_ui — if the tab already exists the
        button is added immediately, otherwise it is queued.

        Example:
            def my_callback(button):
                print("clicked!")

            game.add_tab_button("settings", "Reset Stats", my_callback)
        """
        page = self._tab_pages.get(tab_id)
        if page is not None:
            btn = Gtk.Button(label=label)
            btn.connect("clicked", lambda b, cb=callback: cb(b))
            page.append(btn)
        else:
            self._pending_buttons.setdefault(tab_id, []).append((label, callback))

    def add_button(self, tab_id: str, label: str, callback):
        """Compatibility alias for add_tab_button()."""
        self.add_tab_button(tab_id, label, callback)

    def disable_vanilla_achievements(self):
        """Remove all built-in achievements. Mod achievements registered after
        this call are unaffected."""
        for key in list(DEFAULT_ACHIEVEMENTS.keys()):
            self.achievements.pop(key, None)

    def disable_vanilla_upgrades(self):
        """Remove all built-in upgrades. Mod upgrades registered after
        this call are unaffected."""
        for key in list(BASE_UPGRADES.keys()):
            self.upgrades.pop(key, None)
        self.invalidate_rate_cache()

    def disable_vanilla(self, primary_currency: str):
        """Remove all built-in upgrades, achievements, and the flesh currency UI,
        and set a new primary currency.

        Call this before registering your own currency/upgrades/achievements.
        The primary_currency you pass must be registered with register_currency()
        either before or after this call — it just needs to exist by the time
        the UI is built.

        Example:
            def register(game):
                game.register_currency("souls", "Souls")
                game.disable_vanilla("souls")
                game.register_upgrade("soul_harvester", { ... })
        """
        self.disable_vanilla_upgrades()
        self.disable_vanilla_achievements()

        # hide vanilla flesh while keeping the saved amount intact for later
        self.currencies.pop("flesh", None)

        # point the primary currency at the mod's replacement
        self.primary_currency = primary_currency
        self.invalidate_rate_cache()

    # ---------- UI BUILD ----------

    def build_ui(self):
        root = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        root.set_wide_handle(True)
        self.set_child(root)

        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        left_box.set_margin_top(12)
        left_box.set_margin_bottom(12)
        left_box.set_margin_start(12)
        left_box.set_margin_end(6)

        self.picture = Gtk.Picture()
        self.picture.set_can_shrink(True)
        self.picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        self.picture.add_css_class("flesh-picture")
        self.picture.set_vexpand(True)
        self.picture.set_hexpand(True)

        click_gesture = Gtk.GestureClick()
        click_gesture.connect("released", self.on_click)
        self.picture.add_controller(click_gesture)

        left_box.append(self.picture)
        self.load_flesh_image()

        # dynamic stats area — rebuilt every tick
        self.stats_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self._currency_amount_labels = {}
        self._currency_cps_labels = {}
        left_box.append(self.stats_box)

        root.set_start_child(left_box)

        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        right_box.set_margin_top(12)
        right_box.set_margin_bottom(12)
        right_box.set_margin_start(6)
        right_box.set_margin_end(12)

        self.notebook = Gtk.Notebook()
        right_box.append(self.notebook)

        self.upgrades_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.build_upgrades_page()
        self.notebook.append_page(self.upgrades_page, Gtk.Label(label="Upgrades"))
        self._tab_pages["upgrades"] = self.upgrades_page

        self.achievements_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.build_achievements_page()
        self.notebook.append_page(self.achievements_page, Gtk.Label(label="Achievements"))
        self._tab_pages["achievements"] = self.achievements_page

        self.leaderboard_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.build_leaderboard_page()
        self.notebook.append_page(self.leaderboard_page, Gtk.Label(label="Leaderboard"))
        self._tab_pages["leaderboard"] = self.leaderboard_page

        self.saves_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.build_saves_page()
        self.notebook.append_page(self.saves_page, Gtk.Label(label="Saves"))
        self._tab_pages["saves"] = self.saves_page

        self.settings_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.build_settings_page()
        self.notebook.append_page(self.settings_page, Gtk.Label(label="Settings"))
        self._tab_pages["settings"] = self.settings_page

        self.console_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.build_console_page()
        self.notebook.append_page(self.console_page, Gtk.Label(label="Console"))
        self._tab_pages["console"] = self.console_page

        self.stats_tab_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.build_stats_tab_page()
        self.notebook.append_page(self.stats_tab_page, Gtk.Label(label="Stats"))
        self._tab_pages["stats"] = self.stats_tab_page

        # flush mod tabs queued before build_ui ran
        for tab_id, label, page_box in self._pending_tabs:
            self.notebook.append_page(page_box, Gtk.Label(label=label))
            self._tab_pages[tab_id] = page_box

        # flush mod buttons queued before build_ui ran
        for tab_id, buttons in self._pending_buttons.items():
            page = self._tab_pages.get(tab_id)
            if page is None:
                continue
            for btn_label, callback in buttons:
                btn = Gtk.Button(label=btn_label)
                btn.connect("clicked", lambda b, cb=callback: cb(b))
                page.append(btn)

        self.refresh_upgrades_ui()
        self.refresh_achievements_ui()
        root.set_end_child(right_box)

    def build_upgrades_page(self):
        self.upgrades_page.set_margin_top(4)
        self.upgrades_page.set_margin_bottom(4)
        self.upgrades_page.set_margin_start(4)
        self.upgrades_page.set_margin_end(4)

        # Search bar
        self.upgrade_search = Gtk.SearchEntry()
        self.upgrade_search.set_placeholder_text("Search upgrades\u2026")
        self.upgrade_search.connect("search-changed", self._on_upgrade_search_changed)
        self.upgrades_page.append(self.upgrade_search)

        # Filter buttons
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.upgrade_filter_buttons = {}

        def make_filter_button(label, key):
            btn = Gtk.Button(label=label)
            btn.connect("clicked", self.on_filter_clicked, key)
            self.upgrade_filter_buttons[key] = btn
            filter_box.append(btn)

        make_filter_button("All",   "all")
        make_filter_button("Click", "click")
        make_filter_button("Auto",  "auto")

        self.upgrades_page.append(filter_box)

        self.upgrades_listbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.current_filter   = "all"
        self._upgrade_search_text = ""

        # Keep a reference to the ScrolledWindow so we never lose scroll position
        self._upgrades_scroll = Gtk.ScrolledWindow()
        self._upgrades_scroll.set_child(self.upgrades_listbox)
        self._upgrades_scroll.set_vexpand(True)
        self.upgrades_page.append(self._upgrades_scroll)

        # Pre-build all upgrade rows once -- stored in _upgrade_rows by uid
        self._upgrade_rows = {}
        self._build_all_upgrade_rows()

    def build_achievements_page(self):
        self.achievements_page.set_margin_top(4)
        self.achievements_page.set_margin_bottom(4)
        self.achievements_page.set_margin_start(4)
        self.achievements_page.set_margin_end(4)

        self.achievements_listbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scroll = Gtk.ScrolledWindow()
        scroll.set_child(self.achievements_listbox)
        scroll.set_vexpand(True)
        self.achievements_page.append(scroll)

    def build_saves_page(self):
        self.saves_page.set_margin_top(4)
        self.saves_page.set_margin_bottom(4)
        self.saves_page.set_margin_start(4)
        self.saves_page.set_margin_end(4)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.new_save_entry = Gtk.Entry()
        self.new_save_entry.set_placeholder_text("Save name")
        self.new_save_entry.set_hexpand(True)
        controls.append(self.new_save_entry)

        create_btn = Gtk.Button(label="Create save")
        create_btn.connect("clicked", self.on_create_save_clicked)
        controls.append(create_btn)

        save_btn = Gtk.Button(label="Save active")
        save_btn.connect("clicked", self.on_save_active_clicked)
        controls.append(save_btn)

        backup_btn = Gtk.Button(label="Backup active")
        backup_btn.connect("clicked", self.on_backup_active_save_clicked)
        controls.append(backup_btn)

        import_btn = Gtk.Button(label="Import save")
        import_btn.connect("clicked", self.on_import_save_clicked)
        controls.append(import_btn)

        self.saves_page.append(controls)

        self.saves_info_label = Gtk.Label(label="", xalign=0)
        self.saves_info_label.set_wrap(True)
        self.saves_page.append(self.saves_info_label)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        self.saves_page.append(scrolled)

        self.saves_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scrolled.set_child(self.saves_list_box)
        self.refresh_saves_list()

    def refresh_saves_list(self):
        if not hasattr(self, "saves_list_box"):
            return
        self.clear_box_children(self.saves_list_box)

        slots = list_save_slots()
        if not slots:
            self.saves_list_box.append(Gtk.Label(label="No saves found.", xalign=0))
            return

        for slot in slots:
            save_id = normalize_save_id(slot.get("id"))
            active = save_id == self.active_save_id
            missing_mods = self._save_slot_missing_mods(slot)
            title = normalize_save_name(slot.get("name") or save_id)
            if active and missing_mods:
                title += " (Active, missing mods)"
            elif active:
                title += " (Active)"
            elif missing_mods:
                title += " (Missing mods)"

            expander = Gtk.Expander(label=title)
            expander.set_hexpand(True)

            details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            details.set_margin_top(4)
            details.set_margin_bottom(4)
            details.set_margin_start(12)
            details.set_margin_end(4)

            updated = slot.get("updated_at") or "Unknown"
            created = slot.get("created_at") or "Unknown"
            details.append(Gtk.Label(label=f"Updated: {updated}", xalign=0))
            details.append(Gtk.Label(label=f"Created: {created}", xalign=0))

            required_mods = slot.get("required_mods") or []
            if required_mods:
                required_names = []
                for mod_req in required_mods:
                    if isinstance(mod_req, dict):
                        name = mod_req.get("name") or mod_req.get("id") or "Unknown mod"
                        version = mod_req.get("version") or ""
                        required_names.append(f"{name} {version}".strip())
                    else:
                        required_names.append(str(mod_req))
                required_label = Gtk.Label(label="Required mods: " + ", ".join(required_names), xalign=0)
                required_label.set_wrap(True)
                details.append(required_label)
            else:
                details.append(Gtk.Label(label="Required mods: None", xalign=0))

            if missing_mods:
                missing_label = Gtk.Label(label="Missing mods: " + ", ".join(missing_mods), xalign=0)
                missing_label.set_wrap(True)
                missing_label.add_css_class("badge-locked")
                details.append(missing_label)

            backups = list_save_backups(save_id)
            backup_count = len(backups)
            details.append(Gtk.Label(label=f"Backups: {backup_count}", xalign=0))

            rename_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            name_entry = Gtk.Entry()
            name_entry.set_text(normalize_save_name(slot.get("name") or save_id))
            name_entry.set_hexpand(True)
            rename_row.append(name_entry)
            rename_btn = Gtk.Button(label="Rename")
            rename_btn.connect("clicked", self.on_rename_save_clicked, save_id, name_entry)
            rename_row.append(rename_btn)
            details.append(rename_row)

            button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            load_btn = Gtk.Button(label="Load")
            load_btn.set_sensitive(not active)
            if missing_mods:
                load_btn.set_tooltip_text("This save has missing required mods. You will be warned before loading.")
            load_btn.connect("clicked", self.on_load_save_clicked, save_id)
            button_row.append(load_btn)

            backup_btn = Gtk.Button(label="Backup")
            backup_btn.connect("clicked", self.on_backup_save_clicked, save_id)
            button_row.append(backup_btn)

            duplicate_btn = Gtk.Button(label="Duplicate")
            duplicate_btn.connect("clicked", self.on_duplicate_save_clicked, save_id)
            button_row.append(duplicate_btn)

            export_btn = Gtk.Button(label="Export")
            export_btn.connect("clicked", self.on_export_save_clicked, save_id)
            button_row.append(export_btn)

            delete_btn = Gtk.Button(label="Delete")
            delete_btn.set_sensitive(not active)
            if active:
                delete_btn.set_tooltip_text("Load another save before deleting this one.")
            delete_btn.connect("clicked", self.on_delete_save_clicked, save_id)
            button_row.append(delete_btn)

            details.append(button_row)

            backup_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            backup_row.append(Gtk.Label(label="Restore backup:", xalign=0))
            backup_combo = Gtk.ComboBoxText()
            backup_combo.set_hexpand(True)
            for backup_path in backups:
                backup_combo.append_text(backup_display_name(backup_path))
            if backups:
                backup_combo.set_active(0)
            backup_combo.set_sensitive(backup_count > 0)
            backup_row.append(backup_combo)

            restore_btn = Gtk.Button(label="Restore selected")
            restore_btn.set_sensitive(backup_count > 0)
            restore_btn.connect(
                "clicked",
                self.on_restore_selected_save_backup_clicked,
                save_id,
                backup_combo,
                backups,
            )
            backup_row.append(restore_btn)
            details.append(backup_row)

            expander.set_child(details)
            self.saves_list_box.append(expander)

    def on_create_save_clicked(self, button):
        name = self.new_save_entry.get_text().strip() if hasattr(self, "new_save_entry") else ""
        slot = self.create_save_slot(name or "New Save")
        self.saves_info_label.set_text(f"Created fresh save '{slot['name']}'.")
        self.new_save_entry.set_text("")
        self.refresh_saves_list()

    def on_save_active_clicked(self, button):
        self.save_current_progress(auto_backup=True)
        self.saves_info_label.set_text(f"Saved '{self.active_save_name}'.")
        self.refresh_saves_list()

    def on_backup_active_save_clicked(self, button):
        self.save_current_progress(auto_backup=False)
        backup_path = backup_save_slot(self.active_save_id, reason="manual")
        if backup_path:
            self.saves_info_label.set_text(f"Backed up '{self.active_save_name}'.")
        else:
            self.saves_info_label.set_text("Backup failed.")
        self.refresh_saves_list()

    def on_load_save_clicked(self, button, save_id: str):
        slot = load_save_slot_data(save_id)
        if not slot:
            self.saves_info_label.set_text("Save could not be loaded.")
            self.refresh_saves_list()
            return
        missing_mods = self._save_slot_missing_mods(slot)
        if missing_mods:
            self.show_missing_mods_load_dialog(save_id, missing_mods)
            return
        ok, message = self.load_save_slot(save_id)
        self.saves_info_label.set_text(message)
        self.refresh_saves_list()

    def show_startup_missing_mods_load_dialog(self, missing_info: dict):
        dialog = Gtk.Dialog()
        dialog.set_title("Missing required mods")
        dialog.set_transient_for(self)
        dialog.set_modal(True)
        content = dialog.get_content_area()
        save_name = normalize_save_name(missing_info.get("save_name") or missing_info.get("save_id"))
        missing_mods = missing_info.get("missing_mods", [])
        warning_label = Gtk.Label(
            label=(
                f"Save '{save_name}' requires missing mods: "
                f"{', '.join(missing_mods)}, loading may cause corruption or loss of data. "
                "Load anyway?"
            ),
            xalign=0,
        )
        warning_label.set_wrap(True)
        warning_label.set_margin_top(12)
        warning_label.set_margin_bottom(12)
        warning_label.set_margin_start(12)
        warning_label.set_margin_end(12)
        content.append(warning_label)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Load anyway", Gtk.ResponseType.ACCEPT)
        dialog.connect("response", self.on_startup_missing_mods_load_response, missing_info)
        dialog.present()

    def on_startup_missing_mods_load_response(self, dialog, response, missing_info: dict):
        try:
            if response == Gtk.ResponseType.ACCEPT:
                message = (
                    f"Loaded '{normalize_save_name(missing_info.get('save_name') or missing_info.get('save_id'))}' "
                    "without its required mods."
                )
                self._emit_event("load", {
                    "save_id": self.active_save_id,
                    "save_name": self.active_save_name,
                    "reason": "startup_missing_accepted",
                    "missing_mods": list(missing_info.get("missing_mods", [])),
                })
            else:
                message = self._switch_to_startup_safe_save(missing_info)
            if hasattr(self, "saves_info_label"):
                self.saves_info_label.set_text(message)
            if hasattr(self, "saves_list_box"):
                self.refresh_saves_list()
        finally:
            dialog.destroy()
            self.start_runtime_services()

    def show_missing_mods_load_dialog(self, save_id: str, missing_mods):
        dialog = Gtk.Dialog()
        dialog.set_title("Missing required mods")
        dialog.set_transient_for(self)
        dialog.set_modal(True)
        content = dialog.get_content_area()
        warning_label = Gtk.Label(
            label=(
                "This save file requires missing mods: "
                f"{', '.join(missing_mods)}, loading may cause corruption or loss of data. "
                "Load anyway?"
            ),
            xalign=0,
        )
        warning_label.set_wrap(True)
        warning_label.set_margin_top(12)
        warning_label.set_margin_bottom(12)
        warning_label.set_margin_start(12)
        warning_label.set_margin_end(12)
        content.append(warning_label)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Load anyway", Gtk.ResponseType.ACCEPT)
        dialog.connect("response", self.on_missing_mods_load_response, save_id)
        dialog.present()

    def on_missing_mods_load_response(self, dialog, response, save_id: str):
        try:
            if response == Gtk.ResponseType.ACCEPT:
                ok, message = self.load_save_slot(save_id, allow_missing_mods=True)
                self.saves_info_label.set_text(message)
                self.refresh_saves_list()
        finally:
            dialog.destroy()

    def on_rename_save_clicked(self, button, save_id: str, name_entry):
        ok, message = self.rename_save_slot(save_id, name_entry.get_text())
        self.saves_info_label.set_text(message)
        self.refresh_saves_list()

    def on_backup_save_clicked(self, button, save_id: str):
        if normalize_save_id(save_id) == self.active_save_id:
            self.save_current_progress(auto_backup=False)
        slot = load_save_slot_data(save_id)
        backup_path = backup_save_slot(save_id, reason="manual")
        if backup_path:
            save_name = normalize_save_name(slot.get("name") if slot else save_id)
            self.saves_info_label.set_text(f"Backed up '{save_name}'.")
        else:
            self.saves_info_label.set_text("Backup failed.")
        self.refresh_saves_list()

    def on_duplicate_save_clicked(self, button, save_id: str):
        ok, message, slot = self.duplicate_save_slot(save_id)
        self.saves_info_label.set_text(message)
        self.refresh_saves_list()

    def on_delete_save_clicked(self, button, save_id: str):
        slot = load_save_slot_data(save_id)
        if not slot:
            self.saves_info_label.set_text("Save could not be deleted.")
            self.refresh_saves_list()
            return
        dialog = Gtk.Dialog()
        dialog.set_title("Delete save")
        dialog.set_transient_for(self)
        dialog.set_modal(True)
        content = dialog.get_content_area()
        warning_label = Gtk.Label(
            label=(
                f"Delete save '{normalize_save_name(slot.get('name') or save_id)}'? "
                "A final backup will be kept, but the save will disappear from the list."
            ),
            xalign=0,
        )
        warning_label.set_wrap(True)
        warning_label.set_margin_top(12)
        warning_label.set_margin_bottom(12)
        warning_label.set_margin_start(12)
        warning_label.set_margin_end(12)
        content.append(warning_label)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Delete", Gtk.ResponseType.ACCEPT)
        dialog.connect("response", self.on_delete_save_response, save_id)
        dialog.present()

    def on_delete_save_response(self, dialog, response, save_id: str):
        try:
            if response == Gtk.ResponseType.ACCEPT:
                ok, message = self.delete_save_slot(save_id)
                self.saves_info_label.set_text(message)
                self.refresh_saves_list()
        finally:
            dialog.destroy()

    def _add_save_file_filters(self, dialog):
        try:
            save_filter = Gtk.FileFilter()
            save_filter.set_name("Fleshfetch saves")
            save_filter.add_pattern("*.json")
            save_filter.add_pattern("*.fleshsave")
            dialog.add_filter(save_filter)
            json_filter = Gtk.FileFilter()
            json_filter.set_name("JSON files")
            json_filter.add_pattern("*.json")
            dialog.add_filter(json_filter)
        except Exception:
            pass

    def _destroy_native_dialog(self, dialog):
        try:
            dialog.destroy()
        except Exception:
            try:
                dialog.hide()
            except Exception:
                pass

    def on_export_save_clicked(self, button, save_id: str):
        slot = load_save_slot_data(save_id)
        if not slot:
            self.saves_info_label.set_text("Save could not be exported.")
            self.refresh_saves_list()
            return
        try:
            dialog = Gtk.FileChooserNative.new(
                "Export save",
                self,
                Gtk.FileChooserAction.SAVE,
                "Export",
                "Cancel",
            )
            dialog.set_current_name(save_name_to_filename(slot.get("name") or save_id))
            self._add_save_file_filters(dialog)
            dialog.connect("response", self.on_export_save_response, save_id)
            self._save_file_dialog = dialog
            dialog.show()
        except Exception as exc:
            self.saves_info_label.set_text(f"Could not open export dialog: {exc}")

    def on_export_save_response(self, dialog, response, save_id: str):
        try:
            if response == Gtk.ResponseType.ACCEPT:
                file_obj = dialog.get_file()
                path = file_obj.get_path() if file_obj else ""
                if path:
                    ok, message = self.export_save_slot(save_id, path)
                    self.saves_info_label.set_text(message)
                else:
                    self.saves_info_label.set_text("Export failed: no file path selected.")
                self.refresh_saves_list()
        finally:
            self._destroy_native_dialog(dialog)

    def on_import_save_clicked(self, button):
        try:
            dialog = Gtk.FileChooserNative.new(
                "Import save",
                self,
                Gtk.FileChooserAction.OPEN,
                "Import",
                "Cancel",
            )
            self._add_save_file_filters(dialog)
            dialog.connect("response", self.on_import_save_response)
            self._save_file_dialog = dialog
            dialog.show()
        except Exception as exc:
            self.saves_info_label.set_text(f"Could not open import dialog: {exc}")

    def on_import_save_response(self, dialog, response):
        try:
            if response == Gtk.ResponseType.ACCEPT:
                file_obj = dialog.get_file()
                path = file_obj.get_path() if file_obj else ""
                if path:
                    ok, message, slot = self.import_save_slot(path)
                    self.saves_info_label.set_text(message)
                else:
                    self.saves_info_label.set_text("Import failed: no file path selected.")
                self.refresh_saves_list()
        finally:
            self._destroy_native_dialog(dialog)

    def on_restore_selected_save_backup_clicked(self, button, save_id: str, backup_combo, backups):
        active_index = backup_combo.get_active()
        if active_index < 0 or active_index >= len(backups):
            self.saves_info_label.set_text("Choose a backup to restore.")
            return
        backup_path = backups[active_index]
        if normalize_save_id(save_id) == self.active_save_id:
            try:
                backup_slot = read_save_slot_file(backup_path)
                missing_mods = self._save_slot_missing_mods(backup_slot)
            except Exception as exc:
                self.saves_info_label.set_text(f"Selected backup could not be read: {exc}")
                return
            if missing_mods:
                self.show_missing_mods_restore_dialog(save_id, backup_path, missing_mods)
                return
        ok, message = self.restore_save_backup(save_id, backup_path)
        self.saves_info_label.set_text(message)
        self.refresh_saves_list()

    def show_missing_mods_restore_dialog(self, save_id: str, backup_path: str, missing_mods):
        dialog = Gtk.Dialog()
        dialog.set_title("Missing required mods")
        dialog.set_transient_for(self)
        dialog.set_modal(True)
        content = dialog.get_content_area()
        warning_label = Gtk.Label(
            label=(
                "This backup requires missing mods: "
                f"{', '.join(missing_mods)}, restoring may cause corruption or loss of data. "
                "Restore anyway?"
            ),
            xalign=0,
        )
        warning_label.set_wrap(True)
        warning_label.set_margin_top(12)
        warning_label.set_margin_bottom(12)
        warning_label.set_margin_start(12)
        warning_label.set_margin_end(12)
        content.append(warning_label)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Restore anyway", Gtk.ResponseType.ACCEPT)
        dialog.connect("response", self.on_missing_mods_restore_response, save_id, backup_path)
        dialog.present()

    def on_missing_mods_restore_response(self, dialog, response, save_id: str, backup_path: str):
        try:
            if response == Gtk.ResponseType.ACCEPT:
                ok, message = self.restore_save_backup(save_id, backup_path, allow_missing_mods=True)
                self.saves_info_label.set_text(message)
                self.refresh_saves_list()
        finally:
            dialog.destroy()

    def on_restore_save_backup_clicked(self, button, save_id: str):
        ok, message = self.restore_latest_save_backup(save_id)
        self.saves_info_label.set_text(message)
        self.refresh_saves_list()

    def build_settings_page(self):
        self.settings_page.set_margin_top(4)
        self.settings_page.set_margin_bottom(4)
        self.settings_page.set_margin_start(4)
        self.settings_page.set_margin_end(4)

        grid = Gtk.Grid(column_spacing=8, row_spacing=8)
        grid.set_hexpand(False)
        self.settings_page.append(grid)
        row = 0

        rpc_label = Gtk.Label(label="Enable Discord RPC", xalign=0)
        grid.attach(rpc_label, 0, row, 1, 1)
        self.rpc_switch = Gtk.Switch()
        self.rpc_switch.set_halign(Gtk.Align.START)
        self.rpc_switch.set_hexpand(False)
        self.rpc_switch.set_active(bool(self.settings.get("enable_rpc")))
        self.rpc_switch.connect("notify::active", self.on_settings_changed)
        grid.attach(self.rpc_switch, 1, row, 1, 1)
        row += 1

        squish_label = Gtk.Label(label="Squish duration (ms)", xalign=0)
        grid.attach(squish_label, 0, row, 1, 1)
        self.squish_spin = Gtk.SpinButton.new_with_range(20, 300, 10)
        self.squish_spin.set_value(int(self.settings.get("squish_ms", 100)))
        self.squish_spin.connect("value-changed", self.on_settings_changed)
        grid.attach(self.squish_spin, 1, row, 1, 1)
        row += 1

        sound_label = Gtk.Label(label="Play click sound", xalign=0)
        grid.attach(sound_label, 0, row, 1, 1)
        self.sound_switch = Gtk.Switch()
        self.sound_switch.set_halign(Gtk.Align.START)
        self.sound_switch.set_hexpand(False)
        self.sound_switch.set_active(bool(self.settings.get("play_click_sound")))
        self.sound_switch.connect("notify::active", self.on_settings_changed)
        grid.attach(self.sound_switch, 1, row, 1, 1)
        row += 1

        volume_label = Gtk.Label(label="Click sound volume", xalign=0)
        grid.attach(volume_label, 0, row, 1, 1)
        self.volume_slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.volume_slider.set_value(int(self.settings.get("click_sound_volume", DEFAULT_SETTINGS["click_sound_volume"])))
        self.volume_slider.set_hexpand(False)
        self.volume_slider.set_size_request(200, -1)
        self.volume_slider.set_draw_value(True)
        self.volume_slider.connect("value-changed", self.on_settings_changed)
        grid.attach(self.volume_slider, 1, row, 1, 1)
        row += 1

        leaderboard_button = Gtk.Button(label="Add leaderboard entry")
        leaderboard_button.connect("clicked", self.on_add_leaderboard_clicked)
        grid.attach(leaderboard_button, 0, row, 2, 1)
        row += 1

        self.settings_info_label = Gtk.Label(label="", xalign=0)
        self.settings_page.append(self.settings_info_label)
        self.build_mod_settings_list()

    def build_mod_settings_list(self):
        mods_label = Gtk.Label(label="Installed mods", xalign=0)
        mods_label.add_css_class("badge-unlocked")
        self.settings_page.append(mods_label)

        mods_scroll = Gtk.ScrolledWindow()
        mods_scroll.set_vexpand(True)
        mods_scroll.set_hexpand(True)
        try:
            mods_scroll.set_min_content_height(160)
        except Exception:
            pass

        self.mods_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        mods_scroll.set_child(self.mods_list_box)
        self.settings_page.append(mods_scroll)
        self.refresh_mod_settings_list()

    def refresh_mod_settings_list(self):
        if not hasattr(self, "mods_list_box"):
            return
        self.clear_box_children(self.mods_list_box)

        if not self.installed_mods:
            self.mods_list_box.append(Gtk.Label(label="No installed mods found.", xalign=0))
            return

        for mod_info in self.installed_mods:
            security_level = int(mod_info.get("security_level", 0) or 0)
            security_label = mod_info.get("security_label") or MOD_SECURITY_LEVEL_NAMES.get(security_level, "Suspicious")
            blocked = bool(mod_info.get("security_blocked"))
            dependency_blocked = bool(mod_info.get("dependency_blocked"))
            warning_dismissed = bool(mod_info.get("security_dismissed"))
            if dependency_blocked:
                status = "Missing dependencies"
            elif security_level == 0:
                status = "Enabled" if mod_info.get("enabled") else "Disabled"
            elif blocked:
                status = f"{security_label} warning"
            elif warning_dismissed:
                state = "Enabled" if mod_info.get("enabled") else "Disabled"
                status = f"{state}, warning dismissed"
            else:
                status = "Enabled" if mod_info.get("enabled") else "Disabled"

            expander_label = Gtk.Label(label=f"{mod_info.get('name') or mod_info['id']} ({status})", xalign=0)
            if security_level == 1:
                expander_label.add_css_class("security-suspicious")
            elif security_level >= 2:
                expander_label.add_css_class("security-extreme")

            expander = Gtk.Expander()
            expander.set_label_widget(expander_label)
            expander.set_hexpand(True)
            mod_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            mod_row.append(expander)

            details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            details.set_margin_top(4)
            details.set_margin_bottom(4)
            details.set_margin_start(12)
            details.set_margin_end(4)

            meta_lines = [
                ("Author", mod_info.get("author") or "Unknown"),
                ("Version", mod_info.get("version") or "Unknown"),
                ("Description", mod_info.get("description") or "No description provided."),
            ]
            if mod_info.get("game_title"):
                meta_lines.append(("Game title", mod_info["game_title"]))
            if mod_info.get("dependencies"):
                dependency_names = []
                for dep in mod_info.get("dependencies", []):
                    dep_text = dep.get("id") or "Unknown mod"
                    if dep.get("version"):
                        dep_text += f" >= {dep['version']}"
                    if dep.get("optional"):
                        dep_text += " (optional)"
                    dependency_names.append(dep_text)
                meta_lines.append(("Dependencies", ", ".join(dependency_names)))
            if dependency_blocked:
                meta_lines.append(("Missing dependencies", ", ".join(mod_info.get("dependency_missing", []))))
            if security_level > 0:
                security_text = f"Level {security_level}: {security_label}"
                if warning_dismissed:
                    security_text += " (warning dismissed)"
                else:
                    security_text += " (paused before loading)"
                meta_lines.append(("Security", security_text))
            for label, value in meta_lines:
                lbl = Gtk.Label(label=f"{label}: {value}", xalign=0)
                lbl.set_wrap(True)
                details.append(lbl)
            if security_level > 0:
                for reason in mod_info.get("security_reasons", [])[:8]:
                    reason_label = Gtk.Label(label=f"Warning reason: {reason}", xalign=0)
                    reason_label.set_wrap(True)
                    if security_level == 1:
                        reason_label.add_css_class("security-suspicious")
                    else:
                        reason_label.add_css_class("security-extreme")
                    details.append(reason_label)
                hidden_count = max(0, len(mod_info.get("security_reasons", [])) - 8)
                if hidden_count:
                    hidden_label = Gtk.Label(label=f"Warning reason: and {hidden_count} more", xalign=0)
                    hidden_label.set_wrap(True)
                    if security_level == 1:
                        hidden_label.add_css_class("security-suspicious")
                    else:
                        hidden_label.add_css_class("security-extreme")
                    details.append(hidden_label)
                if blocked:
                    dismiss_btn = Gtk.Button(label="Dismiss warning")
                    dismiss_btn.connect("clicked", self.on_mod_dismiss_warning_clicked, mod_info)
                    details.append(dismiss_btn)

            button_label = "Disable" if mod_info.get("enabled") else "Enable"
            toggle_btn = Gtk.Button(label=button_label)
            if dependency_blocked:
                toggle_btn.set_sensitive(False)
                toggle_btn.set_tooltip_text("Install and enable this mod's dependencies first.")
            if blocked and not mod_info.get("enabled"):
                toggle_btn.set_sensitive(False)
                toggle_btn.set_tooltip_text("Dismiss this security warning before enabling or loading this mod.")
            toggle_btn.connect("clicked", self.on_mod_toggle_clicked, mod_info)
            details.append(toggle_btn)

            expander.set_child(details)
            if mod_info.get("game_title"):
                title_label = Gtk.Label(label="Title")
                title_switch = Gtk.Switch()
                title_switch.set_valign(Gtk.Align.CENTER)
                title_switch.set_sensitive(bool(mod_info.get("enabled")) and not blocked and not dependency_blocked)
                title_switch.set_active(
                    bool(mod_info.get("enabled"))
                    and not blocked
                    and not dependency_blocked
                    and self.settings.get("game_title_mod_key") == mod_info["title_key"]
                )
                title_switch.set_tooltip_text(f'Use "{mod_info["game_title"]}" as the game title')
                title_switch.connect("notify::active", self.on_mod_title_switch_changed, mod_info)
                mod_row.append(title_label)
                mod_row.append(title_switch)

            self.mods_list_box.append(mod_row)

    def on_mod_dismiss_warning_clicked(self, button, mod_info: dict):
        dialog = Gtk.Dialog()
        dialog.set_title("Dismiss security warning")
        dialog.set_transient_for(self)
        dialog.set_modal(True)
        content = dialog.get_content_area()
        warning_label = Gtk.Label(
            label=(
                "Are you sure you want to dismiss this warning? You might be running "
                "very harmful code, or just a normal mod. Only continue if you trust "
                "the mod and its source."
            ),
            xalign=0,
        )
        warning_label.set_wrap(True)
        warning_label.set_margin_top(12)
        warning_label.set_margin_bottom(12)
        warning_label.set_margin_start(12)
        warning_label.set_margin_end(12)
        content.append(warning_label)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("I don't care", Gtk.ResponseType.ACCEPT)
        dialog.connect("response", self.on_mod_dismiss_warning_response, mod_info)
        dialog.present()

    def on_mod_dismiss_warning_response(self, dialog, response, mod_info: dict):
        try:
            if response == Gtk.ResponseType.ACCEPT:
                self._dismiss_mod_security_warning(mod_info)
                self.settings_info_label.set_text(
                    f"Warning dismissed for '{mod_info.get('name', mod_info['id'])}'. Restart Fleshfetch to load it."
                )
                self.refresh_mod_settings_list()
        finally:
            dialog.destroy()

    def on_mod_title_switch_changed(self, switch, _pspec, mod_info: dict):
        mod_key = mod_info["title_key"]
        if switch.get_active():
            if (
                not mod_info.get("enabled")
                or mod_info.get("security_blocked")
                or mod_info.get("dependency_blocked")
                or not mod_info.get("game_title")
            ):
                return
            self.settings["game_title_mod_key"] = mod_key
            message = f"Game title changed to '{mod_info['game_title']}'."
        elif self.settings.get("game_title_mod_key") == mod_key:
            self.settings["game_title_mod_key"] = ""
            message = f"Game title reset to '{DEFAULT_GAME_TITLE}'."
        else:
            return

        save_json(SETTINGS_FILE, self.settings)
        self._apply_selected_game_title()
        self.settings_info_label.set_text(message)
        self.refresh_mod_settings_list()

    def on_mod_toggle_clicked(self, button, mod_info: dict):
        new_enabled = not mod_info.get("enabled", True)
        if new_enabled and mod_info.get("security_blocked"):
            first_reason = next(iter(mod_info.get("security_reasons", [])), "security warning")
            self.settings_info_label.set_text(
                f"Mod '{mod_info.get('name', mod_info['id'])}' has an undismissed warning: {first_reason}"
            )
            return
        try:
            self._write_mod_enabled(mod_info, new_enabled)
        except Exception as e:
            self.settings_info_label.set_text(f"Failed to update mod '{mod_info.get('name', mod_info['id'])}': {e}")
            return

        if not new_enabled and self.settings.get("game_title_mod_key") == mod_info["title_key"]:
            self.settings["game_title_mod_key"] = ""
            save_json(SETTINGS_FILE, self.settings)
            self._apply_selected_game_title()

        state = "enabled" if new_enabled else "disabled"
        self.settings_info_label.set_text(
            f"Mod '{mod_info.get('name', mod_info['id'])}' {state}. Restart Fleshfetch to apply."
        )
        self.refresh_mod_settings_list()

    # ---------- CONSOLE COMMANDS ----------

    def console_print(self, text=""):
        print(str(text))

    def _register_default_console_commands(self):
        self.register_console_command(
            "addcurrency",
            self._cmd_addcurrency,
            "Add currency: /addcurrency <currency> <amount>",
            aliases=["ac", "add"],
        )
        self.register_console_command(
            "takecurrency",
            self._cmd_takecurrency,
            "Take currency: /takecurrency <currency> <amount>",
            aliases=["tc", "take"],
        )
        self.register_console_command(
            "currencymodifier",
            self._cmd_currencymodifier,
            "Multiply a currency amount: /currencymodifier <currency> <multiplier>",
            aliases=["cm", "multcurrency", "multiplycurrency"],
        )
        self.register_console_command(
            "setcurrency",
            self._cmd_setcurrency,
            "Set currency: /setcurrency <currency> <amount>",
            aliases=["sc"],
        )
        self.register_console_command(
            "currencies",
            self._cmd_currencies,
            "List known currencies.",
            aliases=["currencylist", "cl"],
        )
        self.register_console_command(
            "clickmodifiers",
            self._cmd_clickmodifiers,
            "List active click gain modifiers.",
            aliases=["modifiers", "clickmods"],
        )
        self.register_console_command(
            "saves",
            self._cmd_saves,
            "List save slots.",
            aliases=["listsaves", "lsaves"],
        )
        self.register_console_command(
            "save",
            self._cmd_save,
            "Save active progress.",
            aliases=["savegame"],
        )
        self.register_console_command(
            "print",
            self._cmd_print,
            "Print text to the console: /print <text>",
            aliases=["p", "echo"],
        )
        self.register_console_command(
            "help",
            self._cmd_help,
            "Show help: /help [command]",
            aliases=["h", "?", "commands"],
        )

    def _resolve_console_command(self, command_name: str):
        command_name = str(command_name or "").strip().lower().lstrip("/")
        command_name = self.console_aliases.get(command_name, command_name)
        return command_name, self.console_commands.get(command_name)

    def execute_console_command(self, text: str):
        raw = str(text or "").strip()
        if not raw:
            return
        if not raw.startswith("/"):
            first = raw.split(None, 1)[0].lower() if raw.split(None, 1) else raw.lower()
            _canonical, info = self._resolve_console_command(first)
            if info:
                raw = "/" + raw
            else:
                raw = "/print " + raw

        self.console_print(f"> {raw}")
        try:
            parts = shlex.split(raw)
        except Exception as exc:
            self.console_print(f"Command parse error: {exc}")
            return
        if not parts:
            return

        _command_name, command_info = self._resolve_console_command(parts[0])
        if not command_info:
            self.console_print(f"Unknown command: {parts[0]}. Try /help.")
            return
        args = parts[1:]
        callback = command_info.get("callback")
        try:
            result = callback(args, raw)
        except TypeError:
            try:
                result = callback(args)
            except Exception as exc:
                self.console_print(f"Command failed: {exc}")
                return
        except Exception as exc:
            self.console_print(f"Command failed: {exc}")
            return
        if result is not None:
            self.console_print(result)

    def _parse_console_amount(self, args, usage):
        if len(args) < 2:
            raise ValueError(usage)
        currency = args[0]
        try:
            amount = float(args[1])
        except Exception:
            raise ValueError("Amount must be a number.")
        if currency not in self.currencies and currency not in self.state.get("currencies", {}):
            raise ValueError(f"Unknown currency: {currency}")
        return currency, amount

    def _cmd_addcurrency(self, args, raw):
        currency, amount = self._parse_console_amount(args, "Usage: /addcurrency <currency> <amount>")
        self.add_currency(currency, amount)
        self.update_labels()
        return f"Added {amount:g} {currency}. New amount: {self.get_currency(currency):g}"

    def _cmd_takecurrency(self, args, raw):
        currency, amount = self._parse_console_amount(args, "Usage: /takecurrency <currency> <amount>")
        self.add_currency(currency, -amount)
        self.update_labels()
        return f"Took {amount:g} {currency}. New amount: {self.get_currency(currency):g}"

    def _cmd_currencymodifier(self, args, raw):
        currency, multiplier = self._parse_console_amount(args, "Usage: /currencymodifier <currency> <multiplier>")
        self.set_currency(currency, self.get_currency(currency) * multiplier)
        self.update_labels()
        return f"Multiplied {currency} by {multiplier:g}. New amount: {self.get_currency(currency):g}"

    def _cmd_setcurrency(self, args, raw):
        currency, amount = self._parse_console_amount(args, "Usage: /setcurrency <currency> <amount>")
        self.set_currency(currency, amount)
        self.update_labels()
        return f"Set {currency} to {self.get_currency(currency):g}"

    def _cmd_currencies(self, args, raw):
        lines = ["Currencies:"]
        seen = set()
        for currency, data in self.currencies.items():
            seen.add(currency)
            display = data.get("display_name", currency)
            lines.append(f"  {currency} ({display}): {self.get_currency(currency):g}")
        for currency in sorted(set(self.state.get("currencies", {})) - seen):
            lines.append(f"  {currency}: {self.get_currency(currency):g}")
        return "\n".join(lines)

    def _cmd_clickmodifiers(self, args, raw):
        modifiers = self.get_click_modifiers()
        if not modifiers:
            return "No active click modifiers."
        lines = ["Click modifiers:"]
        for modifier in modifiers:
            description = modifier.get("description") or "No description"
            owner = modifier.get("owner") or "unknown"
            currency = modifier.get("currency") or "all click gains"
            lines.append(f"  {modifier.get('key')}: {description} ({currency}, owner: {owner})")
        return "\n".join(lines)

    def _cmd_saves(self, args, raw):
        lines = ["Saves:"]
        for slot in list_save_slots():
            save_id = normalize_save_id(slot.get("id"))
            marker = "*" if save_id == self.active_save_id else " "
            lines.append(f" {marker} {save_id}: {normalize_save_name(slot.get('name') or save_id)}")
        return "\n".join(lines)

    def _cmd_save(self, args, raw):
        self.save_current_progress(auto_backup=True)
        return f"Saved '{self.active_save_name}'."

    def _cmd_print(self, args, raw):
        return " ".join(args)

    def _cmd_help(self, args, raw):
        if args:
            command_name, command_info = self._resolve_console_command(args[0])
            if not command_info:
                return f"Unknown command: {args[0]}"
            aliases = command_info.get("aliases", [])
            alias_text = f" Aliases: {', '.join('/' + alias for alias in aliases)}." if aliases else ""
            help_text = command_info.get("help") or f"/{command_name}"
            return f"/{command_name}: {help_text}.{alias_text}"

        lines = ["Commands:"]
        for command_name in sorted(self.console_commands):
            info = self.console_commands[command_name]
            aliases = info.get("aliases", [])
            alias_text = f" ({', '.join('/' + alias for alias in aliases)})" if aliases else ""
            help_text = info.get("help") or ""
            lines.append(f"  /{command_name}{alias_text} - {help_text}")
        return "\n".join(lines)

    def build_console_page(self):
        self.console_page.set_margin_top(4)
        self.console_page.set_margin_bottom(4)
        self.console_page.set_margin_start(4)
        self.console_page.set_margin_end(4)

        # toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        clear_btn = Gtk.Button(label="Clear")
        clear_btn.connect("clicked", self._on_console_clear)
        toolbar.append(clear_btn)

        self._console_command_entry = Gtk.Entry()
        self._console_command_entry.set_placeholder_text("/help")
        self._console_command_entry.set_hexpand(True)
        self._console_command_entry.connect("activate", self._on_console_command_activate)
        toolbar.append(self._console_command_entry)

        run_btn = Gtk.Button(label="Run")
        run_btn.connect("clicked", self._on_console_run_clicked)
        toolbar.append(run_btn)
        self.console_page.append(toolbar)

        # scrolled textview
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        self.console_page.append(scrolled)

        self._console_textview = Gtk.TextView()
        self._console_textview.set_editable(False)
        self._console_textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        try:
            self._console_textview.set_monospace(True)
        except Exception:
            pass
        scrolled.set_child(self._console_textview)
        self._console_buffer = self._console_textview.get_buffer()
        self._console_pending_chunks = []
        self._console_flush_pending = False

        # hook into the tee streams
        _stdout_tee._callbacks.append(self._console_append)
        _stderr_tee._callbacks.append(self._console_append)
        for text in list(_stdout_tee._history) + list(_stderr_tee._history):
            if text:
                self._console_append(text)

    def _console_append(self, text: str):
        """Append text to the console buffer in small batches."""
        if not hasattr(self, "_console_pending_chunks"):
            return
        self._console_pending_chunks.append(str(text))
        if not self._console_flush_pending:
            self._console_flush_pending = True
            GLib.timeout_add(CONSOLE_FLUSH_INTERVAL_MS, self._flush_console_pending)

    def _trim_console_buffer(self):
        try:
            char_count = self._console_buffer.get_char_count()
        except Exception:
            return
        excess = char_count - CONSOLE_MAX_BUFFER_CHARS
        if excess <= 0:
            return
        start = self._console_buffer.get_start_iter()
        cutoff = self._console_buffer.get_iter_at_offset(excess)
        self._console_buffer.delete(start, cutoff)

    def _flush_console_pending(self):
        self._console_flush_pending = False
        if not getattr(self, "_console_pending_chunks", None):
            return False
        text = "".join(self._console_pending_chunks)
        self._console_pending_chunks.clear()
        end = self._console_buffer.get_end_iter()
        self._console_buffer.insert(end, text, -1)
        self._trim_console_buffer()
        new_end = self._console_buffer.get_end_iter()
        self._console_buffer.place_cursor(new_end)
        mark = self._console_buffer.get_insert()
        self._console_textview.scroll_mark_onscreen(mark)
        return False

    def _on_console_clear(self, button):
        if hasattr(self, "_console_pending_chunks"):
            self._console_pending_chunks.clear()
        self._console_flush_pending = False
        self._console_buffer.set_text("", -1)

    def _run_console_entry(self):
        text = self._console_command_entry.get_text() if hasattr(self, "_console_command_entry") else ""
        self.execute_console_command(text)
        self._console_command_entry.set_text("")

    def _on_console_command_activate(self, entry):
        self._run_console_entry()

    def _on_console_run_clicked(self, button):
        self._run_console_entry()

    def build_stats_tab_page(self):
        self.stats_tab_page.set_margin_top(4)
        self.stats_tab_page.set_margin_bottom(4)
        self.stats_tab_page.set_margin_start(4)
        self.stats_tab_page.set_margin_end(4)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        self.stats_tab_page.append(scrolled)

        self._stats_tab_textview = Gtk.TextView()
        self._stats_tab_textview.set_editable(False)
        self._stats_tab_textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        try:
            self._stats_tab_textview.set_monospace(True)
        except Exception:
            pass
        scrolled.set_child(self._stats_tab_textview)
        self._stats_tab_buffer = self._stats_tab_textview.get_buffer()

    def refresh_stats_tab(self, force=False):
        if not hasattr(self, "_stats_tab_buffer"):
            return
        now = time.monotonic()
        if not force and now - getattr(self, "_last_stats_tab_refresh", 0.0) < 0.5:
            return
        self._last_stats_tab_refresh = now

        lines = []

        # ── Currencies ──────────────────────────────────────────────────────
        lines.append("=== Currencies ===")
        for reg_name, cur_data in self.currencies.items():
            amount = self.get_currency(reg_name)
            display = cur_data.get("display_name", reg_name)
            cps = self.compute_cps(reg_name)
            if reg_name == self.primary_currency:
                cpc = self.effective_fpc()
            else:
                cpc = self.compute_cpc(reg_name)
            lines.append(
                f"{display}: {int(amount)}  "
                f"(per second: {cps:.2f}, per click: {cpc:.2f})"
            )

        # ── Upgrades owned ──────────────────────────────────────────────────
        lines.append("")
        lines.append("=== Upgrades ===")
        any_owned = False
        for uid, u in self.upgrades.items():
            count = self.get_upgrade_count(uid)
            if count > 0:
                lines.append(f"{u.get('name', uid)}: {count}")
                any_owned = True
        if not any_owned:
            lines.append("(none owned yet)")

        self._stats_tab_buffer.set_text("\n".join(lines), -1)

    def build_leaderboard_page(self):
        self.leaderboard_page.set_margin_top(4)
        self.leaderboard_page.set_margin_bottom(4)
        self.leaderboard_page.set_margin_start(4)
        self.leaderboard_page.set_margin_end(4)

        outer    = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        outer.append(controls)
        self.leaderboard_page.append(outer)

        refresh_btn = Gtk.Button(label="Refresh leaderboard")
        refresh_btn.connect("clicked", self.on_refresh_leaderboard_clicked)
        controls.append(refresh_btn)

        self.leaderboard_info_label = Gtk.Label(label="", xalign=0)
        outer.append(self.leaderboard_info_label)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        outer.append(scrolled)

        self.leaderboard_textview = Gtk.TextView()
        self.leaderboard_textview.set_editable(False)
        try:
            self.leaderboard_textview.set_monospace(True)
        except Exception:
            pass
        scrolled.set_child(self.leaderboard_textview)
        self.load_leaderboard()

    def update_leaderboard_view(self, rows):
        buffer = self.leaderboard_textview.get_buffer()
        if not rows:
            buffer.set_text("No leaderboard entries yet.", -1)
            return
        header    = f"{'Username':<20} {'Flesh':>10}  {'Timestamp':<32}\n"
        separator = "-" * 64 + "\n"
        lines     = [header, separator]
        for row in rows:
            username = str(row.get("username") or "?")
            flesh    = row.get("flesh_amount") or row.get("flesh")
            try:
                flesh_str = str(int(flesh))
            except Exception:
                flesh_str = str(flesh)
            ts = row.get("last_update") or row.get("created_at") or ""
            lines.append(f"{username:<20} {flesh_str:>10}  {ts:<32}\n")
        buffer.set_text("".join(lines), -1)

    def load_leaderboard(self):
        if not hasattr(self, "leaderboard_textview"):
            return
        ok, err, rows = fetch_leaderboard_entries()
        if not ok:
            if hasattr(self, "leaderboard_info_label"):
                self.leaderboard_info_label.set_text(f"Error loading leaderboard: {err}")
            return
        if hasattr(self, "leaderboard_info_label"):
            self.leaderboard_info_label.set_text(f"Loaded {len(rows)} entries.")
        self.update_leaderboard_view(rows)

    def on_refresh_leaderboard_clicked(self, button):
        self.load_leaderboard()

    def on_add_leaderboard_clicked(self, button):
        username     = get_default_username()
        flesh_amount = int(self.flesh)
        ok, info = submit_leaderboard_entry(username, flesh_amount)
        if ok:
            msg = f"Submitted leaderboard entry as '{username}' with {flesh_amount} flesh."
            if hasattr(self, "leaderboard_textview"):
                self.load_leaderboard()
        else:
            msg = f"Failed to submit leaderboard entry: {info}"
        if hasattr(self, "settings_info_label"):
            self.settings_info_label.set_text(msg)
        else:
            print(msg)

    # ---------- IMAGE ----------

    def load_flesh_image(self):
        if not hasattr(self, "picture"):
            return  # UI not built yet — build_ui() will call this again
        try:
            texture = Gdk.Texture.new_from_filename(self.flesh_image_path)
            self.picture.set_paintable(texture)
        except Exception as e:
            print(f"Failed to load image '{self.flesh_image_path}':", e)

    # ---------- SOUND ----------

    def play_click_sound(self):
        """Play the click sound if enabled in settings."""
        if not self.settings.get("play_click_sound"):
            return
        path = self.click_sound_path
        if not os.path.exists(path):
            return

        volume = max(0, min(100, int(self.settings.get("click_sound_volume", DEFAULT_SETTINGS["click_sound_volume"]))))

        # --- pygame path (fast, in-memory, no process spawning) ---
        if self._pygame_mixer_ok:
            try:
                import pygame.mixer
                if path not in self._sound_cache:
                    self._sound_cache[path] = pygame.mixer.Sound(path)
                snd = self._sound_cache[path]
                snd.set_volume(volume / 100.0)
                snd.play()
                return
            except Exception as e:
                print(f"[sound] pygame failed: {e}")

        # --- fallback: throttle to avoid process backlog ---
        now = time.monotonic()
        if now - self._last_sound_time < 0.08:
            return
        self._last_sound_time = now

        try:
            if sys.platform == "win32":
                import winsound
                if volume == 100:
                    winsound.PlaySound(
                        path,
                        winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
                    )
                else:
                    import wave, struct, tempfile
                    with wave.open(path, "rb") as wf:
                        params = wf.getparams()
                        frames = wf.readframes(params.nframes)
                    factor = volume / 100.0
                    sw = params.sampwidth
                    fmt = {1: "b", 2: "h", 4: "i"}.get(sw)
                    if fmt:
                        n = len(frames) // sw
                        samples = struct.unpack_from(f"{n}{fmt}", frames)
                        scaled  = struct.pack(f"{n}{fmt}", *(max(-32768, min(32767, int(s * factor))) for s in samples))
                    else:
                        scaled = frames
                    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                    with wave.open(tmp.name, "wb") as wf:
                        wf.setparams(params)
                        wf.writeframes(scaled)
                    winsound.PlaySound(
                        tmp.name,
                        winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
                    )
                    def _cleanup(f=tmp.name):
                        try:
                            os.unlink(f)
                        except Exception:
                            pass
                        return False
                    GLib.timeout_add(2000, _cleanup)
            else:
                import subprocess
                vol_pa = int(65536 * volume / 100)
                for player, args in [
                    ("paplay", ["--volume", str(vol_pa), path]),
                    ("aplay",  [path]),
                ]:
                    try:
                        subprocess.Popen(
                            [player] + args,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        break
                    except FileNotFoundError:
                        continue
        except Exception as e:
            print(f"Failed to play click sound '{path}':", e)

    # ---------- UI HELPERS ----------

    def clear_box_children(self, box: Gtk.Box):
        child = box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            box.remove(child)
            child = nxt

    def check_requires(self, uid: str) -> bool:
        """Return True if all requirements for an upgrade are satisfied.

        The ``requires`` field on an upgrade can be a single dict or a list
        of dicts.  Each dict may contain:

            upgrade  (str)  — another upgrade uid that must be owned
            count    (int)  — minimum number of that upgrade owned (default 1)
            currency (str)  — a currency registry name
            amount   (float)— minimum amount of that currency required (default 0)

        All conditions in a single dict must be satisfied (AND logic).
        If ``requires`` is a list, *any* one dict being satisfied is enough
        (OR logic between list items, AND within each item).

        Example — require lignification AND at least 500 wood::

            "requires": {"upgrade": "lignification", "currency": "wood", "amount": 500}

        Example — require either sapwood OR heartwood::

            "requires": [
                {"upgrade": "sapwood"},
                {"upgrade": "heartwood"},
            ]
        """
        u = self.upgrades.get(uid)
        if u is None:
            return False
        req = u.get("requires")
        if req is None:
            return True

        # normalise to a list of condition-dicts
        conditions = req if isinstance(req, list) else [req]

        for cond in conditions:
            ok = True
            needed_upgrade  = cond.get("upgrade")
            needed_count    = int(cond.get("count", 1))
            needed_currency = cond.get("currency")
            needed_amount   = float(cond.get("amount", 0))

            if needed_upgrade is not None:
                if self.get_upgrade_count(needed_upgrade) < needed_count:
                    ok = False
            if needed_currency is not None:
                if self.get_currency(needed_currency) < needed_amount:
                    ok = False

            if ok:
                return True  # at least one condition-set satisfied

        return False

    def _build_all_upgrade_rows(self):
        """Build every upgrade row once and append to the listbox.
        Rows are shown/hidden via set_visible() -- the DOM is never rebuilt."""
        if not hasattr(self, "upgrades_listbox"):
            return
        for uid, u in self.upgrades.items():
            if uid in self._upgrade_rows:
                continue  # already built
            self._build_upgrade_row(uid, u)

    def _build_upgrade_row(self, uid: str, u: dict):
        """Create the GTK widgets for a single upgrade and store references."""
        owned         = self.get_upgrade_count(uid)
        cost          = self.get_upgrade_cost(uid, owned)
        cost_currency = u.get("cost_currency", "flesh")
        cost_display  = self.currencies.get(cost_currency, {}).get("display_name", cost_currency)
        cat           = u.get("category") or u.get("type") or "misc"

        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        row.add_css_class("upgrade-row")

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        name_label = Gtk.Label(label=f"{u['name']} ({cat})", xalign=0)
        name_label.set_hexpand(True)
        top.append(name_label)

        cost_label = Gtk.Label(label=f"Cost: {int(cost)} {cost_display},", xalign=1)
        top.append(cost_label)
        owned_label = Gtk.Label(label=f"Owned: {owned}", xalign=1)
        top.append(owned_label)
        row.append(top)

        desc_label = Gtk.Label(label=u["desc"], xalign=0)
        desc_label.set_wrap(True)
        row.append(desc_label)

        btn = Gtk.Button(label="Buy")
        btn.connect("clicked", self.on_buy_upgrade_clicked, uid)
        row.append(btn)

        self.upgrades_listbox.append(row)
        self._upgrade_rows[uid] = {
            "row":         row,
            "cost_label":  cost_label,
            "owned_label": owned_label,
            "buy_btn":     btn,
            "category":    cat,
            "name":        u["name"].lower(),
            "desc":        u["desc"].lower(),
        }

    def _on_upgrade_search_changed(self, entry):
        self._upgrade_search_text = entry.get_text().lower()
        self._apply_upgrade_visibility()

    def _apply_upgrade_visibility(self):
        """Show/hide rows in-place. Updates filter button styles and cost labels.
        Never rebuilds widgets -- scroll position is always preserved."""
        if not hasattr(self, "_upgrade_rows"):
            return

        selected_filter = getattr(self, "current_filter", "all")
        search = getattr(self, "_upgrade_search_text", "")

        # Update filter button styles
        if hasattr(self, "upgrade_filter_buttons"):
            for key, btn in self.upgrade_filter_buttons.items():
                if key == selected_filter:
                    btn.add_css_class("suggested-action")
                else:
                    btn.remove_css_class("suggested-action")

        for uid, meta in self._upgrade_rows.items():
            u = self.upgrades.get(uid)
            if u is None:
                meta["row"].set_visible(False)
                continue

            # Category filter
            if selected_filter != "all" and meta["category"] != selected_filter:
                meta["row"].set_visible(False)
                continue

            # Requirements gate
            if not self.check_requires(uid):
                meta["row"].set_visible(False)
                continue

            # Search filter
            if search and search not in meta["name"] and search not in meta["desc"]:
                meta["row"].set_visible(False)
                continue

            # Row is visible -- refresh cost label in-place
            owned         = self.get_upgrade_count(uid)
            cost          = self.get_upgrade_cost(uid, owned)
            cost_currency = u.get("cost_currency", "flesh")
            cost_display  = self.currencies.get(cost_currency, {}).get("display_name", cost_currency)
            meta["cost_label"].set_text(f"Cost: {int(cost)} {cost_display},")
            meta["owned_label"].set_text(f"Owned: {owned}")
            meta["row"].set_visible(True)

    def refresh_upgrades_ui(self):
        """Public method kept for mod compatibility.
        Builds any newly registered rows then updates visibility in-place."""
        if not hasattr(self, "upgrades_listbox"):
            return
        # Build rows for any upgrades added since initial build (e.g. by mods)
        if hasattr(self, "_upgrade_rows"):
            self._build_all_upgrade_rows()
        self._apply_upgrade_visibility()

    def refresh_achievements_ui(self):
        if not hasattr(self, "achievements_listbox"):
            return
        self.clear_box_children(self.achievements_listbox)
        unlocked_any = False
        for key, data in self.achievements.items():
            if not data.get("unlocked", False):
                continue
            if not self._achievement_is_active(key, data):
                continue
            unlocked_any = True
            row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            row.add_css_class("achievement-row")
            name_label = Gtk.Label(label=data.get("name", key), xalign=0)
            desc_label = Gtk.Label(label=data.get("desc", ""),  xalign=0)
            desc_label.set_wrap(True)
            name_label.add_css_class("badge-unlocked")
            row.append(name_label)
            row.append(desc_label)
            self.achievements_listbox.append(row)
        if not unlocked_any:
            placeholder = Gtk.Label(label="No achievements unlocked yet.", xalign=0)
            self.achievements_listbox.append(placeholder)

    # ---------- TIMER / GAME LOOP ----------

    def on_timer_tick(self):
        for reg_name in self.currencies:
            cps = self.compute_cps(reg_name)
            if cps > 0:
                self.add_currency(reg_name, cps)
        self.update_labels()
        return True

    def update_labels(self):
        if not hasattr(self, "stats_box"):
            return
        amount_labels = getattr(self, "_currency_amount_labels", {})
        cps_labels = getattr(self, "_currency_cps_labels", {})
        visible_amount = set()
        visible_cps = set()

        for reg_name, cur_data in self.currencies.items():
            amount = self.get_currency(reg_name)
            # hide mod currencies until the player first obtains some
            show_currency = amount > 0 or reg_name == "flesh"
            if not show_currency:
                if reg_name in amount_labels:
                    amount_labels[reg_name].set_visible(False)
                if reg_name in cps_labels:
                    cps_labels[reg_name].set_visible(False)
                continue
            display = cur_data.get("display_name", reg_name)

            lbl = amount_labels.get(reg_name)
            if lbl is None:
                lbl = Gtk.Label(xalign=0)
                amount_labels[reg_name] = lbl
                self.stats_box.append(lbl)
            lbl.set_text(f"{display}: {int(amount)}")
            lbl.set_visible(True)
            visible_amount.add(reg_name)

            cps = self.compute_cps(reg_name)
            cps_lbl = cps_labels.get(reg_name)
            if cps > 0:
                if cps_lbl is None:
                    cps_lbl = Gtk.Label(xalign=0)
                    cps_labels[reg_name] = cps_lbl
                    self.stats_box.append(cps_lbl)
                cps_lbl.set_text(f"{display} per second: {cps:.1f}")
                cps_lbl.set_visible(True)
                visible_cps.add(reg_name)
            elif cps_lbl is not None:
                cps_lbl.set_visible(False)

        for reg_name, lbl in amount_labels.items():
            if reg_name not in visible_amount:
                lbl.set_visible(False)
        for reg_name, lbl in cps_labels.items():
            if reg_name not in visible_cps:
                lbl.set_visible(False)

        self.refresh_stats_tab()

    # ---------- UPGRADE LOGIC ----------

    def on_buy_upgrade_clicked(self, button, uid: str):
        owned         = self.get_upgrade_count(uid)
        cost          = self.get_upgrade_cost(uid, owned)
        cost_currency = self.upgrades[uid].get("cost_currency", "flesh")

        if self.get_currency(cost_currency) < cost:
            return

        self.add_currency(cost_currency, -cost)
        self.set_upgrade_count(uid, owned + 1)

        # one-time on_buy currency grants
        for effect in self._get_effects(uid):
            on_buy = effect.get("on_buy", 0.0)
            if on_buy:
                self.add_currency(effect["currency"], on_buy)

        self._emit_event("upgrade_bought", {
            "upgrade_id": uid,
            "upgrade": dict(self.upgrades.get(uid, {})),
            "owned_before": owned,
            "owned_after": owned + 1,
            "cost": cost,
            "cost_currency": cost_currency,
        })

        total = self.total_upgrades_owned()
        if total >= 1: self.unlock_achievement("first_upgrade")
        if total >= 5: self.unlock_achievement("five_upgrades")

        # Update cost labels and visibility in-place -- no rebuild, no scroll jump
        self._apply_upgrade_visibility()
        self.update_labels()

    def play_squish(self):
        self.picture.remove_css_class("squish")
        duration = int(self.settings.get("squish_ms", 100))

        def do_squish():
            self.picture.add_css_class("squish")
            GLib.timeout_add(duration, lambda: (self.picture.remove_css_class("squish"), False)[1])
            return False

        GLib.idle_add(do_squish)

    # ---------- CLICK HANDLER ----------

    def on_click(self, gesture, n_press, x, y):
        self.play_squish()
        self.play_click_sound()

        # primary currency uses base fpc + upgrade cpc; others use only upgrade cpc
        base_gains = {}
        for reg_name in self.currencies:
            if reg_name == self.primary_currency:
                gain = self.effective_fpc()
            else:
                gain = self.compute_cpc(reg_name)
            if gain:
                base_gains[reg_name] = gain

        next_total_clicks = self.state["total_clicks"] + 1
        gains, click_modifier_events = self._apply_click_modifiers(base_gains, {
            "x": x,
            "y": y,
            "n_press": n_press,
            "total_clicks": next_total_clicks,
            "vanilla_multiplier": 1.0,
            "crit_multiplier": 1.0,
        })
        crit_multiplier = 1.0
        for modifier_event in click_modifier_events:
            if modifier_event.get("key") == "__global__:critical_clicks":
                crit_multiplier *= self._coerce_modifier_number(modifier_event.get("multiplier"), 1.0)

        for reg_name, gain in gains.items():
            if gain:
                self.add_currency(reg_name, gain)

        self.state["total_clicks"] = next_total_clicks
        self._emit_event("flesh_clicked", {
            "x": x,
            "y": y,
            "n_press": n_press,
            "multiplier": crit_multiplier,
            "vanilla_multiplier": crit_multiplier,
            "crit_multiplier": crit_multiplier,
            "base_gains": dict(base_gains),
            "gains": dict(gains),
            "modifiers": list(click_modifier_events),
            "total_clicks": self.state["total_clicks"],
        })
        self.mark_save_dirty(auto_backup=True)

        clicks = self.state["total_clicks"]
        if clicks >= 1:   self.unlock_achievement("first_click")
        if clicks >= 10:  self.unlock_achievement("ten_clicks")
        if clicks >= 100: self.unlock_achievement("hundred_clicks")
        if self.flesh >= 100:  self.unlock_achievement("hundred_flesh")
        if self.flesh >= 1000: self.unlock_achievement("thousand_flesh")

        self.update_labels()

    # ---------- ACHIEVEMENTS ----------

    def unlock_achievement(self, key: str):
        if key not in self.achievements:
            return
        if not self._achievement_is_active(key, self.achievements[key]):
            return
        if not self.achievements[key].get("unlocked", False):
            self.achievements[key]["unlocked"] = True
            self.mark_save_dirty(auto_backup=False)
            self.refresh_achievements_ui()

    # ---------- SETTINGS ----------

    def on_settings_changed(self, *args):
        was_rpc_enabled = bool(self.settings.get("enable_rpc"))
        is_rpc_enabled = self.rpc_switch.get_active()

        self.settings["enable_rpc"]           = is_rpc_enabled
        self.settings["squish_ms"]            = int(self.squish_spin.get_value())
        self.settings["play_click_sound"]     = self.sound_switch.get_active()
        self.settings["click_sound_volume"]   = int(self.volume_slider.get_value())
        save_json(SETTINGS_FILE, self.settings)

        if is_rpc_enabled == was_rpc_enabled:
            return
        if is_rpc_enabled:
            self.init_rpc()
            self._ensure_rpc_update_timer()
        else:
            self.shutdown_rpc()


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
