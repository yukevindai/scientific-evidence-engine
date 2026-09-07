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
        else:
            result = verify_export(args.bundle, args.store)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
        print(f"evidence-engine: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
