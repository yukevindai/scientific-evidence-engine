# Scientific Evidence Engine

Local Python tools that connect published scientific evidence to inspectable datasets and conclusions. Designed for chemistry, materials science, and chemical engineering, with portable exports for [ChemData Auditor](https://github.com/yukevindai/chemdata-auditor).

The **Figure-to-Dataset Validator** snapshots PDFs, renders reproducible page crops, converts manual or automatically traced pixels through calibrated linear/logarithmic axes, and exports values with digitization uncertainty and provenance. It retains paper hashes, page and figure identities, axes, units, extraction configuration, affected rows, and recommended review actions.

The **Evidence-Grounded Research Agent** is the next subsystem: exact evidence locations and explicit supporting/contradicting claim links, with inspectable research reports.

## Quick start

```bash
python -m pip install -e '.[dev]'
python examples/demo.py outputs/demo
evidence-engine verify outputs/demo/dataset --store outputs/demo/store
python -m pytest -q
```

The demo creates a synthetic PDF, traces its red line, and exports a CSV, manifest, and Auditor configuration. It requires a new destination and does not download literature or call a hosted model.

## Work with a paper

```bash
evidence-engine ingest paper.pdf --store workspace --metadata metadata.json
evidence-engine render --store workspace --paper PAPER_ID --page 3 --label 'Figure 2a' --scale 2 --crop 100 200 900 800
evidence-engine digitize --store workspace --figure FIGURE_ID --config digitize.json --output outputs/curve
evidence-engine verify outputs/curve --store workspace
```

Use the full `paper_…` / `figure_…` IDs returned by each command. Metadata minimally contains `{"title": "Paper title"}`. DOI, URL, authors, year, license, and notes are optional, explicitly user-supplied assertions. Page numbers start at 1. Crops use **rendered page pixels**, origin at the top left. Calibration and curve points use pixels relative to the resulting crop, also with top-left origin.

See [digitization configuration and uncertainty](docs/FIGURE_VALIDATOR.md), [data contracts](docs/DATA_CONTRACTS.md), and [limitations](docs/LIMITATIONS.md).

## Export to ChemData Auditor

With ChemData Auditor installed in your environment:

```bash
chemdata audit outputs/curve/dataset.csv --config outputs/curve/auditor-config.json --output outputs/audit.json
```

For split leakage checks, add your partition column and set `split_column` in the Auditor configuration. Preserve `paper_id` and `figure_id` as grouping columns. Hundreds of digitized points from one curve are not hundreds of independent experiments. Add experiment/cell/formulation identities when available; a DOI alone cannot detect cross-paper reuse.

All artifacts stay local. Output directories are never overwritten. Hashes detect changes relative to recorded snapshots; they do not authenticate a publisher or establish the correctness of a scientific claim.
