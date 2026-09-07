# Validation coverage

| Requirement | Implementation and evidence |
| --- | --- |
| Retain paper, page, figure and exact source bytes | `papers.py`; synthetic PDF roundtrip, crop coordinates, tamper tests |
| Extract curves/numerical values | `digitize.py`; known PDF line recovery, manual points, RGB tracing, absent/ambiguous-column handling |
| Axis definitions, units and digitization uncertainty | `calibration.py`; linear/log10/reversed mappings, interval bounds, nonfinite/degenerate/underflow rejection |
| Export inspectable data/provenance | `exports.py`; CSV/manifest verification, source-record matching, tampered derived-field rejection, source-bound row import |
| Connect claims to exact passages/figures/tables/equations | `evidence.py`; exact quotes and offsets, crop provenance for all visual kinds, quantitative row references |
| Retain support and contradictions | `research.py`; proposed/rejected/contested exclusion, counterevidence beyond top retrieval hits, explicit mixed status |
| Avoid untraceable generated summaries | `research.py`, `reports.py`; template synthesis from reviewed links, unknown-citation rejection, altered-report rejection, escaped source text |
| Reproducible local workflow | CLI integration tests; `examples/research_demo.py` generates the complete chain without external services |
| ChemData Auditor handoff | `dataset.csv` + `auditor-config.json`; local integration smoke test against sibling ChemData Auditor checkout |

Run `python -m pytest -q` and `python examples/research_demo.py outputs/new-demo` after `python -m pip install -e '.[dev]'`. CI runs tests on Python 3.10 and 3.12. The synthetic tests check mathematical and provenance invariants; they are not a benchmark of accuracy across real scientific figures or claim entailment.

External implementation reference for PDF rendering/text extraction: [pypdfium2 Python API](https://pypdfium2.readthedocs.io/en/stable/python_api.html). Axis calibration and bounded uncertainty are implemented directly and documented in `FIGURE_VALIDATOR.md`.
