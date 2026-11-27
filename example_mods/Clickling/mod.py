import random
import time


DEFAULT_SIZE = 80
MIN_SIZE = 48
MAX_SIZE = 160
SIZE_STEP = 16
GRAVITY = 900
WALK_SPEED = 86


def register(game):
    if not hasattr(game, "create_sprite") or not hasattr(game, "get_sprite_platforms"):
        print("[Clickling] Needs the Qt sprite API with dragging support.")
        return

    try:
        saved_size = int(game.get_mod_setting("size", DEFAULT_SIZE, namespace="Clickling"))
    except (TypeError, ValueError):
        saved_size = DEFAULT_SIZE
    size = max(MIN_SIZE, min(MAX_SIZE, saved_size))
    sprite = game.create_sprite("clickling-idle.png", size=(size, size),
                                pos=(160, 80), tooltip="Clickling: drag and throw me")
    sprite.set_draggable(True)
    sprite.set_auto_motion(False)
    state = {"held": False, "vx": 0.0, "vy": 0.0, "last": time.monotonic(),
             "pause_until": 0.0, "roam_until": 0.0, "happy_until": 0.0,
             "next_hop": 0.0, "grounded": False, "size": size,
             "pose": "idle"}

    def pose(name):
        if state["pose"] != name:
            sprite.set_image("clickling-" + name + ".png")
            state["pose"] = name

    def show(_button=None):
        sprite.show()
        if sprite.get_window_bounds()["width"]:
            sprite.move_to(100, 30)
        state["vx"] = state["vy"] = 0.0
        state["pause_until"] = time.monotonic() + 2
        pose("idle")

    def hide(_button=None):
        sprite.hide()

    tab = game.add_tab("clickling", "Clickling")
    tab.add_button("Call Clickling", show)
    tab.add_button("Hide Clickling", hide)

    def change_size(delta):
        old_size = state["size"]
        new_size = max(MIN_SIZE, min(MAX_SIZE, old_size + delta))
        if new_size == old_size:
            return
        x, y = sprite.get_pos()
        bounds = sprite.get_window_bounds()
        state["size"] = new_size
        sprite.set_size(new_size, new_size)
        sprite.move_to(max(0, min(bounds["width"] - new_size, x + (old_size - new_size) / 2)),
                       max(0, min(bounds["height"] - new_size, y + old_size - new_size)))
        game.set_mod_setting("size", new_size, namespace="Clickling")
        smaller.set_label(f"Smaller ({new_size} px)")
        larger.set_label(f"Larger ({new_size} px)")
        smaller.set_sensitive(new_size > MIN_SIZE)
        larger.set_sensitive(new_size < MAX_SIZE)

    smaller = tab.add_button(f"Smaller ({size} px)", lambda _button: change_size(-SIZE_STEP))
    larger = tab.add_button(f"Larger ({size} px)", lambda _button: change_size(SIZE_STEP))
    smaller.set_sensitive(size > MIN_SIZE)
    larger.set_sensitive(size < MAX_SIZE)

    def on_grab(event):
        if event.get("sprite_id") != sprite.id:
            return
        state["held"] = True
        state["grounded"] = False
        state["vx"] = state["vy"] = 0.0
        state["happy_until"] = time.monotonic() + 0.5
        pose("happy")

    def on_release(event):
        if event.get("sprite_id") != sprite.id:
            return
        state["held"] = False
        state["grounded"] = False
        state["last"] = time.monotonic()
        state["vx"] = max(-650, min(650, float(event.get("vx", 0))))
        state["vy"] = max(-650, min(650, float(event.get("vy", 0))))
        state["pause_until"] = state["last"] + 1.0

    def on_click(_event):
        if not sprite.is_visible():
            return
        now = time.monotonic()
        state["happy_until"] = now + 0.45
        if not state["held"] and state["grounded"] and now >= state["next_hop"]:
            state["vy"] = -170
            state["grounded"] = False
            state["next_hop"] = now + 0.9
        pose("happy")

    game.on_event("sprite_grabbed", on_grab)
    game.on_event("sprite_released", on_release)
    game.on_flesh_clicked(on_click)

    def tick():
        now = time.monotonic()
        dt = min(0.05, now - state["last"])
        state["last"] = now
        if not sprite.is_visible() or state["held"]:
            return True
        bounds = sprite.get_window_bounds()
        if not bounds["width"] or not bounds["height"]:
            return True

        x, y = sprite.get_pos()
        size = state["size"]
        max_x = max(0, bounds["width"] - size)
        floor = max(0, bounds["height"] - size - 4)
        vx, vy = state["vx"], state["vy"]
        surfaces = game.get_sprite_platforms()
        platform_top = None
        for platform in surfaces:
            top = platform["y"]
            if (x + size > platform["x"] + 8 and x < platform["x"] + platform["width"] - 8
                    and abs(y + size - top) < 3):
                platform_top = top
                break
        resting = (platform_top is not None or y >= floor - 1) and abs(vy) < 1
        state["grounded"] = resting
        if resting and now >= state["pause_until"] and abs(vx) < 1:
            vx = random.choice((-WALK_SPEED, WALK_SPEED))
            state["roam_until"] = now + random.uniform(0.7, 1.5)
        if resting and abs(vx) >= 1 and now >= state["roam_until"]:
            vx = 0.0
            state["pause_until"] = now + random.uniform(0.5, 1.5)

        next_x = max(0, min(max_x, x + vx * dt))
        if (next_x == 0 and vx < 0) or (next_x == max_x and vx > 0):
            vx = -vx * 0.5
        next_y = y + vy * dt + GRAVITY * dt * dt / 2
        vy += GRAVITY * dt
        if vy >= 0:
            for platform in surfaces:
                top = platform["y"]
                if (next_x + size <= platform["x"] + 8 or next_x >= platform["x"] + platform["width"] - 8):
                    continue
                if y + size <= top + 4 and next_y + size >= top:
                    next_y = top - size
                    vy = -vy * 0.25 if vy > 180 else 0.0
                    break
        if next_y >= floor:
            next_y = floor
            vy = -vy * 0.25 if vy > 180 else 0.0
        state["vx"], state["vy"] = vx, vy
        if abs(next_x - x) > 0.01 or abs(next_y - y) > 0.01:
            sprite.move_to(next_x, next_y)
        if now > state["happy_until"]:
            if abs(vx) > 1 and abs(vy) < 15:
                pose("walk-1" if int(now / 0.16) % 2 else "walk-2")
            else:
                pose("idle")
        return True

    game.set_timer(0.033, tick)
