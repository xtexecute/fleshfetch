DEFAULT_SETTINGS = {
    "enable_rpc": False,
    "squish_ms": 100,
    "play_click_sound": False,
    "click_sound_volume": 15,
    "game_title_mod_key": "",
    "auto_reload_mod_changes": True,
    "dismissed_mod_security_warnings": {},
    "active_save_id": "main",
    "mod_settings": {},
}

DEFAULT_STATE = {
    "currencies": {"flesh": 0.0},
    "flesh_per_click": 1.0,
    "upgrades_owned": {},
    "total_clicks": 0,
}

DEFAULT_ACHIEVEMENTS = {
    "first_click":    {"name": "First Click",      "desc": "Click the flesh at least once.",  "unlocked": False},
    "ten_clicks":     {"name": "Ten Clicks",        "desc": "Click the flesh 10 times.",       "unlocked": False},
    "hundred_clicks": {"name": "Hundred Clicks",    "desc": "Click the flesh 100 times.",      "unlocked": False},
    "first_upgrade":  {"name": "First Upgrade",     "desc": "Buy your first upgrade.",         "unlocked": False},
    "five_upgrades":  {"name": "Upgrade Collector", "desc": "Own at least 5 upgrades total.",  "unlocked": False},
    "hundred_flesh":  {"name": "Flesh Pile",        "desc": "Reach 100 flesh.",                "unlocked": False},
    "thousand_flesh": {"name": "Flesh Mountain",    "desc": "Reach 1000 flesh.",               "unlocked": False},
}

# ---------- CURRENCY REGISTRY ----------
# Built-in currencies. Mods add more via game.register_currency().
BASE_CURRENCIES = {
    "flesh": {"display_name": "Flesh"},
}

# ---------- UPGRADE SCHEMA ----------
# Each upgrade defines:
#   base_cost, cost_mult       — scaling cost
#   cost_currency              — which currency is spent (default: "flesh")
#   currency_effects: list of:
#       currency   — registry name of the currency affected
#       cpc        — added to click gain per upgrade owned
#       cps        — added to per-second gain per upgrade owned
#       on_buy     — granted once when the upgrade is purchased
#
# Legacy fps/fpc keys are still accepted transparently.

BASE_UPGRADES = {
    "bigger_clicks": {
        "name": "Bigger Clicks",
        "desc": "+1 flesh per click.",
        "category": "click",
        "base_cost": 10, "cost_mult": 1.15,
        "cost_currency": "flesh",
        "currency_effects": [
            {"currency": "flesh", "cpc": 1.0, "cps": 0.0, "on_buy": 0.0},
        ],
    },
    "auto_clicker_1": {
        "name": "Autoclicker Mk.I",
        "desc": "+1 flesh/sec per unit.",
        "category": "auto",
        "base_cost": 25, "cost_mult": 1.15,
        "cost_currency": "flesh",
        "currency_effects": [
            {"currency": "flesh", "cpc": 0.0, "cps": 1.0, "on_buy": 0.0},
        ],
    },
    "auto_clicker_2": {
        "name": "Autoclicker Mk.II",
        "desc": "+2 flesh/sec per unit.",
        "category": "auto",
        "base_cost": 100, "cost_mult": 1.18,
        "cost_currency": "flesh",
        "currency_effects": [
            {"currency": "flesh", "cpc": 0.0, "cps": 2.0, "on_buy": 0.0},
        ],
    },
    "crit_click": {
        "name": "Critical Clicks",
        "desc": "Each owned upgrade gives +5% chance to double click gains.",
        "category": "click",
        "base_cost": 200, "cost_mult": 1.2,
        "cost_currency": "flesh",
        "currency_effects": [],  # handled by the built-in click modifier
    },
}
