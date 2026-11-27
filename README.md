# fleshfetch

A Qt clicker game and Python modding framework. The base game is Mod #1.
I used to call this a joke, but I'm not so sure anymore.

This game is **IN DEVELOPMENT**.

**1.5.0-rc1** is a prerelease. New features are frozen while bugs and compatibility
are checked. Progression can still become repetitive after several rebirths;
longer-run pacing needs more player feedback before the stable release.

Please report bugs in Issues.

## Branches

- [`main`](https://github.com/xtexecute/fleshfetch/tree/main): Stable releases.
- [`experimental`](https://github.com/xtexecute/fleshfetch/tree/experimental): Changes that have passed basic testing and are ready for wider testing.
- [`bleeding-edge`](https://github.com/xtexecute/fleshfetch/tree/bleeding-edge): The newest available code. Every in-progress change may be committed here, so it may be incomplete, broken, or unable to launch.

Changes move from `bleeding-edge` to `experimental`, then from `experimental` to `main` when they are ready. Experimental builds are published as prereleases. Use the experimental bug report form for experimental and bleeding-edge builds.

## Run

Windows: extract the release ZIP and run `fleshfetch.exe` from its `fleshfetch` folder.

Arch Linux: install from the AUR, then run `fleshfetch`.

Debian 13: install the release `.deb`, then run `fleshfetch`.

Source: install `requirements-qt.txt` with pip, then run `python main.py`. Qt is the default frontend. The optional GTK frontend is available with `python main.py --gtk` if its dependencies are installed.

Run `fleshfetch --info` for the terminal save and mod browser.
Run `fleshfetch --version` to check the installed version.

Mod authors: [current mod API](docs/mod_ui.md), [live surfaces](docs/mod_surfaces.md).

See the [changelog](CHANGELOG.md) for recent releases.

The flesh image is by Sifat Wizard via Vecteezy.
The Bitcrush click and glass-crack sounds use Kenney's [UI Audio](https://kenney.nl/assets/ui-audio) and [Impact Sounds](https://kenney.nl/assets/impact-sounds) packs (CC0).
Blacksmith's hammer hit is an isolated strike from Hansjoerg Malthaner's [Smithing Sound](https://opengameart.org/content/smithing-sound) ([CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)). It was trimmed and faded for the game.
Mint's leaf rustle is "Foliage04.wav" from Antoine Goumain's [Nature Sounds Pack](https://opengameart.org/content/nature-sounds-pack) ([CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/)). The game uses the recording unmodified.
Squeaky Toy uses "squeak toy - squeak2.wav" by bart from [Squeak toy sounds](https://opengameart.org/content/squeak-toy-sounds) (CC0).
Cat's meow was rendered with the MIT-licensed [MeowSynth recreation](https://github.com/mcardonaserrano/meowsynth-mpc) by mcardonaserrano, based on the original MeowSynth by KNOBSTER.
