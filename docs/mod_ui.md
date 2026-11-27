# Mod API

Current Qt API for 1.5.0-rc1. The versioned 1.3 and 1.4 PDFs
describe older builds; use this page for the calls below.

## Disable vanilla components

```python
game.disable_vanilla(upgrades=True, achievements=True, crates=True,
                     rebirth=True, streak=True)
```

Pass any combination of these boolean options:

| Option | Effect |
| --- | --- |
| `upgrades` | Removes built-in shop upgrades and their income and critical-click effects. Mod-owned replacements remain. |
| `achievements` | Hides built-in achievements and stops unlocking them. Earned flags remain saved. |
| `currencies` | Hides vanilla Flesh and Flesh Tokens. Supply a replacement `primary_currency`. |
| `crates` | Stops built-in drops, purchases, openings, and grants. Mod crates remain available. |
| `rebirth` | Disables vanilla resets, token upgrades, bonus choices, and permanent income/luck bonuses. Mod permanent upgrades remain available. |
| `streak` | Disables streak fill, its income multiplier, and the streak liquid. |
| `equipment` | Disables built-in equipped items, potions, and run boosts without deleting them. Mod items remain available. |
| `cosmetics` | Disables vanilla skin display and selection without deleting the saved selection. |
| `clicker` | Hides the Qt clicker panel and blocks its click rewards. Mod controls and passive production remain available. |

Omitted options and `False` leave that component unchanged. Calls are cumulative;
reload mods to restore the default configuration. Invalid options raise before
changing anything. Check a component with `game.is_vanilla_enabled("crates")`.

With no options, `game.disable_vanilla()` disables upgrades, achievements,
crates, rebirth, streak, equipment, and cosmetics. It keeps the shared clicker
and currencies so a mod can build its own game on them.

For a complete content replacement with a new currency:

```python
def register(game):
    game.register_currency("souls", "Souls")
    game.disable_vanilla(primary_currency="souls")
```

That form also hides vanilla currencies; the shared clicker awards Souls.
The replacement currency can be registered before or after the call, but must
exist when registration finishes. To hide the shared clicker too, call
`game.disable_vanilla(clicker=True)` afterward.

Crates and their inventories are separate switches. Disabling equipment or
cosmetics does not change crate odds or delete rewards. Disabling crates
collects already-earned pending drops once; later grants of built-in crates raise
`RuntimeError`. The Crates and Rebirth tabs remain when registered mod content
uses them. All component switches are runtime configuration, not save edits.

The older `disable_vanilla("souls")` call still works. The helpers
`disable_vanilla_upgrades()` and `disable_vanilla_achievements()` remain as
compatibility wrappers; new code should use the boolean options.

## Registries and assets

To start a mod with no income from clicking:

```python
def register(game):
    game.set_base_cpc(0)
```

This changes the base click gain, not the gains supplied by owned upgrades.
Zero is valid; vanilla still starts at 1. Set a specific registered currency
with `game.set_base_cpc(0, currency="souls")`, or omit `currency` to use the
current primary currency. Call it after choosing a replacement primary currency.
`get_base_cpc(currency=None)` reads the base; `compute_click_gain(currency)`
includes upgrades and applicable progression multipliers. `compute_cpc(currency)`
continues to return only the upgrade contribution.

Base CPC overrides apply while their mod is loaded, including after rebirth or
switching saves. They do not overwrite saved click values. Reloading or removing
the mod restores the saved/default base unless another mod sets an override.
When several mods set the same currency, the most recent call wins.

`register_currency(name, display_name)` creates or renames a currency without
replacing its balance. `register_upgrade()` and `register_achievement()` update
the live Qt interface, including when called after startup.
New upgrades use `category` and a `currency_effects` list with `currency`, `cpc`,
`cps`, and optional `on_buy` fields. Legacy `type`, `fpc`, and `fps` fields are
translated, including when overriding a built-in upgrade.

```python
game.set_flesh_image("assets/body.png")
game.set_click_sound("assets/click.wav")
path = game.resolve_asset_path("assets/icon.png")
```

Relative asset paths resolve against the owning mod, including inside timers,
event hooks, and button callbacks. Absolute paths also work. A replacement
flesh image takes precedence over an equipped vanilla skin and uses its own
alpha hitbox. The skin selection returns when the mod is unloaded.
`set_click_sound()` changes the default click audio; equipped skins can have
separate sounds. Disable cosmetics when a mod replaces all click feedback.
`game.active_cosmetic()` returns the displayed registered skin ID, or an empty
string for the default image or an unregistered `set_flesh_image()` replacement.
Make registry and UI changes from `register()` or API callbacks on the UI thread.
Live surfaces can receive frames from a worker thread, as described below.

## Progression registration

Definitions belong to the current mod. IDs returned by these calls are
`mod_id:local_id`; local IDs also work inside that mod's callbacks. Register
rarities and items before crates that refer to them. Built-in rarity IDs are
`Common`, `Uncommon`, `Rare`, `Epic`, `Legendary`, `Mythical`, `Radiant`, and
`Celestial`, ranked 0 through 7.

```python
def register(game):
    rarity = game.register_rarity("unusual", name="Unusual",
                                  color="#53bbaa", rank=2.5)
    glove = game.register_equipment("glove", name="Workshop Glove",
        rarity=rarity, bonuses={"click": 0.25, "cps": 0.10},
        max_level=5, icon="assets/glove.png")
    box = game.register_crate("workshop", name="Workshop Crate",
        kind="equipment", currency="flesh", cost=500,
        rarity_weights={rarity: 1})
```

Equipment bonuses are fractions: `0.25` adds 25%. Supported stats are `click`,
`cps`, `drop`, and `luck`. Duplicate levels use
`base * (1 + level_growth * sqrt(level - 1))`; `level_growth` defaults to 0.2.
Click and production bonuses also work with a replacement primary currency.
The existing drop and luck caps still apply.

| Call | Required keyword arguments | Optional arguments |
| --- | --- | --- |
| `register_rarity(id, ...)` | `name`, `color`, `rank` | None |
| `register_equipment(id, ...)` | `name`, `bonuses` | `rarity="Common"`, `max_level=10`, `level_growth=0.2`, `icon` |
| `register_skin(id, ...)` | `name` | `rarity="Common"`, `image`, `overlay`, `icon`, `click_sound`, `sound_profile="default"`, `description`, `crate_pool=True`, `on_click` |
| `register_potion(id, ...)` | `name`, `stat`, `duration` | `amount=2`, `mode="multiply"`, `description`, `icon` |
| `register_run_upgrade(id, ...)` | `name`, `stat`, `amount` | `description` |
| `register_rebirth_upgrade(id, ...)` | `name`, `stat`, `amount`, `base_cost` | `cost_multiplier=2`, `currency="tokens"`, `max_level=10`, `description` |
| `register_crate(id, ...)` | `name`, `rarity_weights` | `kind="equipment"`, `currency="flesh"`, `cost=0`, `rewards`, `icon`, `drop_chance=0`, `pity_after=0`, `pity_rarity` |

`grant_equipment(id, count=1)`, `grant_skin(id)`, `grant_potion(id, count=1)`,
and `grant_run_upgrade(id, count=1)` add owned content. Equipment grants respect
its level cap. Use `equip_gear(id)`, `select_skin(id)`, `use_potion(id)`, and
`buy_rebirth_upgrade(id)` for player actions; they return `(ok, message)`.
Registration does not grant items. Runtime definitions clear on reload; owned
IDs, equipped IDs, crate counts, and settings stay saved if a mod is absent.
Unavailable content has no effects and returns when its mod registers it again.
Rebirth still clears unequipped equipment, potions, and run upgrades.

Skins can replace the body with `image`, add an `overlay`, or use both. Overlay
images should share the body's canvas and alignment; they inherit its click
motion. Replacement images use their own alpha hitbox. `click_sound` accepts a
WAV path; `sound_profile` is `default`, `organic`, or `mechanical`. A skin's
`on_click(context)` runs only for accepted clicks while selected. Its context
contains `game`, `x`, `y`, `gains`, and `total_clicks`. Coordinates are logical
pixels within the click stage. Use
`set_skin_frame("assets/open.png")` to change that skin's body frame; switching
skins, saves, or reloading clears the override. Timers and event hooks remain
available for effects. `skin_changed` supplies `skin_id` when selection changes.

Registered equipment and skins enter built-in crate pools at their rarity.
`crate_pool=False` keeps a skin out of those pools without hiding it from the
inventory. New rarities need a custom crate with matching `rarity_weights`.
Custom crates use weighted equipment or skin pools by default. For explicit
rewards:

```python
game.register_crate("supplies", name="Supplies", currency="flesh", cost=100,
    rarity_weights={"Common": 1}, rewards=[
        {"type": "potion", "id": "quick_hands", "weight": 3, "amount": 2},
        {"type": "currency", "id": "flesh", "weight": 1, "amount": 50},
    ])
```

Reward types are `equipment`, `skin`, `potion`, `run_upgrade`, and `currency`.
Entries inherit an item's rarity, or Common for potions, run upgrades, and
currency. Override it with `rarity`. Each weighted rarity needs a reward.
Exhausted or unavailable rewards leave the crate unopened. `drop_chance` is a
per-accepted-click probability, scaled by drop bonuses and capped at 100%.
Custom drops use the falling-crate effect. Optional pity guarantees at least
`pity_rarity` on opening number `pity_after` without a qualifying reward.
`register_crate_reward()` remains available for callback rewards in vanilla crates.
`crate_preview(kind, tier)` returns eligible reel entries without consuming a
crate or rolling a reward. Entries include item IDs, names, icons, rarity colors,
and visual weights; the animation does not change the gameplay roll.

Potions last `duration` seconds. `mode="multiply"` uses `amount` as a multiplier;
`mode="add"` adds a fractional stat bonus. Using a potion replaces the active
potion for that stat. Run and rebirth upgrades add `amount` per level; permanent
upgrade prices are `ceil(base_cost * cost_multiplier ** level)`.

## Streak and settings

```python
game.configure_streak(clicks_to_full=300, max_multiplier=1.4, curve=2,
                      grace=2, drain_base=0.8, drain_acceleration=1.5,
                      drain_max=48, currency="flesh")
```

Omitted values stay unchanged. Defaults are 250 clicks, x1.5 maximum, curve 2.4,
1.5 seconds of grace, and the drain values above. Drain is measured in fill
percentage points per second. Changes reset the current streak and clear on
mod reload; when mods change the same setting, the last call wins. This does
not re-enable a disabled streak.

```python
game.register_setting("particles", name="Leaf particles", default=True)
game.register_setting("speed", name="Growth speed", kind="number",
                      default=2, minimum=1, maximum=5, step=0.1)
game.register_setting("season", name="Season", kind="choice",
                      default="Spring", choices=["Spring", "Autumn"])
```

These create controls in Settings. Values use the existing
`get_mod_setting(key)` and `set_mod_setting(key, value)` storage. Optional
`on_change(value)` runs under the owning mod when a value changes. Numeric
values must be within bounds; choices and boolean values are validated too.
Defaults do not trigger callbacks. Set up initial behavior from the stored
value in `register()`.

## Tabs and buttons

```python
garden = game.add_tab("garden", "Garden")
garden.add_label("Seeds")
garden.add_button("Plant", lambda button: game.add_currency("flesh", 1))
```

Qt returns `TabHandle` and `ButtonHandle` objects, not GTK widgets. Handles
support `hide()`, `show()`, and `remove()`; buttons also support `set_label()`,
`set_sensitive()`, and `set_tooltip_text()`. Removed mod-owned controls are
cleaned up on reload.

Built-in tab IDs are `upgrades`, `achievements`, `crates`, `rebirth`, `saves`,
`stats`, `settings`, `console`, and `leaderboard`. Add controls to an existing
tab with `game.add_tab_button("settings", "Reset", callback)`. `add_tab()`
requires a new ID; it cannot replace a built-in tab.

For live pixel buffers and focused keyboard/pointer input, see [mod surfaces](mod_surfaces.md).

## Tab colors

```python
game.set_tab_theme("garden", canvas="#142820", surface="#224030",
                   accent="#48ba78", text="#e0ffe8", hover="#386848")
```

The tab handle also supports `garden.set_theme(...)`. Available colors are
`canvas`, `surface`, `raised`, `hover`, `pressed`, `text`, `muted`, `line`,
`accent`, `accentHover`, `focus`, `warning`, and `danger`. Use `#RRGGBB`.
Omitted colors inherit the user's light or dark theme. The active tab's palette
colors the window; each tab header uses its own palette. Calling
`game.set_tab_theme("garden")` removes this mod's override. Overrides clear
on mod reload. When mods set the same color, the last registered value wins.

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
sheet's top-left corner. The border keeps the corners fixed, stretches edges
in one direction, and stretches the center in both directions. Keep states
the same size to avoid visual jumps. For unequal edges, use
`"border": {"left": 8, "top": 6, "right": 8, "bottom": 6}`.

Separate images also work: omit `sheet` and use image paths for the states.
Missing states fall back to `normal`; invalid images use the standard button
frame. Text is drawn over the sprite. Callbacks receive the button handle.
Change the skin later with `button.set_sprites({...})`. The older
`game.add_button("garden", "Plant", plant)` and `button.set_sprite(...)`
calls remain supported. Named button IDs must be unique within a mod.
