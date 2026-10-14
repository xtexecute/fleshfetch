from gtk_compat import Gtk


class UiLayoutMixin:
    def build_ui(self):
        self._window_overlay = Gtk.Overlay()
        self._window_overlay.set_hexpand(True)
        self._window_overlay.set_vexpand(True)

        root = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        root.set_wide_handle(True)
        self._window_overlay.set_child(root)

        self._sprite_layer = Gtk.Fixed()
        self._sprite_layer.set_hexpand(True)
        self._sprite_layer.set_vexpand(True)
        self._sprite_layer.set_halign(Gtk.Align.FILL)
        self._sprite_layer.set_valign(Gtk.Align.FILL)
        self._sprite_layer.set_can_target(False)
        self._window_overlay.add_overlay(self._sprite_layer)
        self.set_child(self._window_overlay)

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
        for pending_tab in self._pending_tabs:
            if len(pending_tab) == 3:
                tab_id, label, page_box = pending_tab
                tab_owner = "__global__"
            else:
                tab_id, label, page_box, tab_owner = pending_tab
            self.notebook.append_page(page_box, Gtk.Label(label=label))
            self._tab_pages[tab_id] = page_box
            if tab_owner != "__global__":
                self._mod_tab_owners[tab_id] = tab_owner

        # flush mod buttons queued before build_ui ran
        for tab_id, buttons in self._pending_buttons.items():
            page = self._tab_pages.get(tab_id)
            if page is None:
                continue
            for pending_button in buttons:
                if len(pending_button) == 2:
                    btn_label, callback = pending_button
                    button_owner = "__global__"
                else:
                    btn_label, callback, button_owner = pending_button
                btn = Gtk.Button(label=btn_label)
                btn.connect("clicked", lambda b, cb=callback: cb(b))
                page.append(btn)
                if button_owner != "__global__":
                    self._mod_button_widgets.append({"owner": button_owner, "widget": btn, "tab_id": tab_id})

        # flush mod images queued before build_ui ran
        for tab_id, image_handles in self._pending_images.items():
            page = self._tab_pages.get(tab_id)
            if page is None:
                continue
            for handle in image_handles:
                page.append(handle.widget)
        self._pending_images.clear()

        for sprite in list(self._pending_sprites):
            self._attach_sprite(sprite)
        self._pending_sprites.clear()

        for layer in list(self._pending_draw_layers):
            self._attach_draw_layer(layer)
        self._pending_draw_layers.clear()

        self.refresh_upgrades_ui()
        self.refresh_achievements_ui()
        root.set_end_child(right_box)
