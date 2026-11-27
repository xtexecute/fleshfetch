# FleshDoom

Play DOOM inside a fleshfetch tab. This mod uses the PrBoom libretro core. It
does not ship an engine or game data.

1. Copy the `FleshDoom` folder to your fleshfetch mods folder.
2. Download the PrBoom core from the [official Libretro buildbot](https://buildbot.libretro.com/nightly/). Put `prboom_libretro.dll` (Windows) or `prboom_libretro.so` (Linux) in this folder or its `cores` subfolder.
3. Put a compatible WAD here too. [Freedoom Phase 1 or 2](https://freedoom.github.io/download.html) is free game data. A WAD from your own DOOM copy also works.
4. Some PrBoom builds also require `prboom.wad`. Get it from the [PrBoom repository](https://github.com/libretro/libretro-prboom/blob/master/prboom.wad) and place it here.
5. Reload mods, open the DOOM tab, and press Start DOOM.

Click the game view to focus it. Use arrows to move/turn, Ctrl to fire, Space
to use, Shift to run, and Esc for the menu. Audio is enabled when a compatible
Qt audio output device is available. PrBoom keeps its own saves under this
mod's `saves` folder, separate from fleshfetch saves.

fleshfetch will flag this mod as suspicious because it loads a native library
through `ctypes`. Only dismiss that warning if you trust the core you downloaded.
Reloading or disabling the mod stops DOOM automatically.
