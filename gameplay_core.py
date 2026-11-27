"""Toolkit-free gameplay actions shared by frontends."""

from collections import deque
import time

from mod_api import vanilla_enabled


def accept_manual_click(game, now=None):
    """Throttle rewarded clicks after sustained implausible input speed."""
    now = time.monotonic() if now is None else now
    attempts = getattr(game, "_click_attempts", None)
    if attempts is None:
        attempts = game._click_attempts = deque(maxlen=64)
    while attempts and now - attempts[0] > 1.0:
        attempts.popleft()
    attempts.append(now)

    capped_until = getattr(game, "_click_rate_capped_until", 0.0)
    implausible = len(attempts) >= 25 or (len(attempts) >= 16 and now - attempts[0] >= 0.5)
    if implausible:
        if now >= capped_until and hasattr(game, "_set_status"):
            game._set_status("Click speed limited to 7 per second.")
        capped_until = game._click_rate_capped_until = now + 10.0

    if now < capped_until and now - getattr(game, "_last_rewarded_click_at", float("-inf")) < 1.0 / 7.0:
        return False
    game._last_rewarded_click_at = now
    return True


class GameplayCoreMixin:
    """Combine with the state/mod/save APIs and frontend hooks.

    Frontends implement update_labels(), play_click_sound(), play_squish(),
    _apply_upgrade_visibility(), and refresh_achievements_ui(). Input callbacks
    retain their original frontend-compatible arguments; purchases return bool.
    """

    def check_requires(self, uid: str) -> bool:
        """Return True if all requirements for an upgrade are satisfied.

        The ``requires`` field on an upgrade can be a single dict or a list
        of dicts.  Each dict may contain:

            upgrade  (str)  - another upgrade uid that must be owned
            count    (int)  - minimum number of that upgrade owned (default 1)
            currency (str)  - a currency registry name
            amount   (float)- minimum amount of that currency required (default 0)

        All conditions in a single dict must be satisfied (AND logic).
        If ``requires`` is a list, *any* one dict being satisfied is enough
        (OR logic between list items, AND within each item).

        Example - require lignification AND at least 500 wood::

            "requires": {"upgrade": "lignification", "currency": "wood", "amount": 500}

        Example - require either sapwood OR heartwood::

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

    def on_timer_tick(self):
        if hasattr(self, "advance_streak"):
            self.advance_streak()
        for reg_name in self.currencies:
            cps = self.compute_cps(reg_name)
            if cps > 0:
                self.add_currency(reg_name, cps)
                if reg_name == "flesh" and hasattr(self, "record_flesh_earned"):
                    self.record_flesh_earned(cps)
        if hasattr(self, "expire_boosts"):
            self.expire_boosts()
        self.update_labels()
        return True

    def on_buy_upgrade_clicked(self, button, uid: str) -> bool:
        if uid not in self.upgrades or not self.check_requires(uid):
            return False

        owned         = self.get_upgrade_count(uid)
        cost          = self.get_upgrade_cost(uid, owned)
        cost_currency = self.upgrades[uid].get("cost_currency", "flesh")

        if self.get_currency(cost_currency) < cost:
            return False

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
        from vanilla_shop import check_shop_achievements
        check_shop_achievements(self)

        # Update cost labels and visibility in-place -- no rebuild, no scroll jump
        self._apply_upgrade_visibility()
        self.update_labels()
        return True

    def on_click(self, gesture, n_press, x, y):
        if not vanilla_enabled(self, "clicker") or not accept_manual_click(self):
            self._last_click_gains = {}
            self._last_click_critical = False
            return False
        if hasattr(self, "register_streak_click"):
            self.register_streak_click()
        self.play_squish()
        self.play_click_sound()

        base_gains = {}
        for reg_name in self.currencies:
            gain = self.compute_click_gain(reg_name)
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

        self._last_click_gains = dict(gains)
        self._last_click_critical = crit_multiplier > 1.0

        for reg_name, gain in gains.items():
            if gain:
                self.add_currency(reg_name, gain)
                if reg_name == "flesh" and hasattr(self, "record_flesh_earned"):
                    self.record_flesh_earned(gain)

        if hasattr(self, "maybe_drop_crate"):
            self.maybe_drop_crate()

        self.state["total_clicks"] = next_total_clicks
        if hasattr(self, "_skin_clicked"):
            self._skin_clicked({"x": x, "y": y, "gains": dict(gains), "total_clicks": next_total_clicks})
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
        return True

    def unlock_achievement(self, key: str):
        if key not in self.achievements:
            return
        if not self._achievement_is_active(key, self.achievements[key]):
            return
        if not self.achievements[key].get("unlocked", False):
            self.achievements[key]["unlocked"] = True
            self.mark_save_dirty(auto_backup=False)
            self.refresh_achievements_ui()

