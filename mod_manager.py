import importlib.machinery
import importlib.util
import json
import os

from gtk_compat import GLib

from defaults import BASE_CURRENCIES, BASE_UPGRADES, DEFAULT_ACHIEVEMENTS
from mod_api import (
    ModDependencyError,
    normalize_mod_dependencies,
    normalize_mod_id,
    version_meets_requirement,
)
from paths import SETTINGS_FILE, SYSTEM_MODS_DIR, USER_MODS_DIR, find_app_asset
from rpc import DEFAULT_GAME_TITLE
from save_manager import clone_json_data, save_json
from security import MOD_SECURITY_LEVEL_NAMES, scan_mod_security


class ModManagerMixin:
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
            "deprecation_warnings": [],
            "path": mod_dir,
        }

    def _add_mod_deprecation_warning(self, message: str, mod_info: dict = None):
        mod_info = mod_info or getattr(self, "_current_mod_info", None)
        if mod_info is None:
            return
        message = str(message or "").strip()
        if not message:
            return
        warnings = mod_info.setdefault("deprecation_warnings", [])
        if message in warnings:
            return
        warnings.append(message)
        self.console_print(
            f"[mods][deprecated] {mod_info.get('name') or mod_info.get('id')}: {message}"
        )

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
                self._mod_paths[mod_info["id"]] = mod_dir
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

    def _remove_widget_from_parent(self, widget):
        try:
            parent = widget.get_parent()
        except Exception:
            parent = None
        if parent is None:
            return
        try:
            parent.remove(widget)
        except Exception:
            pass

    def _remove_tab_page(self, tab_id: str):
        page = self._tab_pages.pop(tab_id, None)
        self._mod_tab_owners.pop(tab_id, None)
        if page is None or not hasattr(self, "notebook"):
            return
        try:
            page_num = self.notebook.page_num(page)
            if page_num >= 0:
                self.notebook.remove_page(page_num)
        except Exception:
            pass

    def _remove_mod_runtime_objects(self):
        for timer_id, timer_info in list(self._mod_timers.items()):
            if timer_info.get("owner") == "__global__":
                continue
            try:
                GLib.source_remove(timer_info["source_id"])
            except Exception:
                pass
            self._mod_timers.pop(timer_id, None)

        for event_name in list(self._event_hooks.keys()):
            kept = [hook for hook in self._event_hooks[event_name] if hook.get("owner") == "__global__"]
            if kept:
                self._event_hooks[event_name] = kept
            else:
                self._event_hooks.pop(event_name, None)

        for key, modifier_info in list(self._click_modifiers.items()):
            if modifier_info.get("owner") != "__global__":
                self._click_modifiers.pop(key, None)

        for api_name, api_info in list(self.mod_apis.items()):
            if api_info.get("owner") != "__global__":
                self.unregister_api(api_name)

        for command_name, command_info in list(self.console_commands.items()):
            if command_info.get("owner") != "__global__":
                self.unregister_console_command(command_name)
        self._register_default_console_commands()

        for item in list(self._mod_button_widgets):
            widget = item.get("widget") if isinstance(item, dict) else item
            self._remove_widget_from_parent(widget)
        self._mod_button_widgets.clear()

        for handle in list(self._mod_image_widgets):
            if getattr(handle, "owner", "__global__") == "__global__":
                continue
            handle.remove()

        for sprite_id, sprite in list(self._mod_sprites.items()):
            if getattr(sprite, "owner", "__global__") == "__global__":
                continue
            sprite.remove()

        for layer_id, layer in list(self._mod_draw_layers.items()):
            if getattr(layer, "owner", "__global__") == "__global__":
                continue
            layer.remove()

        for tab_id in list(self._tab_pages.keys()):
            if tab_id not in self._builtin_tab_ids:
                self._remove_tab_page(tab_id)

        self._pending_tabs.clear()
        self._pending_buttons.clear()
        self._pending_images.clear()
        self._pending_sprites = [sprite for sprite in self._pending_sprites if getattr(sprite, "owner", "__global__") == "__global__"]
        self._pending_draw_layers = [layer for layer in self._pending_draw_layers if getattr(layer, "owner", "__global__") == "__global__"]

    def _reset_mod_registries(self):
        self.currencies = clone_json_data(BASE_CURRENCIES)
        self.upgrades = clone_json_data(BASE_UPGRADES)
        self.primary_currency = "flesh"
        self.flesh_image_path = find_app_asset("flesh.png")
        self.click_sound_path = find_app_asset("click.wav")
        self._mod_currency_owners = {}
        self._mod_upgrade_owners = {}
        self._mod_tab_owners = {}
        self._mod_paths = {}
        self.current_game_title = DEFAULT_GAME_TITLE
        for key, value in DEFAULT_ACHIEVEMENTS.items():
            existing = self.achievements.get(key)
            if not isinstance(existing, dict):
                existing = {}
            merged = dict(value)
            merged.update(existing)
            merged["source"] = "builtin"
            merged.pop("mod_id", None)
            merged.pop("mod_name", None)
            self.achievements[key] = merged
        if hasattr(self, "upgrades_listbox"):
            self.clear_box_children(self.upgrades_listbox)
            self._upgrade_rows = {}
        self.invalidate_rate_cache()

    def _refresh_after_mod_reload(self):
        self._apply_selected_game_title()
        if hasattr(self, "picture"):
            self.load_flesh_image()
        self.refresh_upgrades_ui()
        self.refresh_achievements_ui()
        if hasattr(self, "mods_list_box"):
            self.refresh_mod_settings_list()
        self.update_labels()

    def reload_mods(self):
        self.flush_dirty_save(auto_backup=False)
        self._current_mod_info = None
        self._remove_mod_runtime_objects()
        self._reset_mod_registries()
        self.installed_mods = []
        self.loaded_mod_ids = set()
        self.load_mods()
        self._refresh_after_mod_reload()
        loaded = len(self.loaded_mod_ids)
        paused = sum(1 for mod in self.installed_mods if mod.get("security_blocked") or mod.get("dependency_blocked"))
        disabled = sum(1 for mod in self.installed_mods if not mod.get("enabled"))
        return f"Reloaded mods. Loaded: {loaded}. Paused: {paused}. Disabled: {disabled}."
