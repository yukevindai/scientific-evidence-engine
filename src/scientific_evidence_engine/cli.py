"""Unified local workflow; no remote model, network upload, or API key required."""
import argparse
import json
import sys

from .common import read_json
from .papers import ingest_paper, render_figure
from .digitize import digitize
from .exports import export_dataset, verify_export


def parser():
    p = argparse.ArgumentParser(prog="evidence-engine")
    sub = p.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest", help="Snapshot a local PDF and its text layer")
    ingest.add_argument("pdf")
    ingest.add_argument("--store", required=True)
    ingest.add_argument("--metadata", required=True)
    render = sub.add_parser("render", help="Render a page or figure crop from registered PDF bytes")
    render.add_argument("--store", required=True)
    render.add_argument("--paper", required=True)
    render.add_argument("--page", type=int, required=True)
    render.add_argument("--label", required=True)
    render.add_argument("--scale", type=float, default=2)
    render.add_argument("--crop", nargs=4, type=int)
    dig = sub.add_parser("digitize", help="Calibrate and extract a figure into an export bundle")
    dig.add_argument("--store", required=True)
    dig.add_argument("--figure", required=True)
    dig.add_argument("--config", required=True)
    dig.add_argument("--output", required=True)
    verify = sub.add_parser("verify", help="Verify exported bytes and provenance references")
    verify.add_argument("bundle")
    verify.add_argument("--store")
    index = sub.add_parser("index", help="Register exact searchable passage spans")
    index.add_argument("--store", required=True)
    index.add_argument("--paper", required=True)
    index.add_argument("--chunk-size", type=int, default=1000)
    evidence = sub.add_parser("add-evidence", help="Register an exact passage or visual evidence crop")
    evidence.add_argument("--store", required=True)
    evidence.add_argument("--config", required=True)
    dataset = sub.add_parser("import-dataset", help="Register a verified digitization export for quantitative citations")
    dataset.add_argument("--store", required=True)
    dataset.add_argument("bundle")
    claim = sub.add_parser("claim", help="Register a scientific claim with explicit scope")
    claim.add_argument("--store", required=True)
    claim.add_argument("--text", required=True)
    claim.add_argument("--scope", required=True)
    link = sub.add_parser("link", help="Propose an evidence relation; does not approve it")
    link.add_argument("--store", required=True)
    link.add_argument("--claim", required=True)
    link.add_argument("--evidence", required=True)
    link.add_argument("--relation", choices=["supports", "contradicts", "context"], required=True)
    link.add_argument("--rationale", required=True)
    review = sub.add_parser("review", help="Record an explicit review decision for a proposed link")
    review.add_argument("--store", required=True)
    review.add_argument("--link", required=True)
    review.add_argument("--decision", choices=["accepted", "rejected"], required=True)
    review.add_argument("--reviewer", required=True)
    review.add_argument("--rationale", required=True)
    review.add_argument("--supersedes")
    search = sub.add_parser("search", help="Rank candidate evidence without asserting entailment")
    search.add_argument("query")
    search.add_argument("--store", required=True)
    search.add_argument("--limit", type=int, default=10)
    research = sub.add_parser("research", help="Synthesize reviewed claims into traceable reports")
    research.add_argument("query")
    research.add_argument("--store", required=True)
    research.add_argument("--claim", action="append")
    research.add_argument("--limit", type=int, default=10)
    research.add_argument("--output", required=True)
    draft = sub.add_parser("import-draft", help="Validate model-proposed citations without approving them")
    draft.add_argument("--store", required=True)
    draft.add_argument("--config", required=True)
    verify_report = sub.add_parser("verify-report", help="Verify report bundle hashes and optionally current source/review state")
    verify_report.add_argument("bundle")
    verify_report.add_argument("--store")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "ingest":
            result = ingest_paper(args.pdf, args.store, read_json(args.metadata))
        elif args.command == "render":
            result = render_figure(args.store, args.paper, args.page, args.label, args.scale, args.crop)
        elif args.command == "digitize":
            extracted = digitize(args.store, args.figure, read_json(args.config))
            result = export_dataset(extracted, args.store, args.output)
        elif args.command == "verify":
            result = verify_export(args.bundle, args.store)
        else:
            from .evidence import add_claim, add_evidence, index_paper, propose_link, review_link
            from .exports import import_dataset
            from .research import search, research, import_draft
            from .reports import export_report, verify_report
            if args.command == "verify-report":
                result = verify_report(args.bundle, args.store)
            elif args.command == "index":
                result = index_paper(args.store, args.paper, args.chunk_size)
            elif args.command == "add-evidence":
                result = add_evidence(args.store, read_json(args.config))
            elif args.command == "import-dataset":
                result = import_dataset(args.store, args.bundle)
            elif args.command == "claim":
                result = add_claim(args.store, args.text, args.scope)
            elif args.command == "link":
                result = propose_link(args.store, args.claim, args.evidence, args.relation, args.rationale)
            elif args.command == "review":
                result = review_link(args.store, args.link, args.decision, args.reviewer, args.rationale, args.supersedes)
            elif args.command == "search":
                result = search(args.store, args.query, args.limit)
            elif args.command == "research":
                result = export_report(research(args.store, args.query, args.claim, args.limit), args.store, args.output)
            else:
                result = import_draft(args.store, read_json(args.config))
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
        print(f"evidence-engine: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
