"""Qt Quick frontend. The engine and mod registries remain Python-owned."""

from collections import deque
import base64
import json
import html
from pathlib import Path
import random
import sys
import threading
import time

from PySide6.QtCore import QObject, QPointF, Property, QSize, QTimer, QUrl, Qt, Signal, Slot
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QImage, QLinearGradient, QPainter
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtWidgets import QApplication, QFileDialog

from console_commands import ConsoleCommandsMixin
from click_audio import pitch_variant_paths
from core_runtime import initialize_runtime
from defaults import DEFAULT_SETTINGS
from game_state import GameStateMixin
from progression import ProgressionMixin, StreakMixin, COSMETICS, TESTABLE_COSMETICS, CRATE_TIERS, GEAR, POTIONS
from gameplay_core import GameplayCoreMixin
from mod_api import ModApiMixin, VANILLA_PARTS, vanilla_enabled
from mod_manager import ModManagerMixin
from paths import SETTINGS_FILE, ensure_app_dirs, find_app_asset
from qt_mod_ui import QtModUiMixin
from qt_legacy_ui import LegacyUiMixin
from qt_sprite_model import SpriteModel
from qt_leaderboard import LeaderboardController
from vanilla_shop import equipment_catalog, equipment_progress, workshop_state
from rpc import ThreadedRpcMixin
import runtime_scheduler as scheduler
from save_manager import (
    SaveManagerMixin, backup_save_slot, clone_json_data, list_save_slots,
    load_save_slot_data, save_json, write_save_slot_data,
)

CAST_FLESH_ASSETS = {
    "gold": "skins/cast-gold.png",
    "liquid_metal": "skins/liquid-metal.png",
    "stained_glass": "skins/stained-glass.png",
    "opal": "skins/opal.png",
}


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
        self.tinted_flesh = {}
        self.clockwork_images = {}
        self.loot_atlas = QImage(find_app_asset("loot/loot-pixel.png"))
        self.hat = QImage(find_app_asset("loot/top-hat.png"))
        atlas = QImage(find_app_asset("shop/equipment-pixel.png"))
        self.equipment = []
        if not atlas.isNull():
            for index in range(8):
                x, y = index % 4, index // 4
                left, top = x * atlas.width() // 4, y * atlas.height() // 2
                right, bottom = (x + 1) * atlas.width() // 4, (y + 1) * atlas.height() // 2
                self.equipment.append(atlas.copy(left, top, right - left, bottom - top))

    @staticmethod
    def _shadow_image(image):
        if max(image.width(), image.height()) > 512:
            image = image.scaled(512, 512, Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
        rim = image.copy()
        core = image.copy()
        inset = max(2, round(min(image.width(), image.height()) * 0.012))
        painter = QPainter(core)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        for dx, dy in ((inset, 0), (-inset, 0), (0, inset), (0, -inset)):
            painter.drawImage(dx, dy, image)
        painter.end()
        for target, high, low in ((rim, "#b29ac8", "#6d5083"), (core, "#584468", "#252031")):
            shade = QLinearGradient(0, 0, target.width() * 0.28, target.height())
            shade.setColorAt(0, QColor(high))
            shade.setColorAt(1, QColor(low))
            painter = QPainter(target)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(target.rect(), shade)
            painter.end()
        painter = QPainter(rim)
        painter.drawImage(0, 0, core)
        painter.end()
        return rim

    @staticmethod
    def _echo_image(image):
        if max(image.width(), image.height()) > 512:
            image = image.scaled(512, 512, Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
        echo = image.convertToFormat(QImage.Format.Format_Grayscale8).convertToFormat(
            QImage.Format.Format_ARGB32_Premultiplied)
        painter = QPainter(echo)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
        painter.fillRect(echo.rect(), QColor("#a4f2e5"))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        painter.fillRect(echo.rect(), QColor("#24514b"))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        painter.drawImage(0, 0, image)
        painter.end()
        return echo

    def requestImage(self, image_id, size, requested_size):
        if image_id.startswith("clockwork/"):
            name = image_id.split("/", 1)[1]
            if name not in {
                "01-chassis", "02-housings", "04-front-brackets", "05-clock-face",
                "clock-hour-hand", "clock-minute-hand", "clock-pivot", "preview",
                "gear-left", "gear-left-pinion", "gear-idler-1", "gear-idler-2",
                "gear-idler-3", "gear-idler-4", "gear-upper-right", "gear-lower-right",
            }:
                return QImage()
            if name not in self.clockwork_images:
                self.clockwork_images[name] = QImage(find_app_asset(f"skins/clockwork/{name}.png"))
            art = self.clockwork_images[name]
            size.setWidth(art.width())
            size.setHeight(art.height())
            return art
        if image_id == "accessory/top_hat":
            size.setWidth(self.hat.width())
            size.setHeight(self.hat.height())
            return self.hat
        if image_id.startswith("preview/"):
            cosmetic = image_id.split("/", 1)[1]
            if cosmetic not in COSMETICS:
                return QImage()
            if cosmetic == "smoke":
                art = QImage(128, 128, QImage.Format.Format_ARGB32)
                art.fill(Qt.GlobalColor.transparent)
                painter = QPainter(art)
                painter.setOpacity(0.4)
                for frame, x, y in ((2, 14, 70), (4, 103, 42), (1, 72, 5)):
                    painter.drawImage(x, y, QImage(find_app_asset(f"skins/smoke-puff-{frame}.png")))
                painter.setOpacity(1)
                painter.drawImage(8, 8, QImage(find_app_asset("flesh.png")).scaled(
                    112, 112, Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation))
                painter.end()
                size.setWidth(art.width())
                size.setHeight(art.height())
                return art
            preview_asset = {
                "cat": "skins/cat-closed.png",
                "rose": "skins/rose-preview.png",
                "sandcastle": "skins/sandcastle-preview.png",
                "sundial": "skins/sundial-preview.png",
                "prism_rain": "skins/prism-rain-preview.png",
                "lightbox": "skins/lightbox-preview.png",
                "firefly_jar": "skins/firefly-jar-preview.png",
                "opal": "skins/opal-preview.png",
                "event_horizon": "skins/event-horizon-preview.png",
                "star_map": "skins/star-map-preview.png",
                "aurora_ribbon": "skins/aurora-ribbon-preview.png",
                "deep_blue": "skins/deep-blue-preview.png",
                "tidal_planet": "skins/tidal-planet-preview.png",
                "neon_outline": "skins/neon-outline-preview.png",
                "snow_globe": "skins/snow-globe-preview.png",
                "lava_lamp": "skins/lava-lamp-preview.png",
                "marionette": "skins/marionette-preview.png",
                "paper_crown": "skins/paper-crown.png", "price_tag": "skins/price-tag.png",
                "sticky_note": "skins/sticky-note.png", "button_badge": "skins/button-badge.png",
                "wind_up_key": "skins/wind-up-key.png", "party_hat": "skins/party-hat.png",
                "sunglasses": "skins/sunglasses.png", "squeaky_toy": "skins/squeaky-toy.png",
                "tiny_flag": "skins/tiny-flag-0.png",
            }.get(cosmetic) or CAST_FLESH_ASSETS.get(cosmetic)
            if preview_asset:
                art = QImage(find_app_asset(preview_asset))
                size.setWidth(art.width())
                size.setHeight(art.height())
                return art
            path = base64.urlsafe_b64encode(find_app_asset("flesh.png").encode()).decode()
            art = self.requestImage(f"flesh/{cosmetic}/{path}", size, requested_size).copy()
            if cosmetic in ("shadow_twin", "temporal_echo") and not art.isNull():
                preview = QImage(128, 128, QImage.Format.Format_ARGB32)
                preview.fill(Qt.GlobalColor.transparent)
                scaled = art.scaled(104, 104, Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)
                painter = QPainter(preview)
                if cosmetic == "shadow_twin":
                    painter.setOpacity(0.54)
                    painter.drawImage(21, 20, scaled)
                    painter.setOpacity(0.91)
                    painter.drawImage(1, 5, scaled)
                else:
                    painter.setOpacity(0.69)
                    painter.drawImage(22, 1, scaled)
                painter.setOpacity(1)
                flesh = QImage(find_app_asset("flesh.png")).scaled(104, 104, Qt.AspectRatioMode.KeepAspectRatio,
                                                                 Qt.TransformationMode.SmoothTransformation)
                painter.drawImage(12, 12, flesh)
                painter.end()
                size.setWidth(preview.width())
                size.setHeight(preview.height())
                return preview
            return art
        if image_id.startswith("loot/") and not self.loot_atlas.isNull():
            try:
                _, kind, name = image_id.split("/", 2)
                if kind == "crate":
                    column = CRATE_TIERS.index(name)
                    row = 0
                elif kind == "gear":
                    index = list(GEAR).index(name)
                    column, row = index % 8, 1 + index // 8
                elif kind == "potion":
                    column = list(POTIONS).index(name)
                    row = 3
                else:
                    return QImage()
                art = self.loot_atlas.copy(column * 24, row * 24, 24, 24)
                size.setWidth(24)
                size.setHeight(24)
                return art
            except (ValueError, IndexError):
                return QImage()
        if image_id.startswith("flesh/"):
            try:
                _, cosmetic, encoded_path = image_id.split("/", 2)
                if cosmetic not in COSMETICS:
                    return QImage()
                key = (cosmetic, encoded_path)
                if key not in self.tinted_flesh:
                    path = base64.urlsafe_b64decode(encoded_path).decode()
                    tinted = QImage(path).convertToFormat(QImage.Format.Format_ARGB32)
                    if tinted.isNull():
                        return QImage()
                    if cosmetic == "bitcrush":
                        coarse = tinted.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio,
                                                Qt.TransformationMode.FastTransformation)
                        tinted = coarse.scaled(tinted.size(), Qt.AspectRatioMode.IgnoreAspectRatio,
                                                Qt.TransformationMode.FastTransformation)
                    if cosmetic == "shadow_twin":
                        tinted = self._shadow_image(tinted)
                    elif cosmetic == "temporal_echo":
                        tinted = self._echo_image(tinted)
                    else:
                        painter = QPainter(tinted)
                        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
                        painter.setOpacity(0.82 if cosmetic == "hologram" else 0.48 if cosmetic in ("smoke", "mint", "sky", "violet", "gold", "rose", "sunlight") else 0.18)
                        painter.fillRect(tinted.rect(), QColor(COSMETICS[cosmetic][2]))
                        if cosmetic == "hologram":
                            spacing = max(6, tinted.height() // 28)
                            painter.setOpacity(0.36)
                            for y in range(spacing // 2, tinted.height(), spacing):
                                painter.fillRect(0, y, tinted.width(), max(2, spacing // 8), QColor("#e6fff4"))
                        painter.end()
                    if len(self.tinted_flesh) >= 64:
                        self.tinted_flesh.clear()
                    self.tinted_flesh[key] = tinted
                art = self.tinted_flesh[key]
                size.setWidth(art.width())
                size.setHeight(art.height())
                return art
            except (ValueError, OSError):
                return QImage()
        if image_id.startswith("equipment/"):
            try:
                art = self.equipment[int(image_id.split("/")[1])]
                size.setWidth(art.width())
                size.setHeight(art.height())
                return art
            except (IndexError, ValueError):
                return QImage()
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


class SurfaceImages(QQuickImageProvider):
    def __init__(self, game):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self.game = game

    def requestImage(self, image_id, size, requested_size):
        surface = self.game.get_surface(image_id.partition("/")[0])
        if surface is None or not surface.is_visible():
            return QImage()
        frame = surface.frame_snapshot()
        if not frame:
            return QImage()
        image = QImage(frame, surface.width, surface.height, surface.width * 4,
                       QImage.Format.Format_RGBA8888).copy()
        size.setWidth(surface.width)
        size.setHeight(surface.height)
        return image


class QtGame(
    LegacyUiMixin, QtModUiMixin, ProgressionMixin, StreakMixin, GameStateMixin, ThreadedRpcMixin, SaveManagerMixin,
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
    crateDropSpawned = Signal(int, str, str)
    upgradePurchased = Signal(str)
    legacyIdle = Signal(object)
    surfaceFrameChanged = Signal(str, int)
    catMeowPlayingChanged = Signal()

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
        self._pitched_sounds = {}
        self._cat_meow_sounds = None
        self._ui_sounds = {}
        self._effect_sounds = {}
        self._pending_crate_drops = {}
        self._next_crate_drop_id = 1
        self._last_ui_hover = 0.0
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
            self._sync_motion_timer()
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

    @Property(bool, notify=catMeowPlayingChanged)
    def catMeowPlaying(self):
        return any(sound.isPlaying() for sound in self._cat_meow_sounds or ())

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
        self._sync_motion_timer()

    def set_currency(self, registry_name, value):
        GameStateMixin.set_currency(self, registry_name, value)
        self._notify_live()

    def _notify_catalog(self, *args, **kwargs):
        self._catalog_dirty = True
        self._live_dirty = True
        self._sprites_dirty = True
        self._sync_motion_timer()

    def _surface_frame_changed(self, surface_id, revision):
        self.surfaceFrameChanged.emit(surface_id, revision)

    @Slot(str, int, bool, int, result=bool)
    def surfaceKey(self, surface_id, key, pressed, modifiers):
        return self.surface_key_event(surface_id, key, pressed, modifiers)

    @Slot(str, str, float, float, int, int, result=bool)
    def surfacePointer(self, surface_id, kind, x, y, button, buttons):
        return self.surface_pointer_event(surface_id, kind, x, y, button, buttons)

    @Slot(str, result=int)
    def surfaceRevision(self, surface_id):
        surface = self.get_surface(surface_id)
        return surface.revision if surface is not None else 0

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
        self.advance_streak()
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
                "cpc": self.compute_click_gain(name),
                "cps": self.compute_cps(name),
            } for name, data in self.currencies.items()
                if name != "tokens" or vanilla_enabled(self, "rebirth")
                or name in self._mod_currency_owners]
            upgrade_info = {}
            for uid, upgrade in self.upgrades.items():
                owned = self.get_upgrade_count(uid)
                cost = self.get_upgrade_cost(uid, owned)
                visible = self.check_requires(uid)
                upgrade_info[uid] = {
                    "owned": owned, "cost": cost, "visible": visible,
                    "canBuy": visible and self.get_currency(upgrade.get("cost_currency", "flesh")) >= cost,
                    "milestone": equipment_progress(self, uid, owned),
                }
            stats = ["Currencies"]
            stats.extend(f"{c['name']}: {c['amount']:,.0f}   Per click: {c['cpc']:g}   Per second: {c['cps']:g}" for c in currencies)
            stats.extend(["", "Upgrades"])
            stats.extend(f"{upgrade.get('name', uid)}: {self.get_upgrade_count(uid)}" for uid, upgrade in self.upgrades.items())
            stats.extend(["", f"Total clicks: {self.state.get('total_clicks', 0):,}"])
            self._live = {
                "vanilla": {part: vanilla_enabled(self, part) for part in VANILLA_PARTS},
                "title": self.current_game_title, "saveName": self.active_save_name,
                "saveId": self.active_save_id, "saveKind": self.active_save_kind,
                "currencies": currencies, "upgradeInfo": upgrade_info,
                "totalClicks": self.state.get("total_clicks", 0),
                "imageUrl": self._flesh_display_url(),
                "fleshCopyUrl": self._flesh_copy_url(),
                "statsText": "\n".join(stats),
                "workshop": workshop_state(self),
                "progression": self.progression_snapshot(),
                "modSettings": self._mod_settings_snapshot(),
                "achievements": [{"id": key, "name": data.get("name", key), "desc": data.get("desc", "")}
                    for key, data in self.achievements.items()
                    if isinstance(data, dict) and data.get("unlocked") and self._achievement_is_active(key, data)],
                "sprites": self._sprite_snapshot(),
            }
            self.liveChanged.emit()
        if self._catalog_dirty:
            self._catalog_dirty = False
            self._catalog = {
                "vanilla": {part: vanilla_enabled(self, part) for part in VANILLA_PARTS},
                "builtinTabs": {
                    "upgrades": vanilla_enabled(self, "upgrades") or bool(self.upgrades),
                    "achievements": vanilla_enabled(self, "achievements") or any(
                        data.get("source") == "mod" and self._achievement_is_active(key, data)
                        for key, data in self.achievements.items() if isinstance(data, dict)),
                    "crates": bool(self._progression_defs("crates")) or any(
                        d["owner"] != "__vanilla__" for table in ("equipment", "skins", "potions", "run_upgrades")
                        for d in self._progression_defs(table).values()),
                    "rebirth": vanilla_enabled(self, "rebirth") or bool(self._progression_defs("rebirth_upgrades")),
                },
                "progression": self.progression_catalog(),
                "shopItems": equipment_catalog(self),
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

    def _flesh_display_url(self):
        image = self._skin_image()
        if image:
            return QUrl.fromLocalFile(image).toString()
        selected = self.active_cosmetic()
        if selected in CAST_FLESH_ASSETS:
            return QUrl.fromLocalFile(find_app_asset(CAST_FLESH_ASSETS[selected])).toString()
        if selected not in TESTABLE_COSMETICS:
            return QUrl.fromLocalFile(self.flesh_image_path).toString()
        if selected in ("top_hat", "wobble", "rose", "reflection", "shadow_twin", "zero_gravity", "sandcastle", "temporal_echo", "sunlight", "magnet", "ticket_roll", "pinball", "clockwork", "cat", "smoke", "mint", "sky", "violet", "thunderhead", "slot_machine", "blacksmith", "comet",
                        "sundial", "prism_rain", "lightbox", "firefly_jar", "event_horizon", "star_map", "aurora_ribbon", "deep_blue", "tidal_planet", "paper_crown", "price_tag", "sticky_note", "button_badge",
                        "wind_up_key", "party_hat", "sunglasses", "squeaky_toy", "tiny_flag", "neon_outline", "snow_globe", "lava_lamp", "marionette"):
            return QUrl.fromLocalFile(self.flesh_image_path).toString()
        if selected in COSMETICS:
            path = base64.urlsafe_b64encode(self.flesh_image_path.encode()).decode()
            return f"image://skins/flesh/{selected}/{path}"
        return QUrl.fromLocalFile(self.flesh_image_path).toString()

    def _flesh_copy_url(self):
        selected = self.active_cosmetic()
        if selected not in ("shadow_twin", "temporal_echo"):
            return ""
        path = base64.urlsafe_b64encode(self.flesh_image_path.encode()).decode()
        return f"image://skins/flesh/{selected}/{path}"

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
            "surfaces": [dict(surface, tabId=surface["tab_id"])
                for surface in data["surfaces"]],
        }

    def _sync_motion_timer(self):
        timer = getattr(self, "_motion", None)
        if timer is None or self._closed:
            return
        if self._sprites_dirty or self.has_qt_mod_motion():
            if not timer.isActive():
                self._motion_time = time.monotonic()
                timer.start()
        else:
            timer.stop()

    def _step_motion(self):
        now = time.monotonic()
        seconds = min(0.1, now - self._motion_time)
        self._motion_time = now
        self.advance_qt_mod_ui(seconds)
        if self._sprites_dirty:
            self._sprites_dirty = False
            self._sprite_model.sync(self._sprite_snapshot())
        self._sync_motion_timer()

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

    def create_save_slot(self, name, save_kind="singleplayer"):
        self._flush_pending_crate_drops()
        return SaveManagerMixin.create_save_slot(self, name, save_kind)

    def load_save_slot(self, save_id, allow_missing_mods=False):
        self._flush_pending_crate_drops()
        return SaveManagerMixin.load_save_slot(self, save_id, allow_missing_mods)

    def _queue_crate_drop(self, kind, tier):
        if tier not in self._progression_defs("crates"):
            return
        drop_id = self._next_crate_drop_id
        self._next_crate_drop_id += 1
        self._pending_crate_drops[drop_id] = (self.active_save_id, kind, tier)
        self.crateDropSpawned.emit(drop_id, kind, tier)
        QTimer.singleShot(2500, lambda: self.collectCrateDrop(drop_id))

    def _flush_pending_crate_drops(self):
        for drop_id in list(self._pending_crate_drops):
            self.collectCrateDrop(drop_id)

    @Slot(int, result=bool)
    def collectCrateDrop(self, drop_id):
        pending = self._pending_crate_drops.pop(drop_id, None)
        if pending is None or pending[2] not in self._progression_defs("crates"):
            return False
        save_id, kind, tier = pending
        if save_id != self.active_save_id:
            slot = load_save_slot_data(save_id)
            if slot:
                from progression import normalize_progression
                counts = normalize_progression(slot["state"])["crates"][kind]
                counts[tier] = counts.get(tier, 0) + 1
                write_save_slot_data(slot)
        else:
            self._add_crate(kind, tier)
            self._emit_event("crate_found", {"kind": kind, "tier": tier})
            self._emit_event("crate_collected", {"kind": kind, "tier": tier})
            self._set_status(f"Collected a {self._progression_defs('crates')[tier]['name']} {kind} crate!")
        return True

    @Slot(result="QVariantMap")
    @Slot(float, float, result="QVariantMap")
    def click(self, x=0.0, y=0.0):
        if self._startup_guard:
            return {"gain": 0, "critical": False, "accepted": False}
        accepted = self.on_click(None, 1, x, y)
        return {"gain": float(getattr(self, "_last_click_gains", {}).get(self.primary_currency, 0)),
                "critical": bool(getattr(self, "_last_click_critical", False)), "accepted": bool(accepted),
                "streakFill": self.streak_snapshot()["fill"]}

    @Slot(float, float, float, float, result=bool)
    def isFleshHit(self, x, y, width, height):
        asset = CAST_FLESH_ASSETS.get(self.active_cosmetic())
        path = self._skin_image() or (find_app_asset(asset) if asset else self.flesh_image_path)
        return self._image_hit(path, x, y, width, height)

    @Slot(float, float, float, float, result=bool)
    def isClockworkHit(self, x, y, width, height):
        return self._image_hit(find_app_asset("skins/clockwork/preview.png"), x, y, width, height)

    @Slot(str, float, float, float, float, result=bool)
    def isCosmeticPropHit(self, cosmetic, x, y, width, height):
        asset = {"snow_globe": "skins/snow-globe-back.png",
                 "lava_lamp": "skins/lava-lamp-back.png"}.get(cosmetic)
        return bool(asset) and self._image_hit(find_app_asset(asset), x, y, width, height)

    @Slot(float, float, float, float, float, float, float, float, float, float, result=bool)
    def isEventHorizonHit(self, x, y, width, height, scale, body_x, body_y, pixel_ratio, origin_x, origin_y):
        if not hasattr(self, "_event_horizon_hit_map"):
            from event_horizon import EventHorizonHitMap
            self._event_horizon_hit_map = EventHorizonHitMap()
        return self._event_horizon_hit_map.hit(x, y, width, height, scale, body_x, body_y,
                                              self.flesh_image_path, pixel_ratio, origin_x, origin_y)

    @Slot(float, float, float, float, result=bool)
    def isCatHit(self, x, y, width, height):
        pose = "cat-open.png" if self.catMeowPlaying else "cat-closed.png"
        return self._image_hit(find_app_asset(f"skins/{pose}"), x, y, width, height)

    def _image_hit(self, path, x, y, width, height):
        if width <= 0 or height <= 0 or x < 0 or y < 0 or x >= width or y >= height:
            return False
        if getattr(self, "_flesh_hit_image_path", None) != path:
            self._flesh_hit_image_path = path
            self._flesh_hit_image = QImage(path)
        image = self._flesh_hit_image
        if image.isNull():
            return False
        pixel_x = min(image.width() - 1, int(x * image.width() / width))
        pixel_y = min(image.height() - 1, int(y * image.height() / height))
        return image.pixelColor(pixel_x, pixel_y).alpha() > 32

    @Slot(str)
    def buy(self, uid):
        if not self._startup_guard:
            if self.on_buy_upgrade_clicked(None, uid):
                self.upgradePurchased.emit(uid)

    @Slot(str, str)
    def buyCrate(self, kind, tier):
        self._perform(lambda: self.buy_crate(kind, tier))

    @Slot(str, str, result="QVariantMap")
    def openCrate(self, kind, tier):
        if self._startup_guard:
            return {"ok": False, "result": "Finish loading the save first."}
        preview = self.crate_preview(kind, tier)
        result = self._perform(lambda: self.open_crate(kind, tier))
        if not isinstance(result, tuple):
            return {"ok": False, "result": "Crate could not be opened."}
        return {"ok": bool(result[0]), "result": result[1],
                "rarity": getattr(self, "_last_crate_rarity", "") if result[0] else "",
                "reward": getattr(self, "_last_crate_reward", {}) if result[0] else {},
                "pool": preview if result[0] else []}

    @Slot(str)
    def equipGear(self, item_id):
        self._perform(lambda: self.equip_gear(item_id))

    @Slot(str)
    def selectCosmetic(self, item_id):
        self._perform(lambda: self.select_cosmetic(item_id))

    @Slot(str)
    def usePotion(self, item_id):
        self._perform(lambda: self.use_potion(item_id))

    @Slot(str)
    def buyRebirthUpgrade(self, key):
        self._perform(lambda: self.buy_rebirth_upgrade(key))

    @Slot(str, "QVariant")
    def setRegisteredModSetting(self, setting_id, value):
        definition = getattr(self, "_mod_setting_definitions", {}).get(setting_id)
        if definition:
            self._perform(lambda: self.set_mod_setting(definition["key"], value, namespace=definition["owner"]))

    @Slot()
    def requestRebirth(self):
        if self._startup_guard:
            return
        amount = self.unclaimed_tokens()
        if amount < 1:
            self._set_status("Earn more flesh before rebirthing.")
            return
        self._confirm("Rebirth", f"Reset your flesh and vanilla upgrades for {amount} Flesh Tokens? Equipped items, cosmetics, and unopened crates stay.", self.rebirth)

    @Slot(str)
    def chooseRebirthBonus(self, key):
        self._perform(lambda: self.choose_rebirth_bonus(key))

    def play_squish(self):
        self.clicked.emit()

    def _play_pitched_sound(self, path, profile):
        from PySide6.QtMultimedia import QSoundEffect
        paths = pitch_variant_paths(path, profile)
        sounds = self._pitched_sounds.get(paths)
        if sounds is None:
            sounds = []
            for variant in paths:
                sound = QSoundEffect(self)
                sound.setSource(QUrl.fromLocalFile(variant))
                sounds.append(sound)
            self._pitched_sounds[paths] = sounds
        sound = random.choice(sounds)
        sound.setVolume(self.settings.get("click_sound_volume", 15) / 100)
        sound.play()

    def play_click_sound(self):
        if not self.settings.get("play_click_sound"):
            return
        cosmetic = self.active_cosmetic()
        skin = self._progression_defs("skins").get(cosmetic, {})
        if skin.get("click_sound"):
            self._play_pitched_sound(skin["click_sound"], skin["sound_profile"])
            return
        if cosmetic == "cat":
            return
        path = find_app_asset("ui/bitcrush-click.wav") if cosmetic == "bitcrush" else self.click_sound_path
        profile = "mechanical" if cosmetic in ("bitcrush", "clockwork") else "default"
        self._play_pitched_sound(path, profile)

    def _play_cat_meow(self):
        from PySide6.QtMultimedia import QSoundEffect
        if self._cat_meow_sounds is None:
            self._cat_meow_sounds = []
            for variant in pitch_variant_paths(find_app_asset("skins/cat-meow.wav"), "organic"):
                sound = QSoundEffect(self)
                sound.playingChanged.connect(self.catMeowPlayingChanged.emit)
                sound.setSource(QUrl.fromLocalFile(variant))
                self._cat_meow_sounds.append(sound)
        sound = random.choice(self._cat_meow_sounds)
        sound.setVolume(self.settings.get("click_sound_volume", 15) / 100)
        sound.play()

    @Slot(str)
    def playUiSound(self, kind):
        if not self.settings.get("play_ui_sounds", True) or kind not in ("hover", "press"):
            return
        if kind == "hover":
            now = time.monotonic()
            if now - self._last_ui_hover < 0.05:
                return
            self._last_ui_hover = now
        if kind == "press":
            self._play_pitched_sound(find_app_asset("ui/button-press.wav"), "mechanical")
            return
        from PySide6.QtMultimedia import QSoundEffect
        sound = self._ui_sounds.get(kind)
        if sound is None:
            sound = QSoundEffect(self)
            sound.setSource(QUrl.fromLocalFile(find_app_asset(f"ui/button-{kind}.wav")))
            self._ui_sounds[kind] = sound
        sound.setVolume(self.settings.get("click_sound_volume", 15) / 100)
        sound.play()

    @Slot(str)
    def playEffectSound(self, kind):
        if kind == "cat":
            if self.settings.get("play_effect_sounds", True):
                self._play_cat_meow()
            return
        files = {"roll": "crate-roll.wav", "open": "crate-open.wav",
                 "rare": "crate-rare.wav", "collect": "crate-collect.wav",
                 "streak": "streak-full.wav", "glass": "glass-crack.wav",
                 "mint": "mint-rustle.wav", "squeak": "toy-squeak.wav",
                 "blacksmith": "blacksmith-hit.wav", "coin": "gold-coin-clink.wav"}
        if not self.settings.get("play_effect_sounds", True) or kind not in files:
            return
        if kind in ("mint", "glass", "squeak", "blacksmith"):
            self._play_pitched_sound(find_app_asset(f"ui/{files[kind]}"),
                                     "mechanical" if kind in ("glass", "blacksmith") else "organic")
            return
        from PySide6.QtMultimedia import QSoundEffect
        sound = self._effect_sounds.get(kind)
        if sound is None:
            sound = QSoundEffect(self)
            sound.setSource(QUrl.fromLocalFile(find_app_asset(f"ui/{files[kind]}")))
            self._effect_sounds[kind] = sound
        sound.setVolume(self.settings.get("click_sound_volume", 15) / 100)
        sound.play()

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
        elif key in ("enable_rpc", "play_click_sound", "play_ui_sounds", "play_effect_sounds", "auto_reload_mod_changes", "show_full_numbers"):
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
        path, _ = QFileDialog.getOpenFileName(None, "Import save", "", "fleshfetch saves (*.json);;All files (*)")
        if path:
            self._perform(lambda: self.import_save_slot(path))

    @Slot(str)
    def exportSave(self, save_id):
        path, _ = QFileDialog.getSaveFileName(None, "Export save", f"{save_id}.json", "fleshfetch saves (*.json)")
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
            self._set_status("Run /reload or restart fleshfetch to apply mod changes.")
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

    @Slot(str, float, float, result=bool)
    def spriteHit(self, sprite_id, x, y):
        sprite = self._mod_sprites.get(sprite_id)
        if not sprite or not sprite.draggable or not sprite.is_visible():
            return False
        image = QImage(sprite.image_path)
        if image.isNull() or sprite.width <= 0 or sprite.height <= 0:
            return False
        drawn = image.size().scaled(int(sprite.width), int(sprite.height), Qt.AspectRatioMode.KeepAspectRatio)
        left = (sprite.width - drawn.width()) / 2
        top = (sprite.height - drawn.height()) / 2
        if not (left <= x < left + drawn.width() and top <= y < top + drawn.height()):
            return False
        pixel_x = min(image.width() - 1, int((x - left) * image.width() / drawn.width()))
        pixel_y = min(image.height() - 1, int((y - top) * image.height() / drawn.height()))
        return image.pixelColor(pixel_x, pixel_y).alpha() > 32

    @Slot(str)
    def grabSprite(self, sprite_id):
        sprite = self._mod_sprites.get(sprite_id)
        if sprite and sprite.draggable:
            sprite.set_velocity(0, 0)
            sprite.set_auto_motion(False)
            self.emit_event("sprite_grabbed", {"sprite_id": sprite_id})

    @Slot(str, float, float)
    def moveSprite(self, sprite_id, x, y):
        sprite = self._mod_sprites.get(sprite_id)
        if sprite and sprite.draggable:
            sprite.move_to(x, y)

    @Slot(str, float, float)
    def releaseSprite(self, sprite_id, vx, vy):
        sprite = self._mod_sprites.get(sprite_id)
        if sprite and sprite.draggable:
            sprite.set_velocity(vx, vy)
            self.emit_event("sprite_released", {"sprite_id": sprite_id, "vx": vx, "vy": vy})
            if not sprite._manual_motion:
                self._sync_motion_timer()

    def get_sprite_platforms(self):
        window = getattr(self, "_qml_window", None)
        if window is None:
            return []
        root = window.contentItem()
        pending = [root]
        items = []
        layer = None
        while pending:
            item = pending.pop()
            if item.objectName() == "spriteLayer":
                layer = item
            if item.objectName() == "spritePlatform" and item.isVisible():
                items.append(item)
            pending.extend(item.childItems())
        if layer is None:
            return []
        platforms = []
        for item in items:
            point = item.mapToItem(layer, QPointF(0, 0))
            top = point.y() + item.height() + 3 if item.property("tabStyle") else point.y()
            if -item.height() <= top <= layer.height():
                platforms.append({"x": point.x(), "y": top,
                                  "width": item.width(), "height": item.height()})
        return platforms

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
                self._flush_pending_crate_drops()
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
            for sounds in self._pitched_sounds.values():
                for sound in sounds:
                    sound.stop()
            for sound in self._cat_meow_sounds or ():
                sound.stop()
            for sound in self._effect_sounds.values():
                sound.stop()
        finally:
            self._closed = True
            self._legacy_idle_pending.clear()
            self._restore_streams()


def create_application(argv=None):
    from app_version import VERSION

    ensure_app_dirs()
    app = QApplication.instance() or QApplication(sys.argv[:1] if argv is None else argv)
    app.setApplicationName("fleshfetch")
    app.setApplicationVersion(VERSION)
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
    engine.addImageProvider("surfaces", SurfaceImages(game))
    from PySide6.QtQml import qmlRegisterType
    from qt_legacy_drawing import LegacyPaintItem
    qmlRegisterType(LegacyPaintItem, "Fleshfetch.Legacy", 1, 0, "LegacyPaintItem")
    engine.rootContext().setContextProperty("game", game)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / "qml" / "Main.qml")))
    if not engine.rootObjects():
        game.shutdown()
        raise RuntimeError("The Qt interface could not be loaded. " + "\n".join(qml_errors))
    game._qml_window = engine.rootObjects()[0]
    engine.rootObjects()[0].installEventFilter(game._legacy_pointer_filter)
    app.aboutToQuit.connect(game.shutdown)
    QTimer.singleShot(0, game.ready)
    return app, engine, game


def main(on_first_frame=None):
    app, engine, game = create_application()
    if on_first_frame is not None:
        window = engine.rootObjects()[0]
        first_frame_seen = False

        def finish_splash():
            nonlocal first_frame_seen
            if first_frame_seen:
                return
            first_frame_seen = True
            on_first_frame()

        window.frameSwapped.connect(finish_splash)
        QTimer.singleShot(3000, finish_splash)
    try:
        return app.exec()
    finally:
        game.shutdown()
