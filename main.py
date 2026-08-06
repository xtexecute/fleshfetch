#!/usr/bin/env python3
import sys

from bootstrap import _handle_uncaught_exception
from paths import ensure_app_dirs


def main():
    ensure_app_dirs()
    from ui import main as run_game

    run_game()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        _handle_uncaught_exception(type(exc), exc, exc.__traceback__)
        sys.exit(1)
