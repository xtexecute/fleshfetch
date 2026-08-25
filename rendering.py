import math
import os

from gtk_compat import Gdk, GdkPixbuf, Gtk, cairo

from paths import find_app_asset


class ModImageHandle:
    """Small handle returned to mods for images added through the public API."""

    def __init__(self, game, widget, owner, image_path="", width=None, height=None):
        self.game = game
        self.widget = widget
        self.owner = owner
        self.image_path = image_path
        self.width = width
        self.height = height
        self.opacity = 1.0
        self._removed = False

    def get_widget(self):
        return self.widget

    def set_image(self, image_path: str):
        if self._removed:
            return False
        return self.game._set_picture_image(self.widget, image_path, owner=self.owner, handle=self)

    def set_size(self, width=None, height=None, size=None):
        width, height = self.game._normalize_image_size(
            size=size,
            width=width,
            height=height,
            default_width=self.width or 100,
            default_height=self.height or 100,
        )
        self.width = width
        self.height = height
        self.widget.set_size_request(width, height)
        return self

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def set_opacity(self, alpha):
        try:
            alpha = float(alpha)
        except Exception:
            alpha = 1.0
        if alpha > 1.0:
            alpha /= 100.0
        alpha = max(0.0, min(1.0, alpha))
        self.opacity = alpha
        self.widget.set_opacity(alpha)
        return self

    def get_opacity(self):
        return self.opacity

    def hide(self):
        self.widget.set_visible(False)
        return self

    def show(self):
        self.widget.set_visible(True)
        return self

    def set_visible(self, visible: bool):
        self.widget.set_visible(bool(visible))
        return self

    def is_visible(self):
        return bool(self.widget.get_visible())

    def remove(self):
        if self._removed:
            return False
        self.game._remove_widget_from_parent(self.widget)
        self._removed = True
        try:
            self.game._mod_image_widgets.remove(self)
        except Exception:
            pass
        return True

class ModSpriteHandle(ModImageHandle):
    """Absolute-position image handle for mod-created moving sprites."""

    def __init__(self, game, sprite_id, widget, owner, image_path="", x=0, y=0, width=100, height=100):
        super().__init__(game, widget, owner, image_path=image_path, width=width, height=height)
        self.sprite_id = sprite_id
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.rotation = 0.0
        self._pixbuf = None
        self._surface = None
        self._draw_logged = False
        self._canvas_width = int(width)
        self._canvas_height = int(height)
        self._attached = False

    def _refresh_canvas_size(self):
        diagonal = int(math.ceil(math.sqrt((self.width or 1) ** 2 + (self.height or 1) ** 2)))
        self._canvas_width = max(1, diagonal)
        self._canvas_height = max(1, diagonal)
        if hasattr(self.widget, "set_content_width"):
            self.widget.set_content_width(self._canvas_width)
        if hasattr(self.widget, "set_content_height"):
            self.widget.set_content_height(self._canvas_height)
        self.widget.set_size_request(self._canvas_width, self._canvas_height)

    def _canvas_pos(self):
        return (
            self.x - ((self._canvas_width - self.width) / 2.0),
            self.y - ((self._canvas_height - self.height) / 2.0),
        )

    def set_image(self, image_path: str):
        if self._removed:
            return False
        return self.game._set_sprite_image(self, image_path)

    def set_size(self, width=None, height=None, size=None):
        super().set_size(width=width, height=height, size=size)
        self._refresh_canvas_size()
        if self._attached and hasattr(self.game, "_sprite_layer"):
            canvas_x, canvas_y = self._canvas_pos()
            self.game._sprite_layer.move(self.widget, canvas_x, canvas_y)
        self.widget.queue_draw()
        return self

    def set_rotation(self, angle):
        try:
            self.rotation = float(angle) % 360.0
        except Exception:
            self.rotation = 0.0
        self.widget.queue_draw()
        return self

    def get_rotation(self):
        return self.rotation

    def rotate_by(self, delta):
        return self.set_rotation(self.rotation + float(delta))

    def move_to(self, x, y):
        self.x = float(x)
        self.y = float(y)
        if self._attached and hasattr(self.game, "_sprite_layer"):
            canvas_x, canvas_y = self._canvas_pos()
            self.game._sprite_layer.move(self.widget, canvas_x, canvas_y)
        return self

    def set_pos(self, x, y):
        return self.move_to(x, y)

    def move_by(self, dx, dy):
        return self.move_to(self.x + float(dx), self.y + float(dy))

    def get_pos(self):
        return self.x, self.y

    def get_x(self):
        return self.x

    def get_y(self):
        return self.y

    def set_x(self, x):
        return self.move_to(x, self.y)

    def set_y(self, y):
        return self.move_to(self.x, y)

    def set_velocity(self, vx, vy):
        self.vx = float(vx)
        self.vy = float(vy)
        return self

    def get_velocity(self):
        return self.vx, self.vy

    def step(self, seconds=1.0):
        return self.move_by(self.vx * float(seconds), self.vy * float(seconds))

    def get_window_bounds(self):
        # Do not use Gtk.Fixed's allocation as the movement boundary. A
        # Gtk.Fixed can grow to include children moved outside the visible
        # window, which makes the boundary chase the sprite forever.
        overlay = getattr(self.game, "_window_overlay", None)
        if overlay is not None:
            width = int(overlay.get_allocated_width())
            height = int(overlay.get_allocated_height())
        else:
            width = int(self.game.get_allocated_width())
            height = int(self.game.get_allocated_height())

        if width <= 0 or height <= 0:
            return {"width": 0, "height": 0}

        return {"width": width, "height": height}

    def get_bounds(self):
        window = self.get_window_bounds()
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "right": self.x + self.width,
            "bottom": self.y + self.height,
            "window_width": window["width"],
            "window_height": window["height"],
        }

    def get_edge_hit(self, margin=0):
        margin = max(0.0, float(margin))
        bounds = self.get_bounds()
        window_width = bounds["window_width"]
        window_height = bounds["window_height"]
        left = bounds["x"] <= margin
        top = bounds["y"] <= margin
        right = window_width > 0 and bounds["right"] >= window_width - margin
        bottom = window_height > 0 and bounds["bottom"] >= window_height - margin
        return {
            "left": left,
            "right": right,
            "top": top,
            "bottom": bottom,
            "horizontal": left or right,
            "vertical": top or bottom,
        }

    def get_corner_hit(self, margin=0):
        edges = self.get_edge_hit(margin)
        if edges["top"] and edges["left"]:
            return "top-left"
        if edges["top"] and edges["right"]:
            return "top-right"
        if edges["bottom"] and edges["left"]:
            return "bottom-left"
        if edges["bottom"] and edges["right"]:
            return "bottom-right"
        return None

    def is_touching_corner(self, margin=0):
        return self.get_corner_hit(margin) is not None

    def bounce(self, vx=None, vy=None, margin=0):
        if vx is None:
            vx = self.vx
        if vy is None:
            vy = self.vy
        vx = float(vx)
        vy = float(vy)
        margin = max(0.0, float(margin))

        # Mods can start their timers before GTK has allocated the window.
        # Waiting here prevents sprites from moving into nowhere during startup.
        initial_bounds = self.get_bounds()
        if initial_bounds["window_width"] <= 0 or initial_bounds["window_height"] <= 0:
            return {
                "vx": self.vx,
                "vy": self.vy,
                "edges": {
                    "left": False,
                    "right": False,
                    "top": False,
                    "bottom": False,
                    "horizontal": False,
                    "vertical": False,
                },
                "corner": None,
            }

        self.move_by(vx, vy)
        bounds = self.get_bounds()
        edge_hit = self.get_edge_hit(margin)

        max_x = max(margin, bounds["window_width"] - self.width - margin)
        max_y = max(margin, bounds["window_height"] - self.height - margin)
        new_x = self.x
        new_y = self.y

        if edge_hit["left"] and vx < 0:
            vx = abs(vx)
            new_x = margin
        elif edge_hit["right"] and vx > 0:
            vx = -abs(vx)
            new_x = max_x

        if edge_hit["top"] and vy < 0:
            vy = abs(vy)
            new_y = margin
        elif edge_hit["bottom"] and vy > 0:
            vy = -abs(vy)
            new_y = max_y

        self.vx = vx
        self.vy = vy
        self.move_to(new_x, new_y)
        return {
            "vx": self.vx,
            "vy": self.vy,
            "edges": edge_hit,
            "corner": self.get_corner_hit(margin),
        }

    def bounce_velocity(self, vx=None, vy=None, margin=0):
        return self.bounce(vx=vx, vy=vy, margin=margin)

    def remove(self):
        removed = super().remove()
        self.game._mod_sprites.pop(self.sprite_id, None)
        try:
            self.game._pending_sprites.remove(self)
        except Exception:
            pass
        return removed


class ModDrawLayerHandle:
    """A mod-owned Cairo overlay with one optional frame-clock callback."""

    def __init__(self, game, layer_id, widget, owner, draw_callback=None):
        self.game = game
        self.layer_id = layer_id
        self.widget = widget
        self.owner = owner
        self._draw_callback = draw_callback
        self._animation_callback = None
        self._tick_callback_id = None
        self._last_frame_time = None
        self._queue_draw_each_frame = True
        self._attached = False
        self._removed = False
        self._draw_error_logged = False

    def get_widget(self):
        return self.widget

    def get_width(self):
        return int(self.widget.get_allocated_width())

    def get_height(self):
        return int(self.widget.get_allocated_height())

    def get_size(self):
        return self.get_width(), self.get_height()

    def set_draw_callback(self, callback):
        if callback is not None and not callable(callback):
            raise ValueError("set_draw_callback() requires a callable or None")
        self._draw_callback = callback
        self._draw_error_logged = False
        self.queue_draw()
        return self

    def queue_draw(self):
        if not self._removed:
            self.widget.queue_draw()
        return self

    def show(self):
        if not self._removed:
            self.widget.set_visible(True)
        return self

    def hide(self):
        if not self._removed:
            self.widget.set_visible(False)
        return self

    def set_visible(self, visible):
        return self.show() if visible else self.hide()

    def is_visible(self):
        return not self._removed and bool(self.widget.get_visible())

    def _draw(self, _area, cr, width, height):
        callback = self._draw_callback
        if self._removed or not callable(callback):
            return
        try:
            self.game._run_with_mod_owner(self.owner, callback, self, cr, width, height)
        except Exception as exc:
            if not self._draw_error_logged:
                print(f"[rendering] Draw layer '{self.layer_id}' failed: {exc}")
                self._draw_error_logged = True

    def start_animation(self, callback, queue_draw=True):
        """Run callback(layer, delta_seconds, frame_time_seconds) each GTK frame."""
        if not callable(callback):
            raise ValueError("start_animation() requires a callable callback")
        self.stop_animation()
        self._animation_callback = callback
        self._queue_draw_each_frame = bool(queue_draw)
        self._last_frame_time = None

        def _tick(_widget, frame_clock):
            if self._removed or not callable(self._animation_callback):
                self._tick_callback_id = None
                return False
            frame_time = float(frame_clock.get_frame_time()) / 1_000_000.0
            if self._last_frame_time is None:
                delta = 0.0
            else:
                delta = max(0.0, min(0.1, frame_time - self._last_frame_time))
            self._last_frame_time = frame_time
            try:
                result = self.game._run_with_mod_owner(
                    self.owner,
                    self._animation_callback,
                    self,
                    delta,
                    frame_time,
                )
            except Exception as exc:
                print(f"[rendering] Animation for layer '{self.layer_id}' failed: {exc}")
                result = False
            if result is False:
                self._animation_callback = None
                self._tick_callback_id = None
                return False
            if self._queue_draw_each_frame:
                self.widget.queue_draw()
            return True

        self._tick_callback_id = self.widget.add_tick_callback(_tick)
        self.queue_draw()
        return self

    def stop_animation(self):
        callback_id = self._tick_callback_id
        self._tick_callback_id = None
        self._animation_callback = None
        self._last_frame_time = None
        if callback_id is not None:
            try:
                self.widget.remove_tick_callback(callback_id)
            except Exception:
                pass
        return self

    def remove(self):
        if self._removed:
            return False
        self.stop_animation()
        self.game._remove_widget_from_parent(self.widget)
        self.game._mod_draw_layers.pop(self.layer_id, None)
        try:
            self.game._pending_draw_layers.remove(self)
        except ValueError:
            pass
        self._attached = False
        self._removed = True
        return True


class RenderingMixin:
    def _normalize_image_size(self, size=None, width=None, height=None, default_width=100, default_height=100):
        if size is not None:
            try:
                width = size[0]
                height = size[1]
            except Exception:
                width = size
                height = size
        if width is None and height is None:
            width = default_width
            height = default_height
        elif width is None:
            width = height
        elif height is None:
            height = width
        try:
            width = int(float(width))
        except Exception:
            width = int(default_width or 100)
        try:
            height = int(float(height))
        except Exception:
            height = int(default_height or width or 100)
        return max(1, width), max(1, height)

    def _normalize_position(self, pos=None, x=None, y=None):
        if pos is not None:
            try:
                x = pos[0]
                y = pos[1]
            except Exception:
                pass
        try:
            x = float(0 if x is None else x)
        except Exception:
            x = 0.0
        try:
            y = float(0 if y is None else y)
        except Exception:
            y = 0.0
        return x, y

    def resolve_asset_path(self, path: str, owner=None) -> str:
        """Resolve app or mod assets. Relative mod paths check the mod folder first."""
        raw_path = str(path or "").strip()
        if not raw_path:
            return raw_path
        expanded = os.path.expanduser(raw_path)
        if os.path.isabs(expanded):
            return expanded

        candidates = []
        mod_dir = None
        current = getattr(self, "_current_mod_info", None)
        if current is not None and (owner is None or current.get("id") == owner):
            mod_dir = current.get("path")
        if mod_dir is None and owner:
            mod_dir = self._mod_paths.get(owner)
        if mod_dir:
            candidates.extend([
                os.path.join(mod_dir, expanded),
                os.path.join(mod_dir, "assets", expanded),
            ])

        app_asset = find_app_asset(expanded)
        candidates.extend([
            os.path.join(os.getcwd(), expanded),
            app_asset,
        ])

        seen = set()
        for candidate in candidates:
            norm = os.path.normcase(os.path.abspath(candidate))
            if norm in seen:
                continue
            seen.add(norm)
            if os.path.exists(candidate):
                return candidate
        return candidates[0] if candidates else expanded

    def resolve_mod_asset_path(self, path: str, owner=None) -> str:
        return self.resolve_asset_path(path, owner=owner)

    def _set_picture_image(self, picture, image_path: str, owner=None, handle=None):
        resolved_path = self.resolve_asset_path(image_path, owner=owner)
        try:
            texture = Gdk.Texture.new_from_filename(resolved_path)
            picture.set_paintable(texture)
        except Exception as exc:
            print(f"[images] Failed to load image '{resolved_path}': {exc}")
            return False
        if handle is not None:
            handle.image_path = resolved_path
        return True

    def _set_sprite_image(self, sprite, image_path: str):
        resolved_path = self.resolve_asset_path(image_path, owner=sprite.owner)

        # Prefer a native PyCairo surface for PNG sprites. This avoids depending
        # on the GdkPixbuf-to-Cairo bridge at draw time, which can be fragile in
        # frozen Windows builds even when both libraries are present.
        sprite._surface = None
        sprite._pixbuf = None
        sprite._draw_logged = False

        if resolved_path.lower().endswith(".png"):
            try:
                sprite._surface = cairo.ImageSurface.create_from_png(resolved_path)
            except Exception as exc:
                print(f"[images] Failed to load PNG sprite image '{resolved_path}': {exc}")
                return False
        else:
            if GdkPixbuf is None:
                print("[images] Non-PNG sprites require GdkPixbuf, which is not available.")
                return False
            try:
                sprite._pixbuf = GdkPixbuf.Pixbuf.new_from_file(resolved_path)
            except Exception as exc:
                print(f"[images] Failed to load sprite image '{resolved_path}': {exc}")
                return False

        sprite.image_path = resolved_path
        sprite.widget.queue_draw()
        return True

    def _draw_sprite(self, sprite, cr, allocated_width, allocated_height):
        surface = getattr(sprite, "_surface", None)
        pixbuf = getattr(sprite, "_pixbuf", None)
        if surface is None and pixbuf is None:
            return

        width = max(1, int(sprite.width or allocated_width or 1))
        height = max(1, int(sprite.height or allocated_height or 1))

        if surface is not None:
            source_width = max(1, int(surface.get_width()))
            source_height = max(1, int(surface.get_height()))
        else:
            source_width = max(1, int(pixbuf.get_width()))
            source_height = max(1, int(pixbuf.get_height()))

        cr.save()
        cr.translate(allocated_width / 2.0, allocated_height / 2.0)
        angle = float(getattr(sprite, "rotation", 0.0) or 0.0)
        if angle:
            cr.rotate(math.radians(angle))
        cr.scale(width / source_width, height / source_height)

        if surface is not None:
            cr.set_source_surface(surface, -source_width / 2.0, -source_height / 2.0)
        else:
            Gdk.cairo_set_source_pixbuf(
                cr,
                pixbuf,
                -source_width / 2.0,
                -source_height / 2.0,
            )

        cr.paint()
        cr.restore()

    def _make_mod_sprite(self, image_path, width, height, owner, x=0, y=0, tooltip=None, visible=True):
        area = Gtk.DrawingArea()
        area.set_content_width(width)
        area.set_content_height(height)
        area.set_size_request(width, height)
        area.set_visible(bool(visible))
        area.set_can_target(False)
        if tooltip:
            area.set_tooltip_text(str(tooltip))

        sprite_id = f"{owner}:sprite_{self._next_sprite_id}"
        self._next_sprite_id += 1
        sprite = ModSpriteHandle(self, sprite_id, area, owner, image_path=image_path, x=x, y=y, width=width, height=height)
        sprite._refresh_canvas_size()
        area.set_draw_func(lambda _area, cr, draw_width, draw_height, handle=sprite: self._draw_sprite(handle, cr, draw_width, draw_height))
        self._set_sprite_image(sprite, image_path)
        return sprite

    def _content_fit_from_name(self, fit):
        fit_name = str(fit or "contain").strip().lower()
        if fit_name == "cover" and hasattr(Gtk.ContentFit, "COVER"):
            return Gtk.ContentFit.COVER
        if fit_name == "fill" and hasattr(Gtk.ContentFit, "FILL"):
            return Gtk.ContentFit.FILL
        if fit_name in ("scale-down", "scale_down") and hasattr(Gtk.ContentFit, "SCALE_DOWN"):
            return Gtk.ContentFit.SCALE_DOWN
        return Gtk.ContentFit.CONTAIN

    def _make_mod_picture(self, image_path, width, height, owner, tooltip=None, visible=True, fit="contain"):
        picture = Gtk.Picture()
        picture.set_can_shrink(True)
        picture.set_content_fit(self._content_fit_from_name(fit))
        picture.set_size_request(width, height)
        picture.set_visible(bool(visible))
        if tooltip:
            picture.set_tooltip_text(str(tooltip))
        self._set_picture_image(picture, image_path, owner=owner)
        return picture

    def _track_mod_image(self, handle):
        if handle not in self._mod_image_widgets:
            self._mod_image_widgets.append(handle)

    def _append_or_queue_image(self, tab_id: str, handle):
        page = self._tab_pages.get(tab_id)
        if page is not None:
            page.append(handle.widget)
        else:
            self._pending_images.setdefault(tab_id, []).append(handle)

    def add_image(self, tab_id: str, image_path: str, size=None, width=None, height=None, tooltip=None, expand=False, fit="contain"):
        """Add an image to a normal GTK tab layout and return a handle.

        Relative paths are resolved from the current mod folder, then the mod's
        assets folder, then the app assets.
        """
        owner = self._current_mod_namespace()
        width, height = self._normalize_image_size(size=size, width=width, height=height, default_width=128, default_height=128)
        picture = self._make_mod_picture(image_path, width, height, owner, tooltip=tooltip, visible=True, fit=fit)
        picture.set_hexpand(bool(expand))
        handle = ModImageHandle(self, picture, owner, width=width, height=height)
        handle.image_path = self.resolve_asset_path(image_path, owner=owner)
        self._track_mod_image(handle)
        self._append_or_queue_image(str(tab_id), handle)
        return handle

    def _attach_sprite(self, sprite):
        if not hasattr(self, "_sprite_layer"):
            if sprite not in self._pending_sprites:
                self._pending_sprites.append(sprite)
            return
        if sprite._attached:
            return
        canvas_x, canvas_y = sprite._canvas_pos()
        self._sprite_layer.put(sprite.widget, canvas_x, canvas_y)
        sprite._attached = True

    def create_image(
        self,
        image_path: str,
        size=(100, 100),
        pos=(0, 0),
        tab_id=None,
        width=None,
        height=None,
        x=None,
        y=None,
        tooltip=None,
        visible=True,
        fit="contain",
        layer="window",
    ):
        """Create a free-positioned image sprite, or add a layout image if tab_id is set."""
        if tab_id is not None:
            return self.add_image(tab_id, image_path, size=size, width=width, height=height, tooltip=tooltip, fit=fit)

        owner = self._current_mod_namespace()
        width, height = self._normalize_image_size(size=size, width=width, height=height)
        x, y = self._normalize_position(pos=pos, x=x, y=y)
        sprite = self._make_mod_sprite(image_path, width, height, owner, x=x, y=y, tooltip=tooltip, visible=visible)
        self._mod_sprites[sprite.sprite_id] = sprite
        self._attach_sprite(sprite)
        return sprite

    def create_sprite(self, *args, **kwargs):
        return self.create_image(*args, **kwargs)

    def get_sprite(self, sprite_id):
        return self._mod_sprites.get(str(sprite_id))

    def _coerce_image_handle(self, image):
        if isinstance(image, (ModImageHandle, ModSpriteHandle)):
            return image
        if isinstance(image, str):
            return self._mod_sprites.get(image)
        return None

    def hide_image(self, image):
        handle = self._coerce_image_handle(image)
        if handle is None:
            return False
        handle.hide()
        return True

    def show_image(self, image):
        handle = self._coerce_image_handle(image)
        if handle is None:
            return False
        handle.show()
        return True

    def remove_image(self, image):
        handle = self._coerce_image_handle(image)
        if handle is None:
            return False
        return handle.remove()

    def _attach_draw_layer(self, layer):
        if not hasattr(self, "_window_overlay"):
            if layer not in self._pending_draw_layers:
                self._pending_draw_layers.append(layer)
            return
        if layer._attached or layer._removed:
            return
        self._window_overlay.add_overlay(layer.widget)
        layer._attached = True

    def create_draw_layer(self, draw_callback=None, name=None, visible=True, can_target=False):
        """Create one full-window Cairo overlay for efficient mod rendering.

        The draw callback receives ``(layer, cairo_context, width, height)``.
        Use ``layer.start_animation(callback)`` for one frame-clock callback;
        the animation callback receives ``(layer, delta_seconds, frame_time)``.
        """
        if draw_callback is not None and not callable(draw_callback):
            raise ValueError("create_draw_layer() requires a callable draw_callback or None")

        owner = self._current_mod_namespace()
        if name is None or not str(name).strip():
            name = f"draw_layer_{self._next_draw_layer_id}"
            self._next_draw_layer_id += 1
        safe_name = str(name).strip().lower().replace(" ", "_")
        layer_id = f"{owner}:{safe_name}"
        if layer_id in self._mod_draw_layers:
            raise ValueError(f"Draw layer '{layer_id}' already exists")

        area = Gtk.DrawingArea()
        area.set_hexpand(True)
        area.set_vexpand(True)
        area.set_halign(Gtk.Align.FILL)
        area.set_valign(Gtk.Align.FILL)
        area.set_can_target(bool(can_target))
        area.set_visible(bool(visible))

        layer = ModDrawLayerHandle(self, layer_id, area, owner, draw_callback)
        area.set_draw_func(layer._draw)
        self._mod_draw_layers[layer_id] = layer
        self._attach_draw_layer(layer)
        return layer

    def create_canvas(self, *args, **kwargs):
        return self.create_draw_layer(*args, **kwargs)

    def get_draw_layer(self, layer_id):
        key = str(layer_id or "").strip()
        if key in self._mod_draw_layers:
            return self._mod_draw_layers[key]
        if ":" not in key:
            return self._mod_draw_layers.get(f"{self._current_mod_namespace()}:{key}")
        return None

    def remove_draw_layer(self, layer):
        if isinstance(layer, str):
            layer = self.get_draw_layer(layer)
        if not isinstance(layer, ModDrawLayerHandle):
            return False
        return layer.remove()
