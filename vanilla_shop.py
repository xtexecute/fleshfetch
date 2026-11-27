"""Vanilla equipment progression, independent of frontends and save formats."""

MILESTONES = ((10, 2), (25, 3), (50, 5))
DELIVERIES = (
    ("bigger_clicks", "Pocket-sized business"),
    ("auto_clicker_1", "OSHA violation"),
    ("auto_clicker_2", "Desk job"),
    ("clicking_press", "Industrial ambitions"),
    ("clicking_conveyor", "The factory floor"),
    ("clicking_satellite", "Ad astra"),
    ("clicking_department", "Clicking Inc."),
)
SHOP_ACHIEVEMENTS = {
    "auto_clicker_1": "shop_fan", "clicking_press": "shop_press",
    "clicking_satellite": "shop_orbit", "clicking_department": "shop_complete",
}


def production_multiplier(upgrade, owned):
    if not upgrade.get("shop_bonus"):
        return 1
    return max((bonus for count, bonus in MILESTONES if owned >= count), default=1)


def is_shop_equipment(game, uid):
    upgrade = game.upgrades.get(uid, {})
    return (game.primary_currency == "flesh" and "flesh" in game.currencies
            and "shop_item" in upgrade
            and not getattr(game, "_mod_upgrade_owners", {}).get(uid))


def equipment_catalog(game):
    return [{"id": uid, "name": upgrade["name"], "art": upgrade["shop_item"]}
            for uid, upgrade in game.upgrades.items() if is_shop_equipment(game, uid)]


def equipment_progress(game, uid, owned):
    if not is_shop_equipment(game, uid) or not game.upgrades[uid].get("shop_bonus"):
        return {}
    next_level = next(((count, bonus) for count, bonus in MILESTONES if count > owned), None)
    return {"multiplier": production_multiplier(game.upgrades[uid], owned),
            "nextCount": next_level[0] if next_level else 0,
            "nextMultiplier": next_level[1] if next_level else 0}


def workshop_state(game):
    available = [uid for uid, _ in DELIVERIES if is_shop_equipment(game, uid)]
    completed = [uid for uid in available if game.get_upgrade_count(uid) > 0]
    next_id = next((uid for uid in available if uid not in completed), None)
    stage = "One very ordinary click"
    for uid, title in DELIVERIES:
        if uid in completed:
            stage = title
    goal = {}
    if next_id:
        upgrade = game.upgrades[next_id]
        cost = game.get_upgrade_cost(next_id, game.get_upgrade_count(next_id))
        currency = upgrade.get("cost_currency", "flesh")
        goal = {"id": next_id, "name": upgrade["name"], "cost": cost,
                "currency": game.currencies.get(currency, {}).get("display_name", currency),
                "progress": max(0.0, min(1.0, game.get_currency(currency) / max(1, cost))),
                "available": game.check_requires(next_id)}
    return {"visible": bool(available), "title": stage, "goal": goal,
            "complete": bool(available) and next_id is None,
            "delivered": len(completed), "total": len(available)}


def check_shop_achievements(game):
    for uid, key in SHOP_ACHIEVEMENTS.items():
        if is_shop_equipment(game, uid) and game.get_upgrade_count(uid) > 0:
            game.unlock_achievement(key)
    if any(is_shop_equipment(game, uid) and upgrade.get("shop_bonus")
           and game.get_upgrade_count(uid) >= 10 for uid, upgrade in game.upgrades.items()):
        game.unlock_achievement("shop_bulk")
