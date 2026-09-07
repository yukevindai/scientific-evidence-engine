"""Self-contained research reports with escaped evidence, IDs and precise locators."""
import html
import json
from pathlib import Path

from .common import new_directory, read_json, safe_path, sha256, write_json


def markdown(report):
    def esc(value):
        value = html.escape(str(value), quote=True)
        for ch in ("\\", "`", "*", "_", "[", "]", "#", "|"):
            value = value.replace(ch, "\\" + ch)
        return value.replace("\r", "").replace("\n", " ")
    lines = ["# Scientific evidence report", "", esc(report["question"]), "",
             "Generated locally from registered evidence and explicit review decisions. Retrieval scores do not measure truth.", ""]
    for assessment in report["assessments"]:
        claim = assessment["claim"]
        lines += ["## " + esc(claim["text"]), "", "Scope: " + esc(claim["scope"]), "",
                  "Status: " + esc(assessment["status"]), "", esc(assessment["conclusion"]), ""]
        for detail in assessment["links"]:
            link = detail["link"]
            lines += [f"- {esc(link['relation'])} ({esc(detail['review_state'])}): {esc(link['evidence_id'])}. {esc(link['rationale'])}"]
        lines += [""]
    lines += ["## Exact evidence references", ""]
    for eid, e in report["citations"].items():
        loc = e["locator"]
        lines += ["### " + esc(e["label"]), "", "Evidence ID: " + esc(eid), "",
                  f"Source: {esc(e['paper_id'])}; page {e['page']}; type {esc(e['kind'])}.", "",
                  "Locator: " + esc(json.dumps({k: v for k, v in loc.items() if k != "quote"}, ensure_ascii=False)), ""]
        if "quote" in loc:
            lines += ["> " + esc(loc["quote"]), ""]
        if e.get("transcription"):
            lines += ["Unverified transcription: " + esc(e["transcription"]), ""]
        if e.get("dataset"):
            lines += ["Digitized dataset: " + esc(e["dataset"]["dataset_id"]), "",
                      "Selected rows and uncertainty: " + esc(json.dumps(e["dataset"], ensure_ascii=False)), ""]
    lines += ["## Review actions", ""]
    for f in report["findings"]:
        lines += [f"- {esc(f['message'])} {esc(f['recommended_action'])}"]
    return "\n".join(lines) + "\n"


def export_report(report, store, destination):
    from .papers import load_figure, load_paper
    from .evidence import load_evidence
    from .research import research
    from .exports import load_dataset
    expected = research(store, report["question"], report["retrieval_config"]["claim_ids"], report["retrieval_config"]["limit"])
    if expected != report:
        raise ValueError("Report differs from current evidence and reviewed claim assessments; regenerate it")
    # Revalidate citation snapshots at export time and include crops for visual inspection.
    images, sources, datasets = {}, {}, {}
    for eid, e in report["citations"].items():
        if load_evidence(store, eid) != e:
            raise ValueError("Report citation no longer matches source evidence")
        _, paper, _ = load_paper(store, e["paper_id"])
        sources[e["paper_id"]] = paper
        if "figure_id" in e["locator"]:
            fid = e["locator"]["figure_id"]
            _, image = load_figure(store, fid)
            images[fid] = image
        if e.get("dataset"):
            did = e["dataset"]["dataset_id"]
            datasets[did] = load_dataset(store, did)
    md = markdown(report)
    page = html_report(report)
    with new_directory(destination) as out:
        write_json(out / "report.json", report)
        write_json(out / "sources.json", sources)
        (out / "report.md").write_bytes(md.encode("utf-8"))
        (out / "report.html").write_bytes(page.encode("utf-8"))
        if images:
            (out / "figures").mkdir()
            for fid, image in images.items():
                image.save(out / "figures" / f"{fid}.png")
        if datasets:
            (out / "datasets").mkdir()
            for did in datasets:
                folder = out / "datasets" / did
                folder.mkdir()
                for name in ("dataset.csv", "manifest.json", "auditor-config.json"):
                    (folder / name).write_bytes((Path(store) / "datasets" / did / name).read_bytes())
        files = {str(p.relative_to(out)): sha256(p.read_bytes()) for p in sorted(out.rglob("*")) if p.is_file()}
        write_json(out / "report-manifest.json", {"schema_version": "1.0", "files": files, "source_pdfs_included": False})
    return {"output": str(Path(destination)), "citations": len(report["citations"]), "files": list(files)}


def html_report(report):
    esc = lambda v: html.escape(str(v), quote=True)
    body = ['<h1>Scientific evidence report</h1>', '<p class="question">' + esc(report["question"]) + '</p>',
            '<p>Local evidence retrieval and reviewed claim synthesis. Candidate similarity does not measure truth.</p>']
    for a in report["assessments"]:
        body += ['<section><h2>' + esc(a["claim"]["text"]) + '</h2>',
                 '<p><strong>Scope:</strong> ' + esc(a["claim"]["scope"]) + '</p>',
                 '<p><strong>Status:</strong> ' + esc(a["status"]) + '</p><p>' + esc(a["conclusion"]) + '</p><ul>']
        for d in a["links"]:
            eid = d["evidence"]["evidence_id"]
            body += [f'<li><a href="#{eid}">{esc(d["evidence"]["label"])}</a> — {esc(d["link"]["relation"])} ({esc(d["review_state"])}): {esc(d["link"]["rationale"])}</li>']
        body += ['</ul></section>']
    body += ['<h2>Exact evidence references</h2>']
    for eid, e in report["citations"].items():
        body += [f'<section id="{eid}"><h3>{esc(e["label"])}</h3><p><code>{esc(eid)}</code></p>',
                 f'<p>Paper <code>{esc(e["paper_id"])}</code>, page {e["page"]}; {esc(e["kind"])}.</p>']
        loc = e["locator"]
        if "quote" in loc:
            body += ['<blockquote>' + esc(loc["quote"]) + '</blockquote>', f'<p>Characters {loc["start"]}–{loc["end"]} in retained page text.</p>']
        else:
            fid = loc["figure_id"]
            body += [f'<figure><img src="figures/{fid}.png" alt="{esc(e["label"])}"><figcaption>Page-pixel crop {esc(loc["crop"])}; scale {loc["render_scale"]}.</figcaption></figure>']
        if e.get("transcription"):
            body += ['<p><strong>Unverified transcription:</strong> ' + esc(e["transcription"]) + '</p>']
        if e.get("dataset"):
            data = e["dataset"]
            body += [f'<p>Dataset <a href="datasets/{data["dataset_id"]}/dataset.csv">{data["dataset_id"]}</a></p>',
                     '<table><thead><tr><th>Row</th><th>x</th><th>x bounds</th><th>y</th><th>y bounds</th></tr></thead><tbody>']
            for p in data["points"]:
                body += [f'<tr><td>{p["row_id"]}</td><td>{esc(p["x"])} {esc(p["x_unit"])}</td><td>{p["x_lower"]}–{p["x_upper"]}</td><td>{esc(p["y"])} {esc(p["y_unit"])}</td><td>{p["y_lower"]}–{p["y_upper"]}</td></tr>']
            body += ['</tbody></table><p>' + esc(data["uncertainty_model"]) + '</p>']
        body += ['</section>']
    body += ['<h2>Review actions</h2><ul>']
    for f in report["findings"]:
        body += ['<li>' + esc(f["message"]) + ' ' + esc(f["recommended_action"]) + '</li>']
    body += ['</ul>']
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Scientific evidence report</title><style>body{max-width:1000px;margin:2rem auto;padding:1rem;font:16px/1.55 system-ui;color:#17232d;background:#f7fafc}section{background:white;padding:1.3rem;margin:1rem 0;border:1px solid #d8e1e8;border-radius:8px}code{overflow-wrap:anywhere;font-size:.8em}blockquote{border-left:3px solid #257583;padding-left:1rem;white-space:pre-wrap}img{max-width:100%}table{border-collapse:collapse;width:100%;font-size:.85em}th,td{border:1px solid #d8e1e8;padding:.5rem;text-align:left}a{color:#126b80}.question{font-size:1.3em}p{overflow-wrap:anywhere}</style><body>' + ''.join(body) + '</body></html>'


def verify_report(directory, store=None):
    manifest = read_json(Path(directory) / "report-manifest.json")
    files = manifest["files"]
    if not {"report.json", "report.md", "report.html", "sources.json"} <= set(files):
        raise ValueError("Report manifest lacks required files")
    for relative, digest in files.items():
        if sha256(safe_path(directory, relative).read_bytes()) != digest:
            raise ValueError(f"Report file hash mismatch: {relative}")
    report = read_json(Path(directory) / "report.json")
    if (Path(directory) / "report.md").read_bytes() != markdown(report).encode("utf-8") or (Path(directory) / "report.html").read_bytes() != html_report(report).encode("utf-8"):
        raise ValueError("Human-readable report differs from structured evidence")
    expected_files = {"report.json", "report.md", "report.html", "sources.json"}
    for evidence in report["citations"].values():
        loc = evidence["locator"]
        if "figure_id" in loc:
            relative = f'figures/{loc["figure_id"]}.png'
            expected_files.add(relative)
            if sha256(safe_path(directory, relative).read_bytes()) != loc["image_sha256"]:
                raise ValueError("Report crop differs from cited source image")
        if evidence.get("dataset"):
            from .exports import verify_export
            did = evidence["dataset"]["dataset_id"]
            folder = safe_path(directory, f"datasets/{did}")
            if verify_export(folder, store)["dataset_id"] != did:
                raise ValueError("Report dataset identity mismatch")
            expected_files.update(f"datasets/{did}/{name}" for name in ("dataset.csv", "manifest.json", "auditor-config.json"))
    if set(files) != expected_files:
        raise ValueError("Report manifest file inventory differs from cited artifacts")
    if store is not None:
        from .research import research
        from .papers import load_paper
        expected = research(store, report["question"], report["retrieval_config"]["claim_ids"], report["retrieval_config"]["limit"])
        if report != expected:
            raise ValueError("Report differs from current source/review state")
        sources = {e["paper_id"]: load_paper(store, e["paper_id"])[1] for e in report["citations"].values()}
        if read_json(Path(directory) / "sources.json") != sources:
            raise ValueError("Report sources differ from retained paper records")
    return dict(valid=True, files=len(files), current_source_state_verified=store is not None,
                note="Bundle hashes prove consistency, not publisher authenticity or reviewer identity.")
