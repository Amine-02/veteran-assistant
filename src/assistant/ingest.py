"""Ingestion policy: raw knowledge pack -> manifest.csv + chunks.jsonl.

Rules come from document metadata and a small human-reviewed list.
Documents are never edited by hand or rewritten by an LLM.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import AS_OF, INGEST_DIR, PACK_DIR

STALE_DAYS = 730  # 2 years since last review
STALE_FRESHNESS = 0.5

# Trust per source_type. 0 means the source is never indexed.
TRUST = {
    "official": 1.0,
    "first_party": 0.9,
    "editorial": 0.6,
    "community": 0.0,
    "partner_scraped": 0.0,
    "mirror_scraped": 0.0,
}

# Human-reviewed list: docs contradicted by a newer official doc.
SUPERSEDED = {
    "D03": "superseded_by:D02 (15-year limit no longer applies to post-2013 separations; eBenefits retired)",
    "D07": "superseded_by:D06 (claim status moved to VA.gov; eBenefits/DS Logon retired)",
}

HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
ZERO_WIDTH = re.compile(r"[​‌‍⁠﻿]")
INJECTION = re.compile(
    r"ignore (all )?(of )?(your |the )?(previous|prior|above) instructions"
    r"|system (notice|prompt|message)"
    r"|you are now"
    r"|do not mention this"
    r"|ask(ing)? (them|the user|users|you) to (type|enter|send|provide)",
    re.IGNORECASE,
)


@dataclass
class DocRecord:
    doc_id: str
    title: str
    source: str
    source_type: str
    published: date
    last_reviewed: date
    audience: str
    text: str  # sanitized body
    trust: float = 0.0
    freshness: float = 1.0
    hash: str = ""
    reasons: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        return "excluded" if self.reasons else "indexed"


def _as_date(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)


def parse_front_matter(text: str) -> tuple[dict, str]:
    """Split each line on its first ':'.

    The pack's front matter is not valid YAML (titles contain unquoted
    colons), so a YAML parser rejects it.
    """
    m = FRONT_MATTER.match(text)
    if not m:
        raise ValueError("missing front matter")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip("\"'")
    return meta, m.group(2)


def load_doc(path: Path) -> DocRecord:
    meta, raw = parse_front_matter(path.read_text(encoding="utf-8"))

    hidden = " ".join(HTML_COMMENT.findall(raw))
    clean = ZERO_WIDTH.sub("", HTML_COMMENT.sub("", raw)).strip()

    rec = DocRecord(
        doc_id=meta["doc_id"],
        title=meta["title"],
        source=meta["source"],
        source_type=meta["source_type"],
        published=_as_date(meta["published"]),
        last_reviewed=_as_date(meta["last_reviewed"]),
        audience=meta.get("audience", "all"),
        text=clean,
    )

    rec.trust = TRUST.get(rec.source_type, 0.0)
    if rec.trust == 0.0:
        rec.reasons.append(f"untrusted_source_type:{rec.source_type}")

    if hidden:
        rec.flags.append("hidden_html_comment_stripped")
    if INJECTION.search(hidden) or INJECTION.search(clean):
        rec.reasons.append("prompt_injection_detected")

    age_days = (AS_OF - rec.last_reviewed).days
    if age_days >= STALE_DAYS:
        rec.freshness = STALE_FRESHNESS
        rec.flags.append(f"stale:{age_days // 365}y_since_review")

    if rec.doc_id in SUPERSEDED:
        rec.reasons.append(SUPERSEDED[rec.doc_id])

    rec.hash = hashlib.sha256(_normalize(clean).encode()).hexdigest()
    return rec


def dedup(records: list[DocRecord]) -> None:
    """Mark exact duplicates. Keep the most trusted, then the oldest doc_id."""
    groups: dict[str, list[DocRecord]] = {}
    for rec in records:
        groups.setdefault(rec.hash, []).append(rec)
    for group in groups.values():
        if len(group) < 2:
            continue
        keep = sorted(group, key=lambda r: (-r.trust, r.doc_id))[0]
        for rec in group:
            if rec is not keep:
                rec.reasons.append(f"duplicate_of:{keep.doc_id}")


def load_pack(pack_dir: Path = PACK_DIR) -> list[DocRecord]:
    records = [load_doc(p) for p in sorted(pack_dir.glob("*.md"))]
    dedup(records)
    return records


def chunk(records: list[DocRecord]) -> list[Document]:
    """Split indexed docs. The title is prepended so it is searchable."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks: list[Document] = []
    for rec in records:
        if rec.status != "indexed":
            continue
        for i, part in enumerate(splitter.split_text(rec.text)):
            chunks.append(
                Document(
                    page_content=f"{rec.title}\n\n{part}",
                    metadata={
                        "doc_id": rec.doc_id,
                        "chunk_id": f"{rec.doc_id}#{i}",
                        "title": rec.title,
                        "source_type": rec.source_type,
                        "last_reviewed": rec.last_reviewed.isoformat(),
                        "trust": rec.trust,
                        "freshness": rec.freshness,
                    },
                )
            )
    return chunks


def write_manifest(records: list[DocRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["doc_id", "title", "source_type", "last_reviewed", "trust",
                    "freshness", "status", "hash", "reasons", "flags"])
        for r in records:
            w.writerow([r.doc_id, r.title, r.source_type, r.last_reviewed.isoformat(),
                        r.trust, r.freshness, r.status, r.hash[:12],
                        "; ".join(r.reasons), "; ".join(r.flags)])


def write_chunks(chunks: list[Document], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps({"text": c.page_content, **c.metadata}) + "\n")


def build() -> tuple[list[DocRecord], list[Document]]:
    records = load_pack()
    return records, chunk(records)


def main() -> None:
    records, chunks = build()
    write_manifest(records, INGEST_DIR / "manifest.csv")
    write_chunks(chunks, INGEST_DIR / "chunks.jsonl")
    indexed = [r for r in records if r.status == "indexed"]
    print(f"{len(records)} docs, {len(indexed)} indexed, {len(chunks)} chunks")
    for r in records:
        if r.status == "excluded" or r.flags:
            print(f"  {r.doc_id} {r.status:8} reasons={r.reasons} flags={r.flags}")


if __name__ == "__main__":
    main()
