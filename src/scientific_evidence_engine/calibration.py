"""Separable Cartesian axes and bounded pixel/calibration uncertainty propagation."""
import itertools
import math

from .common import fields, number, text


class Axis:
    def __init__(self, config, extent):
        fields(config, {"label", "unit", "anchors"}, {"scale"})
        self.label, self.unit = text(config["label"], "axis label"), text(config["unit"], "unit")
        self.scale = config.get("scale", "linear")
        if self.scale not in {"linear", "log10"}:
            raise ValueError("Axis scale must be linear or log10")
        anchors = config["anchors"]
        if not isinstance(anchors, list) or len(anchors) != 2:
            raise ValueError("Each axis needs exactly two calibration anchors")
        self.anchors = []
        for anchor in anchors:
            fields(anchor, {"pixel", "value"}, {"pixel_uncertainty", "value_uncertainty"})
            p, v = number(anchor["pixel"], "pixel"), number(anchor["value"], "value")
            ep = number(anchor.get("pixel_uncertainty", 0.5), "pixel uncertainty", 0)
            ev = number(anchor.get("value_uncertainty", 0), "value uncertainty", 0)
            if not 0 <= p <= extent - 1:
                raise ValueError("Calibration anchor outside image")
            if self.scale == "log10" and v - ev <= 0:
                raise ValueError("Log-axis values including uncertainty must be positive")
            self.anchors.append((p, v, ep, ev))
        a, b = self.anchors
        if abs(a[0] - b[0]) <= a[2] + b[2] or abs(a[1] - b[1]) <= a[3] + b[3]:
            raise ValueError("Calibration anchor intervals overlap or axis is degenerate")

    def _map(self, pixel, p0, v0, p1, v1):
        if self.scale == "log10":
            v0, v1 = math.log10(v0), math.log10(v1)
        value = v0 + (pixel - p0) * (v1 - v0) / (p1 - p0)
        try:
            value = 10 ** value if self.scale == "log10" else value
        except OverflowError as exc:
            raise ValueError("Calibration overflows numeric range") from exc
        return number(value, "calibrated value")

    def convert(self, pixel, uncertainty):
        pixel, uncertainty = number(pixel, "pixel"), number(uncertainty, "uncertainty", 0)
        a, b = self.anchors
        nominal = self._map(pixel, a[0], a[1], b[0], b[1])
        # Multilinear-fractional extrema occur at corners while denominator sign is fixed.
        corners = itertools.product([pixel - uncertainty, pixel + uncertainty],
                                    [a[0] - a[2], a[0] + a[2]], [a[1] - a[3], a[1] + a[3]],
                                    [b[0] - b[2], b[0] + b[2]], [b[1] - b[3], b[1] + b[3]])
        vals = [self._map(*corner) for corner in corners]
        return nominal, min(vals + [nominal]), max(vals + [nominal])
