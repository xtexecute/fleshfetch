"""Vanilla crates, equipment and rebirth. All data lives in the active save's state."""

import math
import os
import random
import time

from mod_api import vanilla_enabled
from progression_registry import ProgressionRegistryMixin, integer

RARITIES = ("Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythical", "Radiant", "Celestial")
CRATE_TIERS = RARITIES[:6]
RARITY_COLORS = {
    "Common": "#9da3aa", "Uncommon": "#67ba76", "Rare": "#55a4e7",
    "Epic": "#b77ae9", "Legendary": "#e8b44c", "Mythical": "#e36e8a",
    "Radiant": "#f1df88", "Celestial": "#39dce8",
}
CRATE_WEIGHTS = {
    "Common": (700, 185, 75, 30, 10, 0, 0, 0),
    "Uncommon": (520, 300, 115, 50, 15, 0, 0, 0),
    "Rare": (350, 310, 215, 95, 27, 3, 0, 0),
    "Epic": (0, 530, 285, 130, 42, 12, 1, 0),
    "Legendary": (0, 240, 300, 250, 145, 57, 7, 1),
    "Mythical": (0, 0, 260, 315, 250, 150, 23, 2),
}
CRATE_COSTS = {
    "Common": ("flesh", 500), "Uncommon": ("flesh", 5000),
    "Rare": ("flesh", 50000), "Epic": ("flesh", 500000),
    "Legendary": ("tokens", 3), "Mythical": ("tokens", 8),
}

# Two pieces per rarity keep a pull interesting even after one has been found.
GEAR = {
    "wrist_wrap": ("Wrist Wrap", "Common", "click", 0.12),
    "desk_weight": ("Desk Weight", "Common", "cps", 0.12),
    "spring_clip": ("Spring Clip", "Uncommon", "click", 0.24),
    "fan_belt": ("Fan Belt", "Uncommon", "cps", 0.24),
    "counterweight": ("Counterweight", "Rare", "click", 0.42),
    "second_motor": ("Second Motor", "Rare", "cps", 0.42),
    "lucky_switch": ("Lucky Switch", "Epic", "luck", 0.65),
    "crate_magnet": ("Crate Magnet", "Epic", "drop", 0.65),
    "heavy_spring": ("Heavy Spring", "Legendary", "click", 0.85),
    "night_shift": ("Night Shift", "Legendary", "cps", 0.85),
    "double_hinge": ("Double Hinge", "Mythical", "click", 1.35),
    "assembly_line": ("Assembly Line", "Mythical", "cps", 1.35),
    "bright_idea": ("Bright Idea", "Radiant", "luck", 1.4),
    "open_season": ("Open Season", "Radiant", "drop", 1.4),
    "last_button": ("The Last Button", "Celestial", "click", 2.4),
    "clock_without_hands": ("Clock Without Hands", "Celestial", "cps", 2.4),
}
COSMETICS = {
    "smoke": ("Smoke", "Common", "#83878d"),
    "mint": ("Mint", "Uncommon", "#56b99b"),
    "sky": ("Sky", "Rare", "#5b9be0"),
    "violet": ("Confusion", "Epic", "#ad73d1"),
    "gold": ("Gold", "Legendary", "#d5a944"),
    "top_hat": ("Top Hat", "Legendary", "#ffffff"),
    "rose": ("Rose", "Mythical", "#de6e9b"),
    "wobble": ("Wobble", "Mythical", "#ffffff"),
    "cat": ("Cat", "Mythical", "#d9c7a8"),
    "sunlight": ("Sunlight", "Radiant", "#edda87"),
    "deep_blue": ("Deep Blue", "Celestial", "#39dce8"),
    "paper_crown": ("Paper Crown", "Common", "#f3d77b"),
    "price_tag": ("Price Tag", "Common", "#f1e9d4"),
    "sticky_note": ("Sticky Note", "Common", "#f6dc77"),
    "button_badge": ("Button Badge", "Common", "#e3e7e8"),
    "wind_up_key": ("Wind-Up Key", "Uncommon", "#c7c9b4"),
    "party_hat": ("Party Hat", "Uncommon", "#ffd674"),
    "sunglasses": ("Sunglasses", "Uncommon", "#777487"),
    "squeaky_toy": ("Squeaky Toy", "Uncommon", "#e9c865"),
    "tiny_flag": ("Tiny Flag", "Uncommon", "#f6b8a2"),
    "pinball": ("Pinball", "Rare", "#aabecb"),
    "magnet": ("Magnet", "Rare", "#df596f"),
    "ticket_roll": ("Ticket Roll", "Rare", "#e9cf9c"),
    "lava_lamp": ("Lava Lamp", "Epic", "#f09d73"),
    "hologram": ("Hologram", "Epic", "#79e0de"),
    "thunderhead": ("Thunderhead", "Epic", "#b8b0dc"),
    "neon_outline": ("Neon Outline", "Epic", "#ee6db8"),
    "snow_globe": ("Snow Globe", "Epic", "#cce6ed"),
    "pixel_tv": ("Pixel TV", "Epic", "#a7b5a7"),
    "fishbowl": ("Fishbowl", "Epic", "#cbd8e1"),
    "marionette": ("Marionette", "Legendary", "#d3aa89"),
    "slot_machine": ("Slot Machine", "Legendary", "#e5c17f"),
    "blacksmith": ("Blacksmith", "Legendary", "#ce8c62"),
    "comet": ("Comet", "Legendary", "#d7b1e0"),
    "bitcrush": ("Bitcrush", "Legendary", "#ffffff"),
    "liquid_metal": ("Liquid Metal", "Mythical", "#b8c3ce"),
    "shadow_twin": ("Shadow Twin", "Mythical", "#8c779c"),
    "zero_gravity": ("Zero Gravity", "Mythical", "#96b9db"),
    "sandcastle": ("Sandcastle", "Mythical", "#d7bd89"),
    "temporal_echo": ("Temporal Echo", "Mythical", "#acd4ce"),
    "reflection": ("Reflection", "Mythical", "#bdd9e5"),
    "stained_glass": ("Stained Glass", "Radiant", "#efb5b9"),
    "sundial": ("Sundial", "Radiant", "#e5d18d"),
    "prism_rain": ("Prism Rain", "Radiant", "#a6d3e8"),
    "lightbox": ("Lightbox", "Radiant", "#f4e4ac"),
    "firefly_jar": ("Firefly Jar", "Radiant", "#dfebb3"),
    "opal": ("Opal", "Radiant", "#d5bbdf"),
    "event_horizon": ("Event Horizon", "Celestial", "#9ec6dc"),
    "star_map": ("Star Map", "Celestial", "#9cd5df"),
    "clockwork": ("Clockwork", "Celestial", "#dfd5ae"),
    "aurora_ribbon": ("Aurora Ribbon", "Celestial", "#88ded3"),
    "tidal_planet": ("Tidal Planet", "Celestial", "#92b7e9"),
}
CRATE_COSMETICS = frozenset((
    "smoke", "mint", "sky", "violet", "gold", "top_hat", "rose", "wobble", "cat",
    "sunlight", "deep_blue", "paper_crown", "price_tag",
    "sticky_note", "button_badge", "bitcrush", "clockwork",
    "wind_up_key", "party_hat", "sunglasses", "squeaky_toy", "tiny_flag", "ticket_roll", "pinball",
    "magnet", "hologram", "thunderhead", "pixel_tv", "fishbowl", "slot_machine",
    "blacksmith", "comet", "reflection", "liquid_metal", "shadow_twin", "zero_gravity",
    "sandcastle", "temporal_echo", "stained_glass", "sundial", "prism_rain", "lightbox", "firefly_jar", "opal",
    "event_horizon",
    "star_map", "aurora_ribbon", "tidal_planet", "neon_outline", "snow_globe", "lava_lamp", "marionette",
))
TESTABLE_COSMETICS = CRATE_COSMETICS
COSMETIC_FEATURES = {
    "neon_outline": "A neon edge sends a bright current around the flesh when clicked",
    "snow_globe": "Click to stir the snow; the streak fills the globe instead of the window",
    "lava_lamp": "Warm wax rises, cools and sinks around the flesh; clicks turn up the heat",
    "marionette": "Taut strings pull and stretch the flesh in a wooden puppet theatre",
    "sunlight": "Quick clicks build up to a sunbreak",
    "stained_glass": "Colored light travels from pane to pane",
    "sundial": "Each click moves the sun and sweeps the flesh's shadow across a stone dial",
    "prism_rain": "A glass prism splits light over the flesh; clicks scatter falling crystals",
    "lightbox": "A light panel scans the flesh into a glowing film exposure that fades back",
    "firefly_jar": "Fireflies drift inside the glass and gather around wherever you click",
    "opal": "Milky stone with patches of color that catch the light as you click",
    "event_horizon": "A black hole bends the flesh around its accretion disc and draws matter inward",
    "star_map": "Stars and constellations form the flesh; clicks brighten them and stir the map",
    "tidal_planet": "A flesh-shaped continent on a turning ocean world, with clouds, a moon and click-driven tides",
    "comet": "An icy wake drifts behind the flesh and breaks into shards on click",
    "liquid_metal": "Ripples in mercury from where you click",
    "blacksmith": "An iron hammer strikes the flesh and scatters sparks",
    "slot_machine": "A lever pulls and three reels spin beneath the flesh",
    "violet": "The flesh ripples between its usual color and purple, with a glow behind it",
    "sky": "Clouds drift beneath the flesh and puff outward on click",
    "hologram": "A projector flickers and sends a scan through the flesh on click",
    "thunderhead": "A storm cloud jolts and strikes the flesh on click",
    "mint": "A mint sprig shakes and sheds leaves on click",
    "wind_up_key": "The key turns when clicked",
    "party_hat": "A paper hat bounces on click",
    "sunglasses": "The glasses slip and settle on click",
    "squeaky_toy": "A toy duck squashes and squeaks on click",
    "tiny_flag": "The flag flutters on click",
    "paper_crown": "Folded crown", "price_tag": "Hanging tag",
    "sticky_note": "A note stuck to the flesh",
    "button_badge": "Pinned badge",
    "top_hat": "Wears a hat", "rose": "Buds open one by one as you click", "wobble": "Bounces on click",
    "cat": "Meows on click",
    "deep_blue": "Moving ocean light, pressure waves and bubbles with each click", "pixel_tv": "A little CRT cracks on click",
    "fishbowl": "Floats in red liquid and sloshes when the bowl is clicked", "bitcrush": "Pixel flesh and 8-bit click",
    "shadow_twin": "A shadow leaves afterimages on click",
    "zero_gravity": "Click to send the flesh drifting across the chamber",
    "sandcastle": "The fort crumbles with clicks and rebuilds between bursts",
    "temporal_echo": "Replays each click a beat later",
    "reflection": "Click the reflection to crack the mirror",
    "aurora_ribbon": "Curtains of light flow around the flesh and brighten with each click",
    "magnet": "Snaps toward the flesh", "clockwork": "Clock and gears advance with each click",
    "ticket_roll": "Feeds a ticket on click",
    "pinball": "A ball ricochets between bumpers on click",
}
POTIONS = {
    "quick_hands": ("Quick Hands", "Click gains x2 for 3 minutes", "click", 180),
    "overtime": ("Overtime", "Production x2 for 5 minutes", "cps", 300),
    "good_omens": ("Good Omens", "More crate drops for 4 minutes", "drop", 240),
}
RUN_UPGRADES = {
    "click": ("Tighter Spring", "Click gains +5% this run"),
    "cps": ("Extra Shift", "Production +5% this run"),
    "drop": ("Better Packing", "Crate chance +8% this run"),
}
REBIRTH_UPGRADES = {
    "click": ("Practice", "Click gains x1.5 per level", 10),
    "cps": ("Maintenance", "Production x1.5 per level", 10),
    "drop": ("Sharp Eyes", "Crate chance +25%", 8),
    "luck": ("Better Odds", "Improved item rarity odds", 8),
    "duration": ("Longer Breaks", "Potions last 25% longer", 4),
    "slot": ("Extra Pocket", "Equip one more item", 2),
    "hybrid": ("Momentum", "Adds capped late-game scaling", 1),
}
BONUS_CHOICES = {
    "click": ("Click Power", "+1% click gains"),
    "cps": ("Production", "+1% production"),
    "drop": ("Crate Finding", "+1% crate chance"),
    "luck": ("Luck", "+1% item luck"),
}
TOKEN_UNIT = 1_000_000
TOKEN_SCALE = 8
STREAK_CLICKS_TO_FULL = 250
MAX_GEAR_LEVEL = 10
MAX_REBIRTH_CHOICES = 3


def new_progression():
    return {
        "lifetime_earned": 0.0, "run_earned": 0.0,
        "tokens_claimed": 0, "rebirths": 0,
        "crates": {kind: {tier: 0 for tier in CRATE_TIERS} for kind in ("equipment", "cosmetic")},
        "gear": {}, "equipped": [], "cosmetics": [], "selected_cosmetic": "",
        "potions": {}, "active_boosts": [], "run_upgrades": {},
        "rebirth_upgrades": {}, "bonus_upgrades": {}, "pending_choices": [],
        "pity": {"Legendary": 0, "Mythical": 0},
    }


def normalize_progression(state):
    state.setdefault("currencies", {}).setdefault("tokens", 0.0)
    progress = state.get("progression")
    if not isinstance(progress, dict):
        progress = new_progression()
        # Older saves have no earned-flesh ledger. Credit their current flesh once.
        legacy = max(0.0, float(state.get("currencies", {}).get("flesh", 0.0)))
        progress["lifetime_earned"] = progress["run_earned"] = legacy
        state["progression"] = progress
    defaults = new_progression()
    for key, value in defaults.items():
        if key not in progress or not isinstance(progress[key], type(value)):
            progress[key] = value
    for kind in defaults["crates"]:
        progress["crates"].setdefault(kind, {})
        if not isinstance(progress["crates"][kind], dict):
            progress["crates"][kind] = {}
        for tier in CRATE_TIERS:
            progress["crates"][kind].setdefault(tier, 0)
    progress["equipped"] = [item for item in progress["equipped"] if item in progress["gear"]]
    progress["selected_cosmetic"] = progress["selected_cosmetic"] if progress["selected_cosmetic"] in progress["cosmetics"] else ""
    return progress


def token_entitlement(run_earned):
    earned = max(0, int(float(run_earned)))
    if earned < TOKEN_UNIT:
        return 0
    return math.isqrt(earned * TOKEN_SCALE ** 2 // TOKEN_UNIT)


def next_token_at(run_earned):
    tokens = token_entitlement(run_earned)
    scale_squared = TOKEN_SCALE ** 2
    threshold = (TOKEN_UNIT * (tokens + 1) ** 2 + scale_squared - 1) // scale_squared
    return max(TOKEN_UNIT, threshold)


class ProgressionMixin(ProgressionRegistryMixin):
    @property
    def progress(self):
        return normalize_progression(self.state)

    def _progress_changed(self):
        self.mark_save_dirty(auto_backup=True)
        self.update_labels()

    def record_flesh_earned(self, amount):
        if amount <= 0 or self.primary_currency != "flesh" or not vanilla_enabled(self, "rebirth"):
            return
        progress = self.progress
        progress["lifetime_earned"] += float(amount)
        progress["run_earned"] += float(amount)
        self.mark_save_dirty(auto_backup=True)

    def unclaimed_tokens(self):
        if not vanilla_enabled(self, "rebirth"):
            return 0
        return token_entitlement(self.progress["run_earned"])

    def active_cosmetic(self):
        """Return the displayed skin, without changing the saved selection."""
        selected = self.progress["selected_cosmetic"]
        definition = self._progression_defs("skins").get(selected)
        if not definition:
            return ""
        if definition["owner"] != "__vanilla__":
            return selected
        if self.primary_currency != "flesh":
            return ""
        image = getattr(self, "flesh_image_path", None)
        if image:
            from paths import find_app_asset
            if os.path.normcase(os.path.abspath(image)) != os.path.normcase(os.path.abspath(find_app_asset("flesh.png"))):
                return ""
        return selected if selected in TESTABLE_COSMETICS else ""

    def equipped_slots(self):
        return 2 + min(2, self.progress["rebirth_upgrades"].get("slot", 0))

    def _active_equipment(self):
        definitions = self._progression_defs("equipment")
        return [key for key in self.progress["equipped"] if key in definitions
                and (self.primary_currency == "flesh" or definitions[key]["owner"] != "__vanilla__")][:self.equipped_slots()]

    def progression_bonus(self, stat):
        p = self.progress
        flesh = self.primary_currency == "flesh"
        rebirth = flesh and vanilla_enabled(self, "rebirth")
        gear_bonus = sum(self._equipment_bonus(item, stat, p["gear"][item]) for item in self._active_equipment())
        gear_bonus += self._custom_progression_bonus(stat)
        shop = p["rebirth_upgrades"] if rebirth else {}
        random_bonuses = p["bonus_upgrades"] if rebirth else {}
        run = p["run_upgrades"] if flesh and vanilla_enabled(self, "equipment") else {}
        potions = {key: d for key, d in self._progression_defs("potions").items() if flesh or d["owner"] != "__vanilla__"}
        boosts = [b for b in p["active_boosts"] if
                  (b.get("id") in potions if "id" in b else flesh and vanilla_enabled(self, "equipment"))
                  and b.get("stat") == stat and b.get("until", 0) > time.time()]
        gear_bonus += sum(b.get("amount", 1) for b in boosts if b.get("mode", "add" if stat == "drop" else "multiply") == "add")
        boost = max([1.0] + [b.get("amount", 2) for b in boosts
                    if b.get("mode", "add" if stat == "drop" else "multiply") == "multiply"])
        if stat in ("click", "cps"):
            additive = gear_bonus + 0.01 * random_bonuses.get(stat, 0) + 0.05 * run.get(stat, 0)
            level = min(REBIRTH_UPGRADES[stat][2], max(0, shop.get(stat, 0)))
            permanent = 1.5 ** level
            first_rebirth = 2.0 if rebirth and p["rebirths"] > 0 else 1.0
            stacks = sum(random_bonuses.values())
            hybrid = math.exp(min(math.log(2), stacks * math.log(1.001))) if shop.get("hybrid", 0) else 1.0
            return (1.0 + additive) * permanent * first_rebirth * hybrid * boost
        if stat == "drop":
            additive = gear_bonus + 0.25 * shop.get("drop", 0) + 0.01 * random_bonuses.get("drop", 0) + 0.08 * run.get("drop", 0)
            return min(5.0, (1.0 + max(0.0, additive)) * boost)
        return min(3.0, max(0.0, gear_bonus + 0.15 * shop.get("luck", 0) + 0.01 * random_bonuses.get("luck", 0)) * boost)

    def _roll_rarity(self, tier):
        crate = self._progression_defs("crates")[tier]
        luck = self.progression_bonus("luck")
        rarities = tuple(crate["rarity_weights"])
        weights = [weight * (1 + 0.08 * luck * self._rarity_rank(key)) for key, weight in crate["rarity_weights"].items()]
        rarity = random.choices(rarities, weights=weights, k=1)[0]
        if crate["pity_after"]:
            target, limit = crate["pity_rarity"], crate["pity_after"]
            if self.progress["pity"].get(tier, 0) >= limit - 1 and self._rarity_rank(rarity) < self._rarity_rank(target):
                rarity = target
        return rarity

    def _add_crate(self, kind, tier):
        crate = self._progression_defs("crates").get(tier)
        if not crate or kind not in crate["kinds"]:
            return
        counts = self.progress["crates"][kind]
        counts[tier] = counts.get(tier, 0) + 1
        self._progress_changed()

    def grant_crate(self, kind, tier, count=1):
        tier = self._definition_id("crates", tier)
        crate = self._progression_defs("crates").get(tier)
        if not crate:
            if tier in self._progression_defs("crates", all_items=True):
                raise RuntimeError("Vanilla crates are disabled")
            raise ValueError("Unknown crate type or tier")
        if kind not in crate["kinds"]:
            raise ValueError("Unknown crate type or tier")
        count = integer(count, "count")
        counts = self.progress["crates"][kind]
        counts[tier] = counts.get(tier, 0) + count
        self._progress_changed()
        return self.progress["crates"][kind][tier]

    def get_flesh_tokens(self):
        return int(self.get_currency("tokens"))

    def add_flesh_tokens(self, amount):
        amount = int(amount)
        if self.get_currency("tokens") + amount < 0:
            raise ValueError("Not enough Flesh Tokens")
        self.add_currency("tokens", amount)
        self._progress_changed()
        return self.get_flesh_tokens()

    def register_crate_reward(self, reward_id, callback, *, kind="equipment", weight=1.0,
                              min_rarity="Common", permanent=False):
        """A callback returns its reward label; permanent rewards can enter token crates."""
        min_rarity = self._require_definition("rarities", min_rarity)
        if not callable(callback) or kind not in ("equipment", "cosmetic"):
            raise ValueError("Invalid crate reward")
        weight = float(weight)
        if not math.isfinite(weight) or not 0 < weight <= 10:
            raise ValueError("Reward weight must be between 0 and 10")
        owner = self._current_mod_namespace()
        key = f"{owner}:{reward_id}"
        self._mod_crate_rewards[key] = {"owner": owner, "kind": kind, "weight": weight,
                                        "min_rarity": min_rarity, "permanent": bool(permanent),
                                        "callback": callback}
        return key

    def maybe_drop_crate(self):
        custom = []
        for key, crate in self._progression_defs("crates").items():
            if crate["owner"] == "__vanilla__" or not crate["drop_chance"]:
                continue
            if random.random() < min(1, crate["drop_chance"] * self.progression_bonus("drop")):
                kind = crate["kinds"][0]
                if hasattr(self, "_queue_crate_drop"):
                    self._queue_crate_drop(kind, key)
                    self._emit_event("crate_dropped", {"kind": kind, "tier": key})
                else:
                    self._add_crate(kind, key)
                    self._emit_event("crate_found", {"kind": kind, "tier": key})
                custom.append((kind, key))
        if self.primary_currency != "flesh" or not vanilla_enabled(self, "crates"):
            return custom[0] if custom else None
        self._last_crate_roll_at = time.monotonic()
        chance = min(0.04, 0.007 * self.progression_bonus("drop"))
        if random.random() >= chance:
            return custom[0] if custom else None
        kind = "cosmetic" if random.random() < 0.25 else "equipment"
        tier = random.choices(CRATE_TIERS[:5], weights=(750, 180, 55, 14, 1), k=1)[0]
        if hasattr(self, "_queue_crate_drop"):
            self._queue_crate_drop(kind, tier)
            self._emit_event("crate_dropped", {"kind": kind, "tier": tier})
            return kind, tier
        self._add_crate(kind, tier)
        self._emit_event("crate_found", {"kind": kind, "tier": tier})
        if hasattr(self, "_set_status"):
            self._set_status(f"Found a {tier} {kind} crate!")
        return kind, tier

    def buy_crate(self, kind, tier):
        tier = self._definition_id("crates", tier)
        crate = self._progression_defs("crates").get(tier)
        if not crate or kind not in crate["kinds"]:
            return False, "Unknown or disabled crate."
        if crate["owner"] == "__vanilla__" and self.primary_currency != "flesh":
            return False, "Crates are available only while Flesh is the main currency."
        currency, cost = crate["currency"], crate["cost"]
        if self.get_currency(currency) < cost:
            return False, "Not enough " + self.currencies.get(currency, {}).get("display_name", currency) + "."
        self.add_currency(currency, -cost)
        self._add_crate(kind, tier)
        return True, f"Bought a {crate['name']} {kind} crate."

    def open_crate(self, kind, tier):
        tier = self._definition_id("crates", tier)
        crate = self._progression_defs("crates").get(tier)
        if not crate or kind not in crate["kinds"]:
            return False, "Unknown or disabled crate."
        p = self.progress
        if p["crates"][kind].get(tier, 0) <= 0:
            return False, "No crate to open."
        before = self._crate_inventory()
        GEAR = self._progression_items("equipment", all_items=True)
        COSMETICS = self._progression_items("skins", all_items=True)
        POTIONS = self._progression_items("potions", all_items=True)
        RUN_UPGRADES = self._progression_items("run_upgrades", all_items=True)
        p["crates"][kind][tier] -= 1
        rarity = self._roll_rarity(tier)
        self._last_crate_rarity = rarity
        if crate["owner"] != "__vanilla__":
            reward = self._registered_crate_reward(crate, kind, rarity)
            if reward is None:
                p["crates"][kind][tier] += 1
                return False, "No available reward at this rarity; the crate was kept."
            return self._finish_crate(kind, tier, rarity, f"{self._progression_defs('rarities')[rarity]['name']}: {reward}", before)
        external = [reward for reward in self._mod_crate_rewards.values()
                    if reward["min_rarity"] in self._progression_defs("rarities")
                    and reward["kind"] == kind and self._rarity_rank(rarity) >= self._rarity_rank(reward["min_rarity"])
                    and (tier not in ("Legendary", "Mythical") or reward["permanent"])]
        if external and random.random() < min(0.25, sum(reward["weight"] for reward in external) / 100):
            reward = random.choices(external, weights=[entry["weight"] for entry in external], k=1)[0]
            try:
                result = self._run_with_mod_owner(reward["owner"], reward["callback"], {
                    "kind": kind, "tier": tier, "rarity": rarity, "game": self,
                })
                if result:
                    result = f"{rarity}: {result}"
                    return self._finish_crate(kind, tier, rarity, result, before)
            except Exception as exc:
                print(f"[crates] Mod reward failed: {exc}")
        if kind == "cosmetic":
            available = [key for key, item in COSMETICS.items()
                         if item[1] == rarity and key not in p["cosmetics"]]
            if available:
                item_id = random.choice(available)
                p["cosmetics"].append(item_id)
                result = f"{rarity}: {COSMETICS[item_id][0]} cosmetic"
            else:
                p["crates"]["equipment"][tier] += 1
                result = f"{rarity} cosmetic already owned. Received an equipment crate instead."
        else:
            # Token-priced crates always contain lasting equipment.
            roll = random.random() if tier not in ("Legendary", "Mythical") else 0.0
            if roll < 0.75:
                candidates = [key for key, item in GEAR.items() if item[1] == rarity]
                fresh = [key for key in candidates if key not in p["gear"]]
                if not candidates:
                    p["crates"][kind][tier] += 1
                    return False, "No equipment at this rarity; the crate was kept."
                item_id = random.choice(fresh or candidates)
                if p["gear"].get(item_id, 0) >= self._progression_defs("equipment", all_items=True)[item_id]["max_level"]:
                    if tier in ("Legendary", "Mythical"):
                        self.add_currency("tokens", 1)
                        result = f"{rarity}: {GEAR[item_id][0]} was maxed. Refunded 1 Flesh Token."
                    else:
                        if not POTIONS:
                            p["crates"][kind][tier] += 1
                            return False, "Equipment is maxed; the crate was kept."
                        potion_id = random.choice(tuple(POTIONS))
                        p["potions"][potion_id] = p["potions"].get(potion_id, 0) + 1
                        result = f"{rarity}: {GEAR[item_id][0]} was maxed. Received a potion instead."
                else:
                    p["gear"][item_id] = p["gear"].get(item_id, 0) + 1
                    result = f"{rarity}: {GEAR[item_id][0]}" + (f" (level {p['gear'][item_id]})" if p["gear"][item_id] > 1 else "")
            elif roll < 0.93:
                if not POTIONS:
                    p["crates"][kind][tier] += 1
                    return False, "No potions available; the crate was kept."
                item_id = random.choice(tuple(POTIONS))
                count = 1 + RARITIES.index(rarity) // 3
                p["potions"][item_id] = p["potions"].get(item_id, 0) + count
                result = f"{rarity}: {POTIONS[item_id][0]} potion x{count}"
            else:
                if not RUN_UPGRADES:
                    p["crates"][kind][tier] += 1
                    return False, "No run upgrades available; the crate was kept."
                item_id = random.choice(tuple(RUN_UPGRADES))
                p["run_upgrades"][item_id] = p["run_upgrades"].get(item_id, 0) + 1 + RARITIES.index(rarity) // 3
                result = f"{rarity}: {RUN_UPGRADES[item_id][0]} upgrade"
        return self._finish_crate(kind, tier, rarity, result, before)

    def _finish_crate(self, kind, tier, rarity, result, before):
        p = self.progress
        crate = self._progression_defs("crates")[tier]
        if crate["pity_after"]:
            target = crate["pity_rarity"]
            p["pity"][tier] = 0 if self._rarity_rank(rarity) >= self._rarity_rank(target) else p["pity"].get(tier, 0) + 1
        self._last_crate_result = result
        self._last_crate_reward = self._crate_reward_since(before, rarity, tier, result)
        self._last_crate_save_id = self.active_save_id
        self._progress_changed()
        self._emit_event("crate_opened", {"kind": kind, "tier": tier, "rarity": rarity, "result": result})
        return True, result

    def equip_gear(self, item_id):
        item_id = self._definition_id("equipment", item_id)
        GEAR = self._progression_items("equipment")
        p = self.progress
        if item_id not in p["gear"] or item_id not in GEAR:
            return False, "Item not owned."
        if self.primary_currency != "flesh" and self._progression_defs("equipment")[item_id]["owner"] == "__vanilla__":
            return False, "Vanilla equipment is available only while Flesh is the main currency."
        active = self._active_equipment()
        if item_id in active:
            p["equipped"].remove(item_id)
            result = f"Unequipped {GEAR[item_id][0]}."
        elif len(active) < self.equipped_slots():
            if item_id in p["equipped"]:
                p["equipped"].remove(item_id)
            p["equipped"].append(item_id)
            result = f"Equipped {GEAR[item_id][0]}."
        else:
            return False, "All equipment slots are full."
        self._progress_changed()
        self._emit_event("equipment_changed", {"item_id": item_id, "equipped": item_id in p["equipped"]})
        return True, result

    def select_cosmetic(self, item_id):
        item_id = self._definition_id("skins", item_id) if item_id else ""
        skins = self._progression_defs("skins")
        p = self.progress
        if item_id and item_id not in skins:
            return False, "Unknown or disabled skin."
        if item_id and item_id not in p["cosmetics"]:
            return False, "Cosmetic not owned."
        p["selected_cosmetic"] = item_id
        self._skin_frame = None
        self._progress_changed()
        self._emit_event("skin_changed", {"skin_id": item_id})
        return True, f"Selected {skins[item_id]['name']}." if item_id else "Using the original flesh image."

    def use_potion(self, item_id):
        item_id = self._definition_id("potions", item_id)
        POTIONS = self._progression_items("potions")
        p = self.progress
        if item_id not in POTIONS or p["potions"].get(item_id, 0) <= 0:
            return False, "Potion not owned."
        p["potions"][item_id] -= 1
        name, _, stat, duration = POTIONS[item_id]
        duration *= 1 + (0.25 * p["rebirth_upgrades"].get("duration", 0) if vanilla_enabled(self, "rebirth") else 0)
        p["active_boosts"] = [b for b in p["active_boosts"] if b.get("stat") != stat and b.get("until", 0) > time.time()]
        definition = self._progression_defs("potions")[item_id]
        p["active_boosts"].append({"id": item_id, "stat": stat, "until": time.time() + duration, "name": name,
                                    "amount": definition["amount"], "mode": definition["mode"]})
        self._progress_changed()
        return True, f"Used {name}."

    def expire_boosts(self):
        p = self.progress
        remaining = [b for b in p["active_boosts"] if b.get("until", 0) > time.time()]
        if len(remaining) != len(p["active_boosts"]):
            p["active_boosts"] = remaining
            self._progress_changed()

    def rebirth_upgrade_cost(self, key):
        key = self._definition_id("rebirth_upgrades", key)
        level = self.progress["rebirth_upgrades"].get(key, 0)
        definition = self._progression_defs("rebirth_upgrades", all_items=True).get(key)
        if definition and definition["owner"] != "__vanilla__":
            try:
                return math.ceil(definition["base_cost"] * definition["cost_multiplier"] ** level)
            except OverflowError:
                return float("inf")
        if key == "hybrid":
            return 40
        if key == "slot":
            return 2 * (level + 1) ** 2
        if key in ("click", "cps"):
            return (level + 1) ** 2 * max(1, level - 1)
        return (2 if key in ("drop", "luck", "duration") else 1) * (level + 1) ** 2

    def buy_rebirth_upgrade(self, key):
        key = self._definition_id("rebirth_upgrades", key)
        REBIRTH_UPGRADES = self._progression_items("rebirth_upgrades")
        if key not in REBIRTH_UPGRADES:
            return False, "Unknown upgrade."
        p = self.progress
        level = p["rebirth_upgrades"].get(key, 0)
        if level >= REBIRTH_UPGRADES[key][2]:
            return False, "Already fully upgraded."
        cost = self.rebirth_upgrade_cost(key)
        currency = self._progression_defs("rebirth_upgrades")[key]["currency"]
        if self.get_currency(currency) < cost:
            return False, "Not enough " + self.currencies.get(currency, {}).get("display_name", currency) + "."
        self.add_currency(currency, -cost)
        p["rebirth_upgrades"][key] = level + 1
        self._progress_changed()
        return True, f"Bought {REBIRTH_UPGRADES[key][0]}."

    def rebirth(self):
        if not vanilla_enabled(self, "rebirth"):
            return False, "Vanilla rebirths are disabled."
        if self.primary_currency != "flesh":
            return False, "Rebirth is available only while Flesh is the main currency."
        gained = self.unclaimed_tokens()
        if gained < 1:
            return False, "Earn more flesh before rebirthing."
        from defaults import BASE_UPGRADES, DEFAULT_STATE
        from save_manager import backup_save_slot
        self.flush_dirty_save()
        backup_save_slot(self.active_save_id, reason="rebirth")
        p = self.progress
        old_claimed = p["tokens_claimed"]
        self.add_currency("tokens", gained)
        p["tokens_claimed"] += gained
        p["rebirths"] += 1
        p["run_earned"] = 0.0
        p["gear"] = {key: level for key, level in p["gear"].items() if key in p["equipped"]}
        p["potions"] = {}
        p["active_boosts"] = []
        p["run_upgrades"] = {}
        # Leave mod currencies and mod-owned upgrades untouched.
        self.state["currencies"]["flesh"] = 0.0
        self.state["flesh_per_click"] = DEFAULT_STATE["flesh_per_click"]
        for uid in BASE_UPGRADES:
            if uid not in getattr(self, "_mod_upgrade_owners", {}):
                self.state["upgrades_owned"].pop(uid, None)
        self.invalidate_rate_cache()
        if hasattr(self, "reset_streak"):
            self.reset_streak()
        old_awards = (math.isqrt(8 * old_claimed + 1) - 1) // 2
        new_awards = (math.isqrt(8 * p["tokens_claimed"] + 1) - 1) // 2
        choice_count = min(MAX_REBIRTH_CHOICES, new_awards - old_awards)
        for _ in range(choice_count):
            p["pending_choices"].append(random.sample(tuple(BONUS_CHOICES), 3))
        bonus = ""
        roll = random.random()
        if roll < 0.04:
            candidates = [key for key, item in GEAR.items()
                          if item[1] == "Rare" and p["gear"].get(key, 0) < MAX_GEAR_LEVEL]
            if candidates:
                item_id = random.choice(candidates)
                p["gear"][item_id] = p["gear"].get(item_id, 0) + 1
                bonus = f" Bonus item: {GEAR[item_id][0]}."
            else:
                p["crates"]["equipment"]["Rare"] += 1
                bonus = " Bonus Rare crate."
        elif roll < 0.24:
            p["crates"]["equipment"]["Rare"] += 1
            bonus = " Bonus Rare crate."
        self.save_current_progress(auto_backup=False)
        self._emit_event("rebirth", {"tokens": gained, "rebirths": p["rebirths"], "bonus": bonus})
        self._progress_changed()
        return True, f"Rebirth complete. +{gained} Flesh Tokens.{bonus}"

    def choose_rebirth_bonus(self, key):
        if not vanilla_enabled(self, "rebirth"):
            return False, "Vanilla rebirths are disabled."
        p = self.progress
        if not p["pending_choices"] or key not in p["pending_choices"][0]:
            return False, "Choose one of the offered upgrades."
        p["pending_choices"].pop(0)
        p["bonus_upgrades"][key] = p["bonus_upgrades"].get(key, 0) + 1
        self._progress_changed()
        return True, f"Permanent {BONUS_CHOICES[key][0]} increased."

    def progression_snapshot(self):
        p = self.progress
        selected = self.active_cosmetic()
        gear = {key: d for key, d in self._progression_defs("equipment").items()
                if self.primary_currency == "flesh" or d["owner"] != "__vanilla__"}
        equipped = self._active_equipment()
        skins = self._progression_defs("skins")
        potions = self._progression_defs("potions")
        run = self._progression_defs("run_upgrades")
        shop = self._progression_defs("rebirth_upgrades")
        skin = skins.get(selected, {})
        now = time.time()
        next_goal = next_token_at(p["run_earned"])
        return {
            "tokens": self.get_flesh_tokens(), "rebirths": p["rebirths"],
            "firstRebirthMultiplier": 2 if vanilla_enabled(self, "rebirth") and p["rebirths"] > 0 else 1,
            "lastReward": getattr(self, "_last_crate_result", "") if getattr(self, "_last_crate_save_id", None) == self.active_save_id else "",
            "runEarned": p["run_earned"], "lifetimeEarned": p["lifetime_earned"],
            "unclaimed": self.unclaimed_tokens(), "nextTokenAt": next_goal,
            "slots": self.equipped_slots(), "selectedCosmetic": selected,
            "cosmeticRarity": skin.get("rarity", ""),
            "cosmeticRank": min(7, int(self._rarity_rank(skin["rarity"]))) if skin else -1,
            "cosmeticColor": skin.get("color", "#e95b68"),
            "skinOverlay": self._asset_url(skin.get("overlay", "")),
            "streak": self.streak_snapshot() if hasattr(self, "streak_snapshot") else {"fill": 0, "multiplier": 1},
            "canRebirth": self.primary_currency == "flesh" and self.unclaimed_tokens() > 0,
            "crates": {kind: dict(counts) for kind, counts in p["crates"].items()},
            "pity": dict(p["pity"]), "equipped": equipped,
            "gear": [{"id": key, "name": gear[key]["name"], "rarity": gear[key]["rarity"],
                      "stat": next(iter(gear[key]["bonuses"])),
                      "bonus": round(self._equipment_bonus(key, next(iter(gear[key]["bonuses"])), level) * 100),
                      "bonuses": {stat: round(self._equipment_bonus(key, stat, level) * 100) for stat in gear[key]["bonuses"]},
                      "icon": self._asset_url(gear[key]["icon"]) or ("image://skins/loot/gear/wrist_wrap" if gear[key]["owner"] != "__vanilla__" else ""),
                      "level": min(gear[key]["max_level"], level), "equipped": key in equipped}
                     for key, level in p["gear"].items() if key in gear],
            "cosmetics": [{"id": key, "name": skins[key]["name"], "rarity": skins[key]["rarity"],
                           "color": skins[key]["color"], "feature": skins[key]["description"],
                           "icon": self._asset_url(skins[key]["icon"])}
                          for key in p["cosmetics"] if key in skins],
            "potions": [{"id": key, "name": potions[key]["name"], "desc": potions[key]["description"], "count": count,
                         "icon": self._asset_url(potions[key]["icon"]) or "image://skins/loot/potion/" +
                            (key if potions[key]["owner"] == "__vanilla__" else "quick_hands")}
                        for key, count in p["potions"].items() if key in potions and count > 0],
            "boosts": [{"name": b.get("name", "Boost"), "seconds": max(0, int(b.get("until", 0) - now))}
                       for b in p["active_boosts"] if b.get("until", 0) > now
                       and (b.get("id") in potions if "id" in b else vanilla_enabled(self, "equipment"))],
            "runUpgrades": [{"name": run[key]["name"], "count": count}
                            for key, count in p["run_upgrades"].items() if key in run],
            "shop": [{"id": key, "name": item["name"], "desc": item["description"], "level": p["rebirth_upgrades"].get(key, 0),
                      "maxLevel": item["max_level"], "cost": self.rebirth_upgrade_cost(key), "currency": item["currency"],
                      "currencyName": self.currencies.get(item["currency"], {}).get("display_name", item["currency"]),
                      "canBuy": self.get_currency(item["currency"]) >= self.rebirth_upgrade_cost(key)}
                     for key, item in shop.items()],
            "choices": [{"id": key, "name": BONUS_CHOICES[key][0], "desc": BONUS_CHOICES[key][1]}
                        for key in (p["pending_choices"][0] if p["pending_choices"] else [])],
            "pendingChoices": len(p["pending_choices"]),
        }

    def progression_catalog(self):
        return {
            "rarities": [{"id": key, "name": d["name"], "color": d["color"], "rank": d["rank"]}
                         for key, d in sorted(self._progression_defs("rarities").items(), key=lambda pair: pair[1]["rank"])],
            "crateTiers": [{"id": key, "name": d["name"], "kinds": list(d["kinds"]),
                            "currency": d["currency"], "currencyName": self.currencies.get(d["currency"], {}).get("display_name", d["currency"]),
                            "cost": d["cost"], "color": d["color"], "icon": self._asset_url(d["icon"]) or
                                "image://skins/loot/crate/" + (key if d["owner"] == "__vanilla__" else "Common"),
                            "pityAfter": d["pity_after"], "pityRarity": d["pity_rarity"] or "",
                            "possibleRarities": [rarity for rarity, weight in d["rarity_weights"].items() if weight]}
                           for key, d in self._progression_defs("crates").items()],
            "equipmentEnabled": bool(self._progression_defs("equipment") or self._progression_defs("potions") or self._progression_defs("run_upgrades")),
            "skinsEnabled": bool(self._progression_defs("skins")),
            "streakSettings": self._streak_config(),
        }


class StreakMixin:
    """Transient click pressure. It never writes to a save slot."""

    def _ensure_streak(self):
        context = (getattr(self, "active_save_id", None), getattr(self, "primary_currency", "flesh"),
                   vanilla_enabled(self, "streak"))
        if getattr(self, "_streak_context", None) != context:
            self._streak_context = context
            self._streak_fill = 0.0
            self._streak_clicks = 0
            self._streak_last_click = None
            self._streak_updated = time.monotonic()

    def reset_streak(self):
        self._streak_context = None
        self._ensure_streak()
        self.update_labels()

    def advance_streak(self, now=None):
        self._ensure_streak()
        if not vanilla_enabled(self, "streak"):
            return
        now = time.monotonic() if now is None else now
        elapsed = max(0.0, min(0.5, now - self._streak_updated))
        self._streak_updated = now
        if self._streak_last_click is None or self._streak_fill <= 0:
            return
        idle = now - self._streak_last_click
        config = self._streak_config()
        if idle <= config["grace"]:
            return
        old = self._streak_fill
        inactive = idle - config["grace"]
        drain_per_second = min(config["drain_max"], config["drain_base"] + config["drain_acceleration"] * inactive * inactive)
        self._streak_fill = max(0.0, old - drain_per_second * elapsed)
        if old - self._streak_fill >= 0.005:
            self.update_labels()

    def register_streak_click(self):
        self._ensure_streak()
        config = self._streak_config()
        if self.primary_currency != config["currency"] or not vanilla_enabled(self, "streak"):
            return
        now = time.monotonic()
        self.advance_streak(now)
        was_full = self._streak_fill >= 100.0
        if self._streak_last_click is None or now - self._streak_last_click > 2.0:
            self._streak_clicks = 0
        self._streak_clicks += 1
        self._streak_last_click = now
        self._streak_fill = min(100.0, self._streak_fill + 100.0 / config["clicks_to_full"])
        if self._streak_fill >= 100.0 and not was_full and hasattr(self, "playEffectSound"):
            self.playEffectSound("streak")
        self.update_labels()

    def streak_multiplier(self):
        self._ensure_streak()
        config = self._streak_config()
        if self.primary_currency != config["currency"] or not vanilla_enabled(self, "streak"):
            return 1.0
        return 1.0 + (config["max_multiplier"] - 1) * (self._streak_fill / 100.0) ** config["curve"]

    def streak_snapshot(self):
        self._ensure_streak()
        return {"fill": round(self._streak_fill, 2),
                "multiplier": round(self.streak_multiplier(), 3),
                "clicks": self._streak_clicks,
                "full": self._streak_fill >= 100.0}
