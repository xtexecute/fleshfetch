"""Sample the same baked light paths used by the Event Horizon renderer."""

import json
import math
from pathlib import Path

from PySide6.QtGui import QImage

from paths import find_app_asset


class EventHorizonHitMap:
    def __init__(self):
        self.geometry = json.loads(Path(find_app_asset("skins/event-horizon-geometry.json")).read_text())
        self.body_rays = QImage(find_app_asset("skins/event-horizon-body-rays.png"))
        self.discs = [QImage(find_app_asset(f"skins/event-horizon-disc-{i}.png")) for i in range(2)]
        self.body_path = None
        self.body = QImage()

    @staticmethod
    def _sample(image, u, v, channels=("red", "green", "blue")):
        x = max(0.0, min(image.width() - 1, u * image.width() - 0.5))
        y = max(0.0, min(image.height() - 1, v * image.height() - 0.5))
        x0, y0 = int(x), int(y)
        x1, y1 = min(image.width() - 1, x0 + 1), min(image.height() - 1, y0 + 1)
        fx, fy = x - x0, y - y0
        colors = [image.pixelColor(a, b) for a, b in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
        return tuple((getattr(colors[0], channel)() * (1 - fx) + getattr(colors[1], channel)() * fx) * (1 - fy)
                     + (getattr(colors[2], channel)() * (1 - fx) + getattr(colors[3], channel)() * fx) * fy
                     for channel in channels)

    def hit(self, x, y, width, height, scale, body_x, body_y, path, pixel_ratio=1.0, origin_x=0.0, origin_y=0.0):
        if width <= 0 or height <= 0 or scale <= 0 or not 0 <= x < width or not 0 <= y < height:
            return False
        if self.body_rays.isNull() or any(image.isNull() for image in self.discs):
            return False
        # Match the fragment centers, including fractional logical pixels on high-DPI screens.
        pixel_ratio = max(1.0, pixel_ratio)
        x = (math.floor((x + origin_x) * pixel_ratio) + 0.5) / pixel_ratio - origin_x
        y = (math.floor((y + origin_y) * pixel_ratio) + 0.5) / pixel_ratio - origin_y
        half = min(width, height) * 0.5
        extent = self.geometry["extent"]
        qx = (x - width * 0.5) / half * extent / scale
        qy = (height * 0.5 - y) / half * extent / scale
        radius = math.hypot(qx, qy)
        if radius <= self.geometry["shadow_radius"]:
            return True
        u, v = qx / (extent * 2) + 0.5, 0.5 - qy / (extent * 2)
        if 0 <= u <= 1 and 0 <= v <= 1:
            for image in self.discs:
                disk_radius = self._sample(image, u, v)[0] / 255 * self.geometry["disc_outer"]
                if self.geometry["disc_inner"] <= disk_radius <= self.geometry["disc_outer"] - 0.10:
                    return True
        if radius >= self.geometry["radial_max"]:
            return False
        red, green, valid = self._sample(self.body_rays, radius / self.geometry["radial_max"], 0.5)
        if valid < 128:
            return False
        encoded = (red * 256 + green) / 65535
        distance = math.tan((encoded - 0.5) * math.pi) * 24
        span = self.geometry["flesh_span"]
        body_u = (qx / radius * distance - body_x) / span + 0.5
        body_v = 0.5 - (qy / radius * distance - body_y) / span
        if not 0 <= body_u < 1 or not 0 <= body_v < 1:
            return False
        if path != self.body_path:
            self.body = QImage(path)
            self.body_path = path
        if self.body.isNull():
            return False
        return self._sample(self.body, body_u, body_v, ("alpha",))[0] > 32
