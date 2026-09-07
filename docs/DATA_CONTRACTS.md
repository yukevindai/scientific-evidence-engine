# Data contracts, schema version 1.0

All JSON is UTF-8, rejects duplicate keys and non-finite values, and uses explicit `schema_version`. Public functions return JSON-compatible dictionaries. IDs use the full SHA-256 digest, not shortened labels. Canonical content identities use sorted JSON keys, UTF-8, no ASCII escaping, no NaN, and compact separators.

| Artifact | Required evidence |
| --- | --- |
| `papers/paper_SHA/paper.json` | Original PDF SHA-256, 1-based page count, unverified bibliographic metadata, per-page text paths and hashes, software versions |
| `figures/figure_SHA/figure.json` | Paper ID/hash, page, figure label, render scale, page size, crop pixel bounds, coordinate system, image size/hash |
| Dataset extraction | Figure record, full configuration, series, method, nominal pixels/values and uncertainty bounds, findings, review status |
| `dataset.csv` | One row per extracted point, source/grouping IDs, axis labels/units, provenance, row ID and extraction method |
| `manifest.json` | CSV digest, column order and row count, original source metadata, figure and full extraction evidence, Auditor configuration |
| `auditor-config.json` | Numeric and unit checks, exact duplication keys, provenance requirements, publication/figure groups |
| `evidence/evidence_SHA/record.json` | Evidence kind, source snapshot, page, exact quote offsets or visual crop, optional verified digitized row references |
| `claims/claim_SHA/record.json` | Scientific statement and explicit scope |
| `links/link_SHA/record.json` | Claim/evidence IDs, proposed relation, rationale, origin; always initially proposed |
| `reviews/review_SHA/record.json` | Link ID, accepted/rejected decision, reviewer assertion, rationale, optional superseded review |
| Research report bundle | Exact citations, all relevant links/reviews, conditional conclusion status, retrieval config, source metadata, cited crops/datasets and file hashes |

Dataset rows preserve raw numerical values. Units are validated for recognizability through Pint but are not inferred or silently converted. An unknown unit produces a warning. CSV is a machine-readable interchange format; treat text fields as data when importing into spreadsheet applications.

`row_id` is the zero-based extraction-row position. `paper_id` identifies exact PDF bytes, so two PDF versions can have different IDs despite sharing a DOI. Figure identity includes crop and rendering configuration; label text alone is not a unique identifier. Dataset identity includes all assumptions and versions. Identity hashes establish consistency, not trusted signatures. Bibliographic metadata is never treated as verified publisher metadata.

Changing exported values requires a new extraction record and manifest. Do not edit a CSV and reuse its original provenance claims. Grouping by paper is a conservative publication holdout; neither it nor figure grouping establishes experimental independence or detects republished data automatically.

Make a separate copy of `auditor-config.json` when customizing downstream audit checks; verification expects the bundled configuration to match its manifest. The contracts are this project's versioned interchange format, not a claim of conformance to an external scientific ontology. CSV and UTF-8 JSON keep the data accessible without this package.
