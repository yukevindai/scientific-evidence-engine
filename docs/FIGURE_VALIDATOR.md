# Figure-to-Dataset Validator

## Configuration

```json
{
  "series": "control, 25 degC",
  "method": "manual",
  "pixel_uncertainty": 0.5,
  "points": [[20, 40], [110, 100], [200, 160]],
  "x_axis": {
    "label": "Time", "unit": "s", "scale": "linear",
    "anchors": [{"pixel": 20, "value": 0}, {"pixel": 200, "value": 180}]
  },
  "y_axis": {
    "label": "Capacity", "unit": "mAh", "scale": "linear",
    "anchors": [{"pixel": 160, "value": 0}, {"pixel": 40, "value": 120}]
  }
}
```

Each axis requires a label, unit, and two distinct anchors. Anchor `pixel_uncertainty` defaults to 0.5 pixels; `value_uncertainty` defaults to 0 in axis units. Both are nonnegative absolute bounds. Values must be finite JSON numbers. Anchor uncertainty intervals must not overlap. Log axes require positive lower bounds. A decreasing pixel-to-value mapping is supported, as is common for vertical axes.

`method: "color"` replaces `points` with an RGB `color`, optional Euclidean RGB `tolerance` (default 30), `roi: [left, top, right, bottom]` (exclusive right/bottom), `stride` (default 1), and `max_thickness` (default 12). Pixel coordinates are in the figure crop. At each sampled x coordinate, one contiguous vertical run of matching pixels is accepted. Multiple runs or excessive thickness are ambiguous and omitted. No interpolation, smoothing, gap filling, or model fitting is performed. Legends, gridlines, and same-colored overlapping curves require manual review and careful cropping.

`reviewer` and `notes` may document who configured extraction, but extraction remains unreviewed until an explicit evidence review is recorded. Unknown or method-inapplicable options are rejected.

## Calibration and uncertainty

For a linear axis, two anchors `(p0, v0)` and `(p1, v1)` define

`v(p) = v0 + (p - p0) * (v1 - v0) / (p1 - p0)`.

For a logarithmic axis, apply the same relation to `log10(v)` and exponentiate the result. A pixel halfway between values 1 and 100 therefore represents 10, not 50.5.

The engine evaluates the corners of the supplied pixel and anchor uncertainty intervals. With the anchor denominator constrained to a fixed sign, these corners bound the separable mapping. The output includes nominal values and asymmetric lower/upper bounds. For automatically traced lines, the vertical pixel bound covers the full accepted run, including half a pixel beyond its first/last centers, or the configured uncertainty, whichever is larger. Horizontal resolution remains explicitly controlled by `pixel_uncertainty`; decimated columns do not imply continuous observations between them.

These bounds are conditional on correct axis labels, calibration points, curve identity, and a rectilinear image. They are **not experimental error bars, standard deviations, or confidence intervals**. Tilt, perspective, broken axes, polar plots, image rescaling outside this workflow, and incorrectly selected ticks invalidate that model. Raster error and compression artifacts are not fully described by a half-pixel default.

## Evidence and integrity

Each extracted dataset has a content-derived ID covering the figure, configuration, points, findings, and software versions. Repeated extraction with identical inputs and versions produces the same identity. Source PDFs and exact extracted text are retained; rendered crops carry their own hashes. Registration and export refuse existing destinations.

`verify` validates CSV bytes, row/schema counts, extraction identity, linked provenance, and Auditor settings. Supplying `--store` also checks retained original PDF and figure image bytes. Export manifests intentionally do not redistribute full papers or images. Keep the source store alongside the export for a complete locally inspectable chain.

Implementation reference: [pypdfium2 rendering and text API](https://pypdfium2.readthedocs.io/en/stable/python_api.html). Text layers can be absent or misordered; there is no implicit OCR or automatic axis recognition.
