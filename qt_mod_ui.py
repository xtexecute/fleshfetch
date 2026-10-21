"""Toolkit-independent mod UI for the Qt frontend.

Put QtModUiMixin before ModApiMixin/ModManagerMixin in the game's MRO and call
init_qt_mod_ui() once, before registering mods. The host supplies
_notify_catalog(), _notify_live(), _current_mod_namespace(),
_run_with_mod_owner(owner, callback, *args), _mod_paths and _current_mod_info.

qt_mod_ui_snapshot() returns JSON-compatible {tabs: [...], buttons: [...],
images: [...]}. Every record has id/owner/visible; tab records include label
and ordered items ({type, id}); labels are inline {type, text, owner} items.
Buttons include tab_id/label/sensitive/tooltip/sprites (state -> file URI).
Images include tab_id (null for overlays), kind, source (file URI), x/y,
width/height, rotation/opacity, vx/vy, tooltip/fit/expand. No callbacks or
handles cross the serialization boundary. All snapshots are detached copies.

QML dispatches clicks through activate_qt_button(id). Its 16 ms motion timer
calls advance_qt_mod_ui(0.016), enabled by has_qt_mod_motion(). Motion emits
one live notification per frame; structural/control edits notify the catalog.
Overlay image edits notify live state; tab image edits notify the catalog.
Hosts may use the same snapshot for both notifications. No timer is started
here. Refresh the timer enabled state after either notification. A backend
which already calls SpriteHandle.step() must not also advance_qt_mod_ui().

Compatibility: handles are NOT widgets. Gtk.Box pages, append(Gtk.*),
get_widget(), widget signals, CSS and Cairo drawing are unsupported. Use
TabHandle.add_label/add_button and the image APIs instead. Image loading and
decode failures belong to the frontend; set_image stores a resolved path.
Like rendering.py, non-None size/pos take precedence over width/height/x/y;
pass size=None or pos=None to use the individual arguments. bounce() moves by
velocity per call; step(seconds) and the frontend timer use pixels/second.
Do not also step a velocity-driven image from a mod timer unless intentional.
"""

from __future__ import annotations

import os
import re
import base64
import json
from pathlib import Path


class QtModCompatibilityError(TypeError):
    """A mod requested a toolkit-specific UI operation."""


def _file_uri(path):
    return Path(path).absolute().as_uri() if path else ""


class _Handle:
    def __init__(self, game, handle_id, owner):
        self.game, self.id, self.owner = game, handle_id, owner
        self.visible = True
        self._removed = False

    def _changed(self):
        if not self._removed:
            self.game._notify_catalog()
        return self

    def set_visible(self, visible):
        self.visible = bool(visible)
        return self._changed()

    def show(self):
        return self.set_visible(True)

    def hide(self):
        return self.set_visible(False)

    def is_visible(self):
        return self.visible and not self._removed

    get_visible = is_visible

    def _snapshot(self):
        return {"id": self.id, "owner": self.owner, "visible": self.is_visible()}


class TabHandle(_Handle):
    def __init__(self, game, tab_id, label, owner):
        super().__init__(game, tab_id, owner)
        self.tab_id, self.label = tab_id, str(label)
        self._items = []

    def add_label(self, text):
        if self._removed:
            raise ValueError("Cannot add content to a removed tab")
        self._items.append({"type": "label", "text": str(text),
                            "owner": self.game._current_mod_namespace()})
        self._changed()
        return self

    def add_button(self, label, callback):
        if self._removed:
            raise ValueError("Cannot add content to a removed tab")
        return self.game.add_tab_button(self.id, label, callback)

    def set_theme(self, colors=None, **kwargs):
        self.game.set_tab_theme(self.id, colors, **kwargs)
        return self

    def append(self, child):
        self.game._legacy_page(self.id).append(child)

    def get_first_child(self):
        return self.game._legacy_page(self.id).get_first_child()

    def remove_child(self, child):
        self.game._legacy_page(self.id).remove(child)

    def set_child(self, child):
        self.game._legacy_page(self.id).set_child(child)

    def set_spacing(self, spacing):
        self.game._legacy_page(self.id).set_spacing(spacing)

    def set_margin_top(self, value):
        self.game._legacy_page(self.id).set_margin_top(value)

    def set_margin_bottom(self, value):
        self.game._legacy_page(self.id).set_margin_bottom(value)

    def set_margin_start(self, value):
        self.game._legacy_page(self.id).set_margin_start(value)

    def set_margin_end(self, value):
        self.game._legacy_page(self.id).set_margin_end(value)

    def remove(self, child=None):
        if child is not None:
            return self.remove_child(child)
        return self.game._remove_tab_page(self.id) if not self._removed else False

    def to_dict(self):
        return dict(self._snapshot(), label=self.label,
                    items=[dict(item) for item in self._items])


class ButtonHandle(_Handle):
    def __init__(self, game, button_id, tab_id, label, callback, owner):
        super().__init__(game, button_id, owner)
        self.tab_id, self.label, self.callback = tab_id, str(label), callback
        self.sensitive, self.tooltip, self.sprites = True, "", {}
        self.sprite_border = {side: 8 for side in ("left", "top", "right", "bottom")}

    def set_label(self, label):
        self.label = str(label)
        return self._changed()

    def get_label(self):
        return self.label

    def set_sensitive(self, sensitive):
        self.sensitive = bool(sensitive)
        return self._changed()

    def get_sensitive(self):
        return self.sensitive

    def set_tooltip_text(self, text):
        self.tooltip = str(text or "")
        return self._changed()

    def set_sprite(self, path, hover=None, pressed=None, disabled=None):
        self.sprites = {state: self.game.resolve_asset_path(value, owner=self.owner)
                        for state, value in (("normal", path), ("hover", hover),
                                             ("pressed", pressed), ("disabled", disabled))
                        if value is not None}
        return self._changed()

    def set_sprites(self, sprites):
        states = dict(sprites)
        sheet = states.pop("sheet", None)
        border = states.pop("border", 8)
        sides = ("left", "top", "right", "bottom")
        borders = dict.fromkeys(sides, border) if isinstance(border, int) else dict(border)
        if set(borders) != set(sides) or any(type(v) is not int or v < 0 for v in borders.values()):
            raise ValueError("Sprite border must be a nonnegative integer or left/top/right/bottom mapping")
        if set(states) - {"normal", "hover", "pressed", "disabled"}:
            raise ValueError("Unknown button sprite state")
        resolved = {}
        for state, value in states.items():
            if sheet:
                if not isinstance(value, (list, tuple)) or len(value) != 4 or any(type(v) is not int for v in value):
                    raise ValueError("Spritesheet states must be [x, y, width, height]")
                x, y, width, height = value
                if min(x, y) < 0 or width <= 0 or height <= 0:
                    raise ValueError("Invalid spritesheet region")
                if borders["left"] + borders["right"] > width or borders["top"] + borders["bottom"] > height:
                    raise ValueError("Nine-slice borders exceed sprite region")
                payload = json.dumps([self.game.resolve_asset_path(sheet, owner=self.owner), list(value)])
                resolved[state] = "image://skins/sprite/" + base64.urlsafe_b64encode(payload.encode()).decode()
            else:
                resolved[state] = self.game.resolve_asset_path(value, owner=self.owner)
        self.sprites, self.sprite_border = resolved, borders
        return self._changed()

    def click(self):
        if self._removed or not self.visible or not self.sensitive:
            return False
        tab = self.game._qt_tabs.get(self.tab_id)
        if tab is not None and not tab.is_visible():
            return False
        self.game._run_with_mod_owner(self.owner, self.callback, self)
        return True

    activate = click

    def remove(self):
        if self._removed:
            return False
        self._removed = True
        self.callback = None
        self.game._qt_buttons.pop(self.id, None)
        self.game._mod_button_widgets[:] = [item for item in self.game._mod_button_widgets
                                             if item.get("widget") is not self]
        self.game._forget_qt_item(self)
        self.game._notify_catalog()
        return True

    def to_dict(self):
        return dict(self._snapshot(), tab_id=self.tab_id, label=self.label,
                    sensitive=self.sensitive, tooltip=self.tooltip,
                    spriteBorder=dict(self.sprite_border),
                    sprites={k: v if v.startswith("image://") else _file_uri(v) for k, v in self.sprites.items()})


class ImageHandle(_Handle):
    """Plain image state; coordinates refer to the unrotated top-left corner."""

    kind = "image"

    def __init__(self, game, image_id, owner, image_path, width, height,
                 x=0, y=0, tab_id=None, tooltip=None, visible=True,
                 fit="contain", expand=False):
        super().__init__(game, image_id, owner)
        self.image_path = game.resolve_asset_path(image_path, owner=owner)
        self.width, self.height = width, height
        self.x, self.y = float(x), float(y)
        self.vx = self.vy = self.rotation = 0.0
        self._manual_motion = False
        self.opacity = 1.0
        self.tab_id, self.tooltip = tab_id, str(tooltip or "")
        self.visible, self.fit, self.expand = bool(visible), str(fit), bool(expand)

    def _changed(self):
        if not self._removed:
            if self.tab_id is None:
                getattr(self.game, "_notify_sprites", self.game._notify_live)()
            else:
                self.game._notify_catalog()
        return self

    def set_image(self, image_path: str):
        if self._removed:
            return False
        self.image_path = self.game.resolve_asset_path(image_path, owner=self.owner)
        self._changed()
        return True

    def set_size(self, width=None, height=None, size=None):
        self.width, self.height = self.game._normalize_image_size(
            size, width, height, self.width, self.height)
        return self._changed()

    def get_size(self):
        return self.width, self.height

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def set_opacity(self, alpha):
        try:
            alpha = float(alpha)
        except (TypeError, ValueError):
            alpha = 1.0
        if alpha > 1:
            alpha /= 100.0
        self.opacity = max(0.0, min(1.0, alpha))
        return self._changed()

    def get_opacity(self):
        return self.opacity

    def set_rotation(self, angle):
        try:
            self.rotation = float(angle) % 360.0
        except (TypeError, ValueError):
            self.rotation = 0.0
        return self._changed()

    def get_rotation(self):
        return self.rotation

    def rotate_by(self, delta):
        return self.set_rotation(self.rotation + float(delta))

    def set_tooltip_text(self, text):
        self.tooltip = str(text or "")
        return self._changed()

    def move_to(self, x, y):
        self.x, self.y = float(x), float(y)
        return self._changed()

    set_pos = move_to

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
        self.vx, self.vy = float(vx), float(vy)
        return self._changed()

    def get_velocity(self):
        return self.vx, self.vy

    def step(self, seconds=1.0):
        self._manual_motion = True
        return self.move_by(self.vx * float(seconds), self.vy * float(seconds))

    def set_auto_motion(self, enabled=True):
        self._manual_motion = not bool(enabled)
        return self._changed()

    def get_window_bounds(self):
        width, height = int(self.game._qt_view_width), int(self.game._qt_view_height)
        return {"width": width, "height": height} if width > 0 and height > 0 else {"width": 0, "height": 0}

    def get_bounds(self):
        window = self.get_window_bounds()
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height,
                "right": self.x + self.width, "bottom": self.y + self.height,
                "window_width": window["width"], "window_height": window["height"]}

    def get_edge_hit(self, margin=0):
        margin, b = max(0.0, float(margin)), self.get_bounds()
        left, top = b["x"] <= margin, b["y"] <= margin
        right = b["window_width"] > 0 and b["right"] >= b["window_width"] - margin
        bottom = b["window_height"] > 0 and b["bottom"] >= b["window_height"] - margin
        return {"left": left, "right": right, "top": top, "bottom": bottom,
                "horizontal": left or right, "vertical": top or bottom}

    def get_corner_hit(self, margin=0):
        edges = self.get_edge_hit(margin)
        for vertical, horizontal in (("top", "left"), ("top", "right"),
                                     ("bottom", "left"), ("bottom", "right")):
            if edges[vertical] and edges[horizontal]:
                return vertical + "-" + horizontal
        return None

    def is_touching_corner(self, margin=0):
        return self.get_corner_hit(margin) is not None

    def bounce(self, vx=None, vy=None, margin=0):
        self._manual_motion = True
        vx, vy = float(self.vx if vx is None else vx), float(self.vy if vy is None else vy)
        margin, window = max(0.0, float(margin)), self.get_window_bounds()
        if not window["width"] or not window["height"]:
            return {"vx": self.vx, "vy": self.vy, "corner": None,
                    "edges": dict.fromkeys(("left", "right", "top", "bottom", "horizontal", "vertical"), False)}
        self.x += vx
        self.y += vy
        edges = self.get_edge_hit(margin)
        if edges["left"] and vx < 0:
            vx, self.x = abs(vx), margin
        elif edges["right"] and vx > 0:
            vx, self.x = -abs(vx), max(margin, window["width"] - self.width - margin)
        if edges["top"] and vy < 0:
            vy, self.y = abs(vy), margin
        elif edges["bottom"] and vy > 0:
            vy, self.y = -abs(vy), max(margin, window["height"] - self.height - margin)
        self.vx, self.vy = vx, vy
        self._changed()
        return {"vx": vx, "vy": vy, "edges": edges, "corner": self.get_corner_hit(margin)}

    bounce_velocity = bounce

    def remove(self):
        if self._removed:
            return False
        self._removed = True
        self.game._qt_images.pop(self.id, None)
        self.game._mod_sprites.pop(self.id, None)
        if self in self.game._mod_image_widgets:
            self.game._mod_image_widgets.remove(self)
        self.game._forget_qt_item(self)
        self.game._notify_catalog()
        return True

    def to_dict(self):
        return dict(self._snapshot(), kind=self.kind, tab_id=self.tab_id,
                    source=_file_uri(self.image_path), x=self.x, y=self.y,
                    width=self.width, height=self.height, rotation=self.rotation,
                    opacity=self.opacity, vx=self.vx, vy=self.vy,
                    tooltip=self.tooltip, fit=self.fit, expand=self.expand)


class SpriteHandle(ImageHandle):
    kind = "sprite"

    @property
    def sprite_id(self):
        return self.id


class QtModUiMixin:
    def init_qt_mod_ui(self):
        self._qt_tabs, self._qt_buttons, self._qt_images = {}, {}, {}
        self._qt_next_id = 1
        self._qt_view_width = self._qt_view_height = 0
        self._tab_pages, self._mod_tab_owners = {}, {}
        self._mod_button_widgets, self._mod_image_widgets, self._mod_sprites = [], [], {}
        self._pending_tabs, self._pending_buttons, self._pending_images = [], {}, {}
        self._pending_sprites, self._pending_draw_layers, self._mod_draw_layers = [], [], {}
        self._qt_items = {}
        self._qt_tab_themes = {}

    def set_tab_theme(self, tab, colors=None, **kwargs):
        """Override palette colors for any tab; None resets this owner's override."""
        tab = str(tab.id if isinstance(tab, TabHandle) else tab)
        owner = self._current_mod_namespace()
        palette = dict(colors or {}, **kwargs)
        allowed = {"canvas", "surface", "raised", "hover", "pressed", "text", "muted",
                   "line", "accent", "accentHover", "focus", "warning", "danger"}
        for key, value in palette.items():
            if key not in allowed:
                raise ValueError(f"Unknown theme color: {key}")
            if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                raise ValueError(f"Theme color '{key}' must use #RRGGBB")
        layers = self._qt_tab_themes.setdefault(tab, {})
        layers.pop(owner, None)
        if palette:
            layers[owner] = palette
        self._notify_catalog()

    def _qt_theme_snapshot(self):
        result = {}
        for tab, layers in self._qt_tab_themes.items():
            result[tab] = {}
            for palette in layers.values():
                result[tab].update(palette)
        return result

    def _reset_mod_registries(self):
        self._qt_tab_themes = {
            tab: {owner: colors for owner, colors in layers.items() if owner == "__global__"}
            for tab, layers in self._qt_tab_themes.items()}
        return super()._reset_mod_registries()

    def _qt_id(self, kind, owner):
        handle_id = f"{owner}:{kind}_{self._qt_next_id}"
        self._qt_next_id += 1
        return handle_id

    def _remember_qt_item(self, handle, kind):
        items = self._qt_items.setdefault(handle.tab_id, [])
        items.append({"type": kind, "id": handle.id})
        tab = self._qt_tabs.get(handle.tab_id)
        if tab is not None:
            tab._items = items

    def _forget_qt_item(self, handle):
        items = self._qt_items.get(handle.tab_id, [])
        items[:] = [item for item in items if item.get("id") != handle.id]

    def add_tab(self, tab_id: str, label: str, page_box=None):
        if page_box is not None:
            raise QtModCompatibilityError(
                "Qt add_tab() cannot accept a GTK page_box; omit page_box and use "
                "the returned TabHandle.add_label() / add_button() methods")
        tab_id = str(tab_id)
        if tab_id in self._qt_tabs:
            raise ValueError(f"Tab '{tab_id}' already exists")
        owner = self._current_mod_namespace()
        tab = TabHandle(self, tab_id, label, owner)
        tab._items = self._qt_items.setdefault(tab_id, [])
        self._qt_tabs[tab_id] = self._tab_pages[tab_id] = tab
        if owner != "__global__":
            self._mod_tab_owners[tab_id] = owner
        self._notify_catalog()
        return tab

    def add_tab_button(self, tab_id: str, label: str, callback):
        if not callable(callback):
            raise ValueError("add_tab_button() requires a callable callback")
        owner = self._current_mod_namespace()
        button = ButtonHandle(self, self._qt_id("button", owner), str(tab_id), label, callback, owner)
        self._qt_buttons[button.id] = button
        if owner != "__global__":
            self._mod_button_widgets.append({"owner": owner, "widget": button, "tab_id": button.tab_id})
        self._remember_qt_item(button, "button")
        self._notify_catalog()
        return button

    def add_button(self, button_id, label=None, callback=None, *, tab=None, text=None,
                   sprites=None, on_click=None):
        # Keep the original (tab_id, label, callback) calling convention.
        if tab is None:
            warn = getattr(self, "_add_mod_deprecation_warning", None)
            if warn:
                warn("add_button(tab_id, label, callback) is deprecated. Use add_tab_button() instead.")
            return self.add_tab_button(button_id, label, callback)
        owner = self._current_mod_namespace()
        handle_id = f"{owner}:{button_id}"
        if handle_id in self._qt_buttons:
            raise ValueError(f"Button '{button_id}' already exists for this mod")
        states = dict(sprites or {})
        if set(states) - {"normal", "hover", "pressed", "disabled", "sheet", "border"}:
            raise ValueError("Unknown button sprite state")
        handler = on_click if on_click is not None else callback
        button = self.add_tab_button(tab, text if text is not None else button_id, handler)
        old_id = button.id
        self._qt_buttons.pop(old_id)
        button.id = handle_id
        self._qt_buttons[handle_id] = button
        for item in self._qt_items[button.tab_id]:
            if item.get("id") == old_id:
                item["id"] = handle_id
        if states:
            try:
                button.set_sprites(states)
            except Exception:
                button.remove()
                raise
        return button

    def activate_qt_button(self, button_id):
        button = self._qt_buttons.get(str(button_id))
        return button.click() if button is not None else False

    def _remove_widget_from_parent(self, handle):
        return handle.remove() if handle is not None else False

    def _remove_tab_page(self, tab_id: str):
        tab_id = str(tab_id)
        tab = self._qt_tabs.pop(tab_id, None)
        existed = tab is not None or tab_id in self._qt_items
        if tab is not None:
            tab._removed = True
            tab._items.clear()
        for handle in list(self._qt_buttons.values()) + list(self._qt_images.values()):
            if handle.tab_id == tab_id:
                handle.remove()
        self._qt_items.pop(tab_id, None)
        self._tab_pages.pop(tab_id, None)
        self._mod_tab_owners.pop(tab_id, None)
        if existed:
            self._notify_catalog()
        return existed

    def _normalize_image_size(self, size=None, width=None, height=None, default_width=100, default_height=100):
        if size is not None:
            try:
                width, height = size[0], size[1]
            except (TypeError, IndexError, KeyError):
                width = height = size
        if width is None and height is None:
            width, height = default_width, default_height
        elif width is None:
            width = height
        elif height is None:
            height = width
        try:
            width = int(float(width))
        except (TypeError, ValueError, OverflowError):
            width = int(default_width or 100)
        try:
            height = int(float(height))
        except (TypeError, ValueError, OverflowError):
            height = int(default_height or width or 100)
        return max(1, width), max(1, height)

    def _normalize_position(self, pos=None, x=None, y=None):
        if pos is not None:
            try:
                x, y = pos[0], pos[1]
            except (TypeError, IndexError, KeyError):
                pass
        def number(value):
            try:
                return float(0 if value is None else value)
            except (TypeError, ValueError):
                return 0.0
        return number(x), number(y)

    def resolve_asset_path(self, path: str, owner=None) -> str:
        raw = str(path or "").strip()
        if not raw:
            return raw
        expanded = os.path.expanduser(raw)
        if os.path.isabs(expanded):
            return expanded
        from paths import find_app_asset

        current, mod_dir = getattr(self, "_current_mod_info", None), None
        if current is not None and (owner is None or current.get("id") == owner):
            mod_dir = current.get("path")
        if mod_dir is None and owner:
            mod_dir = self._mod_paths.get(owner)
        candidates = []
        if mod_dir:
            candidates.extend([os.path.join(mod_dir, expanded), os.path.join(mod_dir, "assets", expanded)])
        candidates.extend([os.path.join(os.getcwd(), expanded), find_app_asset(expanded)])
        seen = set()
        for candidate in candidates:
            norm = os.path.normcase(os.path.abspath(candidate))
            if norm not in seen and os.path.exists(candidate):
                return candidate
            seen.add(norm)
        return candidates[0]

    resolve_mod_asset_path = resolve_asset_path

    def add_image(self, tab_id: str, image_path: str, size=None, width=None, height=None,
                  tooltip=None, expand=False, fit="contain"):
        owner = self._current_mod_namespace()
        width, height = self._normalize_image_size(size, width, height, 128, 128)
        image = ImageHandle(self, self._qt_id("image", owner), owner, image_path,
                            width, height, tab_id=str(tab_id), tooltip=tooltip, fit=fit, expand=expand)
        self._qt_images[image.id] = image
        self._mod_image_widgets.append(image)
        self._remember_qt_item(image, "image")
        self._notify_catalog()
        return image

    def create_image(self, image_path: str, size=(100, 100), pos=(0, 0), tab_id=None,
                     width=None, height=None, x=None, y=None, tooltip=None,
                     visible=True, fit="contain", layer="window"):
        if tab_id is not None:
            return self.add_image(tab_id, image_path, size=size, width=width, height=height,
                                  tooltip=tooltip, fit=fit)
        owner = self._current_mod_namespace()
        width, height = self._normalize_image_size(size, width, height)
        x, y = self._normalize_position(pos, x, y)
        sprite = SpriteHandle(self, self._qt_id("sprite", owner), owner, image_path,
                              width, height, x, y, tooltip=tooltip, visible=visible, fit=fit)
        self._qt_images[sprite.id] = self._mod_sprites[sprite.id] = sprite
        self._notify_catalog()
        return sprite

    def create_sprite(self, *args, **kwargs):
        return self.create_image(*args, **kwargs)

    def get_sprite(self, sprite_id):
        return self._mod_sprites.get(str(sprite_id))

    def _coerce_image_handle(self, image):
        handle = self._qt_images.get(image) if isinstance(image, str) else image
        if isinstance(handle, ImageHandle) and self._qt_images.get(handle.id) is handle:
            return handle
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
        return handle.remove() if handle is not None else False

    def has_qt_mod_motion(self):
        return any((image.vx or image.vy) and not image._manual_motion
                   for image in self._qt_images.values())

    def advance_qt_mod_ui(self, seconds=0.016):
        seconds = max(0.0, float(seconds))
        moved = catalog_changed = False
        for image in self._qt_images.values():
            if seconds and (image.vx or image.vy) and not image._manual_motion:
                image.x += image.vx * seconds
                image.y += image.vy * seconds
                moved = True
                catalog_changed = catalog_changed or image.tab_id is not None
        if catalog_changed:
            self._notify_catalog()
        if moved:
            getattr(self, "_notify_sprites", self._notify_live)()
        return moved

    def qt_mod_ui_snapshot(self):
        return {"tabs": [tab.to_dict() for tab in self._qt_tabs.values()],
                "buttons": [button.to_dict() for button in self._qt_buttons.values()],
                "images": [image.to_dict() for image in self._qt_images.values()]}

    def set_flesh_image(self, path: str):
        self.flesh_image_path = self.resolve_asset_path(path, owner=self._current_mod_namespace())
        self._notify_live()

    def create_draw_layer(self, draw_callback=None, name=None, visible=True, can_target=False):
        raise NotImplementedError("GTK/Cairo drawing mods need a Qt-compatible drawing API")

    def create_canvas(self, *args, **kwargs):
        return self.create_draw_layer(*args, **kwargs)
