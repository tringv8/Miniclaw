from __future__ import annotations

import argparse
import json
import re
import sqlite3
import ssl
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


DEFAULT_DB = Path.home() / ".miniclaw" / "benchmark_results.db"
RUN_ID = "book1_import"
ARXIV_OAI = "https://oaipmh.arxiv.org/oai"
OAI_NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "ax": "http://arxiv.org/OAI/arXiv/",
}


@dataclass(frozen=True)
class PaperMeta:
    arxiv_id: str
    title: str
    authors: list[str]
    published: str
    link: str
    doi: str
    abstract: str


def _base_id(arxiv_id: str) -> str:
    return re.sub(r"v\d+$", "", arxiv_id.strip())


def _extract_ids(raw: str) -> list[str]:
    ids: list[str] = []
    for match in re.finditer(r"arxiv\.org/(?:abs|pdf)/([\w.]+)", raw or "", re.IGNORECASE):
        arxiv_id = match.group(1).rstrip("/")
        if arxiv_id not in ids:
            ids.append(arxiv_id)
    return ids


def _blocks(raw: str) -> list[str]:
    return [
        block.strip()
        for block in re.split(r"(?m)^\s*(?=(?:\*\*)?\[?\d+\]?\.\s*)", raw or "")
        if block.strip()
    ]


def _fetch_oai(params: dict[str, str]) -> bytes:
    req = urllib.request.Request(
        f"{ARXIV_OAI}?{urllib.parse.urlencode(params)}",
        headers={"User-Agent": "Miniclaw-Book1-Backfill/1.0"},
    )
    with urllib.request.urlopen(req, timeout=60, context=ssl._create_unverified_context()) as resp:
        return resp.read()


def _author_name(author_node: ET.Element) -> str:
    keyname = (author_node.findtext("ax:keyname", default="", namespaces=OAI_NS) or "").strip()
    forenames = (author_node.findtext("ax:forenames", default="", namespaces=OAI_NS) or "").strip()
    suffix = (author_node.findtext("ax:suffix", default="", namespaces=OAI_NS) or "").strip()
    name = " ".join(part for part in (forenames, keyname, suffix) if part)
    return re.sub(r"\s+", " ", name).strip()


def _paper_from_meta(meta: ET.Element, original_id: str | None = None) -> PaperMeta | None:
    arxiv_id = (meta.findtext("ax:id", default="", namespaces=OAI_NS) or "").strip()
    title = re.sub(
        r"\s+",
        " ",
        meta.findtext("ax:title", default="", namespaces=OAI_NS) or "",
    ).strip()
    abstract = re.sub(
        r"\s+",
        " ",
        meta.findtext("ax:abstract", default="", namespaces=OAI_NS) or "",
    ).strip()
    published = (meta.findtext("ax:created", default="", namespaces=OAI_NS) or "").strip()
    doi = (meta.findtext("ax:doi", default="", namespaces=OAI_NS) or "").strip()
    authors_node = meta.find("ax:authors", OAI_NS)
    authors = []
    if authors_node is not None:
        authors = [
            name
            for name in (_author_name(author) for author in authors_node.findall("ax:author", OAI_NS))
            if name
        ]
    if not arxiv_id or not title or not abstract:
        return None
    display_id = original_id or arxiv_id
    return PaperMeta(
        arxiv_id=display_id,
        title=title,
        authors=authors,
        published=published,
        link=f"https://arxiv.org/abs/{display_id}",
        doi=doi,
        abstract=abstract,
    )


def _fetch_metadata(ids: set[str], cache_path: Path, refresh: bool) -> dict[str, PaperMeta]:
    if cache_path.exists() and not refresh:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
        cached = {key: PaperMeta(**value) for key, value in raw.items()}
        if ids.issubset(set(cached)):
            return cached

    target_base = {_base_id(arxiv_id): arxiv_id for arxiv_id in ids}
    found: dict[str, PaperMeta] = {}
    params = {
        "verb": "ListRecords",
        "metadataPrefix": "arXiv",
        "set": "physics:cond-mat",
        "from": "2026-01-01",
    }
    token = ""
    while set(found) != set(ids):
        payload = _fetch_oai({"verb": "ListRecords", "resumptionToken": token} if token else params)
        root = ET.fromstring(payload)
        for record in root.findall(".//oai:record", OAI_NS):
            meta = record.find(".//ax:arXiv", OAI_NS)
            if meta is None:
                continue
            base = (meta.findtext("ax:id", default="", namespaces=OAI_NS) or "").strip()
            if base not in target_base:
                continue
            original_id = target_base[base]
            paper = _paper_from_meta(meta, original_id=original_id)
            if paper:
                found[original_id] = paper
        if set(found) == set(ids):
            break
        token = (root.findtext(".//oai:resumptionToken", default="", namespaces=OAI_NS) or "").strip()
        if not token:
            missing = sorted(set(ids) - set(found))
            raise RuntimeError(f"Missing OAI metadata for {len(missing)} ids: {missing[:10]}")
        time.sleep(3.2)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps({key: asdict(value) for key, value in found.items()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return found


def _author_display(authors: list[str]) -> str:
    if not authors:
        return "N/A"
    shown = authors[:4]
    suffix = "..." if len(authors) > 4 else ""
    return ", ".join(shown) + suffix


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text.strip())
    return [part.strip() for part in parts if len(part.strip()) > 20]


def _pick_sentence(sentences: list[str], keywords: tuple[str, ...], fallback_index: int) -> str:
    for sentence in sentences:
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in keywords):
            return sentence
    if sentences:
        return sentences[min(fallback_index, len(sentences) - 1)]
    return ""


def _numbers(text: str) -> str:
    values = re.findall(
        r"(?:\b\d+(?:\.\d+)?\s?(?:K|T|V|nm|mm|cm|eV|meV|%|°C|cycles?|Torr|GPa|MPa|μC/m2|mA|GHz|THz)\b|\b\d+\^\d+\b|\b\d+(?:\.\d+)?\s?x\s?\d+(?:\.\d+)?)",
        text,
        flags=re.IGNORECASE,
    )
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return ", ".join(deduped[:5])


def _summary_bullets(paper: PaperMeta) -> list[str]:
    sentences = _sentences(paper.abstract)
    focus = _pick_sentence(sentences, ("study", "investigate", "present", "report", "propose"), 0)
    method = _pick_sentence(
        sentences,
        ("using", "through", "via", "based on", "combine", "measurement", "calculation", "simulation", "diffraction", "microscopy", "spectroscopy"),
        1,
    )
    result = _pick_sentence(
        sentences,
        ("result", "show", "find", "reveal", "demonstrate", "improve", "achieve", "increase", "decrease", "confirm"),
        2,
    )
    contribution = _pick_sentence(
        sentences,
        ("provide", "establish", "enable", "uncover", "highlight", "suggest", "offer"),
        3,
    )
    bullets = [
        f"Bài này nghiên cứu \"{paper.title}\"; abstract mô tả trọng tâm là: {focus}",
        f"Vấn đề hoặc cách tiếp cận chính được nêu trong abstract: {method}",
        f"Kết quả/đóng góp chính: {result}",
    ]
    numeric = _numbers(paper.abstract)
    if numeric:
        bullets.append(f"Số liệu hoặc điều kiện đáng chú ý trong abstract: {numeric}.")
    elif contribution and contribution not in {focus, method, result}:
        bullets.append(f"Ý nghĩa được nhấn mạnh: {contribution}")
    return [bullet if bullet.endswith((".", "!", "?")) else bullet + "." for bullet in bullets[:5]]


def _valid_article(stt: int, paper: PaperMeta) -> str:
    lines = [
        f"**{stt}. {paper.title}**",
        f"-  **Tác giả**: {_author_display(paper.authors)}",
        f"-  **Ngày đăng**: {paper.published}",
        f"-  **Link**: {paper.link}",
    ]
    if paper.doi:
        lines.append(f"-  **DOI**: {paper.doi}")
    lines.append("-  **Tóm tắt**:")
    lines.extend(f"  - {bullet}" for bullet in _summary_bullets(paper))
    return "\n".join(lines)


def _placeholder(stt: int, original_block: str) -> str:
    first = original_block.splitlines()[0].strip() if original_block.strip() else ""
    if first:
        return first
    return f"Sai format {stt}: không có bài báo arXiv hợp lệ trong slot này."


def _rewrite_row(raw: str, metadata: dict[str, PaperMeta]) -> str:
    rewritten: list[str] = []
    for index, block in enumerate(_blocks(raw), start=1):
        ids = _extract_ids(block)
        if ids and ids[0] in metadata:
            rewritten.append(_valid_article(index, metadata[ids[0]]))
        else:
            rewritten.append(_placeholder(index, block))
    return "\n\n".join(rewritten)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--cache", type=Path, default=Path(__file__).resolve().parents[1] / ".tmp" / "book1_article_metadata.json")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    with sqlite3.connect(args.db) as conn:
        rows = conn.execute(
            "SELECT id, raw_response FROM benchmark_results WHERE run_id = ? ORDER BY day, model_id",
            (args.run_id,),
        ).fetchall()
        if not rows:
            raise RuntimeError(f"No rows found for run_id={args.run_id}")
        ids: set[str] = set()
        for _row_id, raw in rows:
            ids.update(_extract_ids(raw or ""))
        metadata = _fetch_metadata(ids, args.cache, args.refresh)
        for row_id, raw in rows:
            conn.execute(
                "UPDATE benchmark_results SET raw_response = ? WHERE id = ?",
                (_rewrite_row(raw or "", metadata), row_id),
            )
        conn.commit()

    print(
        json.dumps(
            {
                "run_id": args.run_id,
                "rows_updated": len(rows),
                "unique_arxiv_ids_enriched": len(metadata),
                "cache": str(args.cache),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
