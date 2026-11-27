# Mod surfaces

The Qt frontend lets a mod put a live image and input target in its own tab.
The mod supplies frames; fleshfetch does not run an emulator or game engine for it.

```python
def register(game):
    game.add_tab("screen", "Screen")

    def on_key(event):
        print(event["key"], event["pressed"])

    def on_pointer(event):
        print(event["kind"], event["x"], event["y"])

    screen = game.create_surface("screen", 320, 200,
                                 on_key=on_key, on_pointer=on_pointer)
    screen.set_frame(bytes((20, 20, 20, 255)) * (320 * 200))
```

`set_frame(rgba)` expects exactly `width * height * 4` bytes in RGBA order,
left to right, top to bottom. Each surface is limited to a 16 MiB frame.
Frame changes repaint without rebuilding the mod tab. A mod can call
`set_frame()` from a worker thread, but input callbacks run on the UI thread.
Keep expensive engine work off the UI thread.

`on_key(event)` receives `key` (a Qt key code), `pressed` (boolean), and
`modifiers` (Qt modifier flags). The surface receives keyboard input after it
has been clicked. `on_pointer(event)` receives `kind` (`press`, `release`, or
`move`), pixel coordinates `x` and `y`, and Qt `button` and `buttons` flags.
The coordinates are scaled back to the surface's original frame size.

The handle supports `hide()`, `show()`, and `remove()`. fleshfetch removes
mod-owned surfaces on reload. This API is for the Qt frontend, not the GTK
fallback.
