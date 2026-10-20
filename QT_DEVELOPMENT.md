# Qt Development Build

This checkout runs the Qt Quick frontend by default. It is separate from the
released game and has not been pushed or packaged for release.

Run on Windows:

```powershell
.\.venv\Scripts\python.exe main.py
```

For another environment, install `requirements-qt.txt` first. Qt does not need
GTK, PyGObject, Cairo, MSYS2, or pygame. Audio uses Qt Multimedia. The optional
legacy frontend remains available through `python main.py --gtk` and still
needs its original dependencies. `-I` / `--info` remains toolkit-independent.

## Appearance

Settings includes System, Light, and Dark. Light uses pale pink surfaces;
Dark uses charcoal. Both use medium-red pixel borders. Theme changes apply
immediately and persist in settings.json. System follows the OS color scheme.

The generated transparent border lives in assets/ui/red-frame.png. Qt decodes
it onto a 64-pixel grid once, then nine-slices it for buttons, tabs and the
window. The image provider uses nearest-neighbor sampling; borders are not
redrawn or regenerated per frame.

## Mod UI

Game APIs for currencies, upgrades, events, timers, commands, namespaces and
dependency registration still use the existing Python engine. Public UI calls
now return framework handles rather than toolkit widgets:

```python
def register(game):
    tab = game.add_tab("sample", "Sample")
    tab.add_label("Sample mod")
    button = tab.add_button("Add currency", lambda button: game.add_currency("flesh", 1))
    button.set_sprite("button.png", hover="button-hover.png", pressed="button-down.png")
```

Button handles support labels, visibility, sensitivity, tooltips and custom
sprite states. Image and sprite handles support position, size, rotation,
opacity, velocity and bounds helpers. A velocity is interpreted as pixels per
second and is advanced by the frontend. Calling `step()` or `bounce()` selects
manual movement so older mods with their own physics timer are not advanced
twice. `sprite.set_auto_motion(True)` resumes automatic velocity movement.
Sprite positions use a separate 16 ms model update; moving sprites keep their
QML items and textures instead of rebuilding through the general UI snapshots.

The Qt frontend includes a compatibility adapter for common old GTK mods.
`gi.repository`, `gtk_compat`, basic GTK controls, page_box containers, widget
signals, GLib timers, dialogs, file choosers, drag/motion controllers, and common
Cairo path/text drawing calls translate into Qt. No GTK installation is needed.
Legacy controls retain their Python values and callbacks when their tab changes.
Mod reload removes their callbacks, timers, controls and overlays.

This adapter is not the complete GTK/GObject or Cairo library. Custom GTK CSS,
native widget handles, Cairo image surfaces, and unimplemented toolkit classes
still need porting. CSS class requests produce deprecation warnings. New mods
should use the framework API and per-tab themes in MOD_UI_THEMES.md.
The old GTK frontend still imports the actual GTK libraries in its own process.
The existing security scan remains enabled; it is a warning system, not a
sandbox or a guarantee that arbitrary Python mods are safe.

`example_mods/LegacyCompatibilityTest` is an intentionally old-style test mod.
Copy that folder into the player mods folder and open its Legacy Test tab.
`tests/qt_legacy_check.py` loads it through the normal mod loader using temporary
player data, exercises controls, drawing, input and reload, and optionally smoke
tests the locally installed older mods. It never opens a multiplayer connection.

Player data uses the existing Fleshfetch configuration folder. Back up saves
before trying this development build; do not run it alongside the released
game against the same data. Tests use isolated temporary configuration folders.
