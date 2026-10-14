import random

from gtk_compat import GLib


class GameStateMixin:
    def get_currency(self, registry_name: str) -> float:
        return float(self.state["currencies"].get(registry_name, 0.0))

    def set_currency(self, registry_name: str, value: float):
        self.state["currencies"][registry_name] = max(0.0, float(value))
        self.mark_save_dirty(auto_backup=True)

    def add_currency(self, registry_name: str, amount: float):
        self.set_currency(registry_name, self.get_currency(registry_name) + amount)

    @property
    def flesh(self) -> float:
        return self.get_currency("flesh")

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

    def start_runtime_services(self):
        if self._runtime_services_started:
            return
        self._runtime_services_started = True
        GLib.timeout_add(1000, self.on_timer_tick)

        if self.settings.get("enable_rpc"):
            self.init_rpc()
            self._ensure_rpc_update_timer()

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
                result = self._run_with_mod_owner(modifier_info.get("owner"), callback, context)
            except Exception as exc:
                print(f"[click modifiers] Modifier '{modifier_info.get('key', '?')}' failed: {exc}")
                continue
            if result is None and isinstance(context.get("gains"), dict) and context["gains"] != final_gains:
                result = {"triggered": True, "gains": context["gains"]}
            self._apply_click_modifier_result(final_gains, modifier_info, result, modifier_events)

        return final_gains, modifier_events
