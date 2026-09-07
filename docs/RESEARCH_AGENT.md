# Evidence-Grounded Research Agent

The agent answers from a local evidence collection. It does not search the entire literature, access paywalls, or call a remote model. Its two roles are distinct: retrieving candidate sources and synthesizing explicit reviewed relationships. Lexical similarity does not establish scientific support.

## 1. Register exact evidence

After PDF ingestion, `index --paper PAPER_ID` registers text chunks with the original page, Unicode character offsets, exact quote, and retained-text SHA-256. Chunk size defaults to 1000 codepoints (allowed 50–10000). Offsets are zero-based and the end is exclusive. Text-layer extraction is not OCR; pages with no text are reported and skipped. Word-boundary chunking improves readability but does not infer sentences or scientific assertions.

For a carefully selected passage, use `add-evidence --config evidence.json`:

```json
{
  "kind": "passage",
  "paper_id": "paper_FULL_SHA256",
  "page": 3,
  "label": "Results paragraph on retention",
  "locator": {"start": 120, "end": 145, "quote": "Exact retained text here."}
}
```

These example offsets are placeholders: the quote must exactly match the retained page text at your chosen offsets. Mismatches, missing files, out-of-range pages, changed PDF/text/image bytes, and invalid references fail explicitly. Do not replace a quote with a paraphrase. Bibliographic metadata remains user supplied and unverified.

Figures, tables, and equations are located through reproducible image crops made by `render`. To cite a table or equation, crop that region, then register:

```json
{
  "kind": "equation",
  "paper_id": "paper_FULL_SHA256",
  "page": 3,
  "label": "Equation 4",
  "locator": {"figure_id": "figure_FULL_SHA256"},
  "transcription": "E = m c^2",
  "notes": "Transcription entered by the researcher; inspect the crop."
}
```

The same format supports `figure` and `table`. The locator preserves page-pixel crop bounds, render scale, coordinate convention, and image hash. Transcriptions are searchable but explicitly unverified, and are displayed alongside the source crop. Table cell recognition and equation OCR are not performed. The `figure_id` type names a reproducible visual crop, which may contain a table or equation as well as a plotted figure.

## 2. Cite quantitative rows

First register a verified digitization bundle:

```bash
evidence-engine import-dataset outputs/curve --store workspace
```

Then add `"dataset_id": "dataset_FULL_SHA256"` and optional `"dataset_rows": [0, 4]` to a visual evidence specification. The dataset must refer to the exact same crop. Row selections are unique, zero-based extraction positions; omission selects all rows. The engine copies the actual points, units, uncertainty bounds, and uncertainty model into the evidence record, verifies them on load, and includes the source dataset bundle with exported research reports.

This makes the complete chain inspectable: original PDF bytes → page and crop → calibrated pixels → numerical rows → evidence reference → proposed relation → review decision → scoped conclusion. The existence of that chain does not establish that calibration, experiment, or scientific inference is valid.

## 3. Register scoped claims and review relations

Every claim has a nonempty text and scope. Scope should identify the population, conditions, measurements, and limits of the assertion. The engine cannot decide whether a claim is causally justified from a correlation or whether two experiments are comparable.

A proposed link names a claim ID, evidence ID, one of `supports`, `contradicts`, or `context`, and a rationale. A separate review accepts or rejects the relation and records a reviewer and rationale. Acceptance means that the reviewer asserts the relation is appropriate, not that the engine verified the scientific truth or authenticated that person.

Reviews are immutable. To correct one, supply `review --supersedes REVIEW_ID`; the previous record remains in history. Multiple active review branches are contested and excluded from conclusions, even if they share the same decision. Resolve each active branch by superseding it to rejected, or use a new proposed link with a reconciled rationale and a single accepted review. Contested old links remain visible in the report.

| Accepted relations | Assessment |
| --- | --- |
| Supporting and contradicting | `mixed`; explicitly disputed |
| Contradicting only | `contradicted` within the collected evidence set |
| Supporting only | `supported_in_reviewed_set`, conditional on scope and review |
| Context only, pending, rejected, or contested | `insufficient_evidence`; conclusion withheld |

Every relation remains visible, including rejected and unreviewed links. Counterevidence linked to an assessed claim is included even when it is absent from the top search results. Distinct PDF snapshot counts are descriptive; multiple papers can reuse the same experiment, and multiple versions can represent one paper.

## 4. Retrieve and generate a research report

`search QUERY` uses deterministic BM25 with Unicode word tokenization, case folding, `k1=1.5`, and `b=0.75`. It searches labels, exact passage text, unverified transcriptions, and notes. Results expose scores and matched terms and are labeled candidates. There is no stemming, embedding model, synonym expansion, or implication that the corpus is complete. The result limit is 1–100, default 10.

`research QUERY --claim CLAIM_ID --output NEW_DIRECTORY` assesses explicit claims and retrieves candidates. Multiple `--claim` arguments are supported. If omitted, registered claims sharing query words in their text or scope are selected; this is lexical discovery, not semantic validation. Conclusions use transparent templates determined by reviewed relationships. No unsupported free-form scientific answer is fabricated when evidence is absent.

Exports include:

- `report.json`: question, retrieval settings, source citations, claims, all links/reviews, assessments, findings, and software versions.
- `report.md` and `report.html`: readable conclusions and precise evidence references; HTML includes local visual crops and tables of selected digitized rows.
- `sources.json`: full bibliographic/source records; `figures/`: cited crops; `datasets/`: cited CSV/manifests/Auditor configurations.
- `report-manifest.json`: SHA-256 of every generated file. Original full PDFs are not bundled.

`verify-report DIRECTORY` checks file hashes. Adding `--store` also regenerates the answer against the **current** source and review state. A historical report can remain internally intact while failing that freshness check after new evidence or corrected reviews. Retain both the bundle and its source-store snapshot for historical replay. Hashes are not digital signatures.

## External model draft contract

An external model can propose claims using IDs supplied by `search` or a report. Save this JSON and run `import-draft --config draft.json --store workspace`:

```json
{
  "claims": [{
    "text": "Candidate claim",
    "scope": "Specified series and experimental conditions only",
    "citations": [{
      "evidence_id": "evidence_FULL_SHA256",
      "relation": "supports",
      "rationale": "Explain the source-to-claim relationship and its limits"
    }]
  }]
}
```

The entire draft is validated before record creation. Unknown evidence IDs, unsupported relation names, unknown fields, or model-declared review status are rejected. A draft may contain 1–100 claims with at most 100 citations each. Valid entries become **proposed** links only. Source text and transcriptions are inert data: no instructions within a paper are executed, and HTML output is escaped. If you use a remote model outside the engine, you control what excerpts you send it.
