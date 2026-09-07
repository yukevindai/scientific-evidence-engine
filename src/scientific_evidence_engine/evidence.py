"""Content-addressed evidence, claims, proposed links, and append-only human review."""
from pathlib import Path

from .common import (fields, identity, integer, new_directory, read_json, sha256,
                     text, valid_id, versions, write_json)
from .papers import load_figure, load_paper, page_text

COLLECTIONS = {"evidence": "evidence", "claim": "claims", "link": "links", "review": "reviews"}


def save_record(store, prefix, record):
    value = dict(record)
    key = prefix + "_id"
    value[key] = identity(prefix, value)
    root = Path(store) / COLLECTIONS[prefix] / value[key]
    if root.exists():
        if read_json(root / "record.json") != value:
            raise ValueError("Existing record differs from its content identity")
    else:
        with new_directory(root) as out:
            write_json(out / "record.json", value)
    return value


def load_record(store, prefix, record_id):
    valid_id(record_id, prefix)
    record = read_json(Path(store) / COLLECTIONS[prefix] / record_id / "record.json")
    if record.get(prefix + "_id") != record_id or identity(prefix, {k: v for k, v in record.items() if k != prefix + "_id"}) != record_id:
        raise ValueError(f"{prefix} record hash mismatch")
    return record


def records(store, prefix):
    root = Path(store) / COLLECTIONS[prefix]
    for path in sorted(root.glob(f"{prefix}_*/record.json")):
        yield load_record(store, prefix, path.parent.name)


def add_evidence(store, spec):
    fields(spec, {"kind", "paper_id", "page", "label", "locator"}, {"transcription", "notes", "dataset_id", "dataset_rows"})
    if spec["kind"] not in {"passage", "figure", "table", "equation"}:
        raise ValueError("Evidence kind must be passage, figure, table, or equation")
    text(spec["label"], "evidence label")
    for k in ("transcription", "notes"):
        if k in spec:
            text(spec[k], k)
    _, paper, _ = load_paper(store, spec["paper_id"])
    page = integer(spec["page"], "page", 1)
    if page > paper["page_count"]:
        raise ValueError("Evidence page outside paper")
    loc = spec["locator"]
    if spec["kind"] == "passage":
        fields(loc, {"start", "end", "quote"})
        start, end = integer(loc["start"], "start"), integer(loc["end"], "end", 1)
        source = page_text(store, spec["paper_id"], page)
        if not start < end <= len(source) or source[start:end] != loc["quote"] or not loc["quote"].strip():
            raise ValueError("Passage quote must exactly match the source text at its character offsets")
        if "transcription" in spec:
            raise ValueError("Passages use exact quotes, not replacement transcriptions")
        locator = dict(loc, coordinate_system="unicode_codepoint_offsets_in_retained_text", text_sha256=sha256(source.encode()))
    else:
        fields(loc, {"figure_id"})
        figure, _ = load_figure(store, loc["figure_id"])
        if figure["paper_id"] != spec["paper_id"] or figure["page"] != page:
            raise ValueError("Visual evidence crop belongs to a different source or page")
        locator = dict(loc, crop=figure["crop"], render_scale=figure["scale"],
                       coordinate_system=figure["coordinate_system"], image_sha256=figure["image_sha256"])
    data = None
    if "dataset_rows" in spec and "dataset_id" not in spec:
        raise ValueError("dataset_rows requires dataset_id")
    if "dataset_id" in spec:
        from .exports import load_dataset
        dataset = load_dataset(store, spec["dataset_id"])
        if spec["kind"] == "passage" or dataset["figure"]["figure_id"] != loc["figure_id"]:
            raise ValueError("Dataset evidence must use its original figure crop")
        selected = spec.get("dataset_rows", list(range(len(dataset["extraction"]["rows"]))))
        if not isinstance(selected, list) or not selected:
            raise ValueError("dataset_rows must be unique nonempty row positions")
        for row in selected:
            integer(row, "dataset row")
            if row >= len(dataset["extraction"]["rows"]):
                raise ValueError("Dataset row outside extraction")
        if len(set(selected)) != len(selected):
            raise ValueError("dataset_rows must be unique")
        data = dict(dataset_id=spec["dataset_id"], row_positions=selected,
                    points=[dataset["extraction"]["rows"][i] for i in selected],
                    uncertainty_model=dataset["extraction"]["uncertainty_model"])
    record = dict(schema_version="1.0", kind=spec["kind"], paper_id=spec["paper_id"], paper_sha256=paper["sha256"],
                  page=page, label=spec["label"], locator=locator,
                  transcription=spec.get("transcription"), transcription_status="user_supplied_unverified" if "transcription" in spec else "not_supplied",
                  notes=spec.get("notes"), dataset=data, software=versions())
    return save_record(store, "evidence", record)


def load_evidence(store, evidence_id):
    record = load_record(store, "evidence", evidence_id)
    _, paper, _ = load_paper(store, record["paper_id"])
    if record["paper_sha256"] != paper["sha256"]:
        raise ValueError("Evidence paper hash mismatch")
    loc = record["locator"]
    if record["kind"] == "passage":
        source = page_text(store, record["paper_id"], record["page"])
        if sha256(source.encode()) != loc["text_sha256"] or source[loc["start"]:loc["end"]] != loc["quote"]:
            raise ValueError("Evidence quote no longer matches source snapshot")
    else:
        figure, _ = load_figure(store, loc["figure_id"])
        if (figure["image_sha256"] != loc["image_sha256"] or figure["paper_id"] != record["paper_id"]
                or figure["page"] != record["page"] or figure["crop"] != loc["crop"] or figure["scale"] != loc["render_scale"]):
            raise ValueError("Evidence figure provenance mismatch")
    if record.get("dataset"):
        from .exports import load_dataset
        data = record["dataset"]
        manifest = load_dataset(store, data["dataset_id"])
        if manifest["figure"]["figure_id"] != loc.get("figure_id") or [manifest["extraction"]["rows"][i] for i in data["row_positions"]] != data["points"]:
            raise ValueError("Evidence dataset points differ from manifest")
    return record


def index_paper(store, paper_id, chunk_size=1000):
    """Index text spans only; no implied claim entailment or scientific interpretation."""
    integer(chunk_size, "chunk_size", 50)
    if chunk_size > 10000:
        raise ValueError("chunk_size exceeds 10000 codepoints")
    _, paper, _ = load_paper(store, paper_id)
    found, skipped = [], []
    for page in range(1, paper["page_count"] + 1):
        source = page_text(store, paper_id, page)
        if not source.strip():
            skipped.append(page)
            continue
        start = 0
        while start < len(source):
            end = min(start + chunk_size, len(source))
            if end < len(source):
                boundary = source.rfind(" ", start + chunk_size // 2, end)
                if boundary > start:
                    end = boundary
            if source[start:end].strip():
                found.append(add_evidence(store, dict(kind="passage", paper_id=paper_id, page=page,
                    label=f"Page {page}, characters {start}:{end}", locator={"start": start, "end": end, "quote": source[start:end]}))["evidence_id"])
            start = end
    return dict(evidence_ids=found, pages_without_text=skipped, method="exact_text_chunks", chunk_size=chunk_size)


def add_claim(store, statement, scope):
    return save_record(store, "claim", dict(schema_version="1.0", text=text(statement, "claim"), scope=text(scope, "scope")))


def propose_link(store, claim_id, evidence_id, relation, rationale, origin="user"):
    load_record(store, "claim", claim_id)
    load_evidence(store, evidence_id)
    if relation not in {"supports", "contradicts", "context"}:
        raise ValueError("relation must be supports, contradicts, or context")
    return save_record(store, "link", dict(schema_version="1.0", claim_id=claim_id, evidence_id=evidence_id,
                       relation=relation, rationale=text(rationale, "rationale"), origin=text(origin, "origin"), status="proposed"))


def review_link(store, link_id, decision, reviewer, rationale, supersedes=None):
    load_record(store, "link", link_id)
    if decision not in {"accepted", "rejected"}:
        raise ValueError("decision must be accepted or rejected")
    if supersedes is not None:
        prior = load_record(store, "review", supersedes)
        if prior["link_id"] != link_id:
            raise ValueError("Cannot supersede a review of another link")
    return save_record(store, "review", dict(schema_version="1.0", link_id=link_id, decision=decision,
                       reviewer=text(reviewer, "reviewer"), rationale=text(rationale, "review rationale"), supersedes=supersedes))


def review_state(reviews):
    """Conflicting review branches remain contested, never silently last-writer-wins."""
    replaced = {r["supersedes"] for r in reviews if r["supersedes"]}
    leaves = [r for r in reviews if r["review_id"] not in replaced]
    if not leaves:
        return "unreviewed"
    if len(leaves) != 1:
        return "contested"
    return leaves[0]["decision"]
