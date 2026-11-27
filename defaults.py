DEFAULT_SETTINGS = {
    "theme": "system",
    "show_full_numbers": False,
    "enable_rpc": False,
    "squish_ms": 100,
    "play_click_sound": False,
    "play_ui_sounds": True,
    "play_effect_sounds": True,
    "click_sound_volume": 15,
    "game_title_mod_key": "",
    "auto_reload_mod_changes": True,
    "dismissed_mod_security_warnings": {},
    "active_save_id": "main",
    "mod_settings": {},
}

DEFAULT_STATE = {
    "currencies": {"flesh": 0.0, "tokens": 0.0},
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
    "shop_fan": {"name": "A Brilliant Bad Idea", "desc": "Buy a Finger Fan.", "unlocked": False},
    "shop_press": {"name": "Industrial Clicking", "desc": "Buy a Clicking Press.", "unlocked": False},
    "shop_orbit": {"name": "Completely Necessary", "desc": "Put a clicking satellite into service.", "unlocked": False},
    "shop_complete": {"name": "Clicking Incorporated", "desc": "Open the Clicking Department.", "unlocked": False},
    "shop_bulk": {"name": "Wholesale Nonsense", "desc": "Own 10 of one production machine or glove.", "unlocked": False},
}

# ---------- CURRENCY REGISTRY ----------
# Built-in currencies. Mods add more via game.register_currency().
BASE_CURRENCIES = {
    "flesh": {"display_name": "Flesh"},
    "tokens": {"display_name": "Flesh Tokens"},
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
        "name": "Spring Glove",
        "desc": "A spring is in the palm. Adds 1 flesh per click.",
        "shop_item": 0,
        "shop_bonus": True,
        "category": "click",
        "base_cost": 10, "cost_mult": 1.15,
        "cost_currency": "flesh",
        "currency_effects": [
            {"currency": "flesh", "cpc": 1.0, "cps": 0.0, "on_buy": 0.0},
        ],
    },
    "auto_clicker_1": {
        "name": "Finger Fan",
        "desc": "We taped a finger to a fan. Makes 1 flesh a second.",
        "shop_item": 1,
        "shop_bonus": True,
        "category": "auto",
        "base_cost": 25, "cost_mult": 1.15,
        "cost_currency": "flesh",
        "currency_effects": [
            {"currency": "flesh", "cpc": 0.0, "cps": 1.0, "on_buy": 0.0},
        ],
    },
    "auto_clicker_2": {
        "name": "Desk Tapper",
        "desc": "Well, at least it does something. Makes 2 flesh a second.",
        "shop_item": 2,
        "shop_bonus": True,
        "category": "auto",
        "base_cost": 100, "cost_mult": 1.18,
        "cost_currency": "flesh",
        "currency_effects": [
            {"currency": "flesh", "cpc": 0.0, "cps": 2.0, "on_buy": 0.0},
        ],
    },
    "thumb_guard": {
        "name": "Thumb Guard",
        "desc": "It's some metal over your thumb. Adds 4 flesh per click.",
        "category": "click",
        "base_cost": 150, "cost_mult": 1.18,
        "cost_currency": "flesh",
        "currency_effects": [
            {"currency": "flesh", "cpc": 4.0, "cps": 0.0, "on_buy": 0.0},
        ],
    },
    "crit_click": {
        "name": "Lucky Spring",
        "desc": "I'm pretty sure this is a malfunction. Each spring adds a 5% double-click chance, up to 100%.",
        "shop_item": 3,
        "category": "click",
        "base_cost": 200, "cost_mult": 1.2,
        "cost_currency": "flesh",
        "currency_effects": [],  # handled by the built-in click modifier
    },
    "clicking_press": {
        "name": "Clicking Press",
        "desc": "Loud enough to hear from the next room. Makes 12 flesh a second.",
        "shop_item": 4, "shop_bonus": True, "category": "auto",
        "base_cost": 750, "cost_mult": 1.16, "cost_currency": "flesh",
        "requires": {"upgrade": "auto_clicker_2", "count": 1},
        "currency_effects": [{"currency": "flesh", "cpc": 0.0, "cps": 12.0, "on_buy": 0.0}],
    },
    "ratchet_glove": {
        "name": "Ratchet Glove",
        "desc": "Like clockwork. Adds 20 flesh per click.",
        "category": "click",
        "base_cost": 2500, "cost_mult": 1.18, "cost_currency": "flesh",
        "currency_effects": [{"currency": "flesh", "cpc": 20.0, "cps": 0.0, "on_buy": 0.0}],
    },
    "clicking_conveyor": {
        "name": "Conveyor Belt",
        "desc": "Don't ask where the fingers are from. Makes 80 flesh a second.",
        "shop_item": 5, "shop_bonus": True, "category": "auto",
        "base_cost": 5000, "cost_mult": 1.17, "cost_currency": "flesh",
        "requires": {"upgrade": "clicking_press", "count": 1},
        "currency_effects": [{"currency": "flesh", "cpc": 0.0, "cps": 80.0, "on_buy": 0.0}],
    },
    "hydraulic_arm": {
        "name": "Hydraulic Arm",
        "desc": "It's really hard to hold. Who designed this?? Adds 120 flesh per click.",
        "category": "click",
        "base_cost": 35000, "cost_mult": 1.2, "cost_currency": "flesh",
        "currency_effects": [{"currency": "flesh", "cpc": 120.0, "cps": 0.0, "on_buy": 0.0}],
    },
    "clicking_satellite": {
        "name": "Click Satellite",
        "desc": "Don't ask why we did this. Makes 600 flesh a second.",
        "shop_item": 6, "shop_bonus": True, "category": "auto",
        "base_cost": 40000, "cost_mult": 1.18, "cost_currency": "flesh",
        "requires": {"upgrade": "clicking_conveyor", "count": 1},
        "currency_effects": [{"currency": "flesh", "cpc": 0.0, "cps": 600.0, "on_buy": 0.0}],
    },
    "clicking_department": {
        "name": "Clicking Department",
        "desc": "We hired people to watch over the machines. Makes 4,200 flesh a second.",
        "shop_item": 7, "shop_bonus": True, "category": "auto",
        "base_cost": 250000, "cost_mult": 1.19, "cost_currency": "flesh",
        "requires": {"upgrade": "clicking_satellite", "count": 1},
        "currency_effects": [{"currency": "flesh", "cpc": 0.0, "cps": 4200.0, "on_buy": 0.0}],
    },
    "clicking_rig": {
        "name": "Clicking Rig",
        "desc": "It's pretty hard to manuever this thing. At least it works. Adds 700 flesh per click.",
        "category": "click",
        "base_cost": 350000, "cost_mult": 1.22, "cost_currency": "flesh",
        "currency_effects": [{"currency": "flesh", "cpc": 700.0, "cps": 0.0, "on_buy": 0.0}],
    },
}
