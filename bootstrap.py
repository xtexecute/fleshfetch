#!/usr/bin/env python3
import os
import sys
import traceback

# PyInstaller's Windows no-console/windowed mode sets stdin, stdout, and
# stderr to None. Several GUI/runtime libraries still expect file-like stream
# objects during startup, so install harmless devnull handles before imports.
_STDIO_DEVNULLS = []


def _ensure_standard_streams():
    for name, mode in (("stdin", "r"), ("stdout", "w"), ("stderr", "w")):
        if getattr(sys, name, None) is None:
            stream = open(os.devnull, mode, encoding="utf-8", buffering=1)
            _STDIO_DEVNULLS.append(stream)
            setattr(sys, name, stream)
        original_name = f"__{name}__"
        if getattr(sys, original_name, None) is None:
            setattr(sys, original_name, getattr(sys, name))


_ensure_standard_streams()


def _get_config_dir():
    if os.name == "nt":
        return os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")), "fleshfetch"
        )
    xdg = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(xdg, "fleshfetch")


CONFIG_DIR = _get_config_dir()
STARTUP_LOG_FILE = os.path.join(CONFIG_DIR, "startup.log")
_STARTUP_ERROR_SHOWN = False


def _write_startup_log(text):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(STARTUP_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(text)
            if not text.endswith("\n"):
                f.write("\n")
    except Exception:
        pass


def _show_startup_error():
    global _STARTUP_ERROR_SHOWN
    if _STARTUP_ERROR_SHOWN:
        return
    _STARTUP_ERROR_SHOWN = True
    if sys.platform != "win32":
        return
    try:
        import ctypes
        message = (
            "Fleshfetch crashed during startup.\n\n"
            "A traceback was written to:\n"
            f"{STARTUP_LOG_FILE}"
        )
        ctypes.windll.user32.MessageBoxW(None, message, "Fleshfetch crashed", 0x10)
    except Exception:
        pass


def _handle_uncaught_exception(exc_type, exc, tb):
    _write_startup_log("\n=== Unhandled exception ===\n")
    _write_startup_log("".join(traceback.format_exception(exc_type, exc, tb)))
    _show_startup_error()
    try:
        sys.__excepthook__(exc_type, exc, tb)
    except Exception:
        pass


sys.excepthook = _handle_uncaught_exception

os.environ["GDK_SCALE"] = "1"
os.environ["GDK_DPI_SCALE"] = "1"
os.environ["GTK_THEME"] = "Adwaita"
