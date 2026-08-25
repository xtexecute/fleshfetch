import time

from gtk_compat import Gtk


class StatsUiMixin:
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
