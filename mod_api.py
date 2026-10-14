import os

from gtk_compat import GLib, Gtk

from defaults import BASE_UPGRADES, DEFAULT_ACHIEVEMENTS


EVENT_ALIASES = {
    "click": "flesh_clicked",
    "clicked": "flesh_clicked",
    "flesh_click": "flesh_clicked",
    "flesh_clicked": "flesh_clicked",
    "on_flesh_clicked": "flesh_clicked",
    "buy": "upgrade_bought",
    "bought": "upgrade_bought",
    "upgrade_buy": "upgrade_bought",
    "upgrade_bought": "upgrade_bought",
    "on_upgrade_bought": "upgrade_bought",
    "save": "save",
    "saved": "save",
    "on_save": "save",
    "load": "load",
    "loaded": "load",
    "on_load": "load",
}


class ModDependencyError(RuntimeError):
    def __init__(self, message, missing=None):
        super().__init__(message)
        self.missing = list(missing or [])


def normalize_mod_id(mod_id: str) -> str:
    return str(mod_id or "").strip()


def normalize_mod_dependencies(raw_dependencies):
    dependencies = []
    if not raw_dependencies:
        return dependencies
    if isinstance(raw_dependencies, (str, dict)):
        raw_dependencies = [raw_dependencies]
    if not isinstance(raw_dependencies, list):
        return dependencies
    for dep in raw_dependencies:
        if isinstance(dep, str):
            dep_id = normalize_mod_id(dep)
            if dep_id:
                dependencies.append({"id": dep_id, "version": "", "optional": False})
        elif isinstance(dep, dict):
            dep_id = normalize_mod_id(dep.get("id") or dep.get("name") or dep.get("mod"))
            if dep_id:
                dependencies.append({
                    "id": dep_id,
                    "version": str(dep.get("version") or dep.get("min_version") or ""),
                    "optional": bool(dep.get("optional", False)),
                })
    return dependencies


def version_meets_requirement(version: str, required: str) -> bool:
    if not required:
        return True
    version = str(version or "")
    required = str(required or "")
    if version == required:
        return True

    def parts(text):
        values = []
        for piece in text.replace("-", ".").split("."):
            digits = "".join(ch for ch in piece if ch.isdigit())
            values.append(int(digits or 0))
        return values

    current_parts = parts(version)
    required_parts = parts(required)
    size = max(len(current_parts), len(required_parts))
    current_parts += [0] * (size - len(current_parts))
    required_parts += [0] * (size - len(required_parts))
    return current_parts >= required_parts


class ModApiMixin:
    def _normalize_event_name(self, event_name: str) -> str:
        name = str(event_name or "").strip().lower().replace("-", "_").replace(" ", "_")
        return EVENT_ALIASES.get(name, name)

    def _current_mod_namespace(self, namespace=None) -> str:
        if namespace:
            return str(namespace).strip()
        current = getattr(self, "_current_mod_info", None)
        if current is not None and current.get("id"):
            return current["id"]
        active_owner = getattr(self, "_active_mod_owner", None)
        if active_owner:
            return active_owner
        return "__global__"

    def _run_with_mod_owner(self, owner, callback, *args, **kwargs):
        previous_owner = getattr(self, "_active_mod_owner", None)
        self._active_mod_owner = owner if owner and owner != "__global__" else None
        try:
            return callback(*args, **kwargs)
        finally:
            self._active_mod_owner = previous_owner

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
                self._run_with_mod_owner(hook.get("owner"), callback, event_payload)
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
                result = self._run_with_mod_owner(owner, callback)
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

    def _normalize_api_name(self, name: str) -> str:
        return str(name or "").strip().lower().replace("-", "_").replace(" ", "_")

    def _resolve_api_name(self, name: str) -> str:
        api_name = self._normalize_api_name(name)
        return self.mod_api_aliases.get(api_name, api_name)

    def register_api(self, name: str, api, version="", description="", aliases=None, replace=False):
        """Register a shared API object for other mods to use.

        Example:
            game.register_api("particles", ParticleAPI(game), version="1.0.0")

        Other mods can then call:
            particles = game.require_api("particles")
        """
        api_name = self._normalize_api_name(name)
        if not api_name:
            raise ValueError("register_api() requires a non-empty API name")
        if api is None:
            raise ValueError("register_api() requires an API object")

        existing = self.mod_apis.get(api_name)
        owner = self._current_mod_namespace()
        if existing and not replace and existing.get("owner") != owner:
            raise ValueError(f"API '{api_name}' is already registered by {existing.get('owner', 'unknown')}")

        alias_list = []
        for alias in aliases or []:
            alias_name = self._normalize_api_name(alias)
            if alias_name and alias_name != api_name and alias_name not in alias_list:
                alias_list.append(alias_name)

        for alias_name in alias_list:
            alias_target = self.mod_api_aliases.get(alias_name)
            if alias_target and alias_target != api_name and not replace:
                raise ValueError(f"API alias '{alias_name}' is already registered for {alias_target}")

        if existing:
            self.unregister_api(api_name)

        api_info = {
            "name": api_name,
            "api": api,
            "version": str(version or ""),
            "description": str(description or ""),
            "aliases": alias_list,
            "owner": owner,
        }
        self.mod_apis[api_name] = api_info
        for alias in alias_list:
            self.mod_api_aliases[alias] = api_name
        return api

    def unregister_api(self, name: str):
        api_name = self._resolve_api_name(name)
        api_info = self.mod_apis.pop(api_name, None)
        if not api_info:
            return False
        api = api_info.get("api")
        for cleanup_name in ("cleanup", "shutdown", "destroy"):
            cleanup = getattr(api, cleanup_name, None)
            if callable(cleanup):
                try:
                    self._run_with_mod_owner(api_info.get("owner"), cleanup)
                except Exception as exc:
                    print(f"[apis] Cleanup for '{api_name}' failed: {exc}")
                break
        for alias in api_info.get("aliases", []):
            if self.mod_api_aliases.get(alias) == api_name:
                self.mod_api_aliases.pop(alias, None)
        return True

    def get_api(self, name: str, default=None):
        api_name = self._resolve_api_name(name)
        api_info = self.mod_apis.get(api_name)
        if not api_info:
            return default
        return api_info.get("api", default)

    def get_api_info(self, name: str):
        api_name = self._resolve_api_name(name)
        api_info = self.mod_apis.get(api_name)
        if not api_info:
            return None
        return {
            "name": api_info.get("name", api_name),
            "version": api_info.get("version", ""),
            "description": api_info.get("description", ""),
            "aliases": list(api_info.get("aliases", [])),
            "owner": api_info.get("owner", ""),
        }

    def has_api(self, name: str, min_version: str = "") -> bool:
        api_name = self._resolve_api_name(name)
        api_info = self.mod_apis.get(api_name)
        if not api_info:
            return False
        return version_meets_requirement(api_info.get("version", ""), min_version)

    def require_api(self, name: str, min_version: str = ""):
        if self.has_api(name, min_version):
            return self.get_api(name)
        api_name = self._normalize_api_name(name)
        requirement = api_name if not min_version else f"{api_name} >= {min_version}"
        raise ModDependencyError(f"Missing required API: {requirement}", [requirement])

    def list_apis(self):
        return [
            self.get_api_info(api_name)
            for api_name in sorted(self.mod_apis)
            if self.get_api_info(api_name) is not None
        ]

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
        owner = self._current_mod_namespace()
        if owner != "__global__":
            self._mod_currency_owners[registry_name] = owner
        self.invalidate_rate_cache()
        self.mark_save_dirty(auto_backup=False)

    def register_upgrade(self, uid: str, data: dict):
        """Add or update an upgrade in the registry."""
        if isinstance(data, dict):
            legacy_fields = [field for field in ("fpc", "fps") if field in data]
            if legacy_fields and "currency_effects" not in data:
                fields = ", ".join(legacy_fields)
                self._add_mod_deprecation_warning(
                    f"Upgrade '{uid}' uses legacy {fields} fields. Use currency_effects with cpc/cps instead."
                )
            if "type" in data and "category" not in data:
                self._add_mod_deprecation_warning(
                    f"Upgrade '{uid}' uses legacy type. Use category instead."
                )
        if uid in self.upgrades:
            self.upgrades[uid].update(data)
        else:
            self.upgrades[uid] = data
        owner = self._current_mod_namespace()
        if owner != "__global__":
            self._mod_upgrade_owners[uid] = owner
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
        if hasattr(self, "picture"):
            self.load_flesh_image()

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

        owner = self._current_mod_namespace()
        if owner != "__global__":
            self._mod_tab_owners[tab_id] = owner

        if hasattr(self, "notebook"):
            # UI already built — add immediately
            self.notebook.append_page(page_box, Gtk.Label(label=label))
            self._tab_pages[tab_id] = page_box
            # flush any buttons that were queued for this tab
            for pending in self._pending_buttons.pop(tab_id, []):
                if len(pending) == 2:
                    btn_label, callback = pending
                    button_owner = owner
                else:
                    btn_label, callback, button_owner = pending
                btn = Gtk.Button(label=btn_label)
                btn.connect("clicked", lambda b, cb=callback: cb(b))
                page_box.append(btn)
                if button_owner != "__global__":
                    self._mod_button_widgets.append({"owner": button_owner, "widget": btn, "tab_id": tab_id})
        else:
            self._pending_tabs.append((tab_id, label, page_box, owner))

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
        owner = self._current_mod_namespace()
        if page is not None:
            btn = Gtk.Button(label=label)
            btn.connect("clicked", lambda b, cb=callback: cb(b))
            page.append(btn)
            if owner != "__global__":
                self._mod_button_widgets.append({"owner": owner, "widget": btn, "tab_id": tab_id})
        else:
            self._pending_buttons.setdefault(tab_id, []).append((label, callback, owner))

    def add_button(self, tab_id: str, label: str, callback):
        """Compatibility alias for add_tab_button()."""
        self._add_mod_deprecation_warning("add_button() is deprecated. Use add_tab_button() instead.")
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
