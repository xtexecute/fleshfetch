# Tab colors and button skins

These APIs belong to the Qt frontend. Paths are relative to the mod folder.

Set colors on any tab, including built-in tabs:

```python
game.set_tab_theme("garden", canvas="#142820", surface="#224030",
                   accent="#48ba78", text="#e0ffe8", hover="#386848")
# The tab handle also supports garden.set_theme(...).
```

Available colors: `canvas`, `surface`, `raised`, `hover`, `pressed`, `text`,
`muted`, `line`, `accent`, `accentHover`, `focus`, `warning`, `danger`.
Use `#RRGGBB`. Omitted colors inherit the user's light or dark theme.
The active tab's palette also colors the surrounding window. Each tab header
uses its own palette. `accent` colors the pixel borders.
Calling `game.set_tab_theme("garden")` removes this mod's override. Overrides
clear on mod reload. When mods target the same color, the last registered wins.

## Nine-slice spritesheet

```python
game.add_button(
    "plant",
    tab="garden",
    text="Plant",
    sprites={
        "sheet": "assets/buttons.png",
        "border": 8,
        "normal": [0, 0, 48, 48],
        "hover": [48, 0, 48, 48],
        "pressed": [96, 0, 48, 48],
        "disabled": [144, 0, 48, 48],
    },
    on_click=plant,
)
```

Each rectangle is `[x, y, width, height]` in source pixels, measured from the
sheet's top-left corner. Draw the four states next to each other in this example.
The border is the number of pixels kept around each region: corners stay fixed,
edges stretch in one direction, and the center stretches in both directions.
Keep all states the same size to prevent visual jumps. Pixel filtering stays off.
For unequal edges, use `"border": {"left": 8, "top": 6, "right": 8, "bottom": 6}`.

Separate images also work: omit `sheet` and use image paths for the state values.
They use the same nine-slice borders. Missing hover, pressed, or disabled states
fall back to normal. A missing or invalid image uses the standard button frame.
Text is drawn over the sprite. Callbacks receive the button handle.

Change skins later with `button.set_sprites({...})`. The original
`game.add_button("garden", "Plant", plant)` and `button.set_sprite(...)` calls
remain supported. Named button IDs must be unique within a mod.

These examples are ready to include in the next modding reference PDF update.
