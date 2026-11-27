"""Runtime progression definitions. Saves contain IDs and counts, never callbacks."""

import math
import os
import random

from mod_api import vanilla_enabled


def number(value, name, minimum=0, maximum=None):
    value = float(value)
    if not math.isfinite(value) or value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f"Invalid {name}")
    return value


def integer(value, name, minimum=1, maximum=1000):
    result = int(number(value, name, minimum, maximum))
    if result != float(value):
        raise ValueError(f"{name} must be an integer")
    return result


class ProgressionRegistryMixin:
    @staticmethod
    def _asset_url(path):
        if not path:
            return ""
        from pathlib import Path
        return Path(path).resolve().as_uri()

    def _ensure_progression_registry(self):
        if hasattr(self, "_progression_registry"):
            return
        from progression import (RARITIES, RARITY_COLORS, GEAR, COSMETICS, COSMETIC_FEATURES,
                                 CRATE_COSMETICS, POTIONS, RUN_UPGRADES, REBIRTH_UPGRADES,
                                 CRATE_TIERS, CRATE_COSTS, CRATE_WEIGHTS)
        self._progression_registry = {key: {} for key in
            ("rarities", "equipment", "skins", "potions", "run_upgrades", "rebirth_upgrades", "crates")}
        self._streak_settings = {}
        self._skin_frame = None
        tables = self._progression_registry
        def put(table, key, **data):
            tables[table][key] = dict(data, id=key, owner="__vanilla__")
        for rank, key in enumerate(RARITIES):
            put("rarities", key, name=key, color=RARITY_COLORS[key], rank=rank)
        for key, (name, rarity, stat, amount) in GEAR.items():
            put("equipment", key, name=name, rarity=rarity, bonuses={stat: amount},
                max_level=10, level_growth=0.2, icon="")
        for key, (name, rarity, color) in COSMETICS.items():
            put("skins", key, name=name, rarity=rarity, color=color, description=COSMETIC_FEATURES.get(key, ""),
                crate_pool=key in CRATE_COSMETICS, image="", overlay="", icon="", click_sound="", on_click=None)
        for key, (name, desc, stat, duration) in POTIONS.items():
            put("potions", key, name=name, description=desc, stat=stat, duration=duration,
                amount=1 if stat == "drop" else 2, mode="add" if stat == "drop" else "multiply", icon="")
        for key, (name, desc) in RUN_UPGRADES.items():
            put("run_upgrades", key, name=name, description=desc, stat=key, amount=0.08 if key == "drop" else 0.05)
        for key, (name, desc, cap) in REBIRTH_UPGRADES.items():
            put("rebirth_upgrades", key, name=name, description=desc, max_level=cap, currency="tokens")
        for key in CRATE_TIERS:
            currency, cost = CRATE_COSTS[key]
            put("crates", key, name=key, kinds=("equipment", "cosmetic"), currency=currency, cost=cost,
                rarity_weights=dict(zip(RARITIES, CRATE_WEIGHTS[key])), icon="", color=RARITY_COLORS[key],
                pity_after=10 if key == "Legendary" else 12 if key == "Mythical" else 0,
                pity_rarity="Mythical" if key == "Legendary" else "Radiant", drop_chance=0)

    def _progression_defs(self, table, *, all_items=False):
        self._ensure_progression_registry()
        part = {"skins": "cosmetics", "potions": "equipment", "run_upgrades": "equipment",
                "rebirth_upgrades": "rebirth"}.get(table, table)
        return {key: item for key, item in self._progression_registry[table].items()
                if all_items or item["owner"] != "__vanilla__" or vanilla_enabled(self, part)}

    def _progression_items(self, table, *, all_items=False):
        items = self._progression_defs(table, all_items=all_items)
        if table == "equipment":
            return {key: (d["name"], d["rarity"], next(iter(d["bonuses"])), next(iter(d["bonuses"].values())))
                    for key, d in items.items()}
        if table == "skins":
            return {key: (d["name"], d["rarity"], d["color"]) for key, d in items.items() if d["crate_pool"]}
        if table == "potions":
            return {key: (d["name"], d["description"], d["stat"], d["duration"]) for key, d in items.items()}
        if table == "run_upgrades":
            return {key: (d["name"], d["description"]) for key, d in items.items()}
        return {key: (d["name"], d["description"], d["max_level"]) for key, d in items.items()}

    def _definition_id(self, table, value):
        value = str(value)
        items = self._progression_defs(table, all_items=True)
        owner = self._current_mod_namespace() if hasattr(self, "_current_mod_namespace") else "__global__"
        local = f"{owner}:{value}"
        return local if local in items else value

    def _require_definition(self, table, value):
        key = self._definition_id(table, value)
        if key not in self._progression_defs(table, all_items=True):
            raise ValueError(f"Unknown {table} ID: {value}")
        return key

    def _register_progression(self, table, key, data):
        owner = self._current_mod_namespace()
        key = str(key).strip()
        if not key or any(c.isspace() for c in key) or ":" in key:
            raise ValueError("Use a nonempty local ID without spaces or colons")
        key = f"{owner}:{key}" if owner != "__global__" else key
        if key in self._progression_defs(table, all_items=True):
            raise ValueError(f"{table} ID already registered: {key}")
        if not isinstance(data.get("name"), str) or not data["name"].strip():
            raise ValueError("A display name is required")
        self._progression_registry[table][key] = dict(data, id=key, owner=owner)
        self._mod_registry_changed()
        return key

    def _progression_asset(self, path):
        if not path:
            return ""
        resolver = getattr(self, "resolve_asset_path", None)
        result = resolver(path) if resolver else os.path.abspath(os.fspath(path))
        if not result or not os.path.isfile(result):
            raise ValueError(f"Asset not found: {path}")
        return result

    def _rarity_rank(self, key):
        return self._progression_defs("rarities", all_items=True)[key]["rank"]

    def register_rarity(self, rarity_id, *, name, color, rank):
        import re
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(color)):
            raise ValueError("Rarity color must be #RRGGBB")
        return self._register_progression("rarities", rarity_id,
            dict(name=name, color=color, rank=number(rank, "rank", 0, 1000)))

    def register_equipment(self, item_id, *, name, rarity="Common", bonuses,
                           max_level=10, level_growth=0.2, icon=None):
        if not bonuses or set(bonuses) - {"click", "cps", "drop", "luck"}:
            raise ValueError("Equipment bonuses support click, cps, drop and luck")
        return self._register_progression("equipment", item_id, dict(name=name,
            rarity=self._require_definition("rarities", rarity),
            bonuses={stat: number(amount, "bonus") for stat, amount in bonuses.items()},
            max_level=integer(max_level, "max_level"), level_growth=number(level_growth, "level_growth"),
            icon=self._progression_asset(icon)))

    def register_skin(self, skin_id, *, name, rarity="Common", image=None, overlay=None,
                      icon=None, click_sound=None, sound_profile="default", description="",
                      crate_pool=True, on_click=None):
        if on_click is not None and not callable(on_click):
            raise ValueError("on_click must be callable")
        if sound_profile not in ("default", "organic", "mechanical"):
            raise ValueError("Unknown sound profile")
        rarity = self._require_definition("rarities", rarity)
        if not (icon or image or overlay):
            from paths import find_app_asset
            icon = find_app_asset("flesh.png")
        return self._register_progression("skins", skin_id, dict(name=name, rarity=rarity,
            color=self._progression_defs("rarities")[rarity]["color"], description=str(description),
            image=self._progression_asset(image), overlay=self._progression_asset(overlay),
            icon=self._progression_asset(icon or image or overlay), click_sound=self._progression_asset(click_sound),
            sound_profile=sound_profile, crate_pool=bool(crate_pool), on_click=on_click))

    def set_skin_frame(self, image):
        """Change the selected skin's image until deselection, save change or reload."""
        selected = self.active_cosmetic()
        if not selected:
            raise RuntimeError("No skin is selected")
        definition = self._progression_defs("skins")[selected]
        if definition["owner"] != self._current_mod_namespace():
            raise ValueError("A mod can only change its own skin frame")
        self._skin_frame = (getattr(self, "active_save_id", None), selected, self._progression_asset(image))
        self.update_labels()

    def _skin_image(self):
        selected = self.active_cosmetic()
        self._ensure_progression_registry()
        if self._skin_frame:
            if self._skin_frame[:2] == (getattr(self, "active_save_id", None), selected):
                return self._skin_frame[2]
            self._skin_frame = None
        return self._progression_defs("skins").get(selected, {}).get("image", "")

    def _skin_clicked(self, context):
        definition = self._progression_defs("skins").get(self.active_cosmetic(), {})
        callback = definition.get("on_click")
        if callback:
            try:
                self._run_with_mod_owner(definition["owner"], callback, dict(context, game=self))
            except Exception as exc:
                print(f"[skins] {definition['id']}: {exc}")

    def register_potion(self, potion_id, *, name, stat, duration, amount=2,
                        mode="multiply", description="", icon=None):
        self._validate_stat(stat)
        if mode not in ("add", "multiply"):
            raise ValueError("Potion mode must be add or multiply")
        return self._register_progression("potions", potion_id, dict(name=name, description=str(description),
            stat=stat, duration=number(duration, "duration", 0.01, 604800),
            amount=number(amount, "amount", 0 if mode == "add" else 0.01), mode=mode,
            icon=self._progression_asset(icon)))

    @staticmethod
    def _validate_stat(stat):
        if stat not in ("click", "cps", "drop", "luck"):
            raise ValueError("Stat must be click, cps, drop or luck")

    def register_run_upgrade(self, upgrade_id, *, name, stat, amount, description=""):
        self._validate_stat(stat)
        return self._register_progression("run_upgrades", upgrade_id,
            dict(name=name, description=str(description), stat=stat, amount=number(amount, "amount")))

    def register_rebirth_upgrade(self, upgrade_id, *, name, stat, amount, base_cost,
                                 cost_multiplier=2, currency="tokens", max_level=10, description=""):
        self._validate_stat(stat)
        if currency not in self.currencies:
            raise ValueError("Register the currency before the upgrade")
        return self._register_progression("rebirth_upgrades", upgrade_id, dict(name=name,
            description=str(description), stat=stat, amount=number(amount, "amount"),
            base_cost=number(base_cost, "base_cost", 0.01), cost_multiplier=number(cost_multiplier, "cost_multiplier", 1),
            currency=currency, max_level=integer(max_level, "max_level")))

    def register_crate(self, crate_id, *, name, rarity_weights, kind="equipment", currency="flesh",
                       cost=0, rewards=None, icon=None, drop_chance=0, pity_after=0, pity_rarity=None):
        if kind not in ("equipment", "cosmetic") or currency not in self.currencies:
            raise ValueError("Unknown crate kind or currency")
        weights = {self._require_definition("rarities", key): number(value, "rarity weight")
                   for key, value in rarity_weights.items()}
        weights = {key: value for key, value in weights.items() if value > 0}
        if not weights:
            raise ValueError("At least one rarity must have positive weight")
        pity_after = integer(pity_after, "pity_after", 0, 100000)
        pity_rarity = self._require_definition("rarities", pity_rarity) if pity_after else None
        if pity_after and pity_rarity not in weights:
            raise ValueError("Pity rarity must be in rarity_weights")
        entries = None
        if rewards is not None:
            entries = []
            tables = {"equipment": "equipment", "skin": "skins", "potion": "potions",
                      "run_upgrade": "run_upgrades"}
            for reward in rewards:
                entry = dict(reward)
                reward_type = entry.get("type")
                if reward_type in tables:
                    entry["id"] = self._require_definition(tables[reward_type], entry["id"])
                    definition = self._progression_defs(tables[reward_type], all_items=True)[entry["id"]]
                    rarity = entry.get("rarity", definition.get("rarity", "Common"))
                elif reward_type == "currency" and entry.get("id") in self.currencies:
                    rarity = entry.get("rarity", "Common")
                else:
                    raise ValueError("Unknown crate reward type or currency")
                entry["rarity"] = self._require_definition("rarities", rarity)
                entry["weight"] = number(entry.get("weight", 1), "reward weight", 0.000001)
                entry["amount"] = integer(entry.get("amount", 1), "reward amount")
                entries.append(entry)
            if any(not any(r["rarity"] == rarity for r in entries) for rarity in weights):
                raise ValueError("Each weighted rarity needs at least one reward")
        else:
            table = "skins" if kind == "cosmetic" else "equipment"
            pool = self._progression_defs(table)
            if any(not any(d["rarity"] == rarity and (table != "skins" or d["crate_pool"])
                           for d in pool.values()) for rarity in weights):
                raise ValueError("Register an item for each weighted rarity before its crate")
        color = self._progression_defs("rarities")[max(weights, key=self._rarity_rank)]["color"]
        return self._register_progression("crates", crate_id, dict(name=name, kinds=(kind,), currency=currency,
            cost=number(cost, "cost"), rarity_weights=weights, rewards=entries, icon=self._progression_asset(icon),
            color=color, drop_chance=number(drop_chance, "drop_chance", 0, 1),
            pity_after=pity_after, pity_rarity=pity_rarity))

    def _grant_progression_item(self, table, state_key, item_id, count):
        item_id = self._require_definition(table, item_id)
        if item_id not in self._progression_defs(table):
            raise RuntimeError("This content is disabled")
        count = integer(count, "count")
        inventory = self.progress[state_key]
        if table == "skins":
            if item_id not in inventory:
                inventory.append(item_id)
            result = 1
        else:
            cap = self._progression_defs(table)[item_id].get("max_level", math.inf)
            inventory[item_id] = min(cap, inventory.get(item_id, 0) + count)
            result = inventory[item_id]
        self._progress_changed()
        return result

    def grant_equipment(self, item_id, count=1):
        return self._grant_progression_item("equipment", "gear", item_id, count)

    def grant_skin(self, skin_id):
        return self._grant_progression_item("skins", "cosmetics", skin_id, 1)

    def grant_potion(self, potion_id, count=1):
        return self._grant_progression_item("potions", "potions", potion_id, count)

    def grant_run_upgrade(self, upgrade_id, count=1):
        return self._grant_progression_item("run_upgrades", "run_upgrades", upgrade_id, count)

    def select_skin(self, skin_id):
        return self.select_cosmetic(skin_id)

    def _equipment_bonus(self, item_id, stat, level):
        item = self._progression_defs("equipment").get(item_id)
        if not item:
            return 0
        return item["bonuses"].get(stat, 0) * (1 + item["level_growth"] * math.sqrt(max(0, min(item["max_level"], level) - 1)))

    def _custom_progression_bonus(self, stat):
        p = self.progress
        bonus = 0
        for table in ("run_upgrades", "rebirth_upgrades"):
            for key, level in p[table].items():
                definition = self._progression_defs(table).get(key, {})
                if definition.get("owner") != "__vanilla__" and definition.get("stat") == stat:
                    bonus += definition["amount"] * min(level, definition.get("max_level", level))
        return bonus

    def _registered_crate_reward(self, crate, kind, rarity):
        entries = crate["rewards"]
        if entries is None:
            table, reward_type, state_key = ("skins", "skin", "cosmetics") if kind == "cosmetic" else ("equipment", "equipment", "gear")
            entries = [dict(type=reward_type, id=key, rarity=rarity, weight=1, amount=1)
                       for key, d in self._progression_defs(table).items() if d["rarity"] == rarity
                       and (table != "skins" or d["crate_pool"])]
        candidates = []
        tables = {"equipment": ("equipment", "gear"), "skin": ("skins", "cosmetics"),
                  "potion": ("potions", "potions"), "run_upgrade": ("run_upgrades", "run_upgrades")}
        for entry in entries:
            if entry["rarity"] != rarity:
                continue
            if entry["type"] == "currency":
                if entry["id"] in self.currencies:
                    candidates.append(entry)
                continue
            table, state_key = tables[entry["type"]]
            definition = self._progression_defs(table).get(entry["id"])
            if not definition:
                continue
            owned = self.progress[state_key]
            if table == "skins" and entry["id"] in owned:
                continue
            if table == "equipment" and owned.get(entry["id"], 0) >= definition["max_level"]:
                continue
            candidates.append(entry)
        if not candidates:
            return None
        entry = random.choices(candidates, weights=[r["weight"] for r in candidates], k=1)[0]
        key, count = entry["id"], entry["amount"]
        if entry["type"] == "currency":
            self.add_currency(key, count)
            return f"{count} {self.currencies[key].get('display_name', key)}"
        table, state_key = tables[entry["type"]]
        self._grant_progression_item(table, state_key, key, count)
        return self._progression_defs(table)[key]["name"]

    def _crate_item(self, reward_type, key, rarity, count=1, name=None):
        tables = {"equipment": "equipment", "skin": "skins", "potion": "potions", "run_upgrade": "run_upgrades"}
        definition = self._progression_defs(tables[reward_type], all_items=True).get(key, {}) if reward_type in tables else {}
        icon = self._asset_url(definition.get("icon", ""))
        if not icon and reward_type == "skin":
            icon = "image://skins/preview/" + key
        elif not icon and reward_type == "equipment":
            icon = "image://skins/loot/gear/" + (key if definition.get("owner") == "__vanilla__" else "wrist_wrap")
        elif not icon and reward_type == "potion":
            icon = "image://skins/loot/potion/" + (key if definition.get("owner") == "__vanilla__" else "quick_hands")
        elif not icon and reward_type == "run_upgrade":
            icon = "image://skins/loot/gear/wrist_wrap"
        elif not icon:
            crate = self._progression_defs("crates", all_items=True).get(key, {})
            icon = self._asset_url(crate.get("icon", "")) or "image://skins/loot/crate/" + (key if crate.get("owner") == "__vanilla__" else "Common")
        info = self._progression_defs("rarities")[rarity]
        return {"type": reward_type, "id": key, "name": name or definition.get("name", key),
                "rarity": rarity, "rarityName": info["name"], "color": info["color"], "icon": icon, "count": count}

    def crate_preview(self, kind, tier):
        """Eligible visual reel entries; this does not roll or award a reward."""
        tier = self._definition_id("crates", tier)
        crate = self._progression_defs("crates").get(tier)
        if not crate or kind not in crate["kinds"]:
            return []
        result = []
        for rarity, weight in crate["rarity_weights"].items():
            if weight <= 0:
                continue
            entries = []
            if crate.get("rewards") is not None:
                for reward in crate["rewards"]:
                    if reward["rarity"] != rarity:
                        continue
                    table = {"equipment": "equipment", "skin": "skins", "potion": "potions", "run_upgrade": "run_upgrades"}.get(reward["type"])
                    definition = self._progression_defs(table).get(reward["id"]) if table else None
                    if table and not definition:
                        continue
                    if reward["type"] == "skin" and reward["id"] in self.progress["cosmetics"]:
                        continue
                    if reward["type"] == "equipment" and self.progress["gear"].get(reward["id"], 0) >= definition["max_level"]:
                        continue
                    name = self.currencies.get(reward["id"], {}).get("display_name", reward["id"]) if reward["type"] == "currency" else None
                    item = self._crate_item(reward["type"], reward["id"], rarity, reward["amount"], name)
                    item["weight"] = reward["weight"]
                    entries.append(item)
            else:
                table, reward_type = ("skins", "skin") if kind == "cosmetic" else ("equipment", "equipment")
                for key, item in self._progression_defs(table, all_items=crate["owner"] == "__vanilla__").items():
                    if item["rarity"] != rarity or (table == "skins" and (not item["crate_pool"] or key in self.progress["cosmetics"])):
                        continue
                    entries.append(dict(self._crate_item(reward_type, key, rarity), weight=1))
                if kind == "equipment" and crate["owner"] == "__vanilla__":
                    fresh = [entry for entry in entries if entry["id"] not in self.progress["gear"]]
                    entries = fresh or entries
                if kind == "cosmetic" and not entries and crate["owner"] == "__vanilla__":
                    entries.append(dict(self._crate_item("crate", tier, rarity, name=crate["name"] + " equipment crate"), weight=1))
                if kind == "equipment" and crate["owner"] == "__vanilla__" and tier not in ("Legendary", "Mythical"):
                    for entry in entries:
                        entry["weight"] = 0.75 / len(entries)
                    for table, reward_type, share in (("potions", "potion", 0.18), ("run_upgrades", "run_upgrade", 0.07)):
                        definitions = self._progression_defs(table, all_items=True)
                        for key in definitions:
                            entries.append(dict(self._crate_item(reward_type, key, rarity), weight=share / max(1, len(definitions))))
            total = sum(entry["weight"] for entry in entries)
            for item in entries:
                item["weight"] = weight * item["weight"] / total
                result.append(item)
        return result

    def _crate_inventory(self):
        p = self.progress
        return {"cosmetics": set(p["cosmetics"]), "gear": dict(p["gear"]), "potions": dict(p["potions"]),
                "run_upgrades": dict(p["run_upgrades"]), "currencies": dict(self.state["currencies"]),
                "crates": {(kind, tier): count for kind, counts in p["crates"].items() for tier, count in counts.items()}}

    def _crate_reward_since(self, before, rarity, tier, result):
        p = self.progress
        for key in p["cosmetics"]:
            if key not in before["cosmetics"]:
                return self._crate_item("skin", key, rarity)
        for inventory, reward_type in (("gear", "equipment"), ("potions", "potion"), ("run_upgrades", "run_upgrade")):
            for key, count in p[inventory].items():
                difference = count - before[inventory].get(key, 0)
                if difference > 0:
                    return self._crate_item(reward_type, key, rarity, difference)
        for key, amount in self.state["currencies"].items():
            difference = amount - before["currencies"].get(key, 0)
            if difference > 0:
                return self._crate_item("currency", key, rarity, difference, self.currencies.get(key, {}).get("display_name", key))
        for kind, counts in p["crates"].items():
            for key, count in counts.items():
                if count > before["crates"].get((kind, key), 0):
                    name = self._progression_defs("crates", all_items=True).get(key, {}).get("name", key)
                    return self._crate_item("crate", key, rarity, name=name + " " + kind + " crate")
        return self._crate_item("callback", tier, rarity, name=result)

    def configure_streak(self, **settings):
        defaults = self._streak_defaults()
        if set(settings) - defaults.keys():
            raise ValueError("Unknown streak setting: " + ", ".join(sorted(set(settings) - defaults.keys())))
        values = dict(getattr(self, "_streak_settings", {}))
        for key, value in settings.items():
            if key == "currency":
                if value not in self.currencies:
                    raise ValueError("Unknown streak currency")
                values[key] = value
            else:
                minimum = 1 if key in ("clicks_to_full", "max_multiplier") else 0.01 if key == "curve" else 0
                values[key] = number(value, key, minimum, 1000000)
        self._ensure_progression_registry()
        self._streak_settings = values
        if hasattr(self, "reset_streak"):
            self.reset_streak()
        self._mod_registry_changed()

    def _remove_progression_owner(self, owner):
        if hasattr(self, "_progression_registry"):
            for table in self._progression_registry.values():
                for key, definition in list(table.items()):
                    if definition["owner"] == owner:
                        table.pop(key)
        for key, definition in list(getattr(self, "_mod_setting_definitions", {}).items()):
            if definition["owner"] == owner:
                self._mod_setting_definitions.pop(key)

    @staticmethod
    def _streak_defaults():
        return dict(clicks_to_full=250, max_multiplier=1.5, curve=2.4, grace=1.5,
                    drain_base=0.8, drain_acceleration=1.5, drain_max=48, currency="flesh")

    def _streak_config(self):
        self._ensure_progression_registry()
        return dict(self._streak_defaults(), **self._streak_settings)

    def _reset_progression_registry(self):
        self.__dict__.pop("_progression_registry", None)
        self._ensure_progression_registry()
        self._streak_context = None
