import os
import sys

from bootstrap import CONFIG_DIR

# ---------- PATHS ----------
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
    # When frozen, user-replaceable assets live beside the executable.
    EXE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXE_DIR  = BASE_DIR
INTERNAL_DIR = os.path.join(EXE_DIR, "_internal")
ASSETS_DIR = os.path.join(EXE_DIR, "assets")
BASE_ASSETS_DIR = os.path.join(BASE_DIR, "assets")


def find_app_asset(filename: str) -> str:
    """Find app assets with platform-specific folders and legacy fallbacks."""
    if sys.platform == "win32":
        candidates = [
            os.path.join(INTERNAL_DIR, filename),
            os.path.join(BASE_DIR, filename),
            os.path.join(EXE_DIR, filename),
            os.path.join(ASSETS_DIR, filename),
            os.path.join(BASE_ASSETS_DIR, filename),
        ]
    else:
        candidates = [
            os.path.join(ASSETS_DIR, filename),
            os.path.join(BASE_ASSETS_DIR, filename),
            os.path.join(BASE_DIR, filename),
            os.path.join(EXE_DIR, filename),
            os.path.join(INTERNAL_DIR, filename),
        ]
    seen = set()
    for path in candidates:
        norm = os.path.normcase(os.path.abspath(path))
        if norm in seen:
            continue
        seen.add(norm)
        if os.path.exists(path):
            return path
    return candidates[0]

STATE_FILE        = os.path.join(CONFIG_DIR, "state.json")
SETTINGS_FILE     = os.path.join(CONFIG_DIR, "settings.json")
ACHIEVEMENTS_FILE = os.path.join(CONFIG_DIR, "achievements.json")
COUNTER_FILE      = os.path.join(CONFIG_DIR, "flesh_counter.txt")
SAVES_DIR         = os.path.join(CONFIG_DIR, "saves")
SAVE_BACKUPS_DIR  = os.path.join(SAVES_DIR, "backups")

LEGACY_STATE_FILE        = os.path.join(BASE_DIR, "state.json")
LEGACY_SETTINGS_FILE     = os.path.join(BASE_DIR, "settings.json")
LEGACY_ACHIEVEMENTS_FILE = os.path.join(BASE_DIR, "achievements.json")
LEGACY_COUNTER_FILE      = os.path.join(BASE_DIR, "flesh_counter.txt")

SYSTEM_MODS_DIR = os.path.join(BASE_DIR, "mods")
USER_MODS_DIR   = os.path.join(CONFIG_DIR, "mods")


def ensure_app_dirs():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(USER_MODS_DIR, exist_ok=True)
    os.makedirs(SAVES_DIR, exist_ok=True)
    os.makedirs(SAVE_BACKUPS_DIR, exist_ok=True)
