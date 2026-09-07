"""Retain original PDF bytes, exact extracted text, and reproducible figure crops."""
import io
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

from .common import (fields, identity, integer, new_directory, number, read_json,
                     safe_path, sha256, text, valid_id, versions, write_json)

MAX_PDF_BYTES = 100 * 1024 * 1024
MAX_RENDER_PIXELS = 25_000_000


def ingest_paper(pdf_path, store, metadata):
    fields(metadata, {"title"}, {"doi", "url", "authors", "year", "license", "notes"})
    text(metadata["title"], "title")
    for key in ("doi", "url", "license", "notes"):
        if key in metadata:
            text(metadata[key], key)
    if "year" in metadata:
        integer(metadata["year"], "year", 1)
    if "authors" in metadata and (not isinstance(metadata["authors"], list) or any(not isinstance(a, str) or not a.strip() for a in metadata["authors"])):
        raise ValueError("authors must be an array of names")
    with Path(pdf_path).open("rb") as stream:
        raw = stream.read(MAX_PDF_BYTES + 1)
    if len(raw) > MAX_PDF_BYTES:
        raise ValueError("PDF exceeds 100 MiB input budget")
    digest = sha256(raw)
    paper_id = "paper_" + digest
    with pdfium.PdfDocument(raw) as pdf:
        if not 0 < len(pdf) <= 2000:
            raise ValueError("PDF must have 1–2000 pages")
        record = dict(schema_version="1.0", paper_id=paper_id, sha256=digest,
                      metadata=metadata, metadata_status="user_supplied_unverified", page_count=len(pdf),
                      original="original.pdf", pages=[], software=versions())
        with new_directory(Path(store) / "papers" / paper_id) as out:
            (out / "original.pdf").write_bytes(raw)
            (out / "pages").mkdir()
            for i in range(len(pdf)):
                page = pdf[i]
                tp = page.get_textpage()
                try:
                    content = tp.get_text_range()
                    file = f"pages/{i + 1:04}.txt"
                    encoded = content.encode("utf-8")
                    (out / file).write_bytes(encoded)
                    record["pages"].append(dict(page=i + 1, text_path=file, text_sha256=sha256(encoded),
                                                 size_points=list(page.get_size()),
                                                 extraction="pdfium_text_layer", has_text=bool(content.strip())))
                finally:
                    tp.close()
                    page.close()
            write_json(out / "paper.json", record)
    return record


def load_paper(store, paper_id):
    valid_id(paper_id, "paper")
    root = Path(store) / "papers" / paper_id
    record = read_json(root / "paper.json")
    raw = safe_path(root, record["original"]).read_bytes()
    if sha256(raw) != record["sha256"] or "paper_" + sha256(raw) != paper_id or record["paper_id"] != paper_id:
        raise ValueError("Paper snapshot hash mismatch")
    return root, record, raw


def page_text(store, paper_id, page):
    root, paper, _ = load_paper(store, paper_id)
    integer(page, "page", 1)
    if page > paper["page_count"]:
        raise ValueError("Page outside document")
    entry = paper["pages"][page - 1]
    raw = safe_path(root, entry["text_path"]).read_bytes()
    if sha256(raw) != entry["text_sha256"]:
        raise ValueError("Extracted text hash mismatch")
    return raw.decode("utf-8")


def render_figure(store, paper_id, page, label, scale=2.0, crop=None):
    _, paper, raw = load_paper(store, paper_id)
    integer(page, "page", 1)
    text(label, "figure label")
    scale = number(scale, "scale", 0.01)
    if page > paper["page_count"]:
        raise ValueError("Page outside document")
    with pdfium.PdfDocument(raw) as pdf:
        pg = pdf[page - 1]
        try:
            width, height = pg.get_size()
            if (width * scale + 1) * (height * scale + 1) > MAX_RENDER_PIXELS:
                raise ValueError("Render exceeds 25 million pixel budget")
            bitmap = pg.render(scale=scale)
            try:
                im = bitmap.to_pil().convert("RGB")
            finally:
                bitmap.close()
        finally:
            pg.close()
    if crop is None:
        crop = [0, 0, *im.size]
    if not isinstance(crop, list) or len(crop) != 4:
        raise ValueError("crop needs four integer page-pixel coordinates")
    for v in crop:
        integer(v, "crop")
    l, t, r, b = crop
    if not (0 <= l < r <= im.width and 0 <= t < b <= im.height):
        raise ValueError("Crop outside rendered page")
    cropped = im.crop(crop)
    buffer = io.BytesIO()
    cropped.save(buffer, format="PNG")
    png = buffer.getvalue()
    record = dict(schema_version="1.0", paper_id=paper_id, paper_sha256=paper["sha256"],
                  page=page, label=label, scale=scale, page_size_points=[width, height],
                  rendered_page_size=list(im.size), crop=crop, coordinate_system="top_left_page_pixels",
                  image_size=list(cropped.size), image_sha256=sha256(png), image="image.png", software=versions())
    record["figure_id"] = identity("figure", record)
    with new_directory(Path(store) / "figures" / record["figure_id"]) as out:
        (out / "image.png").write_bytes(png)
        write_json(out / "figure.json", record)
    return record


def load_figure(store, figure_id):
    valid_id(figure_id, "figure")
    root = Path(store) / "figures" / figure_id
    record = read_json(root / "figure.json")
    if record.get("figure_id") != figure_id or identity("figure", {k: v for k, v in record.items() if k != "figure_id"}) != figure_id:
        raise ValueError("Figure metadata hash mismatch")
    _, paper, _ = load_paper(store, record["paper_id"])
    if paper["sha256"] != record["paper_sha256"]:
        raise ValueError("Figure refers to different paper bytes")
    png = safe_path(root, record["image"]).read_bytes()
    if sha256(png) != record["image_sha256"]:
        raise ValueError("Figure image hash mismatch")
    with Image.open(io.BytesIO(png)) as im:
        image = im.convert("RGB")
    if list(image.size) != record["image_size"]:
        raise ValueError("Figure image size mismatch")
    return record, image
