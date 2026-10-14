"""Read-only terminal browser for Fleshfetch saves and installed mods."""

from __future__ import annotations

import json
import os
import sys
import textwrap
from dataclasses import dataclass

from defaults import BASE_UPGRADES, DEFAULT_ACHIEVEMENTS, DEFAULT_STATE
from paths import SAVES_DIR, SETTINGS_FILE, SYSTEM_MODS_DIR, USER_MODS_DIR


ASCII_LOGO = (
    "   __ _           _      __     _       _     ",
    "  / _| |         | |    / _|   | |     | |    ",
    " | |_| | ___  ___| |__ | |_ ___| |_ ___| |__  ",
    " |  _| |/ _ \\/ __| '_ \\|  _/ _ \\ __/ __| '_ \\ ",
    " | | | |  __/\\__ \\ | | | ||  __/ || (__| | | |",
    " |_| |_|\\___||___/_| |_|_| \\___|\\__\\___|_| |_|",
)


@dataclass
class BrowserData:
    settings: dict
    saves: list[dict]
    mods: list[dict]


def _load_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value
    except (OSError, ValueError, TypeError):
        return default


def _load_json_object(path: str) -> tuple[dict, bool]:
    if not os.path.isfile(path):
        return {}, False
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
        if isinstance(value, dict):
            return value, False
    except (OSError, ValueError, TypeError):
        pass
    return {}, True


def _normalize_dependencies(raw_dependencies) -> list[dict]:
    if isinstance(raw_dependencies, (str, dict)):
        raw_dependencies = [raw_dependencies]
    if not isinstance(raw_dependencies, list):
        return []

    dependencies = []
    for dependency in raw_dependencies:
        if isinstance(dependency, str):
            mod_id = dependency.strip()
            version = ""
            optional = False
        elif isinstance(dependency, dict):
            mod_id = str(
                dependency.get("id")
                or dependency.get("name")
                or dependency.get("mod")
                or ""
            ).strip()
            version = str(
                dependency.get("version") or dependency.get("min_version") or ""
            )
            optional = bool(dependency.get("optional", False))
        else:
            continue
        if mod_id:
            dependencies.append({"id": mod_id, "version": version, "optional": optional})
    return dependencies


def _version_meets_requirement(version: str, required: str) -> bool:
    if not required or version == required:
        return True

    def parts(value):
        result = []
        for piece in str(value or "").replace("-", ".").split("."):
            digits = "".join(character for character in piece if character.isdigit())
            result.append(int(digits or 0))
        return result

    current = parts(version)
    minimum = parts(required)
    size = max(len(current), len(minimum))
    return current + [0] * (size - len(current)) >= minimum + [0] * (size - len(minimum))


def load_saves(saves_dir: str = SAVES_DIR, settings_file: str = SETTINGS_FILE) -> tuple[dict, list[dict]]:
    settings = _load_json(settings_file, {})
    if not isinstance(settings, dict):
        settings = {}
    active_save_id = str(settings.get("active_save_id") or "main")
    saves = []
    try:
        filenames = sorted(os.listdir(saves_dir))
    except OSError:
        filenames = []

    for filename in filenames:
        path = os.path.join(saves_dir, filename)
        if not filename.lower().endswith(".json") or not os.path.isfile(path):
            continue
        data = _load_json(path, None)
        if not isinstance(data, dict):
            continue
        save_id = str(data.get("id") or os.path.splitext(filename)[0])
        data = dict(data)
        data.setdefault("id", save_id)
        data.setdefault("name", "Main Save" if save_id == "main" else save_id)
        data.setdefault("save_kind", "singleplayer")
        data.setdefault("created_at", "Unknown")
        data.setdefault("updated_at", data["created_at"])
        data.setdefault("required_mods", [])
        data.setdefault("mod_data", {})
        data.setdefault("state", dict(DEFAULT_STATE))
        data.setdefault("achievements", dict(DEFAULT_ACHIEVEMENTS))
        data["_path"] = path
        data["_active"] = save_id == active_save_id
        saves.append(data)

    saves.sort(key=lambda save: str(save.get("updated_at") or ""), reverse=True)
    return settings, saves


def _read_enabled(mod_dir: str) -> tuple[bool, bool]:
    path = os.path.join(mod_dir, "enabled.txt")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return "false" not in handle.read().strip().lower(), True
    except OSError:
        return True, False


def discover_mods(
    system_mods_dir: str = SYSTEM_MODS_DIR,
    user_mods_dir: str = USER_MODS_DIR,
) -> list[dict]:
    mods = []
    for source, root in (("system", system_mods_dir), ("user", user_mods_dir)):
        try:
            entries = sorted(os.listdir(root), key=str.lower)
        except OSError:
            continue
        for entry in entries:
            mod_dir = os.path.join(root, entry)
            if not os.path.isdir(mod_dir) or not os.path.isfile(os.path.join(mod_dir, "mod.py")):
                continue
            manifest_path = os.path.join(mod_dir, "manifest.json")
            manifest, manifest_error = _load_json_object(manifest_path)
            enabled, has_enabled_file = _read_enabled(mod_dir)
            dependencies = _normalize_dependencies(
                manifest.get("dependencies")
                or manifest.get("depends")
                or manifest.get("requires_mods")
                or manifest.get("required_mods")
            )
            mods.append(
                {
                    "id": entry,
                    "key": f"{source}:{entry}",
                    "source": source,
                    "path": mod_dir,
                    "name": str(manifest.get("name") or manifest.get("title") or entry),
                    "version": str(manifest.get("version") or ""),
                    "author": str(manifest.get("author") or ""),
                    "description": str(manifest.get("description") or ""),
                    "game_title": str(manifest.get("game_title") or "").strip(),
                    "dependencies": dependencies,
                    "enabled": enabled,
                    "has_enabled_file": has_enabled_file,
                    "manifest_error": manifest_error,
                }
            )

    available = {mod["id"]: mod for mod in mods if mod["enabled"]}
    for mod in mods:
        missing = []
        for dependency in mod["dependencies"]:
            if dependency["optional"]:
                continue
            installed = available.get(dependency["id"])
            if installed is None or not _version_meets_requirement(
                installed.get("version", ""), dependency["version"]
            ):
                label = dependency["id"]
                if dependency["version"]:
                    label += f" >= {dependency['version']}"
                missing.append(label)
        mod["missing_dependencies"] = missing
    return mods


def collect_browser_data(
    saves_dir: str = SAVES_DIR,
    settings_file: str = SETTINGS_FILE,
    system_mods_dir: str = SYSTEM_MODS_DIR,
    user_mods_dir: str = USER_MODS_DIR,
) -> BrowserData:
    settings, saves = load_saves(saves_dir, settings_file)
    mods = discover_mods(system_mods_dir, user_mods_dir)
    return BrowserData(settings=settings, saves=saves, mods=mods)


def _number(value) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}"


def _float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError, OverflowError):
        return float(default)


def _vanilla_rates(state: dict) -> tuple[dict, dict]:
    currencies = state.get("currencies") if isinstance(state.get("currencies"), dict) else {}
    cpc = {str(name): 0.0 for name in currencies}
    cps = {str(name): 0.0 for name in currencies}
    cpc["flesh"] = _float(state.get("flesh_per_click", 1.0), 1.0)
    cps.setdefault("flesh", 0.0)
    owned = state.get("upgrades_owned") if isinstance(state.get("upgrades_owned"), dict) else {}
    for upgrade_id, upgrade in BASE_UPGRADES.items():
        try:
            count = int(owned.get(upgrade_id, 0) or 0)
        except (TypeError, ValueError):
            count = 0
        for effect in upgrade.get("currency_effects", []):
            currency = str(effect.get("currency") or "flesh")
            cpc[currency] = cpc.get(currency, 0.0) + _float(effect.get("cpc", 0.0)) * count
            cps[currency] = cps.get(currency, 0.0) + _float(effect.get("cps", 0.0)) * count
    return cpc, cps


def _required_mod_lines(required_mods, installed_ids: set[str]) -> list[str]:
    if not isinstance(required_mods, list) or not required_mods:
        return ["  None"]
    lines = []
    for requirement in required_mods:
        if isinstance(requirement, dict):
            mod_id = str(requirement.get("id") or "")
            label = str(requirement.get("name") or mod_id or "Unknown mod")
            version = str(requirement.get("version") or "")
            if version:
                label += f" {version}"
        else:
            mod_id = str(requirement)
            label = mod_id
        status = "installed" if mod_id in installed_ids else "MISSING"
        lines.append(f"  {label} [{status}]")
    return lines


def save_detail_lines(save: dict, mods: list[dict]) -> list[str]:
    state = save.get("state") if isinstance(save.get("state"), dict) else {}
    currencies = state.get("currencies") if isinstance(state.get("currencies"), dict) else {}
    owned = state.get("upgrades_owned") if isinstance(state.get("upgrades_owned"), dict) else {}
    achievements = save.get("achievements") if isinstance(save.get("achievements"), dict) else {}
    namespaces = save.get("mod_data") if isinstance(save.get("mod_data"), dict) else {}
    installed_ids = {mod["id"] for mod in mods}
    cpc, cps = _vanilla_rates(state)

    lines = [
        f"Name: {save.get('name')}",
        f"ID: {save.get('id')}",
        f"Active: {'yes' if save.get('_active') else 'no'}",
        f"Type: {save.get('save_kind')}",
        f"Created: {save.get('created_at')}",
        f"Updated: {save.get('updated_at')}",
        f"File: {save.get('_path')}",
        "",
        "Stats",
        f"  Total clicks: {_number(state.get('total_clicks', 0))}",
        "  Vanilla rates exclude effects supplied by mod code.",
    ]
    for currency in sorted(set(currencies) | set(cpc) | set(cps)):
        lines.append(
            f"  {currency}: {_number(currencies.get(currency, 0))} "
            f"(per click: {_number(cpc.get(currency, 0))}, per second: {_number(cps.get(currency, 0))})"
        )

    lines.extend(["", "Upgrades"])
    populated_upgrades = []
    for upgrade_id, raw_count in sorted(owned.items()):
        try:
            count = int(raw_count or 0)
        except (TypeError, ValueError):
            count = raw_count
        if not count:
            continue
        upgrade = BASE_UPGRADES.get(upgrade_id, {})
        populated_upgrades.append(f"  {upgrade.get('name') or upgrade_id}: {count}")
    lines.extend(populated_upgrades or ["  None"])

    lines.extend(["", "Achievements"])
    unlocked = []
    for achievement_id, achievement in sorted(achievements.items()):
        if isinstance(achievement, dict) and achievement.get("unlocked"):
            unlocked.append(f"  {achievement.get('name') or achievement_id}")
    lines.extend(unlocked or ["  None unlocked"])

    lines.extend(["", "Required mods"])
    lines.extend(_required_mod_lines(save.get("required_mods"), installed_ids))
    lines.extend(["", "Mod save namespaces"])
    if namespaces:
        for namespace, value in sorted(namespaces.items()):
            if isinstance(value, dict):
                summary = f"{len(value)} key(s): {', '.join(map(str, list(value)[:6]))}"
            elif isinstance(value, list):
                summary = f"list with {len(value)} item(s)"
            else:
                summary = type(value).__name__
            lines.append(f"  {namespace}: {summary}")
    else:
        lines.append("  None")
    return lines


def mod_detail_lines(mod: dict) -> list[str]:
    if not mod["enabled"]:
        status = "Disabled"
    elif mod.get("missing_dependencies"):
        status = "Missing dependencies"
    else:
        status = "Enabled"
    lines = [
        f"Name: {mod['name']}",
        f"ID: {mod['id']}",
        f"Version: {mod['version'] or 'Not specified'}",
        f"Author: {mod['author'] or 'Not specified'}",
        f"Status: {status}",
        f"Source: {mod['source']}",
        f"Path: {mod['path']}",
        f"enabled.txt: {'present' if mod['has_enabled_file'] else 'missing (defaults to true)'}",
        "",
        "Description",
        f"  {mod['description'] or 'No description provided.'}",
        "",
        "Dependencies",
    ]
    if mod["dependencies"]:
        for dependency in mod["dependencies"]:
            label = dependency["id"]
            if dependency["version"]:
                label += f" >= {dependency['version']}"
            if dependency["optional"]:
                label += " (optional)"
            lines.append(f"  {label}")
    else:
        lines.append("  None")
    if mod.get("missing_dependencies"):
        lines.extend(["", "Missing dependencies"])
        lines.extend(f"  {item}" for item in mod["missing_dependencies"])
    if mod["game_title"]:
        lines.extend(["", f"Custom game title: {mod['game_title']}"])
    if mod["manifest_error"]:
        lines.extend(["", "Warning: manifest.json could not be parsed."])
    lines.extend(["", "Mod code was not imported or executed by this browser."])
    return lines


def game_info_lines(data: BrowserData) -> list[str]:
    return [
        *ASCII_LOGO,
        "",
        "Fleshfetch terminal information browser",
        "",
        f"Save directory: {SAVES_DIR}",
        f"User mod directory: {USER_MODS_DIR}",
        f"System mod directory: {SYSTEM_MODS_DIR}",
        f"Discovered saves: {len(data.saves)}",
        f"Discovered mods: {len(data.mods)}",
        "",
        "This browser is read-only and does not initialize GTK or execute mod code.",
    ]


def print_static_report(data: BrowserData, stream=None) -> None:
    stream = stream or sys.stdout
    print("\n".join(ASCII_LOGO), file=stream)
    print("\nSaves", file=stream)
    if not data.saves:
        print("  No saves found.", file=stream)
    for save in data.saves:
        marker = "*" if save.get("_active") else " "
        print(
            f" {marker} {save.get('name')} [{save.get('save_kind')}] "
            f"updated {save.get('updated_at')}",
            file=stream,
        )
    print("\nInstalled mods", file=stream)
    if not data.mods:
        print("  No mods found.", file=stream)
    for mod in data.mods:
        status = "enabled" if mod["enabled"] else "disabled"
        print(f"  {mod['name']} {mod['version']} [{status}, {mod['source']}]".rstrip(), file=stream)


class InfoBrowser:
    HOME_ITEMS = ("Saves", "Installed Mods", "Game Information", "Exit")

    def __init__(self, screen, data: BrowserData, curses_module):
        self.screen = screen
        self.data = data
        self.curses = curses_module
        self.page = "home"
        self.selection = 0
        self.scroll = 0
        self.detail_title = ""
        self.detail_lines = []
        self.detail_parent = "home"

    def run(self):
        try:
            self.curses.curs_set(0)
        except self.curses.error:
            pass
        self.screen.keypad(True)
        while True:
            self._draw()
            key = self.screen.getch()
            if key in (24, ord("q"), ord("Q")):
                return
            if key == self.curses.KEY_RESIZE:
                continue
            if key in (27, self.curses.KEY_LEFT, self.curses.KEY_BACKSPACE, 8, 127):
                if self.page == "detail":
                    self.page = self.detail_parent
                    self.selection = 0
                    self.scroll = 0
                elif self.page != "home":
                    self.page = "home"
                    self.selection = 0
                    self.scroll = 0
                continue
            if self.page == "detail":
                self._handle_detail_key(key)
            else:
                self._handle_menu_key(key)

    def _menu_items(self):
        if self.page == "home":
            return list(self.HOME_ITEMS)
        if self.page == "saves":
            return [
                ("* " if save.get("_active") else "  ")
                + f"{save.get('name')} [{save.get('save_kind')}]"
                for save in self.data.saves
            ]
        return [
            ("[on] " if mod["enabled"] else "[off] ")
            + f"{mod['name']} {mod['version']} ({mod['source']})"
            for mod in self.data.mods
        ]

    def _handle_menu_key(self, key):
        items = self._menu_items()
        if key == self.curses.KEY_UP and items:
            self.selection = (self.selection - 1) % len(items)
        elif key == self.curses.KEY_DOWN and items:
            self.selection = (self.selection + 1) % len(items)
        elif key in (10, 13, self.curses.KEY_RIGHT):
            if self.page == "home":
                if self.selection == 0:
                    self._open_menu("saves")
                elif self.selection == 1:
                    self._open_menu("mods")
                elif self.selection == 2:
                    self._open_detail("Game Information", game_info_lines(self.data))
                else:
                    raise SystemExit
            elif self.page == "saves" and self.data.saves:
                save = self.data.saves[self.selection]
                self._open_detail(str(save.get("name")), save_detail_lines(save, self.data.mods))
            elif self.page == "mods" and self.data.mods:
                mod = self.data.mods[self.selection]
                self._open_detail(mod["name"], mod_detail_lines(mod))

    def _handle_detail_key(self, key):
        height, _width = self.screen.getmaxyx()
        visible = max(1, height - 5)
        maximum = max(0, len(self._wrapped_detail(_width)) - visible)
        if key == self.curses.KEY_UP:
            self.scroll = max(0, self.scroll - 1)
        elif key == self.curses.KEY_DOWN:
            self.scroll = min(maximum, self.scroll + 1)
        elif key == self.curses.KEY_PPAGE:
            self.scroll = max(0, self.scroll - visible)
        elif key == self.curses.KEY_NPAGE:
            self.scroll = min(maximum, self.scroll + visible)

    def _open_menu(self, page):
        self.page = page
        self.selection = 0
        self.scroll = 0

    def _open_detail(self, title, lines):
        self.detail_parent = self.page
        self.page = "detail"
        self.detail_title = title
        self.detail_lines = lines
        self.scroll = 0

    def _safe_addstr(self, row, column, value, style=0):
        height, width = self.screen.getmaxyx()
        if row < 0 or row >= height or column >= width:
            return
        try:
            self.screen.addnstr(row, column, str(value), max(0, width - column - 1), style)
        except self.curses.error:
            pass

    def _wrapped_detail(self, width):
        available = max(12, width - 4)
        wrapped = []
        for line in self.detail_lines:
            if not line:
                wrapped.append("")
                continue
            indent = len(line) - len(line.lstrip(" "))
            wrapped.extend(
                textwrap.wrap(
                    line,
                    width=available,
                    subsequent_indent=" " * indent,
                    replace_whitespace=False,
                    drop_whitespace=True,
                )
                or [""]
            )
        return wrapped

    def _draw(self):
        self.screen.erase()
        height, width = self.screen.getmaxyx()
        if height < 8 or width < 28:
            self._safe_addstr(0, 0, "Terminal is too small.", self.curses.A_BOLD)
            self._safe_addstr(2, 0, "Resize it or press Ctrl+X.")
            self.screen.refresh()
            return

        if self.page == "detail":
            self._draw_detail(height, width)
        else:
            self._draw_menu(height, width)
        self.screen.refresh()

    def _draw_menu(self, height, width):
        row = 1
        if self.page == "home" and width > max(map(len, ASCII_LOGO)) + 2 and height >= 16:
            for line in ASCII_LOGO:
                self._safe_addstr(row, 2, line, self.curses.A_BOLD)
                row += 1
            row += 1
        title = {"home": "Information Browser", "saves": "Saves", "mods": "Installed Mods"}[self.page]
        self._safe_addstr(row, 2, title, self.curses.A_BOLD)
        row += 2
        items = self._menu_items()
        if not items:
            message = "No saves found." if self.page == "saves" else "No installed mods found."
            self._safe_addstr(row, 4, message)
        else:
            visible = max(1, height - row - 3)
            if self.selection < self.scroll:
                self.scroll = self.selection
            if self.selection >= self.scroll + visible:
                self.scroll = self.selection - visible + 1
            for index in range(self.scroll, min(len(items), self.scroll + visible)):
                style = self.curses.A_REVERSE if index == self.selection else 0
                self._safe_addstr(row + index - self.scroll, 4, items[index], style)
        footer = "Arrows navigate  Enter opens  Left/Esc goes back  Ctrl+X exits"
        self._safe_addstr(height - 2, 2, footer, self.curses.A_DIM)

    def _draw_detail(self, height, width):
        self._safe_addstr(1, 2, self.detail_title, self.curses.A_BOLD)
        lines = self._wrapped_detail(width)
        visible = max(1, height - 5)
        maximum = max(0, len(lines) - visible)
        self.scroll = min(self.scroll, maximum)
        for index, line in enumerate(lines[self.scroll : self.scroll + visible]):
            self._safe_addstr(3 + index, 2, line)
        position = f"{self.scroll + 1}-{min(len(lines), self.scroll + visible)} of {max(1, len(lines))}"
        footer = f"Up/Down scroll  PgUp/PgDn page  Left/Esc back  Ctrl+X exit  {position}"
        self._safe_addstr(height - 1, 2, footer, self.curses.A_DIM)


def run_info_tui() -> int:
    data = collect_browser_data()
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print_static_report(data)
        return 0
    try:
        import curses
    except ImportError:
        print_static_report(data)
        print("\nInteractive mode requires Python's curses module.", file=sys.stderr)
        return 0

    def wrapped(screen):
        try:
            InfoBrowser(screen, data, curses).run()
        except SystemExit:
            return

    curses.wrapper(wrapped)
    return 0
