"""Portable CSV bundles with manifests and ChemData Auditor configuration."""
import csv
import io
from pathlib import Path

from .common import identity, new_directory, read_json, safe_path, sha256, write_json
from .papers import load_paper, load_figure


def export_dataset(result, store, destination):
    if identity("dataset", {k: v for k, v in result.items() if k != "dataset_id"}) != result.get("dataset_id"):
        raise ValueError("Dataset content hash mismatch")
    figure, _ = load_figure(store, result["figure"]["figure_id"])
    if figure != result["figure"]:
        raise ValueError("Dataset figure metadata mismatch")
    _, paper, _ = load_paper(store, figure["paper_id"])
    rows = []
    for row in result["rows"]:
        rows.append(dict(row, dataset_id=result["dataset_id"], paper_id=paper["paper_id"],
                         paper_sha256=paper["sha256"], paper_title=paper["metadata"]["title"],
                         doi=paper["metadata"].get("doi", ""), page=figure["page"], figure_id=figure["figure_id"],
                         figure_label=figure["label"], series=result["config"]["series"],
                         x_label=result["config"]["x_axis"]["label"], y_label=result["config"]["y_axis"]["label"],
                         extraction_method=result["extraction_method"], review_status=result["review_status"]))
    if not rows:
        raise ValueError("Cannot export an empty dataset")
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    raw = buf.getvalue().encode("utf-8")
    config = dict(numeric_columns=["x", "y", "x_lower", "x_upper", "y_lower", "y_upper"],
                  duplicate_columns=["paper_id", "figure_id", "series", "x", "y"],
                  group_columns=["paper_id", "figure_id"],
                  provenance_columns=["paper_id", "paper_sha256", "page", "figure_id", "extraction_method"],
                  units={"x": {"column": "x_unit", "expected": rows[0]["x_unit"]},
                         "y": {"column": "y_unit", "expected": rows[0]["y_unit"]}})
    manifest = dict(schema_version="1.0", dataset_id=result["dataset_id"],
                    data={"path": "dataset.csv", "sha256": sha256(raw), "row_count": len(rows), "columns": list(rows[0])},
                    source=paper, figure=figure, extraction=result, auditor_config=config,
                    grouping_guidance="Group by paper_id to hold out publications. Digitized points from one curve are not independent experiments. Add experimental sample identities when known.",
                    source_files_included=False)
    with new_directory(destination) as out:
        (out / "dataset.csv").write_bytes(raw)
        write_json(out / "manifest.json", manifest)
        write_json(out / "auditor-config.json", config)
    return manifest


def verify_export(directory, store=None):
    manifest = read_json(Path(directory) / "manifest.json")
    data = manifest["data"]
    raw = safe_path(directory, data["path"]).read_bytes()
    if sha256(raw) != data["sha256"]:
        raise ValueError("CSV hash mismatch")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    rows = list(reader)
    if reader.fieldnames != data["columns"] or len(rows) != data["row_count"]:
        raise ValueError("CSV schema or row count mismatch")
    result = manifest["extraction"]
    if identity("dataset", {k: v for k, v in result.items() if k != "dataset_id"}) != result.get("dataset_id") or result["dataset_id"] != manifest["dataset_id"]:
        raise ValueError("Extraction content hash mismatch")
    figure = result["figure"]
    if manifest["figure"] != figure or manifest["source"]["paper_id"] != figure["paper_id"]:
        raise ValueError("Manifest source linkage mismatch")
    if store is not None:
        registered, _ = load_figure(store, figure["figure_id"])
        if registered != figure:
            raise ValueError("Source figure snapshot mismatch")
    if len(rows) != len(result["rows"]):
        raise ValueError("Extraction row count mismatch")
    for exported, point in zip(rows, result["rows"]):
        if any(exported.get(k) != str(v) for k, v in point.items()) or exported.get("dataset_id") != result["dataset_id"]:
            raise ValueError("CSV does not match extraction evidence")
        for k, v in {"paper_id": figure["paper_id"], "paper_sha256": figure["paper_sha256"], "page": figure["page"], "figure_id": figure["figure_id"]}.items():
            if exported.get(k) != str(v):
                raise ValueError("CSV provenance differs from manifest")
    if read_json(Path(directory) / "auditor-config.json") != manifest["auditor_config"]:
        raise ValueError("Auditor configuration differs from manifest")
    return dict(valid=True, row_count=len(rows), dataset_id=result["dataset_id"], source_verified=store is not None,
                note="Hashes establish internal consistency, not publisher authenticity or scientific correctness.")
