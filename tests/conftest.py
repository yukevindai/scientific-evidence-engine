import pytest
from reportlab.pdfgen import canvas

from scientific_evidence_engine import ingest_paper, render_figure


@pytest.fixture
def paper(tmp_path):
    path = tmp_path / "synthetic.pdf"
    c = canvas.Canvas(str(path), pagesize=(240, 200))
    c.drawString(10, 185, "Synthetic experiment: capacity decreases.")
    c.drawString(10, 172, "Source text spans multiple lines.")
    c.setStrokeColorRGB(1, 0, 0)
    c.setLineWidth(2)
    c.line(20, 160, 200, 40)
    c.save()
    store = tmp_path / "store"
    p = ingest_paper(path, store, {"title": "Synthetic fixture", "license": "CC0"})
    f = render_figure(store, p["paper_id"], 1, "Figure 1", scale=1)
    return store, p, f


@pytest.fixture
def config():
    return {"x_axis": {"label": "Time", "unit": "s", "anchors": [{"pixel": 20, "value": 0}, {"pixel": 200, "value": 180}]},
            "y_axis": {"label": "Capacity", "unit": "mAh", "anchors": [{"pixel": 160, "value": 0}, {"pixel": 40, "value": 120}]},
            "series": "control", "method": "manual", "points": [[20, 40], [110, 100], [200, 160]]}
