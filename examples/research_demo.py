"""Complete synthetic figure -> dataset -> reviewed evidence -> research report chain."""
import argparse

from demo import run
from scientific_evidence_engine import (add_claim, add_evidence, export_report, import_dataset,
                                       index_paper, propose_link, research, review_link)


def run_research(destination):
    root, paper, figure = run(destination)
    store = root / "store"
    index_paper(store, paper["paper_id"])
    manifest = import_dataset(store, root / "dataset")
    evidence = add_evidence(store, {"kind": "figure", "paper_id": paper["paper_id"], "page": 1,
        "label": "Figure 1 endpoints", "locator": {"figure_id": figure["figure_id"]},
        "dataset_id": manifest["dataset_id"], "dataset_rows": [0, manifest["data"]["row_count"] - 1]})
    claim = add_claim(store, "The red series decreases with time", "Only the synthetic demonstration; no experimental or causal claim")
    link = propose_link(store, claim["claim_id"], evidence["evidence_id"], "supports",
                        "The generated line and digitized endpoints have a decreasing trend; bounds are retained.")
    # This scripted review is ONLY for the known synthetic fixture, never for user papers.
    review_link(store, link["link_id"], "accepted", "synthetic-fixture-check", "Reviewed against the line construction in examples/demo.py")
    report = research(store, "Does the red series decrease with time?", [claim["claim_id"]])
    print(export_report(report, store, root / "research-report"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("destination")
    run_research(parser.parse_args().destination)
