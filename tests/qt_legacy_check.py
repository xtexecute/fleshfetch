"""Exercise old mods in an isolated configuration, without network connections."""

import importlib.util
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    with tempfile.TemporaryDirectory() as temp:
        os.environ.update(APPDATA=temp, XDG_CONFIG_HOME=temp,
                          QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
        destination = Path(temp) / "fleshfetch" / "mods" / "LegacyCompatibilityTest"
        shutil.copytree(ROOT / "example_mods" / "LegacyCompatibilityTest", destination)
        (destination / "enabled.txt").write_text("true\n", encoding="utf-8")
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QFont, QFontDatabase
        from PySide6.QtQuick import QQuickItem
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        app = QApplication([])
        if os.name == "nt" and not QFontDatabase.families():
            for filename in ("segoeui.ttf", "consola.ttf"):
                QFontDatabase.addApplicationFont(str(Path("C:/Windows/Fonts") / filename))
            app.setFont(QFont("Segoe UI", 10))
        from qt_frontend import create_application
        sys.excepthook = sys.__excepthook__
        app, engine, game = create_application([])
        window = engine.rootObjects()[0]
        try:
            assert "LegacyCompatibilityTest" in game.loaded_mod_ids, game.installed_mods
            warnings = []
            engine.warnings.connect(lambda errors: warnings.extend(str(e) for e in errors))
            from gi.repository import GLib
            hits = []
            GLib.timeout_add(1, lambda: hits.append("once"))
            import threading
            thread = threading.Thread(target=lambda: GLib.idle_add(lambda: hits.append("worker")))
            thread.start()
            thread.join()
            window.setProperty("selectedTab", "legacy_test")
            QTest.qWait(300)
            assert sorted(hits) == ["once", "worker"], hits
            controls = game._legacy_test_controls
            controls["entry"].action("text", "7")
            previous = game.flesh
            controls["button"].action("click", None)
            assert game.flesh == previous + 7
            controls["switch"].action("active", False)
            controls["button"].action("click", None)
            assert game.flesh == previous + 7
            controls["combo"].action("index", 1)
            assert controls["status"].get_text() == "Option B"
            controls["spin"].action("value", 4.5)
            assert controls["entry"].get_text() == "4.5"
            assert "TextBuffer.insert works" in controls["buffer"].get_text()
            assert "ticks:" in controls["timer"].get_text()
            assert "#ffff00" in game.consoleHtml
            # Exercise actual QML input, not just Python signal dispatch.
            controls["switch"].set_active(True)
            QTest.qWait(100)
            def descendants(item):
                for child in item.childItems():
                    yield child
                    yield from descendants(child)
            button = next(item for item in descendants(window.contentItem())
                          if item.property("text") == "Add" and item.isVisible())
            point = button.mapToScene(QPointF(button.width()/2, button.height()/2))
            QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                             QPoint(round(point.x()), round(point.y())))
            assert game.flesh == previous + 11.5
            entry_item = next(item for item in descendants(window.contentItem())
                              if item.property("placeholderText") == "Type here, then press Add" and item.isVisible())
            point = entry_item.mapToScene(QPointF(20, entry_item.height()/2))
            QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                             QPoint(round(point.x()), round(point.y())))
            QTest.keyClick(window, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
            QTest.keyClick(window, Qt.Key.Key_9)
            assert controls["entry"].get_text() == "9"
            QTest.qWait(60)
            image = window.grabWindow()
            assert not image.isNull()
            (ROOT / "output").mkdir(exist_ok=True)
            image.save(str(ROOT / "output" / "qt-legacy-compatibility.png"))
            assert not warnings, "\n".join(warnings)
            from gi.repository import Gtk
            responses = []
            dialog = Gtk.Dialog()
            dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
            dialog.connect("response", lambda widget, response: responses.append(response))
            dialog.present()
            dialog._dialog.reject()
            QTest.qWait(20)
            assert responses == [Gtk.ResponseType.CANCEL], responses
            frames, draws = [], []
            def draw_layer(layer, context, width, height):
                draws.append((width, height))
                context.set_source_rgb(0.2, 0.6, 0.8)
                context.rectangle(1, 1, 2, 2)
                context.fill()
            layer = game.create_canvas(draw_layer, name="legacy_canvas_test")
            layer.start_animation(lambda layer, delta, now: frames.append(delta))
            QTest.qWait(60)
            window.grabWindow()
            assert frames and draws, (frames, draws)
            layer.remove()
            QTest.qWait(30)
            before = len(game._legacy_nodes)
            game.reload_mods()
            QTest.qWait(300)
            assert "LegacyCompatibilityTest" in game.loaded_mod_ids
            assert len(game._legacy_nodes) == before
            assert all(timer["owner"] in ("__global__", "LegacyCompatibilityTest") for timer in game._mod_timers.values())
            # Built-in tabs must display queued legacy buttons too.
            game.add_button("console", "Built-in test", lambda b: hits.append("builtin"))
            game._publish()
            window.setProperty("selectedTab", "console")
            QTest.qWait(120)
            assert any(item.property("text") == "Built-in test" and item.isVisible()
                       for item in descendants(window.contentItem()))
            # Optional read-only smoke tests of locally installed old mods.
            old_root = Path("C:/Users/Beyazay/AppData/Roaming/fleshfetch/mods")
            modules = {}
            for name in ("BackCompatTest", "RegEdit", "FFTogether", "BouncingFlesh", "OfficialPlantExpansion", "consoletester", "flesh_test"):
                source = old_root / name / "mod.py"
                if not source.exists():
                    continue
                info = {"id": name, "name": name, "path": str(source.parent), "deprecation_warnings": []}
                game._current_mod_info = info
                game._mod_paths[name] = str(source.parent)
                spec = importlib.util.spec_from_file_location("legacy_smoke_" + name, source)
                mod = importlib.util.module_from_spec(spec)
                mod.MOD_DIR, mod.MANIFEST = str(source.parent), {}
                spec.loader.exec_module(mod)
                mod.register(game)
                modules[name] = mod
                game._current_mod_info = None
                print("Loaded installed legacy mod:", name)
            if "FFTogether" in modules:
                api = game.get_api("fftogether")
                client = api.client if hasattr(api, "client") else api._client
                client._upsert_player({"id": "test_cursor", "name": "Compat cursor", "color": "#33cc88"})
                client._refresh_cursor_positions()
                client._refresh_players_list()
                game._sprite_layer.queue_draw()
            if "BouncingFlesh" in modules:
                sprite = next(image for image in game._mod_sprites.values() if image.owner == "BouncingFlesh")
                origin_x, origin_y = game._legacy_origin
                start = QPoint(round(origin_x + sprite.get_x() + 15), round(origin_y + sprite.get_y() + 15))
                previous_x = sprite.get_x()
                QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
                QTest.mouseMove(window, start + QPoint(30, 15), 10)
                QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start + QPoint(30, 15))
                assert sprite.get_x() >= previous_x + 29, (previous_x, sprite.get_x())
            game._notify_catalog()
            QTest.qWait(150)
            for tab in ("regedit", "fftogether", "fftogether_saves"):
                if tab in game._qt_tabs:
                    window.setProperty("selectedTab", tab)
                    QTest.qWait(120)
                    window.grabWindow().save(str(ROOT / "output" / ("qt-legacy-" + tab + ".png")))
            assert not warnings, "\n".join(warnings)
            print("Legacy controls, QML clicks, drawing, timers, reload and installed-mod smoke checks passed.")
        finally:
            game._current_mod_info = None
            game.shutdown()
            window.close()
            app.processEvents()


if __name__ == "__main__":
    main()
