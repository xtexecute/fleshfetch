import ast
import builtins
import importlib.util
import inspect
import json
from pathlib import Path
import tempfile
import types
import sys
import unittest
from unittest import mock

import qt_mod_ui as ui


class Game(ui.QtModUiMixin):
    def __init__(self):
        self.catalog_updates = self.live_updates = 0
        self.owner = "test_mod"
        self._mod_paths = {}
        self._current_mod_info = None
        self.init_qt_mod_ui()

    def _notify_catalog(self):
        self.catalog_updates += 1

    def _notify_live(self):
        self.live_updates += 1

    def _current_mod_namespace(self):
        return self.owner

    def _run_with_mod_owner(self, owner, callback, *args):
        previous, self.owner = self.owner, owner
        try:
            return callback(*args)
        finally:
            self.owner = previous


class QtModUiTests(unittest.TestCase):
    def test_named_button_sheet_and_legacy_alias(self):
        g = self.game
        g.add_tab("garden", "Garden")
        called = []
        button = g.add_button("plant", tab="garden", text="Plant", on_click=lambda b: called.append(b.id),
                              sprites={"sheet": "assets/buttons.png", "border": 4,
                                       "normal": [0, 0, 32, 32], "hover": [32, 0, 32, 32]})
        data = button.to_dict()
        self.assertTrue(data["sprites"]["normal"].startswith("image://skins/sprite/"))
        self.assertEqual(data["spriteBorder"]["left"], 4)
        self.assertEqual(g._qt_items["garden"][0]["id"], button.id)
        self.assertTrue(button.click())
        self.assertEqual(called, [button.id])
        g.add_button("garden", "Legacy", lambda b: None)
        with self.assertRaises(ValueError):
            g.add_button("bad", tab="garden", on_click=lambda b: None,
                         sprites={"sheet": "x.png", "normal": [0, 0, 4, 4]})
        self.assertNotIn("test_mod:bad", g._qt_buttons)

    def test_tab_theme_layering_and_reset(self):
        g = self.game
        g.set_tab_theme("stats", accent="#22aa55", text="#ffffff")
        g.owner = "other"
        g.set_tab_theme("stats", accent="#aa2255")
        snapshot = g._qt_theme_snapshot()
        self.assertEqual(snapshot["stats"], {"accent": "#aa2255", "text": "#ffffff"})
        snapshot["stats"]["text"] = "changed"
        g.set_tab_theme("stats")
        self.assertEqual(g._qt_theme_snapshot()["stats"]["accent"], "#22aa55")
        with self.assertRaises(ValueError):
            g.set_tab_theme("stats", text="invalid")

    def setUp(self):
        self.paths = types.ModuleType("paths")
        self.paths.find_app_asset = lambda name: str(Path(ui.__file__).parent / name)
        patcher = mock.patch.dict(sys.modules, {"paths": self.paths})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.game = Game()

    def test_import_needs_no_toolkit_or_legacy_rendering(self):
        original = builtins.__import__

        def guarded(name, *args, **kwargs):
            if name.split(".")[0] in {"gtk_compat", "gi", "cairo", "rendering",
                                       "PySide6", "PyQt6", "bootstrap"}:
                raise AssertionError("Unexpected import: " + name)
            return original(name, *args, **kwargs)

        spec = importlib.util.spec_from_file_location("qt_mod_ui_isolated", ui.__file__)
        module = importlib.util.module_from_spec(spec)
        with mock.patch("builtins.__import__", side_effect=guarded):
            spec.loader.exec_module(module)
            game = type("IsolatedGame", (module.QtModUiMixin, Game), {})()
            game.add_tab("plain", "Plain").add_label("Hello")
            game.create_image("missing.png")
            game.qt_mod_ui_snapshot()

    def test_public_signature_parity_without_importing_rendering(self):
        source = Path(ui.__file__).with_name("rendering.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        rendering = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                         and node.name == "RenderingMixin")
        for name in ("create_image", "create_sprite", "add_image", "create_draw_layer"):
            legacy = next(node for node in rendering.body if isinstance(node, ast.FunctionDef)
                          and node.name == name)
            current = inspect.signature(getattr(ui.QtModUiMixin, name))
            args = legacy.args
            expected = [arg.arg for arg in args.args]
            if args.vararg:
                expected.append(args.vararg.arg)
            if args.kwarg:
                expected.append(args.kwarg.arg)
            self.assertEqual(list(current.parameters), expected, name)
            defaults = [ast.literal_eval(value) for value in args.defaults]
            actual = [p.default for p in current.parameters.values()
                      if p.default is not inspect.Parameter.empty]
            self.assertEqual(actual, defaults, name)

    def test_tabs_and_queued_content_keep_order(self):
        g = self.game
        button = g.add_tab_button("tools", "Before", lambda b: None)
        image = g.add_image("tools", "missing.png")
        tab = g.add_tab("tools", "Tools")
        self.assertIsInstance(tab, ui.TabHandle)
        self.assertIs(g._tab_pages["tools"], tab)
        self.assertEqual(g._mod_tab_owners["tools"], "test_mod")
        self.assertIs(tab.add_label("Status"), tab)
        after = tab.add_button("After", lambda b: None)
        self.assertEqual(tab.to_dict()["items"], [
            {"type": "button", "id": button.id}, {"type": "image", "id": image.id},
            {"type": "label", "text": "Status", "owner": "test_mod"},
            {"type": "button", "id": after.id}])
        with self.assertRaisesRegex(ValueError, "already exists"):
            g.add_tab("tools", "Duplicate")
        with self.assertRaisesRegex(ui.QtModCompatibilityError, "TabHandle.add_label"):
            g.add_tab("old", "Old", object())
        for handle in (tab, button, image):
            self.assertFalse(hasattr(handle, "widget"))
            self.assertFalse(hasattr(handle, "get_widget"))

    def test_callback_uses_handle_and_original_owner(self):
        g, calls = self.game, []

        def clicked(button):
            calls.append((button, g.owner))
            g.add_image("settings", "nested.png")

        button = g.add_button("settings", "Click", clicked)
        g.owner = "other_mod"
        self.assertTrue(g.activate_qt_button(button.id))
        self.assertEqual(calls, [(button, "test_mod")])
        self.assertEqual(g.owner, "other_mod")
        self.assertEqual(g._mod_image_widgets[0].owner, "test_mod")
        self.assertIs(button.set_label("Updated"), button)
        self.assertEqual(button.get_label(), "Updated")
        button.set_sensitive(False)
        self.assertFalse(button.get_sensitive())
        self.assertFalse(g.activate_qt_button(button.id))
        button.set_sensitive(True).hide()
        self.assertFalse(button.click())
        button.show().set_visible(True).set_tooltip_text("Hint")
        self.assertTrue(button.activate())
        g.add_tab("settings", "Settings").hide()
        self.assertFalse(button.click())
        self.assertFalse(g.activate_qt_button("unknown"))
        with self.assertRaises(ValueError):
            g.add_button("settings", "Broken", None)

    def test_snapshot_is_serializable_and_detached_with_uri_escaping(self):
        g = self.game
        tab = g.add_tab("custom", "Custom")
        tab.add_label("Text")
        button = tab.add_button("Run", lambda b: None)
        button.set_tooltip_text("Tip").set_sprite("normal #1.png", hover="hover.png",
                                               pressed="pressed.png", disabled="disabled.png")
        image = g.create_image("image #1.png", pos=(10, 20), size=(30, 40), visible=False)
        image.rotate_by(45).set_opacity(50).set_velocity(2, 3)
        snapshot = g.qt_mod_ui_snapshot()
        json.dumps(snapshot, allow_nan=False)
        self.assertEqual(set(snapshot), {"tabs", "buttons", "images"})
        self.assertEqual(set(snapshot["buttons"][0]["sprites"]), {"normal", "hover", "pressed", "disabled"})
        record = snapshot["images"][0]
        self.assertIn("%20%231.png", record["source"])
        self.assertTrue(record["source"].startswith("file:///"))
        self.assertEqual((record["kind"], record["tab_id"], record["opacity"]), ("sprite", None, 0.5))
        snapshot["tabs"][0]["items"][0]["text"] = "Changed"
        snapshot["buttons"][0]["sprites"].clear()
        snapshot["images"][0]["x"] = 999
        self.assertEqual(tab.to_dict()["items"][0]["text"], "Text")
        self.assertEqual(len(button.sprites), 4)
        self.assertEqual(image.x, 10)

    def test_image_creation_normalization_and_mutators(self):
        g = self.game
        layout = g.add_image("stats", "missing.png", width=12, expand=True)
        self.assertIsInstance(layout, ui.ImageHandle)
        self.assertEqual(layout.get_size(), (12, 12))
        self.assertTrue(layout.to_dict()["expand"])
        sprite = g.create_sprite("missing.png", size=None, pos=None, width=20, height=30, x=4, y=5)
        self.assertIsInstance(sprite, ui.SpriteHandle)
        self.assertIs(g.get_sprite(sprite.sprite_id), sprite)
        self.assertEqual(sprite.get_pos(), (4, 5))
        self.assertEqual(sprite.get_size(), (20, 30))
        default = g.create_image("missing.png", width=500, x=500)
        self.assertEqual((default.get_size(), default.get_pos()), ((100, 100), (0, 0)))
        layout2 = g.create_image("missing.png", tab_id="stats", size=25)
        self.assertEqual(layout2.get_size(), (25, 25))
        sprite.set_size(size=(50, 60)).set_x(7).set_y(8).move_by(1, 2)
        self.assertEqual((sprite.get_x(), sprite.get_y()), (8, 10))
        self.assertEqual((sprite.get_width(), sprite.get_height()), (50, 60))
        sprite.set_pos(1, 2).set_velocity(10, -5).step(0.5)
        self.assertEqual(sprite.get_pos(), (6, -0.5))
        self.assertEqual(sprite.get_velocity(), (10, -5))
        sprite.set_rotation(-30).rotate_by(60)
        self.assertEqual(sprite.get_rotation(), 30)
        sprite.set_rotation("bad").set_opacity("bad")
        self.assertEqual((sprite.get_rotation(), sprite.get_opacity()), (0, 1))
        sprite.set_opacity(-1)
        self.assertEqual(sprite.get_opacity(), 0)
        self.assertTrue(sprite.set_image("replacement.png"))
        self.assertTrue(g.hide_image(sprite.id))
        self.assertFalse(sprite.is_visible())
        self.assertTrue(g.show_image(sprite))
        self.assertTrue(sprite.get_visible())
        self.assertEqual(g._normalize_image_size(size="bad"), (100, 100))
        self.assertEqual(g._normalize_position(pos=None, x="bad", y=None), (0, 0))

    def test_bounds_bounce_and_unallocated_canvas(self):
        g = self.game
        image = g.create_image("missing.png", size=(10, 20), pos=(85, 70))
        image.set_velocity(8, 12)
        result = image.bounce()
        self.assertEqual(image.get_pos(), (85, 70))
        self.assertFalse(any(result["edges"].values()))
        g._qt_view_width, g._qt_view_height = 100, 100
        result = image.bounce()
        self.assertEqual(image.get_pos(), (90, 80))
        self.assertEqual(image.get_velocity(), (-8, -12))
        self.assertEqual(result["corner"], "bottom-right")
        self.assertTrue(result["edges"]["horizontal"])
        self.assertTrue(image.is_touching_corner())
        image.move_to(3, 3)
        result = image.bounce_velocity(-10, -10, margin=2)
        self.assertEqual(image.get_pos(), (2, 2))
        self.assertEqual(result["corner"], "top-left")
        self.assertEqual(image.get_bounds()["window_width"], 100)
        for pos, corner in (((0, 80), "bottom-left"), ((90, 0), "top-right")):
            image.move_to(*pos)
            self.assertEqual(image.get_corner_hit(), corner)
        image.move_to(50, 50)
        self.assertIsNone(image.get_corner_hit())

    def test_timer_batches_live_updates_and_stops_after_removal(self):
        g = self.game
        first = g.create_image("one.png").set_velocity(100, 50)
        second = g.create_image("two.png").set_velocity(-50, 0).hide()
        self.assertTrue(g.has_qt_mod_motion())
        before, catalog = g.live_updates, g.catalog_updates
        self.assertTrue(g.advance_qt_mod_ui())
        self.assertEqual(g.live_updates, before + 1)
        self.assertEqual(g.catalog_updates, catalog)
        self.assertEqual(first.get_pos(), (1.6, 0.8))
        self.assertEqual(second.get_pos(), (-0.8, 0))
        self.assertFalse(g.advance_qt_mod_ui(-1))
        first.remove()
        second.remove()
        self.assertFalse(g.has_qt_mod_motion())
        self.assertFalse(g.advance_qt_mod_ui())

    def test_image_notifications_follow_frontend_catalog_and_live_split(self):
        g = self.game
        layout = g.add_image("stats", "layout.png")
        overlay = g.create_image("overlay.png")
        before = g.catalog_updates, g.live_updates
        layout.set_opacity(0.5)
        self.assertEqual((g.catalog_updates, g.live_updates), (before[0] + 1, before[1]))
        overlay.set_rotation(30)
        self.assertEqual((g.catalog_updates, g.live_updates), (before[0] + 1, before[1] + 1))
        layout.set_velocity(1, 0)
        before = g.catalog_updates, g.live_updates
        g.advance_qt_mod_ui()
        self.assertEqual((g.catalog_updates, g.live_updates), (before[0] + 1, before[1] + 1))

    def test_callback_owner_is_restored_on_exception(self):
        g = self.game

        def broken(button):
            self.assertEqual(g.owner, button.owner)
            raise RuntimeError("mod failure")

        button = g.add_button("settings", "Fail", broken)
        g.owner = "other"
        with self.assertRaisesRegex(RuntimeError, "mod failure"):
            button.activate()
        self.assertEqual(g.owner, "other")

    def test_cleanup_removes_all_tab_children_and_tracking(self):
        g = self.game
        tab = g.add_tab("tools", "Tools")
        button = tab.add_button("Run", lambda b: None)
        image = g.add_image("tools", "image.png")
        overlay = g.create_sprite("overlay.png")
        g.owner = "another_mod"
        foreign = g.add_button("tools", "Foreign", lambda b: None)
        self.assertTrue(tab.remove())
        self.assertTrue(all(h._removed for h in (tab, button, image, foreign)))
        self.assertEqual(g._qt_tabs, {})
        self.assertEqual(g._qt_buttons, {})
        self.assertEqual(g._mod_button_widgets, [])
        self.assertEqual(g._mod_image_widgets, [])
        self.assertEqual(g._mod_tab_owners, {})
        self.assertEqual(g._tab_pages, {})
        self.assertEqual(g._qt_items, {})
        self.assertEqual(list(g._qt_images), [overlay.id])
        self.assertTrue(g._remove_widget_from_parent(overlay))
        self.assertEqual(g._mod_sprites, {})
        self.assertFalse(overlay.remove())
        self.assertFalse(overlay.set_image("no.png"))
        self.assertFalse(button.click())
        self.assertFalse(tab.remove())
        self.assertFalse(g.remove_image(overlay))
        self.assertFalse(g.show_image("unknown"))
        with self.assertRaises(ValueError):
            tab.add_label("stale")
        fresh = g.add_tab("tools", "Again")
        self.assertFalse(tab.remove())
        self.assertIs(g._qt_tabs["tools"], fresh)

    def test_reload_style_cleanup_also_removes_builtin_tab_content(self):
        g = self.game
        button = g.add_button("settings", "Mod option", lambda b: None)
        layout = g.add_image("stats", "image.png")
        sprite = g.create_sprite("sprite.png")
        for item in list(g._mod_button_widgets):
            g._remove_widget_from_parent(item["widget"])
        for handle in list(g._mod_image_widgets):
            handle.remove()
        for handle in list(g._mod_sprites.values()):
            handle.remove()
        self.assertTrue(all(h._removed for h in (button, layout, sprite)))
        self.assertEqual(g.qt_mod_ui_snapshot(), {"tabs": [], "buttons": [], "images": []})
        self.assertEqual(g._qt_items["settings"], [])

    def test_asset_resolution_order_and_owner_after_registration(self):
        g = self.game
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            root = Path(folder)
            mod = root / "mod"
            assets = mod / "assets"
            assets.mkdir(parents=True)
            app = root / "app.png"
            app.touch()
            nested = assets / "picture.png"
            nested.touch()
            direct = mod / "picture.png"
            g._mod_paths["test_mod"] = str(mod)
            g._current_mod_info = {"id": "test_mod", "path": str(mod)}
            with mock.patch.object(self.paths, "find_app_asset", return_value=str(app)):
                self.assertEqual(Path(g.resolve_asset_path("picture.png")), nested)
                direct.touch()
                self.assertEqual(Path(g.resolve_asset_path("picture.png")), direct)
                self.assertEqual(g.resolve_asset_path(str(app)), str(app))
                self.assertEqual(g.resolve_asset_path(""), "")
                self.assertEqual(Path(g.resolve_asset_path("not-found.png", owner="other")), app)
                image = g.create_image("picture.png")
                g._current_mod_info = {"id": "other", "path": str(root)}
                g.owner = "other"
                image.set_image("picture.png")
                self.assertEqual(Path(image.image_path), direct)
                with mock.patch("os.path.exists", return_value=False):
                    self.assertEqual(Path(g.resolve_mod_asset_path("missing.png", owner="test_mod")), mod / "missing.png")

    def test_flesh_image_only_notifies_live_and_drawing_is_explicitly_unsupported(self):
        g = self.game
        g.picture = object()
        g.load_flesh_image = mock.Mock(side_effect=AssertionError("No widget loader"))
        before = g.live_updates
        g.set_flesh_image("new.png")
        self.assertEqual(g.live_updates, before + 1)
        self.assertTrue(g.flesh_image_path.endswith("new.png"))
        g.load_flesh_image.assert_not_called()
        for factory in (g.create_draw_layer, g.create_canvas):
            with self.assertRaisesRegex(NotImplementedError,
                                        "GTK/Cairo drawing mods need a Qt-compatible drawing API"):
                factory()


if __name__ == "__main__":
    unittest.main()
