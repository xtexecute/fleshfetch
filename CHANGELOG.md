# Changelog

## 1.5.0-rc1

First release candidate for 1.5.0. Everything below is new since 1.4.0, including the work previously drafted for 1.4.1. Features are frozen for the RC phase.

### In the current build

#### Progression

- Added equipment and cosmetic crates. There are six crate tiers and eight possible reward rarities, from Common through Celestial. Higher-tier crates change the odds and which rarities can appear.
- Crates can drop while clicking or be bought with Flesh. Legendary and Mythical crates cost Flesh Tokens instead. Those two tiers also have pity counters for their higher-rarity rewards.
- Added 16 equippable items that improve clicking, production, luck, or crate drops. Duplicate items level up to a cap; maxed items give a potion or a token refund instead of another useless copy.
- Equipment crates can also give three temporary potions or three upgrades that last for the current run. Cosmetic crates avoid duplicate skins; when a rarity has nothing left to unlock, the crate becomes an equipment crate of the same tier.
- Added rebirths. Flesh earned during a run determines how many Flesh Tokens a rebirth gives. Flesh and vanilla upgrades reset; equipped items, unlocked cosmetics, unopened crates, and tokens stay. Unequipped items, potions, and run upgrades do not.
- Added seven Flesh Token upgrade lines and occasional permanent bonus choices. Rebirth also backs up the save before resetting the run.
- A rebirth awards at most three rounds of permanent bonus choices, even after a very large token payout. This limits the number of choices, not how many levels those bonuses can accumulate.
- Flesh Token payouts use a square-root curve with a larger early payout: 1 million flesh gives 8 tokens, 5 million gives 17, and 100 million gives 80.
- The first rebirth permanently doubles click gains and production. Practice and Maintenance each multiply their income by 1.5 per level, including gear and run bonuses. Their first three levels still cost 1, 4, and 9 tokens; later levels cost more. Other token prices are unchanged.
- Rebirth bonus items respect the level-10 equipment cap. If both Rare items are maxed, the bonus gives a Rare equipment crate instead.
- Added four manual-click upgrades and an equipment shop with production bonuses. Rewrote the vanilla upgrade names and descriptions.

#### Clicking and feedback

- The flesh tilts and compresses when clicked. Click particles come from the point of contact, and transparent pixels or empty space no longer trigger a click.
- Added a liquid click-streak meter. It takes 250 rewarded clicks to fill, raises income as it fills, and drains faster the longer clicking stops.
- Sustained implausible click speeds trigger a temporary limit of seven rewarded clicks per second.
- Every rewarded click gets a crate-drop roll. Removed a separate cooldown that gave steady 7-CPS clicking fewer rolls than 6.5 CPS.
- Dropped crates emerge from the flesh, fall to the bottom of its window, then burst into particles when collected. Click gains and crate pickups appear beside the action instead of only in text.
- Crates now have a rolling reveal when opened, with separate sounds for the roll, opening, rare rewards, collection, and a full streak.
- The reveal scrolls through item cards, loses speed, and stops on the actual awarded item. Skipping the animation does not roll or award a second reward.

#### Cosmetics and sound

- Rebuilt the skin collection around distinct artwork and behavior. All 52 finished cosmetics are obtainable from crates, across eight rarities.
- Clockwork replaces the flesh with a brass machine. Its separate gears turn in opposite directions, and its clock hands advance when clicked.
- Bitcrush has pixel artwork and its own 8-bit click. Smoke uses animated rising particles. Mint grows a pixel-art sprig that shakes, plays a leaf rustle, and sheds leaves when clicked.
- Added the Common Paper Crown, Price Tag, Sticky Note, and Button Badge accessories. The tag swings when clicked; Wobble has its own bouncier click motion.
- Added five more Uncommon skins: a turning Wind-Up Key, bouncing Party Hat, slipping Sunglasses, squeaking toy duck, and fluttering Tiny Flag. All are drawn on the same pixel grid as the Common accessories.
- Added a Mythical Cat skin using separate closed-mouth and meowing photo cutouts. Its mouth follows the MeowSynth sound when clicked.
- Added button hover and press sounds and pitch variation: 3% for ordinary clicks, 5% for organic effects, and 2% for mechanical clicks. Screen and mirror skins have pixel-art glass cracks.

#### Interface and mods

- Purchases no longer recreate the upgrade list or reset its scroll position. The tab strip has scroll arrows, mouse-wheel scrolling, and keyboard focus scrolling; selecting a tab no longer moves it before the click finishes.
- Removed Shadow Twin's second permanent shadow. Its temporary click afterimages remain.
- Mods can register rarities, crates, equipment, skins, potions, run upgrades, and permanent upgrades. Custom content uses the existing inventories and crate reveals, supports mod currencies, and stays usable when the corresponding vanilla content is disabled. Owned mod items survive unloading and reloading their definitions.
- Added configurable streak buildup, multiplier, and decay, plus registered mod settings with saved toggles, sliders, and choices. Custom skins support replacement images, overlays, sounds, alpha hitboxes, and selected-skin click callbacks.
- Mods can set the base click income per currency, including zero, without overwriting saved values or income from upgrades. Default saves no longer show an unnecessary singleplayer label.
- `disable_vanilla()` accepts separate options for upgrades, achievements, currencies, crates, rebirth, streak, equipment, cosmetics, and the clicker. Several options can be passed together. Disabled systems stop running and their Qt controls are hidden; saved progress stays intact. Older calls remain supported.
- Fixed callback ownership for assets and registrations, live updates after registry changes, hidden tab images, and mod images being overridden by equipped skins. Built-in tab IDs now give an error instead of creating an inaccessible tab.
- Legacy upgrade fields are translated when registering overrides, so old `fpc`, `fps`, and `type` values are no longer silently ignored by newer upgrade definitions.
- Added a separate startup splash with the fleshfetch and xtexecute logos, so loading has a visible screen before the main window appears.
- Added a switch between abbreviated and full currency amounts. Flesh Tokens now use the same currency system as Flesh.
- Mods can make sprites draggable and throwable, and can render live RGBA surfaces that receive keyboard and pointer input.
- Mods can register crate rewards with rarity requirements, weights, and rules for token-priced crates.
- Added `--version` and consistent release identifiers across the app, Windows launcher, source archive, Debian package, and local Arch package.

### Known limitations

- Progression can become repetitive after a few rebirths. The current systems are frozen for RC1; later-run pacing still needs feedback.
- Debian and Arch desktop installation still need verification on their target systems before the stable release.

## 1.4.0

- Switched the default frontend from GTK4 to Qt, with pixel borders and light and dark themes.
- Added tab colors and nine-slice button sprites for mods.
- Improved sprite animation and compatibility with older mods.
- Fixed mod dependency prerelease version ordering and Windows CPU build flags.
- Restored the leaderboard and added Debian 13 packaging.
