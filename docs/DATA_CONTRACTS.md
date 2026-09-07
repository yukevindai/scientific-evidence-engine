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

Dataset rows preserve raw numerical values. Units are validated for recognizability through Pint but are not inferred or silently converted. An unknown unit produces a warning. CSV is a machine-readable interchange format; treat text fields as data when importing into spreadsheet applications.

`row_id` is the zero-based extraction-row position. `paper_id` identifies exact PDF bytes, so two PDF versions can have different IDs despite sharing a DOI. Figure identity includes crop and rendering configuration; label text alone is not a unique identifier. Dataset identity includes all assumptions and versions. Identity hashes establish consistency, not trusted signatures. Bibliographic metadata is never treated as verified publisher metadata.

Changing exported values requires a new extraction record and manifest. Do not edit a CSV and reuse its original provenance claims. Grouping by paper is a conservative publication holdout; neither it nor figure grouping establishes experimental independence or detects republished data automatically.
