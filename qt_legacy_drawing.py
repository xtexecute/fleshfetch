"""Translate the Cairo drawing subset used by legacy mods into QPainter."""

import math
import types
from PySide6.QtCore import QObject, Property, Signal, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen
from PySide6.QtQuick import QQuickPaintedItem


class CairoContext:
    def __init__(self, painter):
        self.painter, self.path = painter, QPainterPath()
        self.color, self.line_width = QColor("white"), 1.0
        self.font = QFont("Sans", 12)
        self.stack = []

    def save(self):
        self.painter.save()
        self.stack.append((QColor(self.color), self.line_width, QFont(self.font)))

    def restore(self):
        self.painter.restore()
        self.color, self.line_width, self.font = self.stack.pop()

    def set_source_rgb(self, r, g, b):
        self.set_source_rgba(r, g, b, 1)

    def set_source_rgba(self, r, g, b, a):
        self.color = QColor.fromRgbF(*[max(0, min(1, float(v))) for v in (r, g, b, a)])

    def set_line_width(self, value):
        self.line_width = value

    def move_to(self, x, y):
        self.path.moveTo(x, y)

    def line_to(self, x, y):
        self.path.lineTo(x, y)

    def curve_to(self, *args):
        self.path.cubicTo(*args)

    def rectangle(self, x, y, width, height):
        self.path.addRect(x, y, width, height)

    def arc(self, x, y, radius, start, end):
        if self.path.isEmpty():
            self.path.arcMoveTo(x-radius, y-radius, 2*radius, 2*radius, -math.degrees(start))
        self.path.arcTo(x-radius, y-radius, 2*radius, 2*radius,
                        -math.degrees(start), -math.degrees(end-start))

    def close_path(self):
        self.path.closeSubpath()

    def new_path(self):
        self.path = QPainterPath()

    def fill_preserve(self):
        self.painter.fillPath(self.path, self.color)

    def fill(self):
        self.fill_preserve()
        self.new_path()

    def stroke_preserve(self):
        self.painter.strokePath(self.path, QPen(self.color, self.line_width))

    def stroke(self):
        self.stroke_preserve()
        self.new_path()

    def paint(self):
        self.painter.fillRect(self.painter.viewport(), self.color)

    def translate(self, x, y):
        self.painter.translate(x, y)

    def scale(self, x, y):
        self.painter.scale(x, y)

    def rotate(self, angle):
        self.painter.rotate(math.degrees(angle))

    def select_font_face(self, family, slant=0, weight=0):
        self.font.setFamily(family)
        self.font.setItalic(bool(slant))
        self.font.setBold(bool(weight))

    def set_font_size(self, size):
        self.font.setPixelSize(max(1, int(size)))

    def text_path(self, text):
        point = self.path.currentPosition()
        self.path.addText(point, self.font, str(text))

    def show_text(self, text):
        point = self.path.currentPosition()
        self.painter.setPen(self.color)
        self.painter.setFont(self.font)
        self.painter.drawText(point, str(text))

    def text_extents(self, text):
        rect = QFontMetricsF(self.font).boundingRect(str(text))
        return (rect.x(), rect.y(), rect.width(), rect.height(),
                QFontMetricsF(self.font).horizontalAdvance(str(text)), 0)


class LegacyPaintItem(QQuickPaintedItem):
    nodeChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._node = None
        self.setAntialiasing(True)

    @Property(QObject, notify=nodeChanged)
    def node(self):
        return self._node

    @node.setter
    def node(self, value):
        if self._node:
            self._node.changed.disconnect(self.update)
        self._node = value
        if value:
            value.changed.connect(self.update)
        self.nodeChanged.emit()
        self.update()

    def paint(self, painter):
        node = self._node
        if node is None or not node.props.get("visible", True):
            return
        callback = getattr(node, "draw_callback", None)
        if callback is None:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        try:
            node.game._run_with_mod_owner(node.owner, callback, node,
                CairoContext(painter), int(self.width()), int(self.height()), *node.draw_args)
        except Exception as exc:
            if not getattr(node, "draw_error", False):
                node.game.console_print(f"[mods] Legacy drawing failed: {exc}")
                node.draw_error = True


def cairo_module():
    module = types.ModuleType("cairo")
    module.FONT_SLANT_NORMAL = 0
    module.FONT_SLANT_ITALIC = 1
    module.FONT_WEIGHT_NORMAL = 0
    module.FONT_WEIGHT_BOLD = 1
    module.Context = CairoContext
    return module
