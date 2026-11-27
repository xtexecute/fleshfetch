#!/usr/bin/env python3
import argparse
import sys

from bootstrap import _handle_uncaught_exception
from paths import ensure_app_dirs
from app_version import VERSION


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="fleshfetch")
    parser.add_argument("--version", action="version", version=f"fleshfetch {VERSION}")
    parser.add_argument(
        "--gtk", action="store_true", help="use the legacy GTK frontend"
    )
    parser.add_argument(
        "-I",
        "--info",
        action="store_true",
        help="browse saves, stats, upgrades, and installed mods in the terminal",
    )
    parser.add_argument("--splash-only", nargs=2, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    if args.splash_only:
        from startup_splash import run_splash

        return run_splash(*args.splash_only)
    ensure_app_dirs()
    if args.info:
        from info_tui import run_info_tui

        return run_info_tui()
    if args.gtk:
        from ui import main as run_game
        return run_game()

    from startup_splash import show_startup_splash

    with show_startup_splash() as splash_done:
        from qt_frontend import main as run_game

        return run_game(on_first_frame=splash_done)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        _handle_uncaught_exception(type(exc), exc, exc.__traceback__)
        sys.exit(1)
