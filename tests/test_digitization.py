import copy
import json
import csv
import io

import pytest

from scientific_evidence_engine import digitize, export_dataset, verify_export, render_figure
from scientific_evidence_engine.calibration import Axis
from scientific_evidence_engine.common import read_json, sha256
from scientific_evidence_engine.papers import page_text
from scientific_evidence_engine.cli import main


def test_end_to_end_pdf_coordinates_and_export(paper, config, tmp_path):
    store, p, f = paper
    assert "capacity decreases" in page_text(store, p["paper_id"], 1)
    result = digitize(store, f["figure_id"], config)
    assert [(r["x"], r["y"]) for r in result["rows"]] == [(0, 120), (90, 60), (180, 0)]
    assert all(r["x_lower"] < r["x"] < r["x_upper"] for r in result["rows"])
    out = tmp_path / "export"
    export_dataset(result, store, out)
    assert verify_export(out, store)["source_verified"]
    with pytest.raises(FileExistsError):
        export_dataset(result, store, out)
    (out / "dataset.csv").write_text("tampered")
    with pytest.raises(ValueError, match="hash"):
        verify_export(out, store)


def test_color_recovers_known_pdf_curve(paper, config):
    store, _, f = paper
    config.pop("points")
    config.update(method="color", color=[255, 0, 0], tolerance=80, roi=[25, 35, 195, 165], stride=5)
    result = digitize(store, f["figure_id"], config)
    assert len(result["rows"]) > 30
    for row in result["rows"]:
        expected = 120 - row["x"] * 2 / 3
        assert row["y_lower"] <= expected <= row["y_upper"]


def test_log_and_reversed_axis_bounds():
    a = Axis({"label": "x", "unit": "s", "scale": "log10", "anchors": [
        {"pixel": 100, "value": 1, "pixel_uncertainty": 0}, {"pixel": 0, "value": 100, "pixel_uncertainty": 0}]}, 101)
    value, lower, upper = a.convert(50, 1)
    assert value == pytest.approx(10)
    assert lower == pytest.approx(10**0.98)
    assert upper == pytest.approx(10**1.02)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 10**400, True, "1"])
def test_bad_numeric_calibration(value, config):
    config["x_axis"]["anchors"][0]["value"] = value
    with pytest.raises(ValueError):
        Axis(config["x_axis"], 240)


def test_degenerate_uncertainty_and_log_zero(config):
    cfg = config["x_axis"]
    cfg["anchors"][0]["pixel_uncertainty"] = 180
    with pytest.raises(ValueError, match="overlap"):
        Axis(cfg, 240)
    cfg["anchors"][0]["pixel_uncertainty"] = 0
    cfg["scale"] = "log10"
    with pytest.raises(ValueError, match="positive"):
        Axis(cfg, 240)


def test_crop_and_tamper_detection(paper):
    store, p, f = paper
    crop = render_figure(store, p["paper_id"], 1, "Figure 1 inset", scale=1, crop=[10, 20, 210, 170])
    assert crop["image_size"] == [200, 150]
    with pytest.raises(ValueError):
        render_figure(store, p["paper_id"], 1, "bad", crop=[0, 0, 99999, 4])
    with pytest.raises(ValueError, match="budget"):
        render_figure(store, p["paper_id"], 1, "huge", scale=1000)
    (store / "papers" / p["paper_id"] / "original.pdf").write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash"):
        page_text(store, p["paper_id"], 1)


def test_strict_configs_and_cli(paper, config, tmp_path, capsys):
    store, _, f = paper
    config["misspelled"] = 2
    with pytest.raises(ValueError):
        digitize(store, f["figure_id"], config)
    config.pop("misspelled")
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps(config))
    out = tmp_path / "cli"
    assert main(["digitize", "--store", str(store), "--figure", f["figure_id"], "--config", str(cfg), "--output", str(out)]) == 0
    assert main(["verify", str(out), "--store", str(store)]) == 0
    assert main(["digitize", "--store", str(store), "--figure", f["figure_id"], "--config", str(cfg), "--output", str(out)]) == 2
    cfg.write_text('{"x": 1, "x": 2}')
    with pytest.raises(ValueError, match="Duplicate"):
        read_json(cfg)


def test_changed_result_cannot_be_exported(paper, config, tmp_path):
    store, _, f = paper
    result = digitize(store, f["figure_id"], config)
    result["rows"][0]["y"] = -123
    with pytest.raises(ValueError, match="hash"):
        export_dataset(result, store, tmp_path / "export")


@pytest.mark.parametrize("field", ["review_status", "series", "x_label", "y_label", "extraction_method", "figure_label", "paper_title", "doi"])
def test_updated_csv_digest_cannot_hide_changed_evidence(paper, config, tmp_path, field):
    store, _, f = paper
    out = tmp_path / "bundle"
    export_dataset(digitize(store, f["figure_id"], config), store, out)
    rows = list(csv.DictReader(io.StringIO((out / "dataset.csv").read_text())))
    rows[0][field] = "fabricated"
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    raw = buf.getvalue().encode()
    (out / "dataset.csv").write_bytes(raw)
    manifest = read_json(out / "manifest.json")
    manifest["data"]["sha256"] = sha256(raw)
    (out / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="provenance"):
        verify_export(out, store)


def test_source_metadata_must_match_retained_record(paper, config, tmp_path):
    store, _, f = paper
    out = tmp_path / "bundle"
    export_dataset(digitize(store, f["figure_id"], config), store, out)
    manifest = read_json(out / "manifest.json")
    manifest["source"]["metadata"]["notes"] = "Invented source assertion"
    (out / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Source metadata"):
        verify_export(out, store)


def test_log_underflow_is_rejected():
    axis = Axis({"label": "x", "unit": "s", "scale": "log10", "anchors": [
        {"pixel": 0, "value": 1, "pixel_uncertainty": 0},
        {"pixel": 1, "value": 1e-300, "pixel_uncertainty": 0}]}, 3)
    with pytest.raises(ValueError, match="underflows"):
        axis.convert(2, 0)
