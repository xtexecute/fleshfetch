"""GTK-shaped compatibility objects rendered by the Qt frontend.

This is a deliberately explicit adapter, not a GTK runtime or a Python sandbox.
Unsupported calls raise AttributeError instead of silently pretending to work.
"""

import itertools
import os
import sys
import time
import types

from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer, QEvent, Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox
import runtime_scheduler as scheduler


class LegacyNode(QObject):
    changed = Signal()

    def __init__(self, game, kind="box", **props):
        super().__init__(game)
        # PySide injects QObject's static helpers onto dynamic widget subclasses.
        self.connect = types.MethodType(LegacyNode.connect, self)
        self.disconnect = types.MethodType(LegacyNode.disconnect, self)
        self.emit = types.MethodType(LegacyNode.emit, self)
        self.game, self.kind = game, kind
        self.owner = game._current_mod_namespace()
        self.key = str(next(game._legacy_ids))
        self.children, self.parent_node, self.handlers = [], None, {}
        self.props = dict(visible=True, sensitive=True, text="", active=False,
                          index=-1, choices=[], spacing=6, orientation=1,
                          minimum=0, maximum=100, step=1, value=0, expanded=False)
        self.props.update(props)
        self.tick_ids = set()
        if "label" in props:
            self.props["text"] = str(props["label"])
        game._legacy_nodes[self.key] = self
        game._legacy_warn(self.owner, "GTK widgets are deprecated; use the framework mod UI API.")

    @Property("QVariantMap", notify=changed)
    def data(self):
        return dict(self.props, kind=self.kind, key=self.key, children=list(self.children))

    def _set(self, key, value):
        if self.props.get(key) != value:
            self.props[key] = value
            self.changed.emit()

    def connect(self, signal, callback, *args):
        ident = next(self.game._legacy_ids)
        self.handlers[ident] = (signal, callback, args)
        return ident

    def disconnect(self, ident):
        self.handlers.pop(ident, None)

    def emit(self, signal, *args):
        result = None
        for name, callback, extra in list(self.handlers.values()):
            if name == signal:
                result = self.game._run_with_mod_owner(self.owner, callback, self, *args, *extra)
        return result

    @Slot(str, "QVariant")
    def action(self, name, value):
        try:
            if not self.props["sensitive"] or not self.props["visible"]:
                return
            if name == "click":
                self.emit("clicked")
            elif name == "text":
                self.set_text(value)
            elif name == "active":
                self.set_active(value)
            elif name == "index":
                self.set_active(int(value))
            elif name == "value":
                self.set_value(value)
            elif name == "expanded":
                self.set_expanded(value)
            elif name == "activate":
                self.emit("activate")
        except Exception as exc:
            self.game.console_print(f"[mods] Legacy UI callback failed: {exc}")

    def append(self, child, text=None):
        if self.kind == "combo":
            choices = list(self.props["choices"])
            choices.append({"id": str(child), "text": str(text)})
            self._set("choices", choices)
            return
        if not isinstance(child, LegacyNode):
            raise TypeError("Legacy containers accept compatibility widgets")
        if child.parent_node:
            child.parent_node.remove(child)
        child.parent_node = self
        self.children.append(child)
        self.changed.emit()

    def prepend(self, child):
        self.append(child)
        self.children.remove(child)
        self.children.insert(0, child)
        self.changed.emit()

    def remove(self, child):
        if child in self.children:
            self.children.remove(child)
            child.parent_node = None
            self.changed.emit()

    def put(self, child, x, y):
        child._set("x", x)
        child._set("y", y)
        self.append(child)

    def move(self, child, x, y):
        child._set("x", x)
        child._set("y", y)

    def set_child(self, child):
        for old in list(self.children):
            self.remove(old)
        if child is not None:
            self.append(child)

    def get_child(self):
        return self.get_first_child()

    def get_first_child(self):
        return self.children[0] if self.children else None

    def get_next_sibling(self):
        siblings = self.parent_node.children if self.parent_node else []
        index = siblings.index(self) + 1 if self in siblings else 0
        return siblings[index] if index < len(siblings) else None

    def get_parent(self):
        return self.parent_node

    def attach(self, child, column, row, width=1, height=1):
        child.props.update(column=column, row=row, columnSpan=width, rowSpan=height)
        self._set("columns", max(self.props.get("columns", 1), column + width))
        self.append(child)

    def set_text(self, text, length=-1):
        text = str(text)
        if length >= 0:
            text = text[:length]
        if self.props["text"] != text:
            self._set("text", text)
            self.emit("changed")

    def get_text(self, *args):
        if self.kind == "text" and len(args) >= 2:
            return self.props["text"][int(args[0]):int(args[1])]
        return self.props["text"]
    set_label = set_text
    get_label = get_text
    set_markup = set_text
    set_visible = lambda self, value: self._set("visible", bool(value))
    get_visible = lambda self: self.props["visible"]
    show = lambda self: self.set_visible(True)
    hide = lambda self: self.set_visible(False)
    set_sensitive = lambda self, value: self._set("sensitive", bool(value))
    get_sensitive = lambda self: self.props["sensitive"]
    set_tooltip_text = lambda self, value: self._set("tooltip", str(value or ""))
    set_placeholder_text = lambda self, value: self._set("placeholder", str(value))
    set_max_length = lambda self, value: self._set("maxLength", int(value))
    set_wrap = lambda self, value: self._set("wrap", bool(value))
    set_wrap_mode = lambda self, value: self._set("wrap", bool(value))
    set_editable = lambda self, value: self._set("editable", bool(value))
    set_monospace = lambda self, value: self._set("monospace", bool(value))
    set_hexpand = lambda self, value: self._set("hexpand", bool(value))
    set_vexpand = lambda self, value: self._set("vexpand", bool(value))
    set_xalign = lambda self, value: self._set("xalign", float(value))
    set_halign = lambda self, value: self._set("halign", value)
    set_valign = lambda self, value: self._set("valign", value)
    set_spacing = lambda self, value: self._set("spacing", value)
    set_margin_top = lambda self, value: self._set("marginTop", value)
    set_margin_bottom = lambda self, value: self._set("marginBottom", value)
    set_margin_start = lambda self, value: self._set("marginLeft", value)
    set_margin_end = lambda self, value: self._set("marginRight", value)
    set_selection_mode = lambda self, value: self._set("selectionMode", value)
    set_policy = lambda self, *value: self._set("scrollPolicy", list(value))
    set_min_content_height = lambda self, value: self._set("height", value)
    set_propagate_natural_height = lambda self, value: self._set("naturalHeight", value)
    set_max_content_height = lambda self, value: self._set("maxHeight", value)
    set_can_target = lambda self, value: self._set("canTarget", bool(value))
    set_content_width = lambda self, value: self._set("width", value)
    set_content_height = lambda self, value: self._set("height", value)
    set_opacity = lambda self, value: self._set("opacity", float(value))
    get_allocated_width = lambda self: int(self.props.get("width", self.game._qt_view_width))
    get_allocated_height = lambda self: int(self.props.get("height", self.game._qt_view_height))
    queue_draw = lambda self: self.changed.emit()
    add_controller = lambda self, value: self.game.add_controller(value)
    remove_controller = lambda self, value: self.game.remove_controller(value)

    def set_draw_func(self, callback, *args):
        self.draw_callback, self.draw_args = callback, args
        self.draw_error = False
        self.queue_draw()

    def add_tick_callback(self, callback):
        clock = types.SimpleNamespace(get_frame_time=lambda: int(time.monotonic() * 1_000_000))
        ident = self.game._run_with_mod_owner(self.owner, self.game.set_timer, 0.016,
                                             lambda: callback(self, clock))
        self.tick_ids.add(ident)
        return ident

    def remove_tick_callback(self, ident):
        self.game.cancel_timer(ident)
        self.tick_ids.discard(ident)

    def set_size_request(self, width, height):
        self._set("width", width)
        self._set("height", height)

    def set_active(self, value):
        field = "index" if self.kind == "combo" else "active"
        value = int(value) if field == "index" else bool(value)
        if value != self.props[field]:
            self._set(field, value)
            self.emit("changed" if field == "index" else "toggled")
            self.emit("notify::active", None)
            if field == "active":
                self.emit("state-set", value)

    def get_active(self):
        return self.props["index"] if self.kind == "combo" else self.props["active"]

    def set_active_id(self, ident):
        index = next((i for i, c in enumerate(self.props["choices"]) if c["id"] == str(ident)), -1)
        self.set_active(index)
        return index >= 0

    def get_active_id(self):
        index = self.props["index"]
        return self.props["choices"][index]["id"] if 0 <= index < len(self.props["choices"]) else None

    def get_active_text(self):
        index = self.props["index"]
        return self.props["choices"][index]["text"] if 0 <= index < len(self.props["choices"]) else None

    def append_text(self, text):
        self.append(str(len(self.props["choices"])), text)

    def remove_all(self):
        self._set("choices", [])
        self.set_active(-1)

    def set_value(self, value):
        value = max(self.props["minimum"], min(self.props["maximum"], float(value)))
        if self.props["value"] != value:
            self._set("value", value)
            self.emit("value-changed")

    get_value = lambda self: self.props["value"]
    get_value_as_int = lambda self: int(self.get_value())
    set_digits = lambda self, value: self._set("digits", value)
    set_expanded = lambda self, value: self._set("expanded", bool(value))
    get_expanded = lambda self: self.props["expanded"]
    get_buffer = lambda self: self
    get_bounds = lambda self: (0, len(self.props["text"]))
    get_start_iter = lambda self: 0
    get_end_iter = lambda self: len(self.props["text"])

    def insert(self, iterator, text, length=-1):
        self.set_text(self.props["text"][:iterator] + str(text)[:length if length >= 0 else None] + self.props["text"][iterator:])

    def add_css_class(self, name):
        self.game._legacy_warn(self.owner, "GTK CSS classes cannot style Qt controls; use set_tab_theme().")

    remove_css_class = add_css_class

    def dispose(self):
        for ident in list(self.tick_ids):
            self.game.cancel_timer(ident)
        for child in list(self.children):
            child.dispose()
        self.handlers.clear()
        self.game._legacy_nodes.pop(self.key, None)
        self.deleteLater()


class LegacyController(LegacyNode):
    def __init__(self, game, kind):
        super().__init__(game, kind)
        self.state, self.origin = 0, None

    set_propagation_phase = lambda self, value: self._set("phase", value)
    set_button = lambda self, value: self._set("button", value)
    set_state = lambda self, value: setattr(self, "state", value)
    get_widget = lambda self: self.game._window_overlay


class PointerFilter(QObject):
    def __init__(self, game):
        super().__init__(game)
        self.game = game

    def eventFilter(self, watched, event):
        kind = event.type()
        if kind not in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
            return False
        game = self.game
        if game._closed:
            return False
        x, y = event.position().x() - game._legacy_origin[0], event.position().y() - game._legacy_origin[1]
        claimed = False
        for controller in list(game._legacy_controllers):
            try:
                if controller.kind == "motion" and kind == QEvent.Type.MouseMove:
                    controller.emit("motion", x, y)
                elif controller.kind == "drag":
                    if kind == QEvent.Type.MouseButtonPress and int(event.button().value) == controller.props.get("button", 1):
                        controller.state, controller.origin = 0, (x, y)
                        controller.emit("drag-begin", x, y)
                    if controller.origin and controller.state != 2:
                        if kind == QEvent.Type.MouseMove:
                            controller.emit("drag-update", x-controller.origin[0], y-controller.origin[1])
                        elif kind == QEvent.Type.MouseButtonRelease:
                            controller.emit("drag-end", x-controller.origin[0], y-controller.origin[1])
                        claimed |= controller.state == 1
                    if kind == QEvent.Type.MouseButtonRelease:
                        controller.origin = None
            except Exception as exc:
                game.console_print(f"[mods] Legacy pointer handler failed: {exc}")
        return claimed


class LegacyDialog(LegacyNode):
    def __init__(self, game, **props):
        super().__init__(game, "dialog", **props)
        self.content, self.responses = LegacyNode(game), []

    set_title = lambda self, value: self._set("title", value)
    set_modal = lambda self, value: self._set("modal", value)
    set_transient_for = lambda self, value: None
    get_content_area = lambda self: self.content

    def add_button(self, text, response):
        self.responses.append((text, response))

    def present(self):
        dialog = QMessageBox()
        dialog.setWindowTitle(self.props.get("title", "Fleshfetch"))
        dialog.setText("\n".join(c.get_text() for c in self.content.children))
        responses = {}
        for text, response in self.responses:
            button = dialog.addButton(text, QMessageBox.ButtonRole.AcceptRole if response == -3 else QMessageBox.ButtonRole.RejectRole)
            responses[button] = response
        self._dialog = dialog
        dialog.finished.connect(lambda _result: self.emit("response", responses.get(dialog.clickedButton(), -6)))
        dialog.open()

    show = present
    destroy = lambda self: self._dialog.close() if hasattr(self, "_dialog") else None


class LegacyFileChooser(LegacyDialog):
    def __init__(self, game, title="Select file", parent=None, action=0, accept_label=None, cancel_label=None):
        super().__init__(game, title=title, action=action)
        self.filters, self.selected_file = [], None

    set_current_name = lambda self, value: self._set("filename", str(value))
    add_filter = lambda self, value: self.filters.append(value)
    get_file = lambda self: types.SimpleNamespace(get_path=lambda: self.selected_file) if self.selected_file else None

    def present(self):
        dialog = QFileDialog(None, self.props["title"])
        if self.props["action"] == 1:
            dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        else:
            dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        if self.props.get("filename"):
            dialog.selectFile(self.props["filename"])
        dialog.setNameFilters([f"{f.name} ({' '.join(f.patterns)})" for f in self.filters])
        def finished(result):
            self.selected_file = dialog.selectedFiles()[0] if result and dialog.selectedFiles() else None
            self.emit("response", -3 if self.selected_file else -6)
        dialog.finished.connect(finished)
        self._dialog = dialog
        dialog.open()

    show = present


class FileFilter:
    def __init__(self):
        self.name, self.patterns = "Files", []

    def set_name(self, name):
        self.name = name

    def add_pattern(self, pattern):
        self.patterns.append(pattern)

    def add_mime_type(self, mime):
        self.patterns.append("*.json" if mime == "application/json" else "*")


class LegacyUiMixin:
    legacyIdle = Signal(object)

    def init_legacy_ui(self):
        self._legacy_ids = itertools.count(1)
        self._legacy_nodes, self._legacy_pages = {}, {}
        self._legacy_controllers = []
        self._legacy_idle_pending = {}
        self._legacy_origin = (0, 0)
        self.legacyIdle.connect(self._dispatch_legacy_idle, Qt.ConnectionType.QueuedConnection)
        self._sprite_layer = LegacyNode(self, "fixed")
        self._window_overlay = self._sprite_layer
        self.picture = self.flesh_picture = LegacyPicture(self)
        self._legacy_pointer_filter = PointerFilter(self)
        self._install_legacy_imports()

    @Slot(object)
    def _dispatch_legacy_idle(self, task):
        ident, owner, callback, args = task
        if self._closed or ident not in self._legacy_idle_pending:
            return
        self._legacy_idle_pending.pop(ident, None)
        try:
            if self._run_with_mod_owner(owner, callback, *args):
                self._legacy_idle_pending[ident] = owner
                self.legacyIdle.emit(task)
        except Exception as exc:
            self.console_print(f"[mods] Legacy idle callback failed: {exc}")

    @Slot(float, float)
    def setLegacyOrigin(self, x, y):
        self._legacy_origin = (x, y)

    def add_controller(self, controller):
        if not isinstance(controller, LegacyController):
            raise TypeError("Expected a legacy event controller")
        if controller not in self._legacy_controllers:
            self._legacy_controllers.append(controller)

    def remove_controller(self, controller):
        if controller in self._legacy_controllers:
            self._legacy_controllers.remove(controller)

    def load_flesh_image(self):
        self._notify_live()

    def refresh_stats_tab(self, *args, **kwargs):
        self._notify_live()

    def create_draw_layer(self, draw_callback=None, name=None, visible=True, can_target=False):
        layer = LegacyDrawLayer(self, name, draw_callback)
        layer.set_visible(visible)
        layer.widget.set_can_target(can_target)
        self._sprite_layer.append(layer.widget)
        self._mod_draw_layers[layer.layer_id] = layer
        return layer

    def create_canvas(self, *args, **kwargs):
        return self.create_draw_layer(*args, **kwargs)

    def get_draw_layer(self, layer_id):
        return self._mod_draw_layers.get(str(layer_id))

    def remove_draw_layer(self, layer):
        layer = self.get_draw_layer(layer) if isinstance(layer, str) else layer
        return layer.remove() if layer else False

    def _legacy_warn(self, owner, message):
        info = getattr(self, "_current_mod_info", None)
        if info is None or info.get("id") != owner:
            info = next((m for m in self.installed_mods if m["id"] == owner), None)
        self._add_mod_deprecation_warning(message, info)

    def _install_legacy_imports(self):
        game = self
        gtk = types.ModuleType("Gtk")
        for name, kind in {"Box": "box", "Grid": "grid", "Label": "label", "Button": "button",
                           "Entry": "entry", "TextView": "text", "TextBuffer": "text", "Switch": "switch",
                           "CheckButton": "check", "ComboBoxText": "combo", "SpinButton": "spin",
                           "Scale": "scale", "Expander": "expander", "ScrolledWindow": "scroll",
                           "ListBox": "box", "Separator": "separator", "Frame": "box",
                           "DrawingArea": "drawing", "Fixed": "fixed"}.items():
            cls = type(name, (LegacyNode,), {"__init__": lambda node, _kind=kind, **kw: LegacyNode.__init__(node, game, _kind, **kw)})
            cls.new = classmethod(lambda cls, **kw: cls(**kw))
            cls.new_with_label = classmethod(lambda cls, text: cls(label=text))
            if kind in ("spin", "scale"):
                cls.new_with_range = classmethod(lambda cls, minimum, maximum, step: cls(minimum=minimum, maximum=maximum, step=step))
            setattr(gtk, name, cls)
        gtk.Orientation = types.SimpleNamespace(HORIZONTAL=0, VERTICAL=1)
        gtk.Align = types.SimpleNamespace(FILL=0, START=1, END=2, CENTER=3)
        gtk.PolicyType = types.SimpleNamespace(AUTOMATIC=0, NEVER=1, ALWAYS=2)
        gtk.WrapMode = types.SimpleNamespace(NONE=0, WORD=1, CHAR=2, WORD_CHAR=3)
        gtk.SelectionMode = types.SimpleNamespace(NONE=0, SINGLE=1)
        gtk.ResponseType = types.SimpleNamespace(ACCEPT=-3, OK=-5, CANCEL=-6, CLOSE=-7)
        gtk.FileChooserAction = types.SimpleNamespace(OPEN=0, SAVE=1)
        gtk.FileFilter = FileFilter
        gtk.EventControllerMotion = lambda: LegacyController(game, "motion")
        gtk.GestureDrag = lambda: LegacyController(game, "drag")
        gtk.PropagationPhase = types.SimpleNamespace(CAPTURE=1, BUBBLE=2)
        gtk.EventSequenceState = types.SimpleNamespace(NONE=0, CLAIMED=1, DENIED=2)
        gtk.Dialog = lambda **kw: LegacyDialog(game, **kw)
        gtk.FileChooserNative = types.SimpleNamespace(new=lambda *args: LegacyFileChooser(game, *args))
        repository = types.ModuleType("gi.repository")
        repository.Gtk, repository.GLib = gtk, self._legacy_glib()
        gi = types.ModuleType("gi")
        gi.__path__ = []
        gi.repository = repository
        def require_version(namespace, version):
            if namespace not in ("Gtk", "Gdk", "GdkPixbuf", "GLib", "Gio"):
                raise ValueError(f"Unsupported legacy namespace: {namespace}")
        gi.require_version = require_version
        gi.require_foreign = lambda name: None
        compat = types.ModuleType("gtk_compat")
        compat.Gtk, compat.GLib = gtk, repository.GLib
        from qt_legacy_drawing import cairo_module
        compat.cairo = cairo_module()
        # File-backed textures preserve the old preloading API without loading GTK.
        pixbuf = types.SimpleNamespace(new_from_file=lambda path: types.SimpleNamespace(path=path))
        repository.GdkPixbuf = compat.GdkPixbuf = types.SimpleNamespace(Pixbuf=pixbuf)
        repository.Gdk = compat.Gdk = types.SimpleNamespace(Texture=types.SimpleNamespace(new_for_pixbuf=lambda pix: pix))
        repository.Gio = compat.Gio = types.SimpleNamespace(File=types.SimpleNamespace(new_for_path=lambda path: types.SimpleNamespace(get_path=lambda: path)))
        sys.modules.update({"gi": gi, "gi.repository": repository,
                            "gi.repository.Gtk": gtk, "gi.repository.GLib": repository.GLib,
                            "gtk_compat": compat, "cairo": compat.cairo})

    def _legacy_glib(self):
        game = self
        glib = types.ModuleType("GLib")
        def timeout(interval, callback, *args, **kwargs):
            owner = game._current_mod_namespace()
            previous = getattr(game, "_active_mod_owner", None)
            game._active_mod_owner = owner
            try:
                return game.set_timer(max(0.001, interval / 1000), lambda: bool(callback(*args)))
            finally:
                game._active_mod_owner = previous
        glib.timeout_add = timeout
        glib.timeout_add_seconds = lambda seconds, callback, *args: timeout(seconds * 1000, callback, *args)
        def idle(callback, *args, **kwargs):
            ident = -next(game._legacy_ids)
            owner = game._current_mod_namespace()
            game._legacy_idle_pending[ident] = owner
            game.legacyIdle.emit((ident, owner, callback, args))
            return ident
        def remove(ident):
            if ident < 0:
                return game._legacy_idle_pending.pop(ident, None) is not None
            return game.cancel_timer(ident)
        glib.source_remove, glib.idle_add = remove, idle
        glib.get_monotonic_time = lambda: int(time.monotonic() * 1_000_000)
        glib.PRIORITY_DEFAULT = 0
        return glib

    def add_tab(self, tab_id, label, page_box=None):
        tab = super().add_tab(tab_id, label)
        if page_box is not None:
            if not isinstance(page_box, LegacyNode):
                raise TypeError("page_box must be a legacy compatibility container")
            self._legacy_pages[str(tab_id)] = page_box
            self._notify_catalog()
            return page_box
        return tab

    def _legacy_page(self, tab_id):
        tab_id = str(tab_id)
        if tab_id not in self._legacy_pages:
            self._legacy_pages[tab_id] = LegacyNode(self)
            self._notify_catalog()
        return self._legacy_pages[tab_id]

    def _remove_tab_page(self, tab_id):
        root = self._legacy_pages.pop(str(tab_id), None)
        if root:
            root.dispose()
        return super()._remove_tab_page(tab_id)

    def _remove_widget_from_parent(self, widget):
        if isinstance(widget, LegacyNode):
            if widget.parent_node:
                widget.parent_node.remove(widget)
            widget.dispose()
            return True
        return super()._remove_widget_from_parent(widget)

    def _reset_mod_registries(self):
        self._legacy_controllers.clear()
        self._legacy_idle_pending.clear()
        self._sprite_layer.set_child(None)
        for node in list(self._legacy_nodes.values()):
            if node.owner != "__global__" and node.key in self._legacy_nodes:
                node.dispose()
        self._legacy_pages.clear()
        return super()._reset_mod_registries()


class LegacyPicture:
    def __init__(self, game):
        self.game = game

    def set_paintable(self, texture):
        self.game.set_flesh_image(texture.path)

    def set_filename(self, filename):
        self.game.set_flesh_image(filename)

    set_from_file = set_filename


class LegacyDrawLayer:
    def __init__(self, game, name, callback):
        self.game, self.owner = game, game._current_mod_namespace()
        self.layer_id = game._qt_id("draw", self.owner) if name is None else f"{self.owner}:{name}"
        self.widget = LegacyNode(game, "drawing")
        self.widget.set_draw_func(lambda area, ctx, w, h: callback(self, ctx, w, h) if callback else None)
        self._removed, self._animation_id = False, None

    get_widget = lambda self: self.widget
    get_width = lambda self: self.widget.get_allocated_width()
    get_height = lambda self: self.widget.get_allocated_height()
    get_size = lambda self: (self.get_width(), self.get_height())
    set_visible = lambda self, value: self.widget.set_visible(value)
    is_visible = lambda self: not self._removed and self.widget.get_visible()
    show = lambda self: self.widget.show()
    hide = lambda self: self.widget.hide()

    def queue_draw(self):
        self.widget.queue_draw()
        return self

    def set_draw_callback(self, callback):
        if callback is not None and not callable(callback):
            raise TypeError("Draw callback must be callable")
        self.widget.set_draw_func(lambda area, ctx, w, h: callback(self, ctx, w, h) if callback else None)
        return self

    def start_animation(self, callback, queue_draw=True):
        self.stop_animation()
        last = [None]
        def tick(widget, clock):
            now = clock.get_frame_time() / 1_000_000
            delta = 0 if last[0] is None else min(0.1, max(0, now-last[0]))
            last[0] = now
            keep = callback(self, delta, now)
            if queue_draw:
                self.queue_draw()
            return keep is not False
        self._animation_id = self.widget.add_tick_callback(tick)
        return self

    def stop_animation(self):
        if self._animation_id is not None:
            self.widget.remove_tick_callback(self._animation_id)
            self._animation_id = None
        return self

    def remove(self):
        if self._removed:
            return False
        self.stop_animation()
        self.game._remove_widget_from_parent(self.widget)
        self.game._mod_draw_layers.pop(self.layer_id, None)
        self._removed = True
        return True
