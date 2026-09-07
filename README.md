# Scientific Evidence Engine

Local Python tools that connect published scientific evidence to inspectable datasets and conclusions. Designed for chemistry, materials science, and chemical engineering, with portable exports for [ChemData Auditor](https://github.com/yukevindai/chemdata-auditor).

The **Figure-to-Dataset Validator** snapshots PDFs, renders reproducible page crops, converts manual or automatically traced pixels through calibrated linear/logarithmic axes, and exports values with digitization uncertainty and provenance. It retains paper hashes, page and figure identities, axes, units, extraction configuration, affected rows, and recommended review actions.

The **Evidence-Grounded Research Agent** indexes exact passages and registers figure, table, and equation crops. It retrieves candidate evidence, links scoped claims to supporting/contradicting/contextual sources, records append-only review decisions, and produces cited JSON, Markdown, and HTML reports. Imported AI suggestions remain proposals until reviewed. Quantitative evidence can cite exact digitized rows and their uncertainty.

## Quick start

```bash
python -m pip install -e '.[dev]'
python examples/demo.py outputs/demo
evidence-engine verify outputs/demo/dataset --store outputs/demo/store
python examples/research_demo.py outputs/research-demo
evidence-engine verify-report outputs/research-demo/research-report --store outputs/research-demo/store
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

See [digitization configuration and uncertainty](docs/FIGURE_VALIDATOR.md), [research agent workflow](docs/RESEARCH_AGENT.md), [data contracts](docs/DATA_CONTRACTS.md), and [limitations](docs/LIMITATIONS.md).

## Research workflow

```bash
evidence-engine index --store workspace --paper PAPER_ID
evidence-engine search 'capacity retention temperature' --store workspace
evidence-engine add-evidence --store workspace --config evidence.json
evidence-engine claim --store workspace --text 'Capacity decreases with time' --scope 'Red series, Figure 2a, stated conditions only'
evidence-engine link --store workspace --claim CLAIM_ID --evidence EVIDENCE_ID --relation supports --rationale 'The selected endpoints decrease under the same conditions'
evidence-engine review --store workspace --link LINK_ID --decision accepted --reviewer 'Researcher name' --rationale 'Inspected the source and its stated conditions'
evidence-engine research 'How does capacity vary with time?' --store workspace --claim CLAIM_ID --output outputs/research
```

Replace placeholders with IDs from preceding commands. `link` proposes a relation; `review` records an explicit decision. The report retains contradictions, pending/rejected links, rationales, and exact citations. Multiple conflicting active reviews are marked contested. Reviewer names are local assertions, not authenticated identities.

The agent works without an API key. Its default answer generation is deterministic synthesis of reviewed relationships. Optional external model output can enter through `import-draft` as strictly validated JSON; the engine never treats a model-provided citation or relation as reviewed evidence automatically.

## Export to ChemData Auditor

With ChemData Auditor installed in your environment:

```bash
chemdata audit outputs/curve/dataset.csv --config outputs/curve/auditor-config.json --output outputs/audit.json
```

For split leakage checks, add your partition column and set `split_column` in the Auditor configuration. Preserve `paper_id` and `figure_id` as grouping columns. Hundreds of digitized points from one curve are not hundreds of independent experiments. Add experiment/cell/formulation identities when available; a DOI alone cannot detect cross-paper reuse.

All artifacts stay local. Output directories are never overwritten. Hashes detect changes relative to recorded snapshots; they do not authenticate a publisher or establish the correctness of a scientific claim.
