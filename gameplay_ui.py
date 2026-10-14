import os
import sys
import time

from gtk_compat import Gdk, GLib, Gtk

from defaults import DEFAULT_SETTINGS


class GameplayUiMixin:
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

    def load_flesh_image(self):
        if not hasattr(self, "picture"):
            return  # UI not built yet — build_ui() will call this again
        try:
            texture = Gdk.Texture.new_from_filename(self.flesh_image_path)
            self.picture.set_paintable(texture)
        except Exception as e:
            print(f"Failed to load image '{self.flesh_image_path}':", e)

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

    def unlock_achievement(self, key: str):
        if key not in self.achievements:
            return
        if not self._achievement_is_active(key, self.achievements[key]):
            return
        if not self.achievements[key].get("unlocked", False):
            self.achievements[key]["unlocked"] = True
            self.mark_save_dirty(auto_backup=False)
            self.refresh_achievements_ui()
