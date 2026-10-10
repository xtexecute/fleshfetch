#!/usr/bin/env python3
import argparse
import sys

from bootstrap import _handle_uncaught_exception
from paths import ensure_app_dirs


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="Fleshfetch")
    parser.add_argument(
        "-I",
        "--info",
        action="store_true",
        help="browse saves, stats, upgrades, and installed mods in the terminal",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    ensure_app_dirs()
    if args.info:
        from info_tui import run_info_tui

        return run_info_tui()
    from ui import main as run_game

    return run_game()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        _handle_uncaught_exception(type(exc), exc, exc.__traceback__)
        sys.exit(1)
