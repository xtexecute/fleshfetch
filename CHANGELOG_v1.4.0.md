## What's New

- Replaced the default GTK4 interface with Qt.
- Added pixel-style borders and light/dark themes.
- Added tab-specific mod colors and custom nine-slice button sprites.
- Improved sprite animation and stopped the motion timer running when idle.
- Improved compatibility with older mods.
- Fixed prerelease version ordering in mod dependency checks.
- Restored the leaderboard tab.
- Split more game logic into separate modules.
- Fixed Windows CPU build flags during compilation and linking to avoid unsupported instructions.
- Added a Debian 13 `.deb` package.
- Updated the modding reference.

## Downloads

Windows: extract the Windows ZIP completely and run `fleshfetch/fleshfetch.exe`.
Keep `assets` and `runtime` beside it.

Source: extract the source ZIP and run `python main.py`.

## Debian 13

```bash
sudo apt update
sudo apt install ./fleshfetch_1.4.0-1_all.deb
fleshfetch
```

## Arch Linux

```bash
sudo pacman -Syu --needed python pyside6 qt6-declarative qt6-multimedia qt6-multimedia-ffmpeg python-requests ttf-dejavu
cd fleshfetch
python main.py
```

If WSL opens a blank window:

```bash
QT_QUICK_BACKEND=software python main.py
```
