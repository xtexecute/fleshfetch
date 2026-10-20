"""Qt Quick frontend. The engine and mod registries remain Python-owned."""

from collections import deque
import base64
import json
import html
from pathlib import Path
import sys
import threading
import time

from PySide6.QtCore import QObject, Property, QSize, QTimer, QUrl, Qt, Signal, Slot
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QImage, QPainter
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtWidgets import QApplication, QFileDialog

from console_commands import ConsoleCommandsMixin
from core_runtime import initialize_runtime
from defaults import DEFAULT_SETTINGS
from game_state import GameStateMixin
from gameplay_core import GameplayCoreMixin
from mod_api import ModApiMixin
from mod_manager import ModManagerMixin
from paths import SETTINGS_FILE, ensure_app_dirs, find_app_asset
from qt_mod_ui import QtModUiMixin
from qt_legacy_ui import LegacyUiMixin
from qt_sprite_model import SpriteModel
from qt_leaderboard import LeaderboardController
from rpc import RpcMixin
import runtime_scheduler as scheduler
from save_manager import (
    SaveManagerMixin, backup_save_slot, clone_json_data, list_save_slots,
    load_save_slot_data, save_json,
)


class _ConsoleStream:
    def __init__(self, original, sink):
        self.original = original
        self.sink = sink

    def write(self, text):
        text = str(text)
        if self.original is not None:
            self.original.write(text)
        self.sink(text)
        return len(text)

    def flush(self):
        if self.original is not None:
            self.original.flush()

    def __getattr__(self, name):
        return getattr(self.original, name)


class SkinImages(QQuickImageProvider):
    """Decode once at a fixed pixel grid; nine-slicing keeps corners sharp."""

    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)
        source = QImage(find_app_asset("ui/red-frame.png"))
        if source.isNull():
            raise RuntimeError("Missing UI sprite: assets/ui/red-frame.png")
        self.frame = source.scaled(64, 64, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
        self.tinted_frames = {}

    def requestImage(self, image_id, size, requested_size):
        if image_id.startswith("sprite/"):
            try:
                path, region = json.loads(base64.urlsafe_b64decode(image_id[7:]).decode())
                source = QImage(path)
                x, y, width, height = region
                if x + width > source.width() or y + height > source.height():
                    return QImage()
                cropped = source.copy(x, y, width, height)
                size.setWidth(cropped.width())
                size.setHeight(cropped.height())
                return cropped
            except (ValueError, TypeError, OSError):
                return QImage()
        color = QColor("#" + image_id.partition("/")[2])
        frame = self.frame
        if color.isValid():
            key = color.name()
            if key not in self.tinted_frames:
                tinted = self.frame.copy()
                painter = QPainter(tinted)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(tinted.rect(), color)
                painter.end()
                if len(self.tinted_frames) >= 64:
                    self.tinted_frames.clear()
                self.tinted_frames[key] = tinted
            frame = self.tinted_frames[key]
        size.setWidth(self.frame.width())
        size.setHeight(self.frame.height())
        return frame


class QtGame(
    LegacyUiMixin, QtModUiMixin, GameStateMixin, RpcMixin, SaveManagerMixin,
    ModManagerMixin, ModApiMixin, GameplayCoreMixin, ConsoleCommandsMixin, QObject,
):
    liveChanged = Signal()
    catalogChanged = Signal()
    preferencesChanged = Signal()
    statusChanged = Signal()
    consoleChanged = Signal()
    darkModeChanged = Signal()
    confirmationRequested = Signal(str, str)
    clicked = Signal()
    legacyIdle = Signal(object)

    @Property(QObject, constant=True)
    def legacyOverlay(self):
        return self._sprite_layer

    @Property(QObject, constant=True)
    def spriteModel(self):
        return self._sprite_model

    @Property(QObject, constant=True)
    def leaderboard(self):
        return self._leaderboard

    @Slot(float, float)
    def setLegacyOrigin(self, x, y):
        LegacyUiMixin.setLegacyOrigin(self, x, y)

    def __init__(self):
        QObject.__init__(self)
        scheduler.configure_qt()
        self._initializing = True
        self._closed = False
        self._startup_guard = False
        self._live_dirty = True
        self._catalog_dirty = True
        self._sprites_dirty = True
        self._sprite_model = SpriteModel(self)
        self._live = {}
        self._catalog = {}
        self._status = ""
        self._console_text = ""
        self._log_pending = deque(maxlen=2000)
        self._log_lock = threading.Lock()
        self._pending_action = None
        self._cancel_action = None
        self._sound = None
        self._sound_path = None
        self._old_stdout, self._old_stderr = sys.stdout, sys.stderr
        self._stdout = _ConsoleStream(sys.stdout, self._queue_log)
        self._stderr = _ConsoleStream(sys.stderr, self._queue_log)
        sys.stdout, sys.stderr = self._stdout, self._stderr
        try:
            initialize_runtime(self)
            self.currencies = clone_json_data(self.currencies)
            self.upgrades = clone_json_data(self.upgrades)
            self.init_qt_mod_ui()
            self.init_legacy_ui()
            self._leaderboard = LeaderboardController(self)
            self.load_mods()
            missing = self._startup_missing_active_save()
            if missing:
                self._startup_guard = True
                if self._dirty_save_timer_id is not None:
                    scheduler.source_remove(self._dirty_save_timer_id)
                    self._dirty_save_timer_id = None
                self._startup_missing_save = missing
            self._initializing = False
            self._pulse = QTimer(self)
            self._pulse.setInterval(50)
            self._pulse.timeout.connect(self._publish)
            self._pulse.start()
            self._motion = QTimer(self)
            self._motion.setTimerType(Qt.TimerType.PreciseTimer)
            self._motion.setInterval(16)
            self._motion.timeout.connect(self._step_motion)
            self._motion_time = time.monotonic()
            self._motion.start()
            QGuiApplication.styleHints().colorSchemeChanged.connect(self._system_theme_changed)
            self._publish()
            if not missing:
                self._begin_play("startup")
        except BaseException:
            self._restore_streams()
            raise

    @Property("QVariantMap", notify=liveChanged)
    def live(self):
        return self._live

    @Property("QVariantMap", notify=catalogChanged)
    def catalog(self):
        return self._catalog

    @Property("QVariantMap", notify=preferencesChanged)
    def preferences(self):
        return {key: self.settings.get(key, default) for key, default in DEFAULT_SETTINGS.items()}

    @Property(bool, notify=darkModeChanged)
    def darkMode(self):
        mode = self.settings.get("theme", "system")
        if mode != "system":
            return mode != "light"
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark

    @Property(str, notify=statusChanged)
    def status(self):
        return self._status

    @Property(str, notify=consoleChanged)
    def consoleText(self):
        return self._console_text

    @Property(str, notify=consoleChanged)
    def consoleHtml(self):
        lines = []
        for line in self._console_text.splitlines():
            escaped = html.escape(line)
            if "[mods][deprecated]" in line:
                escaped = '<span style="color:#ffff00">' + escaped + '</span>'
            lines.append(escaped)
        return '<pre style="white-space:pre-wrap">' + "\n".join(lines) + '</pre>'

    def _system_theme_changed(self, *args):
        if self.settings.get("theme") == "system":
            self.darkModeChanged.emit()

    def _set_status(self, message):
        self._status = str(message)
        self.statusChanged.emit()

    def _notify_live(self, *args, **kwargs):
        self._live_dirty = True

    def _notify_sprites(self):
        self._sprites_dirty = True

    def set_currency(self, registry_name, value):
        GameStateMixin.set_currency(self, registry_name, value)
        self._notify_live()

    def _notify_catalog(self, *args, **kwargs):
        self._catalog_dirty = True
        self._live_dirty = True
        self._sprites_dirty = True

    update_labels = _notify_live
    refresh_upgrades_ui = _notify_catalog
    refresh_achievements_ui = _notify_live
    refresh_stats_tab = _notify_live
    refresh_saves_list = _notify_catalog
    refresh_mod_settings_list = _notify_catalog
    _apply_upgrade_visibility = _notify_live
    load_flesh_image = _notify_live

    def set_title(self, title):
        self.current_game_title = str(title)
        self._notify_live()

    def _queue_log(self, text):
        with self._log_lock:
            self._log_pending.append(text[-100_000:])

    def console_print(self, text=""):
        print(str(text))

    def _publish(self):
        if self._initializing or self._closed:
            return
        with self._log_lock:
            text = "".join(self._log_pending)
            self._log_pending.clear()
        if text:
            self._console_text = (self._console_text + text)[-100_000:]
            self.consoleChanged.emit()
        if self._live_dirty:
            self._live_dirty = False
            currencies = [{
                "id": name, "name": data.get("display_name", name),
                "amount": self.get_currency(name),
                "cpc": self.effective_fpc() if name == self.primary_currency else self.compute_cpc(name),
                "cps": self.compute_cps(name),
            } for name, data in self.currencies.items()]
            upgrade_info = {}
            for uid, upgrade in self.upgrades.items():
                owned = self.get_upgrade_count(uid)
                cost = self.get_upgrade_cost(uid, owned)
                visible = self.check_requires(uid)
                upgrade_info[uid] = {
                    "owned": owned, "cost": cost, "visible": visible,
                    "canBuy": visible and self.get_currency(upgrade.get("cost_currency", "flesh")) >= cost,
                }
            stats = ["Currencies"]
            stats.extend(f"{c['name']}: {c['amount']:,.0f}   Per click: {c['cpc']:g}   Per second: {c['cps']:g}" for c in currencies)
            stats.extend(["", "Upgrades"])
            stats.extend(f"{upgrade.get('name', uid)}: {self.get_upgrade_count(uid)}" for uid, upgrade in self.upgrades.items())
            stats.extend(["", f"Total clicks: {self.state.get('total_clicks', 0):,}"])
            self._live = {
                "title": self.current_game_title, "saveName": self.active_save_name,
                "saveId": self.active_save_id, "saveKind": self.active_save_kind,
                "currencies": currencies, "upgradeInfo": upgrade_info,
                "totalClicks": self.state.get("total_clicks", 0),
                "imageUrl": QUrl.fromLocalFile(self.flesh_image_path).toString(),
                "statsText": "\n".join(stats),
                "achievements": [{"id": key, "name": data.get("name", key), "desc": data.get("desc", "")}
                    for key, data in self.achievements.items()
                    if isinstance(data, dict) and data.get("unlocked") and self._achievement_is_active(key, data)],
                "sprites": self._sprite_snapshot(),
            }
            self.liveChanged.emit()
        if self._catalog_dirty:
            self._catalog_dirty = False
            self._catalog = {
                "upgrades": [{"id": uid, "name": data.get("name", uid), "desc": data.get("desc", ""),
                    "category": data.get("category", data.get("type", "misc")),
                    "currency": self.currencies.get(data.get("cost_currency", "flesh"), {}).get("display_name", data.get("cost_currency", "flesh"))}
                    for uid, data in self.upgrades.items()],
                "saves": [{"id": slot["id"], "name": slot["name"], "kind": slot.get("save_kind", "singleplayer"),
                    "updated": str(slot.get("updated_at", "")), "active": slot["id"] == self.active_save_id,
                    "requiredMods": [m.get("name", m.get("id", "")) if isinstance(m, dict) else str(m) for m in slot.get("required_mods", [])]}
                    for slot in list_save_slots()],
                "mods": [{"id": info["id"], "key": info["title_key"], "name": info.get("name", info["id"]),
                    "author": info.get("author", "Unknown"), "version": info.get("version", ""),
                    "description": info.get("description", ""), "enabled": bool(info.get("enabled")),
                    "blocked": bool(info.get("security_blocked") or info.get("dependency_blocked")),
                    "level": info.get("security_level", 0),
                    "reasons": info.get("security_reasons", []) + info.get("dependency_missing", []),
                    "legacy": bool(info.get("deprecation_warnings")), "gameTitle": info.get("game_title", ""),
                    "titleSelected": self.settings.get("game_title_mod_key") == info["title_key"]}
                    for info in self.installed_mods],
                **self._mod_ui_snapshot(),
            }
            self.catalogChanged.emit()

    def _sprite_snapshot(self):
        records = []
        for image in self._qt_images.values():
            if image.tab_id is None:
                record = image.to_dict()
                records.append(dict(record, url=record["source"]))
        return records

    def _mod_ui_snapshot(self):
        data = self.qt_mod_ui_snapshot()
        return {
            "tabs": [dict(tab, legacyRoot=self._legacy_pages.get(tab["id"])) for tab in data["tabs"]],
            "tabThemes": self._qt_theme_snapshot(),
            "extraTabs": [{"id": tab_id, "items": list(items),
                           "legacyRoot": self._legacy_pages.get(tab_id)}
                          for tab_id, items in self._qt_items.items() if tab_id not in self._qt_tabs],
            "buttons": [dict(button, tabId=button["tab_id"], enabled=button["sensitive"],
                sprite=button["sprites"].get("normal", ""), hoverSprite=button["sprites"].get("hover", ""),
                pressedSprite=button["sprites"].get("pressed", ""), disabledSprite=button["sprites"].get("disabled", ""))
                for button in data["buttons"]],
            "images": [dict(image, tabId=image["tab_id"], url=image["source"])
                for image in data["images"] if image["tab_id"] is not None],
        }

    def _step_motion(self):
        now = time.monotonic()
        seconds = min(0.1, now - self._motion_time)
        self._motion_time = now
        self.advance_qt_mod_ui(seconds)
        if self._sprites_dirty:
            self._sprites_dirty = False
            self._sprite_model.sync(self._sprite_snapshot())

    def _begin_play(self, reason):
        self._emit_event("load", {"save_id": self.active_save_id, "save_name": self.active_save_name,
            "save_kind": self.active_save_kind, "reason": reason})
        if not self._runtime_services_started:
            self._runtime_services_started = True
            self._tick_source = scheduler.timeout_add_seconds(1, self.on_timer_tick)
            if self.settings.get("enable_rpc"):
                self.init_rpc()
                self._ensure_rpc_update_timer()

    @Slot()
    def ready(self):
        if not self._startup_guard:
            return
        info = self._startup_missing_save
        def accept():
            self._startup_guard = False
            self._begin_play("startup")
        def cancel():
            self._startup_guard = False
            self._set_status(self._switch_to_startup_safe_save(info))
            self._notify_catalog()
            self._begin_play("startup_fallback")
        self._confirm("Missing mods", self._missing_mod_message(info["missing_mods"]), accept, cancel)

    @staticmethod
    def _missing_mod_message(names):
        return "This save file requires missing mods: " + ", ".join(names) + ", loading may cause corruption or loss of data. Load anyway?"

    def mark_save_dirty(self, auto_backup=True):
        if self._startup_guard:
            self._save_dirty = True
            self._save_dirty_auto_backup |= bool(auto_backup)
            return
        return SaveManagerMixin.mark_save_dirty(self, auto_backup)

    def save_current_progress(self, auto_backup=True):
        if self._startup_guard:
            return
        result = SaveManagerMixin.save_current_progress(self, auto_backup)
        return result

    @Slot()
    def click(self):
        if not self._startup_guard:
            self.on_click(None, 1, 0, 0)

    @Slot(str)
    def buy(self, uid):
        if not self._startup_guard:
            self.on_buy_upgrade_clicked(None, uid)

    def play_squish(self):
        self.clicked.emit()

    def play_click_sound(self):
        if not self.settings.get("play_click_sound"):
            return
        from PySide6.QtMultimedia import QSoundEffect
        if self._sound is None:
            self._sound = QSoundEffect(self)
        if self._sound_path != self.click_sound_path:
            self._sound_path = self.click_sound_path
            self._sound.setSource(QUrl.fromLocalFile(self.click_sound_path))
        self._sound.setVolume(self.settings.get("click_sound_volume", 15) / 100)
        self._sound.play()

    def set_flesh_image(self, path):
        self.flesh_image_path = self.resolve_asset_path(path, self._current_mod_namespace())
        self._notify_live()

    def set_click_sound(self, path):
        self.click_sound_path = self.resolve_asset_path(path, self._current_mod_namespace())

    @Slot(str, "QVariant")
    def setPreference(self, key, value):
        if key == "theme":
            if value not in ("light", "dark", "system"):
                return
        elif key in ("enable_rpc", "play_click_sound", "auto_reload_mod_changes"):
            value = bool(value)
        elif key in ("click_sound_volume", "squish_ms"):
            try:
                value = max(0, min(100 if key == "click_sound_volume" else 2000, int(value)))
            except (ValueError, TypeError):
                return
        else:
            return
        old = self.settings.get(key)
        self.settings[key] = value
        save_json(SETTINGS_FILE, self.settings)
        self.preferencesChanged.emit()
        if key == "theme":
            self.darkModeChanged.emit()
        if key == "enable_rpc" and old != value:
            if value:
                self.init_rpc()
                self._ensure_rpc_update_timer()
            else:
                self.shutdown_rpc()

    def _confirm(self, title, message, accept, cancel=None):
        if self._pending_action is not None:
            return
        self._pending_action, self._cancel_action = accept, cancel
        self.confirmationRequested.emit(title, message)

    @Slot(bool)
    def confirmPending(self, accepted):
        action = self._pending_action if accepted else self._cancel_action
        self._pending_action = self._cancel_action = None
        if action:
            self._perform(action)

    def _perform(self, action):
        try:
            result = action()
            if isinstance(result, tuple) and len(result) > 1:
                self._set_status(result[1])
            elif isinstance(result, str):
                self._set_status(result)
            self._notify_catalog()
            return result
        except Exception as exc:
            self._set_status(str(exc))
            print(f"[Qt] {exc}")

    @Slot(str)
    def createSave(self, name):
        if not self._startup_guard:
            self._perform(lambda: self.create_save_slot(name or "New Save"))

    @Slot(str)
    def loadSave(self, save_id):
        if self._startup_guard:
            return
        slot = load_save_slot_data(save_id)
        if not slot:
            self._set_status("Save could not be loaded.")
            return
        missing = self._save_slot_missing_mods(slot)
        action = lambda: self.load_save_slot(save_id, allow_missing_mods=True)
        if missing:
            self._confirm("Missing mods", self._missing_mod_message(missing), action)
        else:
            self._perform(action)

    @Slot(str, str)
    def renameSave(self, save_id, name):
        self._perform(lambda: self.rename_save_slot(save_id, name))

    @Slot(str)
    def duplicateSave(self, save_id):
        self._perform(lambda: self.duplicate_save_slot(save_id))

    @Slot(str)
    def deleteSave(self, save_id):
        self._confirm("Delete save", "Delete this save? A final backup will be kept.", lambda: self.delete_save_slot(save_id))

    @Slot(str)
    def backupSave(self, save_id):
        def backup():
            if save_id == self.active_save_id:
                self.save_current_progress(auto_backup=False)
            backup_save_slot(save_id, reason="manual")
            return "Backup created."
        self._perform(backup)

    @Slot(str)
    def restoreSave(self, save_id):
        self._confirm("Restore backup", "Replace this save with its latest backup?", lambda: self.restore_latest_save_backup(save_id))

    @Slot()
    def importSave(self):
        path, _ = QFileDialog.getOpenFileName(None, "Import save", "", "Fleshfetch saves (*.json);;All files (*)")
        if path:
            self._perform(lambda: self.import_save_slot(path))

    @Slot(str)
    def exportSave(self, save_id):
        path, _ = QFileDialog.getSaveFileName(None, "Export save", f"{save_id}.json", "Fleshfetch saves (*.json)")
        if path:
            self._perform(lambda: self.export_save_slot(save_id, path))

    @Slot()
    def manualSave(self):
        if not self._startup_guard:
            def save():
                self.save_current_progress(auto_backup=True)
                return "Saved."
            self._perform(save)

    def _find_mod(self, key):
        return next((info for info in self.installed_mods if info["title_key"] == key), None)

    def _finish_mod_change(self):
        if self.settings.get("auto_reload_mod_changes", True):
            self._set_status(self.reload_mods())
        else:
            self._set_status("Run /reload or restart Fleshfetch to apply mod changes.")
        self._notify_catalog()

    @Slot(str)
    def toggleMod(self, key):
        info = self._find_mod(key)
        if not info:
            return
        if not info.get("enabled") and info.get("security_blocked"):
            self._set_status("Dismiss the security warning before enabling this mod.")
            return
        def change():
            self._write_mod_enabled(info, not info.get("enabled", True))
            self._apply_selected_game_title()
            self._finish_mod_change()
        self._perform(change)

    @Slot(str)
    def dismissModWarning(self, key):
        info = self._find_mod(key)
        if not info:
            return
        def dismiss():
            self._dismiss_mod_security_warning(info)
            self._finish_mod_change()
        self._confirm("Dismiss security warning", "Are you sure you want to dismiss this warning? You might be running very harmful code, or just a normal mod. Only continue if you trust the mod and its source.", dismiss)

    @Slot(str, bool)
    def selectModTitle(self, key, enabled):
        info = self._find_mod(key)
        if not info or info.get("security_blocked") or not info.get("enabled"):
            return
        self.settings["game_title_mod_key"] = key if enabled else ""
        save_json(SETTINGS_FILE, self.settings)
        self._apply_selected_game_title()
        self._notify_catalog()

    @Slot()
    def reloadMods(self):
        self._perform(self.reload_mods)

    def _refresh_after_mod_reload(self):
        self._apply_selected_game_title()
        self._notify_catalog()

    @Slot(str)
    def executeCommand(self, text):
        if not self._startup_guard:
            self.execute_console_command(text)
            self._notify_live()

    @Slot()
    def clearConsole(self):
        self._console_text = ""
        with self._log_lock:
            self._log_pending.clear()
        self.consoleChanged.emit()

    @Slot(str)
    def activateModButton(self, button_id):
        button = self._qt_buttons.get(button_id)
        if button:
            self._perform(button.click)

    @Slot(float, float)
    def setViewport(self, width, height):
        self._qt_view_width = max(1, width)
        self._qt_view_height = max(1, height)

    def _restore_streams(self):
        if sys.stdout is self._stdout:
            sys.stdout = self._old_stdout
        if sys.stderr is self._stderr:
            sys.stderr = self._old_stderr

    @Slot()
    def shutdown(self):
        if self._closed:
            return
        try:
            if not self._startup_guard:
                self.save_current_progress(auto_backup=True)
            self.shutdown_rpc()
            self._leaderboard.close()
            for timer in list(self._mod_timers):
                self.cancel_timer(timer)
            for source in (getattr(self, "_tick_source", None), self._dirty_save_timer_id):
                if source is not None:
                    scheduler.source_remove(source)
            self._pulse.stop()
            self._motion.stop()
            if self._sound:
                self._sound.stop()
        finally:
            self._closed = True
            self._legacy_idle_pending.clear()
            self._restore_streams()


def create_application(argv=None):
    ensure_app_dirs()
    app = QApplication.instance() or QApplication(sys.argv[:1] if argv is None else argv)
    app.setApplicationName("Fleshfetch")
    icon = find_app_asset("flesh.ico")
    if Path(icon).exists():
        app.setWindowIcon(QIcon(icon))
    from PySide6.QtQuickControls2 import QQuickStyle
    QQuickStyle.setStyle("Basic")
    game = QtGame()
    engine = QQmlApplicationEngine()
    qml_errors = []
    def record_qml_errors(errors):
        for error in errors:
            message = error.toString()
            qml_errors.append(message)
            print(message, file=sys.stderr)
    engine.warnings.connect(record_qml_errors)
    engine.addImageProvider("skins", SkinImages())
    from PySide6.QtQml import qmlRegisterType
    from qt_legacy_drawing import LegacyPaintItem
    qmlRegisterType(LegacyPaintItem, "Fleshfetch.Legacy", 1, 0, "LegacyPaintItem")
    engine.rootContext().setContextProperty("game", game)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / "qml" / "Main.qml")))
    if not engine.rootObjects():
        game.shutdown()
        raise RuntimeError("The Qt interface could not be loaded. " + "\n".join(qml_errors))
    engine.rootObjects()[0].installEventFilter(game._legacy_pointer_filter)
    app.aboutToQuit.connect(game.shutdown)
    QTimer.singleShot(0, game.ready)
    return app, engine, game


def main():
    app, engine, game = create_application()
    try:
        return app.exec()
    finally:
        game.shutdown()
