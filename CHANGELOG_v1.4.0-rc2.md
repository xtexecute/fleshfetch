## Fixes

- Stopped the sprite motion timer from running when idle.
- Fixed mod dependency version checks treating prereleases as newer than final releases.
- Updated outdated Qt release documentation and clarified the optional GTK fallback.

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
