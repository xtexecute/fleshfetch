# Fleshfetch 1.4 release candidate

RC1 is published on GitHub. This working copy contains the RC2 fixes.
The AUR package has not been updated to Qt.
FFTogether network testing is deferred.

## Windows

Extract `ff_v1.4.0-rc2_win.zip` completely. Open `fleshfetch/fleshfetch.exe`.
Keep `assets` and `runtime` beside it. Python, GTK and MSYS2 are not required.
The source build uses Nuitka standalone, not a self-extracting onefile bundle.

For a separate test profile in PowerShell, from the extracted fleshfetch folder:

```powershell
$env:APPDATA = Join-Path $PWD 'test-profile'
.\fleshfetch.exe
```

The normal profile is `%APPDATA%\fleshfetch`. Closing that PowerShell window
discards the temporary environment setting; the test files remain in test-profile.

Test opening the extracted ZIP on another PC too, especially an older processor.
If startup fails, check `test-profile\fleshfetch\startup.log` or the normal
profile's `startup.log`. A successful build on the developer PC is not proof of
compatibility with every other CPU or machine.

## Arch Linux / WSL

The source is copied to `/home/xtexecute/fleshfetch-1.4-test`. Your AUR checkout
at `/home/xtexecute/fleshfetch` is separate.

Install the system packages, including a font for minimal WSL installations:

```bash
sudo pacman -Syu --needed python pyside6 qt6-declarative qt6-multimedia qt6-multimedia-ffmpeg python-requests ttf-dejavu
cd /home/xtexecute/fleshfetch-1.4-test
XDG_CONFIG_HOME="$PWD/.test-profile" python main.py
```

`pyside6` is the Arch package name. Qt supplies the sound backend, so GTK,
PyGObject, pygame and external sound-player utilities are not needed for the Qt UI.
The old `--gtk` frontend still needs its own GTK dependencies.

WSLg supplies Linux GUI and audio support. Run the command in the Arch WSL shell.
If the Qt window opens but graphics are blank or unstable under WSLg, test:

```bash
XDG_CONFIG_HOME="$PWD/.test-profile" QT_QUICK_BACKEND=software python main.py
```

An isolated pip environment can also run this source without replacing Arch's
Python packages. A test environment is available at
`/home/xtexecute/fleshfetch-1.4-test-venv`:

```bash
cd /home/xtexecute/fleshfetch-1.4-test
XDG_CONFIG_HOME="$PWD/.test-profile" /home/xtexecute/fleshfetch-1.4-test-venv/bin/python main.py
```

Discord presence is optional. For a system-package-based environment, install
it in a venv rather than modifying Arch's system Python:

```bash
python -m venv --system-site-packages .venv
.venv/bin/python -m pip install pypresence
XDG_CONFIG_HOME="$PWD/.test-profile" .venv/bin/python main.py
```

The terminal browser works without opening the GUI:

```bash
XDG_CONFIG_HOME="$PWD/.test-profile" python main.py --info
```

## Things to check

- Click, buy an upgrade, and confirm that its price names the required currency.
- Create a fresh save, switch saves, back up, export, import and restore a save.
- Close and reopen the app. Check that currency and owned upgrades were saved.
- Toggle Light/Dark/System, sound and volume, then check those after reopening.
- Drag the divider and resize the window. Check currency tiles and long labels.
- Enable the Legacy Compatibility Test mod on a test save. Try its controls,
  timer, drawing and dialog. Reload twice and check for duplicates.
- Try a moving sprite; check its motion, dragging and bounds after resizing.
- Open the leaderboard. Without server environment settings, it should show an
  unavailable message and the game should remain responsive. Real submissions
  require the existing `SUPABASE_URL` and `SUPABASE_KEY` configuration.
- Check the console for tracebacks. Legacy warnings are expected in yellow.

The mod scanner is advisory. Python mods are not sandboxed. The compatibility
adapter covers common GTK controls and drawing calls, not every GTK/Cairo API.
