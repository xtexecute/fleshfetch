import unittest
from unittest import mock

import rendering


class FakeFrameClock:
    def __init__(self, frame_time):
        self.frame_time = frame_time

    def get_frame_time(self):
        return self.frame_time


class FakeDrawingArea:
    def __init__(self):
        self.draw_callback = None
        self.tick_callback = None
        self.parent = None
        self.visible = True
        self.draw_requests = 0
        self.removed_tick_ids = []

    def set_hexpand(self, _value):
        pass

    def set_vexpand(self, _value):
        pass

    def set_halign(self, _value):
        pass

    def set_valign(self, _value):
        pass

    def set_can_target(self, _value):
        pass

    def set_visible(self, value):
        self.visible = bool(value)

    def get_visible(self):
        return self.visible

    def set_draw_func(self, callback):
        self.draw_callback = callback

    def add_tick_callback(self, callback):
        self.tick_callback = callback
        return 17

    def remove_tick_callback(self, callback_id):
        self.removed_tick_ids.append(callback_id)

    def queue_draw(self):
        self.draw_requests += 1

    def get_allocated_width(self):
        return 900

    def get_allocated_height(self):
        return 600

    def get_parent(self):
        return self.parent


class FakeOverlay:
    def __init__(self):
        self.children = []

    def add_overlay(self, widget):
        widget.parent = self
        self.children.append(widget)

    def remove(self, widget):
        widget.parent = None
        self.children.remove(widget)


class RenderingGame(rendering.RenderingMixin):
    def __init__(self):
        self._mod_draw_layers = {}
        self._pending_draw_layers = []
        self._next_draw_layer_id = 1
        self.callback_owners = []

    def _current_mod_namespace(self):
        return "particle_api"

    def _run_with_mod_owner(self, owner, callback, *args):
        self.callback_owners.append(owner)
        return callback(*args)

    def _remove_widget_from_parent(self, widget):
        parent = widget.get_parent()
        if parent is not None:
            parent.remove(widget)


class DrawLayerTests(unittest.TestCase):
    def test_layer_draw_animation_and_cleanup(self):
        game = RenderingGame()
        draw_calls = []
        animation_calls = []

        def draw(layer, context, width, height):
            draw_calls.append((layer.layer_id, context, width, height))

        with mock.patch.object(rendering.Gtk, "DrawingArea", FakeDrawingArea):
            layer = game.create_draw_layer(draw, name="particles")

        self.assertEqual(layer.layer_id, "particle_api:particles")
        self.assertEqual(game._pending_draw_layers, [layer])

        game._window_overlay = FakeOverlay()
        game._attach_draw_layer(layer)
        self.assertEqual(game._window_overlay.children, [layer.widget])

        context = object()
        layer.widget.draw_callback(layer.widget, context, 900, 600)
        self.assertEqual(draw_calls, [("particle_api:particles", context, 900, 600)])

        def animate(_layer, delta, frame_time):
            animation_calls.append((delta, frame_time))
            return len(animation_calls) < 2

        layer.start_animation(animate)
        self.assertTrue(layer.widget.tick_callback(layer.widget, FakeFrameClock(1_000_000)))
        self.assertFalse(layer.widget.tick_callback(layer.widget, FakeFrameClock(1_016_000)))
        self.assertEqual(animation_calls[0], (0.0, 1.0))
        self.assertAlmostEqual(animation_calls[1][0], 0.016)
        self.assertEqual(game.callback_owners, ["particle_api", "particle_api", "particle_api"])

        self.assertTrue(layer.remove())
        self.assertNotIn(layer.layer_id, game._mod_draw_layers)
        self.assertEqual(game._window_overlay.children, [])
        self.assertFalse(layer.remove())

    def test_duplicate_layer_names_are_rejected(self):
        game = RenderingGame()
        with mock.patch.object(rendering.Gtk, "DrawingArea", FakeDrawingArea):
            game.create_canvas(name="particles")
            with self.assertRaises(ValueError):
                game.create_draw_layer(name="particles")


if __name__ == "__main__":
    unittest.main()
