"""Generate our own synthetic PDF; no publisher content is redistributed."""
import argparse
import json
from pathlib import Path

from reportlab.pdfgen import canvas

from scientific_evidence_engine import ingest_paper, render_figure, digitize, export_dataset, verify_export
from scientific_evidence_engine.common import write_json


def run(destination):
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=False)
    pdf = root / "synthetic-paper.pdf"
    c = canvas.Canvas(str(pdf), pagesize=(400, 300))
    c.drawString(20, 280, "Synthetic demonstration, not experimental evidence")
    c.drawString(20, 260, "The red series decreases with time (Figure 1).")
    c.setStrokeColorRGB(0, 0, 0)
    c.line(50, 50, 350, 50)
    c.line(50, 50, 50, 240)
    c.setStrokeColorRGB(1, 0, 0)
    c.setLineWidth(2)
    c.line(50, 230, 350, 80)
    c.save()
    store = root / "store"
    paper = ingest_paper(pdf, store, {"title": "Synthetic demonstration", "license": "CC0", "notes": "Not experimental data"})
    fig = render_figure(store, paper["paper_id"], 1, "Figure 1", scale=1)
    cfg = dict(series="synthetic_red", method="color", color=[255, 0, 0], tolerance=80,
               roi=[55, 65, 345, 225], stride=10,
               x_axis={"label": "Time", "unit": "s", "anchors": [{"pixel": 50, "value": 0}, {"pixel": 350, "value": 300}]},
               y_axis={"label": "Capacity", "unit": "mAh", "anchors": [{"pixel": 250, "value": 0}, {"pixel": 70, "value": 180}]})
    write_json(root / "digitize-config.json", cfg)
    result = digitize(store, fig["figure_id"], cfg)
    export_dataset(result, store, root / "dataset")
    print(json.dumps(verify_export(root / "dataset", store), indent=2))
    return root, paper, fig


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("destination")
    run(p.parse_args().destination)
