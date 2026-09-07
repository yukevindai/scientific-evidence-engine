import pytest
from reportlab.pdfgen import canvas

from scientific_evidence_engine import ingest_paper, render_figure, digitize


def test_ambiguous_and_absent_columns_are_not_interpolated(tmp_path):
    path = tmp_path / "ambiguous.pdf"
    c = canvas.Canvas(str(path), pagesize=(100, 100))
    c.setStrokeColorRGB(1, 0, 0)
    c.setLineWidth(2)
    c.line(10, 50, 30, 50)
    c.line(40, 50, 60, 50)
    c.line(40, 70, 60, 70)
    c.save()
    p = ingest_paper(path, tmp_path / "store", {"title": "Two overlapping series"})
    f = render_figure(tmp_path / "store", p["paper_id"], 1, "Figure 1", scale=1)
    axis = {"label": "coordinate", "unit": "dimensionless", "anchors": [{"pixel": 0, "value": 0}, {"pixel": 99, "value": 99}]}
    config = {"series": "red", "method": "color", "color": [255, 0, 0], "roi": [15, 10, 85, 90], "stride": 10,
              "x_axis": axis, "y_axis": axis}
    result = digitize(tmp_path / "store", f["figure_id"], config)
    assert [r["pixel_x"] for r in result["rows"]] == [15, 25]
    findings = {f["code"]: f for f in result["findings"]}
    assert findings["ambiguous_columns"]["evidence"]["pixel_columns"] == [45, 55]
    assert findings["unobserved_columns"]["evidence"]["pixel_columns"] == [35, 65, 75]
    config["color"] = [0, 255, 0]
    with pytest.raises(ValueError, match="No unambiguous"):
        digitize(tmp_path / "store", f["figure_id"], config)
