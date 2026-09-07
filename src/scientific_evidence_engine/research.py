"""Deterministic local retrieval and citation-grounded synthesis of reviewed links."""
import math
import re
from collections import Counter

from .common import fields, finding, integer, text, versions
from .evidence import (add_claim, load_evidence, load_record, propose_link, records,
                       review_state)


def tokens(value):
    return re.findall(r"\w+", value.casefold(), flags=re.UNICODE)


def search(store, query, limit=10):
    text(query, "query")
    integer(limit, "limit", 1)
    if limit > 100:
        raise ValueError("Search limit exceeds 100")
    evidence = [load_evidence(store, r["evidence_id"]) for r in records(store, "evidence")]
    corpus = [tokens(" ".join([e["label"], e["locator"].get("quote", ""), e.get("transcription") or "", e.get("notes") or ""])) for e in evidence]
    query_terms = set(tokens(query))
    if not corpus or not query_terms:
        return []
    mean_length = sum(map(len, corpus)) / len(corpus) or 1
    document_frequency = Counter(word for doc in corpus for word in set(doc))
    hits = []
    for e, doc in zip(evidence, corpus):
        freq = Counter(doc)
        score, matched = 0.0, []
        for word in sorted(query_terms):
            if freq[word]:
                idf = math.log(1 + (len(corpus) - document_frequency[word] + 0.5) / (document_frequency[word] + 0.5))
                score += idf * freq[word] * 2.5 / (freq[word] + 1.5 * (0.25 + 0.75 * len(doc) / mean_length))
                matched.append(word)
        if score:
            hits.append(dict(evidence=e, score=score, matched_terms=matched, status="candidate_not_entailment"))
    return sorted(hits, key=lambda h: (-h["score"], h["evidence"]["evidence_id"]))[:limit]


def assess_claim(store, claim_id):
    claim = load_record(store, "claim", claim_id)
    links = [r for r in records(store, "link") if r["claim_id"] == claim_id]
    all_reviews = list(records(store, "review"))
    details = []
    groups = {key: [] for key in ("supports", "contradicts", "context")}
    for link in links:
        evidence = load_evidence(store, link["evidence_id"])
        reviews = [r for r in all_reviews if r["link_id"] == link["link_id"]]
        state = review_state(reviews)
        details.append(dict(link=link, evidence=evidence, reviews=reviews, review_state=state))
        if state == "accepted":
            groups[link["relation"]].append(evidence["evidence_id"])
    if groups["supports"] and groups["contradicts"]:
        status = "mixed"
        sentence = "Reviewed links include both supporting and contradicting evidence; the claim remains disputed."
    elif groups["contradicts"]:
        status = "contradicted"
        sentence = "Reviewed links identify contradicting evidence; the claim is not supported by this evidence set."
    elif groups["supports"]:
        status = "supported_in_reviewed_set"
        sentence = "Reviewed links identify supporting evidence within the stated scope; this does not establish consensus or independent replication."
    else:
        status = "insufficient_evidence"
        sentence = "No accepted supporting or contradicting link is available; a scientific conclusion is withheld."
    papers = {d["evidence"]["paper_id"] for d in details if d["review_state"] == "accepted" and d["link"]["relation"] != "context"}
    findings = []
    if any(d["review_state"] == "contested" for d in details):
        findings.append(finding("contested_review", "warning", "Multiple active review decisions exist for a link.", "Resolve the review branches before using that link."))
    return dict(claim=claim, status=status, conclusion=sentence, citations=groups, links=details,
                distinct_source_snapshots=len(papers), findings=findings,
                limitation="Evidence relations are reviewer assertions. Multiple PDF snapshots can represent the same study; source count is not an independence count.")


def research(store, query, claim_ids=None, limit=10):
    """Answer from explicit reviewed relationships; search hits remain candidates."""
    hits = search(store, query, limit)
    if claim_ids is None:
        # Discover relevant registered claims, then assess all their links (including counterevidence).
        q = set(tokens(query))
        claim_ids = [c["claim_id"] for c in records(store, "claim") if q.intersection(tokens(c["text"] + " " + c["scope"]))]
    if not isinstance(claim_ids, list) or any(not isinstance(c, str) for c in claim_ids):
        raise ValueError("claim_ids must be an array of claim IDs")
    assessments = [assess_claim(store, c) for c in dict.fromkeys(claim_ids)]
    findings = [finding("retrieval_scope", "info", "Search similarity ranks candidates; it does not establish support, contradiction, or literature completeness.",
                        "Review exact passages/crops and explicitly assess their relation to scoped claims.")]
    if not assessments:
        findings.append(finding("no_reviewed_claim", "warning", "No relevant registered claim was found; no scientific conclusion was generated.", "Register a scoped claim and review its evidence links."))
    citations = {h["evidence"]["evidence_id"]: h["evidence"] for h in hits}
    for a in assessments:
        for detail in a["links"]:
            e = detail["evidence"]
            citations[e["evidence_id"]] = e
    return dict(schema_version="1.0", question=query, method="local_BM25_candidates_and_reviewed_link_synthesis",
                retrieval_config={"limit": limit, "k1": 1.5, "b": 0.75, "tokenization": "unicode_word_casefold", "claim_ids": claim_ids},
                candidates=hits, assessments=assessments, citations=citations, findings=findings, software=versions(),
                generated_by="deterministic_local_agent", external_model_used=False)


def import_draft(store, draft):
    """Accept structured model/user suggestions, never model-declared review decisions."""
    fields(draft, {"claims"})
    if not isinstance(draft["claims"], list) or not draft["claims"] or len(draft["claims"]) > 100:
        raise ValueError("Draft requires 1–100 claims")
    # Validate the entire draft and all evidence references before creating any records.
    for claim in draft["claims"]:
        fields(claim, {"text", "scope", "citations"})
        text(claim["text"], "claim")
        text(claim["scope"], "scope")
        if not isinstance(claim["citations"], list) or len(claim["citations"]) > 100:
            raise ValueError("citations must be an array with at most 100 entries")
        for cite in claim["citations"]:
            fields(cite, {"evidence_id", "relation", "rationale"})
            if cite["relation"] not in {"supports", "contradicts", "context"}:
                raise ValueError("Unknown evidence relation")
            text(cite["rationale"], "rationale")
            load_evidence(store, cite["evidence_id"])
    created = []
    for claim in draft["claims"]:
        c = add_claim(store, claim["text"], claim["scope"])
        links = [propose_link(store, c["claim_id"], cite["evidence_id"], cite["relation"], cite["rationale"], origin="imported_draft") for cite in claim["citations"]]
        created.append(dict(claim=c, links=links))
    return dict(created=created, review_status="proposed_only", instruction="Review every relation before drawing conclusions.")
