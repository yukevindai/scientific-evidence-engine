"""Manual points or conservative color tracing; never interpolate absent evidence."""
import numpy as np
import pint

from .calibration import Axis
from .common import fields, finding, identity, integer, number, text, versions
from .papers import load_figure


def digitize(store, figure_id, config):
    fields(config, {"x_axis", "y_axis", "series", "method"}, {"points", "pixel_uncertainty", "color", "tolerance", "roi", "stride", "max_thickness", "reviewer", "notes"})
    text(config["series"], "series")
    for k in ("reviewer", "notes"):
        if k in config:
            text(config[k], k)
    figure, image = load_figure(store, figure_id)
    xaxis, yaxis = Axis(config["x_axis"], image.width), Axis(config["y_axis"], image.height)
    findings, points = [], []
    method = config["method"]
    e = number(config.get("pixel_uncertainty", 0.5), "pixel uncertainty", 0)
    if method == "manual":
        if any(k in config for k in ("color", "tolerance", "roi", "stride", "max_thickness")):
            raise ValueError("Color-tracing options do not apply to manual extraction")
        if not isinstance(config.get("points"), list) or not config["points"]:
            raise ValueError("Manual extraction requires nonempty pixel points")
        if len(config["points"]) > 100000:
            raise ValueError("Point budget exceeded (100000)")
        for pair in config["points"]:
            if not isinstance(pair, list) or len(pair) != 2:
                raise ValueError("Points must be [pixel_x, pixel_y] pairs")
            px, py = (number(v, "point coordinate") for v in pair)
            if not (0 <= px <= image.width - 1 and 0 <= py <= image.height - 1):
                raise ValueError("Point outside figure image")
            points.append((px, py, e, e))
    elif method == "color":
        if "points" in config:
            raise ValueError("Manual points do not apply to color tracing")
        color = config.get("color")
        if not isinstance(color, list) or len(color) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in color):
            raise ValueError("Color needs three integer RGB channels in [0,255]")
        tol = number(config.get("tolerance", 30), "color tolerance", 0)
        if tol > 441.673:
            raise ValueError("Color tolerance exceeds RGB distance range")
        stride = integer(config.get("stride", 1), "stride", 1)
        max_thickness = integer(config.get("max_thickness", 12), "max_thickness", 1)
        roi = config.get("roi", [0, 0, image.width, image.height])
        if not isinstance(roi, list) or len(roi) != 4 or any(type(v) is not int for v in roi):
            raise ValueError("roi requires four integer image coordinates")
        l, t, r, b = roi
        if not (0 <= l < r <= image.width and 0 <= t < b <= image.height):
            raise ValueError("ROI outside figure image")
        # Process columns individually to bound memory independently of image area.
        pixels = np.asarray(image)
        absent, ambiguous = [], []
        for x in range(l, r, stride):
            column = pixels[t:b, x].astype(float)
            ys = np.flatnonzero(np.linalg.norm(column - color, axis=1) <= tol) + t
            if not len(ys):
                absent.append(x)
            elif np.any(np.diff(ys) > 1) or len(ys) > max_thickness:
                ambiguous.append(x)
            else:
                points.append((x, float((ys[0] + ys[-1]) / 2), e, max(e, (ys[-1] - ys[0] + 1) / 2)))
        for code, cols in (("unobserved_columns", absent), ("ambiguous_columns", ambiguous)):
            if cols:
                findings.append(finding(code, "warning", f"{len(cols)} columns omitted; no interpolation performed.",
                                        "Inspect the crop, legend, color selection and overlapping curves.", evidence={"pixel_columns": cols}))
        if not points:
            raise ValueError("No unambiguous curve pixels found")
    else:
        raise ValueError("method must be manual or color")
    rows = []
    for i, (px, py, ex, ey) in enumerate(points):
        x, xl, xu = xaxis.convert(px, ex)
        y, yl, yu = yaxis.convert(py, ey)
        rows.append(dict(row_id=i, pixel_x=px, pixel_y=py, pixel_x_bound=ex, pixel_y_bound=ey,
                         x=x, x_lower=xl, x_upper=xu, y=y, y_lower=yl, y_upper=yu,
                         x_unit=xaxis.unit, y_unit=yaxis.unit))
    units = pint.UnitRegistry()
    for axis, label in ((xaxis, "x"), (yaxis, "y")):
        try:
            units.Unit(axis.unit)
        except (pint.errors.PintError, TypeError, ValueError):
            findings.append(finding("unknown_unit", "warning", f"Unrecognized {label} unit: {axis.unit}",
                                    "Confirm the original axis unit and configure a valid unit spelling."))
    outside = [i for i, (px, py, _, _) in enumerate(points)
               if any(not min(a.anchors[0][0], a.anchors[1][0]) <= p <= max(a.anchors[0][0], a.anchors[1][0]) for a, p in ((xaxis, px), (yaxis, py)))]
    if outside:
        findings.append(finding("calibration_extrapolation", "warning", "Some points lie outside calibration anchors.",
                                "Extend calibration anchors or review extrapolated uncertainty.", outside))
    findings.append(finding("digitization_scope", "info", "Bounds cover declared pixel and anchor uncertainty only; they are not experimental error bars or confidence intervals.",
                            "Review axes, curve identity and raster artifacts; retain experimental uncertainty separately.", range(len(rows))))
    result = dict(schema_version="1.0", figure=figure, config=config, rows=rows, findings=findings,
                  extraction_method=method, review_status="unreviewed", software=versions(),
                  uncertainty_model="bounded_corner_propagation; independent pixel/anchor bounds; no probabilistic interpretation")
    result["dataset_id"] = identity("dataset", result)
    return result
