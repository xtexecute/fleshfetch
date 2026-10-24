"""Render the real QML app against isolated data and exercise a mouse click."""

from pathlib import Path
import os
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    with tempfile.TemporaryDirectory() as temp:
        os.environ["APPDATA"] = temp
        os.environ["XDG_CONFIG_HOME"] = temp
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ.setdefault("QT_QUICK_BACKEND", "software")
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtQuick import QQuickItem
        from PySide6.QtTest import QTest
        from PySide6.QtGui import QFont, QFontDatabase
        from PySide6.QtWidgets import QApplication
        from qt_frontend import create_application

        sys.excepthook = sys.__excepthook__
        app = QApplication([])
        if os.name == "nt" and not QFontDatabase.families():
            # The Windows offscreen platform does not enumerate system fonts.
            for font in ("segoeui.ttf", "segoeuib.ttf", "consola.ttf"):
                QFontDatabase.addApplicationFont(str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / font))
            app.setFont(QFont("Segoe UI", 10))
        app, engine, game = create_application([])
        window = engine.rootObjects()[0]
        warnings = []
        engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
        out = ROOT / "output"
        out.mkdir(exist_ok=True)
        try:
            QTest.qWait(150)
            target = window.findChild(QQuickItem, "clickTarget")
            assert target is not None
            point = target.mapToScene(QPointF(target.width() / 2, target.height() / 2))
            QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                             QPoint(round(point.x()), round(point.y())))
            assert game.state["total_clicks"] == 1
            game.set_currency("flesh", 125)
            game._current_mod_info = {"id": "demo", "name": "Demo", "path": str(ROOT)}
            tab = game.add_tab("demo", "Mod example")
            tab.add_label("Mod-owned controls")
            tab.add_button("Add 10 flesh", lambda button: game.add_currency("flesh", 10))
            tab.set_theme(canvas="#142820", accent="#48ba78", text="#e0ffe8")
            sheet = Path(temp) / "buttons.png"
            from PySide6.QtGui import QImage, QColor
            artwork = QImage(128, 32, QImage.Format.Format_ARGB32)
            artwork.fill(QColor("#34784d"))
            assert artwork.save(str(sheet))
            game.add_button("plant", tab="demo", text="Plant", on_click=lambda button: None,
                sprites={"sheet": str(sheet), "border": 4, "normal": [0, 0, 32, 32],
                         "hover": [32, 0, 32, 32], "pressed": [64, 0, 32, 32],
                         "disabled": [96, 0, 32, 32]})
            game._current_mod_info = None
            for theme in ("light", "dark"):
                game.setPreference("theme", theme)
                for width, height in ((1100, 740), (800, 600)):
                    window.setWidth(width)
                    window.setHeight(height)
                    for page in ("upgrades", "saves", "settings", "console", "demo", "leaderboard"):
                        window.setProperty("selectedTab", page)
                        QTest.qWait(140)
                        image = window.grabWindow()
                        assert not image.isNull(), (theme, page, width)
                        colors = {image.pixelColor(x, y).name() for x in range(0, width, 19)
                                  for y in range(0, height, 19)}
                        assert len(colors) > 8, ("Blank render", theme, page)
                        assert image.save(str(out / f"qt-{theme}-{width}-{page}.png"))
            window.setWidth(1100)
            window.setHeight(740)
            window.setProperty("selectedTab", "upgrades")
            game.register_currency("leaves", "Leaves")
            game.register_currency("wood", "Wood")
            game.set_currency("leaves", 66)
            game.set_currency("wood", 20)
            QTest.qWait(100)
            pane = window.findChild(QQuickItem, "clickPane")
            divider = window.findChild(QQuickItem, "paneDivider")
            assert pane and divider
            before = pane.width()
            point = divider.mapToScene(QPointF(divider.width()/2, divider.height()/2))
            start = QPoint(round(point.x()), round(point.y()))
            QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
            QTest.mouseMove(window, start + QPoint(120, 0), 20)
            QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start + QPoint(120, 0))
            QTest.qWait(80)
            assert pane.width() > before + 60, (before, pane.width())
            grid = window.findChild(QQuickItem, "currencyTiles")
            assert grid.property("columns") >= 2
            assert window.grabWindow().save(str(out / "qt-currency-tiles-divider.png"))
            assert not warnings, "\n".join(warnings)
            print("Rendered both themes at two sizes; click input, currency tiling and divider dragging work.")
        finally:
            game.shutdown()
            window.close()
            app.processEvents()


if __name__ == "__main__":
    main()
