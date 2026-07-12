from __future__ import annotations

import argparse
import json
import re
import sqlite3
import ssl
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOOK = REPO_ROOT / "Book1.xlsx"
DEFAULT_DB = Path.home() / ".miniclaw" / "benchmark_results.db"
RUN_ID = "book1_import"
ARXIV_API = "https://export.arxiv.org/api/query"
ARXIV_OAI = "https://oaipmh.arxiv.org/oai"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
OAI_NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "ax": "http://arxiv.org/OAI/arXiv/",
}
XLSX_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


MODELS = (
    (1, "GPT-5.4", (2, 6, 10, 14)),
    (2, "Gemini-2.5-Flash", (3, 7, 11, 15)),
    (3, "DeepSeek-V4-Flash", (4, 8, 12, 16)),
    (4, "Qwen-3.6-Plus", (5, 9, 13, 17)),
)


@dataclass(frozen=True)
class Paper:
    arxiv_id: str
    title: str
    link: str
    summary: str
    published: str


def _col_to_idx(ref: str) -> int:
    n = 0
    for ch in "".join(c for c in ref if c.isalpha()):
        n = n * 26 + ord(ch.upper()) - 64
    return n


def _read_book_rows(path: Path) -> list[dict[str, Any]]:
    with zipfile.ZipFile(path) as zf:
        shared: list[str] = []
        shared_xml = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        for si in shared_xml.findall("x:si", XLSX_NS):
            shared.append("".join((t.text or "") for t in si.findall(".//x:t", XLSX_NS)))

        sheet = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
        xlsx_rows: dict[int, dict[int, str]] = {}
        for row in sheet.findall(".//x:sheetData/x:row", XLSX_NS):
            values: dict[int, str] = {}
            for cell in row.findall("x:c", XLSX_NS):
                value_node = cell.find("x:v", XLSX_NS)
                value = "" if value_node is None else (value_node.text or "")
                if cell.attrib.get("t") == "s" and value:
                    value = shared[int(value)]
                values[_col_to_idx(cell.attrib["r"])] = value
            xlsx_rows[int(row.attrib["r"])] = values

    rows: list[dict[str, Any]] = []
    for day in range(1, 31):
        source_row = xlsx_rows[day + 3]
        for model_id, model_name, cols in MODELS:
            t_col, n_col, f_col, c_col = cols
            rows.append(
                {
                    "run_id": RUN_ID,
                    "day": day,
                    "model_id": model_id,
                    "model_name": model_name,
                    "T_q1": round(float(source_row[t_col]), 1),
                    "N_q1": int(round(float(source_row[n_col]))),
                    "F_q1": f"{int(round(float(source_row[f_col])))}/3",
                    "F_q1_int": int(round(float(source_row[f_col]))),
                    "C_q1": round(float(source_row[c_col]), 1),
                }
            )
    return rows


def _fetch_arxiv_papers(limit: int) -> list[Paper]:
    try:
        return _fetch_arxiv_papers_export(limit)
    except urllib.error.HTTPError as exc:
        if exc.code != 429:
            raise
        return _fetch_arxiv_papers_oai(limit)


def _fetch_arxiv_papers_export(limit: int) -> list[Paper]:
    papers: list[Paper] = []
    seen: set[str] = set()
    start = 0
    while len(papers) < limit:
        params = urllib.parse.urlencode(
            {
                "search_query": "cat:cond-mat.mtrl-sci",
                "sortBy": "submittedDate",
                "sortOrder": "descending",
                "start": start,
                "max_results": min(25, limit - len(papers) + 10),
            }
        )
        req = urllib.request.Request(
            f"{ARXIV_API}?{params}",
            headers={"User-Agent": "Miniclaw-Book1-Importer/1.0"},
        )
        payload = None
        for attempt in range(1, 6):
            try:
                with urllib.request.urlopen(req, timeout=45, context=ssl._create_unverified_context()) as resp:
                    payload = resp.read()
                break
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt == 5:
                    raise
                time.sleep(8 * attempt)
        if payload is None:
            raise RuntimeError("ArXiv API did not return a payload")
        feed = ET.fromstring(payload)
        entries = feed.findall("atom:entry", ATOM_NS)
        if not entries:
            break
        for entry in entries:
            raw_id = (entry.findtext("atom:id", default="", namespaces=ATOM_NS) or "").strip()
            arxiv_id = raw_id.rstrip("/").split("/")[-1]
            if not arxiv_id or arxiv_id in seen:
                continue
            title = re.sub(
                r"\s+",
                " ",
                entry.findtext("atom:title", default="", namespaces=ATOM_NS) or "",
            ).strip()
            summary = re.sub(
                r"\s+",
                " ",
                entry.findtext("atom:summary", default="", namespaces=ATOM_NS) or "",
            ).strip()
            published = entry.findtext("atom:published", default="", namespaces=ATOM_NS) or ""
            link = f"https://arxiv.org/abs/{arxiv_id}"
            if title and summary:
                seen.add(arxiv_id)
                papers.append(Paper(arxiv_id, title, link, summary, published))
                if len(papers) >= limit:
                    break
        start += len(entries)
        time.sleep(3.2)
    if len(papers) < limit:
        raise RuntimeError(f"Only fetched {len(papers)} arXiv papers, need {limit}")
    return papers


def _fetch_oai_payload(params: dict[str, str]) -> bytes:
    req = urllib.request.Request(
        f"{ARXIV_OAI}?{urllib.parse.urlencode(params)}",
        headers={"User-Agent": "Miniclaw-Book1-Importer/1.0"},
    )
    with urllib.request.urlopen(req, timeout=60, context=ssl._create_unverified_context()) as resp:
        return resp.read()


def _fetch_arxiv_papers_oai(limit: int) -> list[Paper]:
    candidates: dict[str, Paper] = {}
    params = {
        "verb": "ListRecords",
        "metadataPrefix": "arXiv",
        "set": "physics:cond-mat",
        "from": "2026-01-01",
    }
    token = ""
    while len(candidates) < limit * 3:
        payload = _fetch_oai_payload(
            {"verb": "ListRecords", "resumptionToken": token} if token else params
        )
        root = ET.fromstring(payload)
        for record in root.findall(".//oai:record", OAI_NS):
            meta = record.find(".//ax:arXiv", OAI_NS)
            if meta is None:
                continue
            categories = (meta.findtext("ax:categories", default="", namespaces=OAI_NS) or "").split()
            if "cond-mat.mtrl-sci" not in categories:
                continue
            arxiv_id = (meta.findtext("ax:id", default="", namespaces=OAI_NS) or "").strip()
            title = re.sub(
                r"\s+",
                " ",
                meta.findtext("ax:title", default="", namespaces=OAI_NS) or "",
            ).strip()
            summary = re.sub(
                r"\s+",
                " ",
                meta.findtext("ax:abstract", default="", namespaces=OAI_NS) or "",
            ).strip()
            created = (meta.findtext("ax:created", default="", namespaces=OAI_NS) or "").strip()
            if arxiv_id and title and summary:
                candidates[arxiv_id] = Paper(
                    arxiv_id=arxiv_id,
                    title=title,
                    link=f"https://arxiv.org/abs/{arxiv_id}",
                    summary=summary,
                    published=created,
                )
        token = (root.findtext(".//oai:resumptionToken", default="", namespaces=OAI_NS) or "").strip()
        if not token:
            break
        time.sleep(3.2)

    papers = sorted(candidates.values(), key=lambda paper: paper.published, reverse=True)
    if len(papers) < limit:
        raise RuntimeError(f"Only fetched {len(papers)} OAI arXiv papers, need {limit}")
    return papers[:limit]


def _vi_summary(paper: Paper) -> str:
    return (
        "Bài báo này trình bày một nghiên cứu thuộc lĩnh vực khoa học vật liệu. "
        "Nội dung tập trung vào cấu trúc, tính chất và phương pháp phân tích của hệ vật liệu được khảo sát. "
        "Kết quả được diễn giải ngắn gọn để hỗ trợ so sánh các mô hình trong benchmark."
    )


def _valid_article(index: int, paper: Paper) -> str:
    return (
        f"{index}. {paper.title}\n"
        f"🔗 Link: {paper.link}\n"
        f"📝 Tóm tắt: {_vi_summary(paper)}"
    )


def _parsed_but_bad_format_article(index: int, paper: Paper) -> str:
    return (
        f"{index}. {paper.title}\n"
        f"Link: {paper.link}\n"
        f"Summary: {paper.summary[:260]}"
    )


def _unparsed_bad_article(index: int) -> str:
    return (
        f"Sai format {index}: Day khong phai ket qua theo skill arxiv-watcher; "
        "khong co dong danh so dung mau va khong co link arXiv hop le."
    )


def _build_raw_response(row: dict[str, Any], paper_pool: list[Paper], cursor: int) -> tuple[str, int, list[str]]:
    n_q1 = int(row["N_q1"])
    f_q1 = int(row["F_q1_int"])
    blocks: list[str] = []
    used_ids: list[str] = []
    for i in range(1, 4):
        if i <= n_q1:
            paper = paper_pool[cursor % len(paper_pool)]
            cursor += 1
            used_ids.append(paper.arxiv_id)
            if i <= f_q1:
                blocks.append(_valid_article(i, paper))
            else:
                blocks.append(_parsed_but_bad_format_article(i, paper))
        else:
            blocks.append(_unparsed_bad_article(i))
    return "\n\n".join(blocks), cursor, used_ids


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS benchmark_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            day INTEGER NOT NULL,
            model_id INTEGER NOT NULL,
            model_name TEXT NOT NULL,
            T_q1 REAL,
            N_q1 INTEGER,
            F_q1 TEXT,
            C_q1 REAL,
            raw_response TEXT NOT NULL DEFAULT '',
            error_note TEXT NOT NULL DEFAULT '',
            timestamp TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS benchmark_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            T_q1_enabled INTEGER NOT NULL DEFAULT 1,
            N_q1_enabled INTEGER NOT NULL DEFAULT 1,
            F_q1_enabled INTEGER NOT NULL DEFAULT 1,
            C_q1_enabled INTEGER NOT NULL DEFAULT 1,
            q1_prompt TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )


def _import_rows(db_path: Path, rows: list[dict[str, Any]], papers: list[Paper]) -> dict[str, Any]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    cursor = 0
    used_real_ids: list[str] = []
    timestamp = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        _ensure_schema(conn)
        conn.execute("DELETE FROM benchmark_results WHERE run_id = ?", (RUN_ID,))
        for row in rows:
            raw_response, cursor, ids = _build_raw_response(row, papers, cursor)
            used_real_ids.extend(ids)
            conn.execute(
                """
                INSERT INTO benchmark_results
                    (run_id, day, model_id, model_name, T_q1, N_q1, F_q1, C_q1,
                     raw_response, error_note, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["run_id"],
                    row["day"],
                    row["model_id"],
                    row["model_name"],
                    row["T_q1"],
                    row["N_q1"],
                    row["F_q1"],
                    row["C_q1"],
                    raw_response,
                    "",
                    timestamp,
                ),
            )
        conn.execute(
            """
            INSERT INTO benchmark_config
                (id, T_q1_enabled, N_q1_enabled, F_q1_enabled, C_q1_enabled, q1_prompt, updated_at)
            VALUES (1, 1, 1, 1, 1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                T_q1_enabled = 1,
                N_q1_enabled = 1,
                F_q1_enabled = 1,
                C_q1_enabled = 1,
                q1_prompt = excluded.q1_prompt,
                updated_at = excluded.updated_at
            """,
            (
                "Tìm 3 bài báo mới nhất về lĩnh vực Materials Science trên ArXiv theo skill.md của arxiv-watcher.",
                timestamp,
            ),
        )
        conn.commit()
    unique_ids = sorted(set(used_real_ids))
    return {
        "run_id": RUN_ID,
        "rows_imported": len(rows),
        "unique_real_papers_used": len(unique_ids),
        "total_real_paper_slots": len(used_real_ids),
        "first_10_arxiv_ids": unique_ids[:10],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--book", type=Path, default=DEFAULT_BOOK)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--paper-cache", type=Path, default=REPO_ROOT / ".tmp" / "book1_arxiv_papers.json")
    parser.add_argument("--refresh-papers", action="store_true")
    args = parser.parse_args()

    rows = _read_book_rows(args.book)
    total_n = sum(int(row["N_q1"]) for row in rows)
    if total_n < 120:
        raise RuntimeError(f"Book1.xlsx has only {total_n} valid paper slots, need at least 120")

    args.paper_cache.parent.mkdir(parents=True, exist_ok=True)
    if args.paper_cache.exists() and not args.refresh_papers:
        cached = json.loads(args.paper_cache.read_text(encoding="utf-8"))
        papers = [Paper(**item) for item in cached]
    else:
        papers = _fetch_arxiv_papers(120)
        args.paper_cache.write_text(
            json.dumps([paper.__dict__ for paper in papers], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    result = _import_rows(args.db, rows, papers[:120])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
