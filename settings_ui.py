from gtk_compat import Gtk

from defaults import DEFAULT_SETTINGS
from paths import SETTINGS_FILE
from rpc import DEFAULT_GAME_TITLE
from save_manager import save_json
from security import MOD_SECURITY_LEVEL_NAMES


class SettingsUiMixin:
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

        auto_reload_label = Gtk.Label(label="Auto reload mod changes", xalign=0)
        grid.attach(auto_reload_label, 0, row, 1, 1)
        self.mod_auto_reload_switch = Gtk.Switch()
        self.mod_auto_reload_switch.set_halign(Gtk.Align.START)
        self.mod_auto_reload_switch.set_hexpand(False)
        self.mod_auto_reload_switch.set_active(bool(self.settings.get(
            "auto_reload_mod_changes",
            DEFAULT_SETTINGS["auto_reload_mod_changes"],
        )))
        self.mod_auto_reload_switch.connect("notify::active", self.on_settings_changed)
        grid.attach(self.mod_auto_reload_switch, 1, row, 1, 1)
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
            deprecation_warnings = list(mod_info.get("deprecation_warnings") or [])
            if dependency_blocked:
                status = "Missing dependencies"
            elif security_level == 0:
                status = "Enabled" if mod_info.get("enabled") else "Disabled"
                if deprecation_warnings:
                    status += ", deprecation warnings"
            elif blocked:
                status = f"{security_label} warning"
            elif warning_dismissed:
                state = "Enabled" if mod_info.get("enabled") else "Disabled"
                status = f"{state}, warning dismissed"
                if deprecation_warnings:
                    status += ", deprecation warnings"
            else:
                status = "Enabled" if mod_info.get("enabled") else "Disabled"
                if deprecation_warnings:
                    status += ", deprecation warnings"

            mod_display_name = mod_info.get("name") or mod_info["id"]
            if deprecation_warnings:
                mod_display_name = f"{mod_display_name} (legacy)"
            expander_label = Gtk.Label(label=f"{mod_display_name} ({status})", xalign=0)
            if security_level == 1:
                expander_label.add_css_class("security-suspicious")
            elif security_level >= 2:
                expander_label.add_css_class("security-extreme")
            elif deprecation_warnings:
                expander_label.add_css_class("mod-deprecation")

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
            provided_apis = [
                api_info
                for api_info in self.list_apis()
                if api_info.get("owner") == mod_info.get("id")
            ]
            if provided_apis:
                api_names = []
                for api_info in provided_apis:
                    api_text = api_info.get("name") or "unknown"
                    if api_info.get("version"):
                        api_text += f" {api_info['version']}"
                    api_names.append(api_text)
                meta_lines.append(("APIs", ", ".join(api_names)))
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
            if deprecation_warnings:
                for warning in deprecation_warnings:
                    warning_label = Gtk.Label(label=f"Deprecation warning: {warning}", xalign=0)
                    warning_label.set_wrap(True)
                    warning_label.add_css_class("mod-deprecation")
                    details.append(warning_label)
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
                self._finish_mod_change(
                    f"Warning dismissed for '{mod_info.get('name', mod_info['id'])}'.",
                    "load it",
                )
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
        self._finish_mod_change(
            f"Mod '{mod_info.get('name', mod_info['id'])}' {state}.",
            "apply",
        )

    def _auto_reload_mod_changes_enabled(self):
        return bool(self.settings.get(
            "auto_reload_mod_changes",
            DEFAULT_SETTINGS.get("auto_reload_mod_changes", True),
        ))

    def _finish_mod_change(self, message: str, action_text="apply"):
        if self._auto_reload_mod_changes_enabled():
            reload_message = self.reload_mods()
            self.settings_info_label.set_text(f"{message} {reload_message}")
        else:
            self.settings_info_label.set_text(
                f"{message} Run /reload or restart Fleshfetch to {action_text}."
            )
            self.refresh_mod_settings_list()

    def on_settings_changed(self, *args):
        was_rpc_enabled = bool(self.settings.get("enable_rpc"))
        is_rpc_enabled = self.rpc_switch.get_active()

        self.settings["enable_rpc"]           = is_rpc_enabled
        self.settings["squish_ms"]            = int(self.squish_spin.get_value())
        self.settings["play_click_sound"]     = self.sound_switch.get_active()
        self.settings["click_sound_volume"]   = int(self.volume_slider.get_value())
        self.settings["auto_reload_mod_changes"] = self.mod_auto_reload_switch.get_active()
        save_json(SETTINGS_FILE, self.settings)

        if is_rpc_enabled == was_rpc_enabled:
            return
        if is_rpc_enabled:
            self.init_rpc()
            self._ensure_rpc_update_timer()
        else:
            self.shutdown_rpc()
