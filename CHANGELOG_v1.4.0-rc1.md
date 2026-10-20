## What's New

- Replaced GTK4 with a Qt interface.
- Added pixel-style borders and light/dark themes.
- Added tab-specific mod colors and custom nine-slice button sprites.
- Improved sprite animation performance.
- Improved compatibility with older mods.
- Restored the leaderboard tab.
- Split more game logic into separate modules.
- Updated the modding reference.

## Downloads

- Windows: extract the Windows ZIP completely and run `fleshfetch/fleshfetch.exe`. Keep `assets` and `runtime` beside it.
- Source: extract the source ZIP and run `python main.py` inside the `fleshfetch` folder.
- The updated modding reference is attached as a PDF.

## Arch Linux

The new interface uses PySide6/Qt instead of GTK4:

```bash
sudo pacman -Syu --needed python pyside6 qt6-declarative qt6-multimedia qt6-multimedia-ffmpeg python-requests ttf-dejavu
cd fleshfetch
python main.py
```

If WSL opens a blank window, use:

```bash
QT_QUICK_BACKEND=software python main.py
```
