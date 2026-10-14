from gtk_compat import Gtk

from save_manager import (
    DEFAULT_SAVE_KIND,
    backup_display_name,
    backup_save_slot,
    list_save_backups,
    list_save_slots,
    load_save_slot_data,
    normalize_save_id,
    normalize_save_name,
    read_save_slot_file,
    save_name_to_filename,
)


class SaveUiMixin:
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

        slots = list_save_slots(DEFAULT_SAVE_KIND)
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
        slot = self.create_save_slot(name or "New Save", save_kind=DEFAULT_SAVE_KIND)
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
                    "save_kind": self.active_save_kind,
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
                    ok, message, slot = self.import_save_slot(path, expected_save_kind=DEFAULT_SAVE_KIND)
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
