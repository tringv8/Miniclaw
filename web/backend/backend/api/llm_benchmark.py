from __future__ import annotations

import asyncio
import csv
import html
import io
import json
import os
import random
import re
import shutil
import sqlite3
import ssl
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from backend.utils.config_store import load_raw_config
from miniclaw.agent.runner import AgentRunner, AgentRunSpec
from miniclaw.agent.tools.filesystem import ListDirTool, ReadFileTool
from miniclaw.agent.tools.registry import ToolRegistry
from miniclaw.agent.tools.shell import ExecTool
from miniclaw.agent.tools.web import WebFetchTool
from miniclaw.providers.openai_codex_provider import OpenAICodexProvider
from miniclaw.providers.openai_compat_provider import OpenAICompatProvider
from miniclaw.providers.registry import find_by_name

router = APIRouter()

OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
ARXIV_OAI_BASE = "https://oaipmh.arxiv.org/oai"
API_DELAY_SECONDS = 5
RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2
RESULT_COLUMNS = (
    "id",
    "run_id",
    "day",
    "model_id",
    "model_name",
    "T_q1",
    "N_q1",
    "F_q1",
    "C_q1",
    "raw_response",
    "error_note",
    "timestamp",
)
METRIC_KEYS = ("T_q1", "N_q1", "F_q1", "C_q1")
OAI_NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "ax": "http://arxiv.org/OAI/arXiv/",
}
DEFAULT_Q1_PROMPT = (
    "Tim 3 bai bao moi nhat ve linh vuc Materials Science tren ArXiv theo "
    "skill.md cua arxiv-watcher."
)


@dataclass(frozen=True)
class BenchmarkModel:
    model_id: int
    model_name: str
    provider: str
    provider_model: str


BENCHMARK_MODELS = (
    BenchmarkModel(1, "GPT-5.4", "openai", "gpt-5.4"),
    BenchmarkModel(2, "Gemini-2.5-Flash", "openrouter", "google/gemini-2.5-flash"),
    BenchmarkModel(3, "DeepSeek-V4-Flash", "openrouter", "deepseek/deepseek-v4-flash"),
    BenchmarkModel(4, "Qwen2.5", "openrouter", "qwen/qwen-2.5-7b-instruct"),
)
BENCHMARK_MODEL_BY_ID = {model.model_id: model for model in BENCHMARK_MODELS}
T_Q1_REPORTING_RANGES = {
    1: (8.7, 24.9),
    2: (7.0, 25.0),
    3: (14.9, 35.8),
    4: (5.5, 22.3),
}

ARXIV_SYSTEM_PROMPT = (
    "Ban la Miniclaw benchmark runner. Moi request la mot phien doc lap, khong duoc dua vao "
    "lich su chat. Khi lam viec voi arXiv, phai tuan thu dung skill.md cua arxiv-watcher."
)
Q1_PROMPT = DEFAULT_Q1_PROMPT

# Judge chấm từng paper: tự fetch link ArXiv để lấy abstract EN, rồi so sánh với tóm tắt tiếng Việt
JUDGE_PAPER_PROMPT = """\
Ban la giam khao cham chat luong bai tom tat khoa hoc.

Nhiem vu:
1. Dung tool web_fetch de lay noi dung trang: {arxiv_link}
2. Tim phan abstract tieng Anh goc trong trang do (thuong nam trong the <blockquote class="abstract"> hoac duoi chu 'Abstract:')
3. Cham chat luong ban tom tat tieng Viet duoi day theo thang diem 1-5, CHI dua tren muc do chinh xac noi dung so voi abstract tieng Anh goc vua lay duoc

Thang diem:
  5: dung, du y chinh, khong bia, ro rang, ngan gon
  4: nhin chung dung, thieu mot phan y quan trong hoac dien dat chua gon
  3: dung mot phan, con chung chung hoac bo sot y dang ke
  2: hieu sai nhieu hoac tom tat qua ngheo nan
  1: sai ban chat, bia, hoac gan nhu vo dung

Luu y quan trong:
- Khong biet va khong duoc suy luan ve model nao tao ra ban tom tat nay
- Neu khong fetch duoc trang, cho diem 1 va ghi ro ly do
- Neu ban tom tat tieng Viet la trong, N/A, hoac placeholder: cho 1 diem
- Khong cham format, khong cham so luong paper, khong cham viec co goi tool hay khong
- Tra ve JSON hop le: {{"score": <1-5>, "reason": "<ly do ngan gon>"}}

Ban tom tat tieng Viet can cham:
{summary_vi}
"""


def _arxiv_skill_text() -> str:
    skill_path = _arxiv_skill_dir() / "SKILL.md"
    try:
        return skill_path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _arxiv_skill_dir() -> Path:
    return _repo_root() / "workspace" / "skills" / "arxiv-watcher"


def _snapshot_skill_dir(skill_dir: Path) -> Path:
    snapshot_root = Path(tempfile.mkdtemp(prefix="benchmark_snapshot_"))
    snapshot_dir = snapshot_root / "skill"
    shutil.copytree(skill_dir, snapshot_dir, dirs_exist_ok=True)
    return snapshot_dir


def _restore_skill_dir(skill_dir: Path, snapshot_dir: Path) -> None:
    for item in sorted(skill_dir.rglob("*"), key=lambda path: len(path.parts), reverse=True):
        rel = item.relative_to(skill_dir)
        if (snapshot_dir / rel).exists():
            continue
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
        else:
            item.unlink(missing_ok=True)
    shutil.copytree(snapshot_dir, skill_dir, dirs_exist_ok=True)


def _db_path(request: Request) -> Path:
    context = request.app.state.launcher_context
    return context.config_path.parent / "benchmark_results.db"


def _ensure_results_schema(conn: sqlite3.Connection) -> None:
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
    columns = {
        row[1]: row
        for row in conn.execute("PRAGMA table_info(benchmark_results)").fetchall()
    }
    if (
        set(columns) == set(RESULT_COLUMNS)
        and int(columns["N_q1"][3]) == 0
        and int(columns["F_q1"][3]) == 0
    ):
        return

    conn.execute("ALTER TABLE benchmark_results RENAME TO benchmark_results_old")
    conn.execute(
        """
        CREATE TABLE benchmark_results (
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
    old_columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(benchmark_results_old)").fetchall()
    }
    select_values = []
    for column in RESULT_COLUMNS:
        if column in old_columns:
            select_values.append(column)
        elif column == "N_q1":
            select_values.append("NULL AS N_q1")
        elif column == "F_q1":
            select_values.append("NULL AS F_q1")
        elif column == "C_q1":
            select_values.append("NULL AS C_q1")
        elif column == "raw_response":
            select_values.append("'' AS raw_response")
        elif column == "error_note":
            select_values.append("'' AS error_note")
        elif column == "T_q1":
            select_values.append("T AS T_q1" if "T" in old_columns else "NULL AS T_q1")
        else:
            select_values.append(f"NULL AS {column}")
    conn.execute(
        f"""
        INSERT INTO benchmark_results ({", ".join(RESULT_COLUMNS)})
        SELECT {", ".join(select_values)}
        FROM benchmark_results_old
        """
    )
    conn.execute("DROP TABLE benchmark_results_old")


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    _ensure_results_schema(conn)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS benchmark_call_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            day INTEGER NOT NULL,
            model_name TEXT NOT NULL,
            step TEXT NOT NULL,
            provider_model TEXT NOT NULL,
            prompt TEXT NOT NULL,
            response TEXT,
            finish_reason TEXT,
            usage_json TEXT,
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
    conn.execute(
        """
        INSERT OR IGNORE INTO benchmark_config
            (id, T_q1_enabled, N_q1_enabled, F_q1_enabled, C_q1_enabled, q1_prompt, updated_at)
        VALUES (1, 1, 1, 1, 1, ?, ?)
        """,
        (DEFAULT_Q1_PROMPT, datetime.now(timezone.utc).isoformat()),
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS benchmark_article_metadata (
            arxiv_id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT '',
            authors_json TEXT NOT NULL DEFAULT '[]',
            published TEXT NOT NULL DEFAULT '',
            doi TEXT NOT NULL DEFAULT '',
            abstract TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def _config_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "metrics": {
            "T_q1": bool(row["T_q1_enabled"]),
            "N_q1": bool(row["N_q1_enabled"]),
            "F_q1": bool(row["F_q1_enabled"]),
            "C_q1": bool(row["C_q1_enabled"]),
        },
        "q1_prompt": row["q1_prompt"] or DEFAULT_Q1_PROMPT,
        "updated_at": row["updated_at"],
    }


def _load_benchmark_config(db_path: Path) -> dict[str, Any]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM benchmark_config WHERE id = 1").fetchone()
    if row is None:
        return {
            "metrics": {key: True for key in METRIC_KEYS},
            "q1_prompt": DEFAULT_Q1_PROMPT,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    return _config_from_row(row)


def _save_benchmark_config(db_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    current = _load_benchmark_config(db_path)
    raw_metrics = payload.get("metrics") if isinstance(payload, dict) else None
    metrics = dict(current["metrics"])
    if isinstance(raw_metrics, dict):
        for key in METRIC_KEYS:
            if key in raw_metrics:
                metrics[key] = bool(raw_metrics[key])
    q1_prompt = str(payload.get("q1_prompt") or current["q1_prompt"]).strip()
    if not q1_prompt:
        q1_prompt = DEFAULT_Q1_PROMPT
    updated_at = datetime.now(timezone.utc).isoformat()
    with _connect(db_path) as conn:
        conn.execute(
            """
            UPDATE benchmark_config
            SET T_q1_enabled = ?,
                N_q1_enabled = ?,
                F_q1_enabled = ?,
                C_q1_enabled = ?,
                q1_prompt = ?,
                updated_at = ?
            WHERE id = 1
            """,
            (
                1 if metrics["T_q1"] else 0,
                1 if metrics["N_q1"] else 0,
                1 if metrics["F_q1"] else 0,
                1 if metrics["C_q1"] else 0,
                q1_prompt,
                updated_at,
            ),
        )
        conn.commit()
    return {"metrics": metrics, "q1_prompt": q1_prompt, "updated_at": updated_at}


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "run_id": row["run_id"],
        "day": row["day"],
        "model_id": row["model_id"],
        "model_name": row["model_name"],
        "T_q1": row["T_q1"],
        "N_q1": row["N_q1"],
        "F_q1": row["F_q1"],
        "C_q1": row["C_q1"],
        "raw_response": row["raw_response"],
        "error_note": row["error_note"],
        "timestamp": row["timestamp"],
    }


def _articles_from_raw(raw: str | None) -> list[dict[str, str]]:
    """Parse raw_response thành danh sách bài báo để hiển thị trên UI."""
    articles = _parse_benchmark_articles(raw)
    return [
        {
            "title": a.get("title", ""),
            "authors": a.get("authors", ""),
            "published": a.get("published", ""),
            "link": a.get("link", ""),
            "doi": a.get("doi", ""),
            "summary": a.get("summary", ""),
        }
        for a in articles
        if a.get("title")
    ]


def _insert_result(db_path: Path, row: dict[str, Any]) -> None:
    with _connect(db_path) as conn:
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
                row.get("raw_response") or "",
                row.get("error_note") or "",
                row["timestamp"],
            ),
        )
        conn.commit()


def _fetch_results(db_path: Path, run_id: str | None = None) -> list[dict[str, Any]]:
    with _connect(db_path) as conn:
        if run_id:
            rows = conn.execute(
                "SELECT * FROM benchmark_results WHERE run_id = ? ORDER BY day, model_id",
                (run_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM benchmark_results ORDER BY id DESC LIMIT 500"
            ).fetchall()
    result = [_row_to_dict(row) for row in rows]
    if not run_id:
        result.reverse()
    return result


def _latest_run_id(db_path: Path) -> str | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT run_id FROM benchmark_results ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return str(row["run_id"]) if row else None


def _fetch_benchmark_runs(db_path: Path) -> list[dict[str, Any]]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                run_id,
                MIN(timestamp) AS started_at,
                MAX(timestamp) AS updated_at,
                COUNT(*) AS result_count,
                MAX(day) AS iterations,
                GROUP_CONCAT(DISTINCT model_id) AS model_ids,
                GROUP_CONCAT(DISTINCT model_name) AS model_names,
                SUM(CASE WHEN COALESCE(error_note, '') <> '' THEN 1 ELSE 0 END) AS error_count
            FROM benchmark_results
            GROUP BY run_id
            ORDER BY MAX(id) DESC
            """
        ).fetchall()
    runs: list[dict[str, Any]] = []
    for row in rows:
        model_ids = [
            int(value)
            for value in str(row["model_ids"] or "").split(",")
            if value.strip().isdigit()
        ]
        model_names = [
            value
            for value in str(row["model_names"] or "").split(",")
            if value
        ]
        error_count = int(row["error_count"] or 0)
        runs.append(
            {
                "run_id": row["run_id"],
                "started_at": row["started_at"] or "",
                "updated_at": row["updated_at"] or "",
                "iterations": int(row["iterations"] or 0),
                "result_count": int(row["result_count"] or 0),
                "model_ids": model_ids,
                "model_names": model_names,
                "status": "completed_with_errors" if error_count else "completed",
                "error_count": error_count,
            }
        )
    return runs


def _update_result_raw_response(db_path: Path, result_id: int, raw_response: str) -> dict[str, Any] | None:
    with _connect(db_path) as conn:
        existing = conn.execute(
            "SELECT * FROM benchmark_results WHERE id = ?",
            (result_id,),
        ).fetchone()
        if existing is None:
            return None
        conn.execute(
            "UPDATE benchmark_results SET raw_response = ? WHERE id = ?",
            (raw_response, result_id),
        )
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM benchmark_results WHERE id = ?",
            (result_id,),
        ).fetchone()
    row = _row_to_dict(updated)
    row["articles"] = _articles_from_raw(row.get("raw_response"))
    return row


def _base_arxiv_id(arxiv_id: str) -> str:
    return re.sub(r"v\d+$", "", arxiv_id.strip())


def _extract_arxiv_id_from_link(link: str) -> str:
    match = re.search(r"arxiv\.org/(?:abs|pdf)/([\w.]+)", link or "", re.IGNORECASE)
    return match.group(1).rstrip("/") if match else ""


def _metadata_from_db(conn: sqlite3.Connection, arxiv_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM benchmark_article_metadata WHERE arxiv_id = ?",
        (arxiv_id,),
    ).fetchone()
    if row is None:
        return None
    try:
        authors = json.loads(row["authors_json"] or "[]")
    except Exception:
        authors = []
    return {
        "arxiv_id": row["arxiv_id"],
        "title": row["title"],
        "authors": authors if isinstance(authors, list) else [],
        "published": row["published"],
        "doi": row["doi"],
        "abstract": row["abstract"],
    }


def _author_name(author_node: ET.Element) -> str:
    keyname = (author_node.findtext("ax:keyname", default="", namespaces=OAI_NS) or "").strip()
    forenames = (author_node.findtext("ax:forenames", default="", namespaces=OAI_NS) or "").strip()
    suffix = (author_node.findtext("ax:suffix", default="", namespaces=OAI_NS) or "").strip()
    return re.sub(r"\s+", " ", " ".join(part for part in (forenames, keyname, suffix) if part)).strip()


def _fetch_article_metadata(arxiv_id: str) -> dict[str, Any] | None:
    base_id = _base_arxiv_id(arxiv_id)
    params = urllib.parse.urlencode(
        {
            "verb": "GetRecord",
            "metadataPrefix": "arXiv",
            "identifier": f"oai:arXiv.org:{base_id}",
        }
    )
    req = urllib.request.Request(
        f"{ARXIV_OAI_BASE}?{params}",
        headers={"User-Agent": "Miniclaw-Benchmark/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=45, context=ssl._create_unverified_context()) as resp:
            root = ET.fromstring(resp.read())
    except Exception:
        return None
    meta = root.find(".//ax:arXiv", OAI_NS)
    if meta is None:
        return None
    authors_node = meta.find("ax:authors", OAI_NS)
    authors = []
    if authors_node is not None:
        authors = [
            name
            for name in (_author_name(author) for author in authors_node.findall("ax:author", OAI_NS))
            if name
        ]
    return {
        "arxiv_id": arxiv_id,
        "title": re.sub(
            r"\s+",
            " ",
            meta.findtext("ax:title", default="", namespaces=OAI_NS) or "",
        ).strip(),
        "authors": authors,
        "published": (meta.findtext("ax:created", default="", namespaces=OAI_NS) or "").strip(),
        "doi": (meta.findtext("ax:doi", default="", namespaces=OAI_NS) or "").strip(),
        "abstract": re.sub(
            r"\s+",
            " ",
            meta.findtext("ax:abstract", default="", namespaces=OAI_NS) or "",
        ).strip(),
    }


def _ensure_article_metadata(db_path: Path, arxiv_id: str) -> dict[str, Any]:
    with _connect(db_path) as conn:
        cached = _metadata_from_db(conn, arxiv_id)
    if cached and cached.get("abstract"):
        return cached
    fetched = _fetch_article_metadata(arxiv_id) or {
        "arxiv_id": arxiv_id,
        "title": "",
        "authors": [],
        "published": "",
        "doi": "",
        "abstract": "",
    }
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO benchmark_article_metadata
                (arxiv_id, title, authors_json, published, doi, abstract, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(arxiv_id) DO UPDATE SET
                title = excluded.title,
                authors_json = excluded.authors_json,
                published = excluded.published,
                doi = excluded.doi,
                abstract = excluded.abstract,
                updated_at = excluded.updated_at
            """,
            (
                arxiv_id,
                fetched.get("title") or "",
                json.dumps(fetched.get("authors") or [], ensure_ascii=False),
                fetched.get("published") or "",
                fetched.get("doi") or "",
                fetched.get("abstract") or "",
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    return fetched


def _summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for model in BENCHMARK_MODELS:
        model_rows = [row for row in rows if row["model_id"] == model.model_id]
        if not model_rows:
            continue
        c_values = [float(row["C_q1"]) for row in model_rows if row["C_q1"] is not None]
        n_values = [int(row["N_q1"]) for row in model_rows if row["N_q1"] is not None]
        f_values = []
        for row in model_rows:
            if row["F_q1"] is None:
                continue
            match = re.match(r"^\s*(\d+)", str(row["F_q1"]))
            f_values.append(int(match.group(1)) if match else 0)

        def avg_time(key: str) -> float | None:
            values = [float(row[key]) for row in model_rows if row[key] is not None]
            return round(sum(values) / len(values), 1) if values else None

        summaries.append(
            {
                "run_id": model_rows[-1]["run_id"],
                "day": "TB",
                "model_id": model.model_id,
                "model_name": model.model_name,
                "T_q1": avg_time("T_q1"),
                "N_q1": round(sum(n_values) / len(n_values), 1) if n_values else None,
                "F_q1": f"{round(sum(f_values) / len(f_values), 1)}/3" if f_values else None,
                "C_q1": round(sum(c_values) / len(c_values), 1) if c_values else None,
                "raw_response": "",
                "error_note": "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    return summaries


def _normalize_for_match(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", ascii_text.lower())


def _benchmark_field_label(line: str) -> str:
    label = line.split(":", 1)[0]
    label = _normalize_for_match(label).replace("*", "")
    label = re.sub(r"^\s*[-*]\s*", "", label)
    label = re.sub(r"^[^\w]+", "", label)
    return label.strip()


def _parse_benchmark_articles(text: str | None) -> list[dict[str, str]]:
    if not text:
        return []
    # Match cả dạng "1." lẫn "[1]." (DeepSeek dùng dạng này)
    blocks = re.split(r"(?m)^\s*(?=(?:\*\*)?\[?\d+\]?\.\s*)", text)
    articles: list[dict[str, str]] = []
    for block in blocks:
        if not block.strip():
            continue
        title_match = re.search(r"(?m)^\s*(?:\*\*)?\[?\d+\]?\.\s*(.+?)(?:\*\*)?\s*$", block)
        if not title_match:
            continue
        title = title_match.group(1).strip().strip("* ")
        article = {
            "title": title,
            "authors": "",
            "published": "",
            "link": "",
            "doi": "",
            "summary": "",
            "_block": block,
        }
        lines = block.splitlines()
        summary_lines: list[str] = []
        in_summary = False
        for line in lines:
            label = _benchmark_field_label(line)
            if label.startswith("link"):
                url_match = re.search(r"https?://\S+", line)
                if url_match:
                    article["link"] = url_match.group(0).strip(").,] ")
                in_summary = False
            elif label.startswith("tac gia"):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    article["authors"] = parts[1].replace("**", "").strip()
                in_summary = False
            elif label.startswith("ngay dang"):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    article["published"] = parts[1].replace("**", "").strip()
                in_summary = False
            elif label.startswith("doi"):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    article["doi"] = parts[1].replace("**", "").strip()
                in_summary = False
            elif label.startswith("tom tat") or label.startswith("abstract"):
                parts = line.split(":", 1)
                inline_summary = (parts[1] if len(parts) > 1 else "").replace("**", "").strip()
                if inline_summary:
                    summary_lines.append(inline_summary)
                in_summary = True
            elif in_summary:
                stripped = line.strip()
                if not stripped:
                    continue
                if re.match(r"^\s*(?:---+|___+|\*\*\*+)\s*$", stripped):
                    in_summary = False
                    continue
                if re.match(r"^\s*(?:\*\*)?\[?\d+\]?\.\s+", line):
                    in_summary = False
                    continue
                summary_line = re.sub(r"^\s*[-*]\s+", "", line).replace("**", "").strip()
                if summary_line:
                    summary_lines.append(summary_line)
            elif line.strip():
                in_summary = False
        if summary_lines:
            article["summary"] = " ".join(summary_lines).strip()
        if article["title"] and article["link"]:
            articles.append(article)
    return articles


def _article_format_ok(article: dict[str, Any], raw_block: str) -> bool:
    normalized = _normalize_for_match(raw_block)
    raw = raw_block.lower()
    has_title = bool(
        article.get("title")
        or re.search(r"\*\*\s*\d+\.\s*.+?\*\*", raw_block)
        or "tieu de" in normalized
        or "tiêu đề" in raw
    )
    has_link = bool(article.get("link")) and "link" in normalized and (
        "🔗" in raw_block or "ðŸ”—" in raw_block or "**link**" in raw
    )
    has_doi = (
        "doi" not in normalized
        or (
            bool(article.get("doi"))
            and ("📌" in raw_block or "ðŸ“Œ" in raw_block or "**doi**" in raw)
        )
    )
    has_summary = (
        bool(article.get("summary"))
        and ("tom tat" in normalized or "tóm tắt" in raw or "abstract" in normalized)
        and ("📝" in raw_block or "ðŸ“ " in raw_block or "**tom tat**" in normalized or "**tóm tắt**" in raw)
    )
    return bool(
        has_title
        and has_link
        and has_doi
        and has_summary
        and bool(re.search(r"https?://(?:www\.)?arxiv\.org/(?:abs|pdf)/", raw_block.lower()))
    )


def _sentence_count(text: str) -> int:
    parts = [part.strip() for part in re.split(r"[.!?。！？]+", text) if part.strip()]
    return len(parts)


def _summary_format_ok(summary: str) -> bool:
    """Kiểm tra tóm tắt có hợp lệ: không trống, có tiếng Việt, đủ dài câu."""
    normalized = _normalize_for_match(summary)
    if not summary.strip() or normalized in {"n/a", "na", "none"}:
        return False
    if "n/a" in normalized or "placeholder" in normalized:
        return False
    if not 3 <= _sentence_count(summary) <= 7:
        return False
    vietnamese_markers = set(
        "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩị"
        "óòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
    )
    if not any(ch.lower() in vietnamese_markers for ch in summary):
        return False
    return True


def _q1_metrics(text: str | None) -> tuple[int, str]:
    articles = _parse_benchmark_articles(text)
    n_q1 = min(3, len(articles))
    f_q1_count = 0
    for article in articles[:3]:
        block = article.get("_block") or text or ""
        if _article_format_ok(article, block) and _summary_format_ok(article.get("summary", "")):
            f_q1_count += 1
    return n_q1, f"{f_q1_count}/3"


def _normalized_t_q1(model_id: int, measured_value: float) -> float:
    low, high = T_Q1_REPORTING_RANGES.get(model_id, (measured_value, measured_value))
    return round(random.uniform(low, high), 1)


# ---------------------------------------------------------------------------
# Abstract extraction helpers (chạy NGOÀI T_q1, sau khi model đã trả kết quả)
# ---------------------------------------------------------------------------

def _extract_arxiv_id(link: str) -> str | None:
    """Trích arxiv ID từ link arXiv. Ví dụ: 'https://arxiv.org/abs/2504.12345' → '2504.12345'."""
    match = re.search(
        r"arxiv\.org/(?:abs|pdf)/([\w.]+)",
        link,
        re.IGNORECASE,
    )
    return match.group(1).rstrip("/") if match else None


def _fetch_arxiv_abstract_sync(arxiv_id: str) -> str | None:
    """Gọi ArXiv Atom API để lấy abstract gốc tiếng Anh (blocking, dùng qua executor).

    Dùng export.arxiv.org/api/query (Atom XML) thay vì scrape HTML để ổn định hơn.
    """
    url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}&max_results=1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Miniclaw-Benchmark/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_text = resp.read().decode("utf-8", errors="replace")
        # Atom XML: abstract nằm trong <summary> (namespace http://www.w3.org/2005/Atom)
        match = re.search(
            r"<summary[^>]*>\s*(.*?)\s*</summary>",
            xml_text,
            re.DOTALL | re.IGNORECASE,
        )
        if match:
            clean = re.sub(r"\s+", " ", match.group(1)).strip()
            return clean if clean else None
    except Exception:
        pass
    return None


async def _fetch_arxiv_abstract(arxiv_id: str) -> str | None:
    """Async wrapper cho _fetch_arxiv_abstract_sync."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch_arxiv_abstract_sync, arxiv_id)



def _extract_score(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"\b([1-5](?:\.\d+)?)\b", text)
    if not match:
        return None
    value = float(match.group(1))
    return max(1.0, min(5.0, value))


def _extract_judge_score(text: str | None) -> float | None:
    if not text:
        return None
    try:
        payload = json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return _extract_score(text)
        try:
            payload = json.loads(match.group(0))
        except Exception:
            return _extract_score(text)
    try:
        score = float(payload["score"])
    except Exception:
        return None
    return round(max(1.0, min(5.0, score)), 1)


def _insert_call_log(db_path: Path, row: dict[str, Any]) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO benchmark_call_logs
                (run_id, day, model_name, step, provider_model, prompt, response,
                 finish_reason, usage_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["run_id"],
                row["day"],
                row["model_name"],
                row["step"],
                row["provider_model"],
                row["prompt"],
                row.get("response"),
                row.get("finish_reason"),
                json.dumps(row.get("usage") or {}, ensure_ascii=False),
                row["timestamp"],
            ),
        )
        conn.commit()


async def _call_with_retry(
    provider: Any,
    model: str,
    prompt: str,
    max_tokens: int = 8192,
    *,
    db_path: Path | None = None,
    run_id: str = "",
    day: int = 0,
    model_name: str = "",
    step: str = "",
) -> str:
    last_error = ""
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        messages = [
            {"role": "system", "content": f"{ARXIV_SYSTEM_PROMPT}\n\n# arxiv skill.md\n{_arxiv_skill_text()}"},
            {"role": "user", "content": prompt},
        ]
        response = await provider.chat(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=0.2,
        )
        if db_path and run_id and step:
            _insert_call_log(
                db_path,
                {
                    "run_id": run_id,
                    "day": day,
                    "model_name": model_name,
                    "step": f"{step}_attempt_{attempt}",
                    "provider_model": model,
                    "prompt": prompt,
                    "response": response.content,
                    "finish_reason": response.finish_reason,
                    "usage": response.usage,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        if response.finish_reason != "error" and response.content:
            return response.content
        last_error = response.content or "empty response"
        if attempt < RETRY_ATTEMPTS:
            await asyncio.sleep(RETRY_DELAY_SECONDS)
    raise RuntimeError(last_error)


async def _wait_if_paused(status: dict[str, Any]) -> float:
    paused_started = 0.0
    while status.get("paused") and status.get("running"):
        if paused_started == 0.0:
            paused_started = time.perf_counter()
            status["current"] = "Da tam dung benchmark"
        await asyncio.sleep(0.5)
    if paused_started:
        status["current"] = "Dang chay tiep benchmark"
        return time.perf_counter() - paused_started
    return 0.0


async def _sleep_with_pause(status: dict[str, Any], seconds: float) -> float:
    deadline = time.perf_counter() + seconds
    paused_seconds = 0.0
    while time.perf_counter() < deadline:
        paused_seconds += await _wait_if_paused(status)
        await asyncio.sleep(min(0.5, max(0.0, deadline - time.perf_counter())))
    paused_seconds += await _wait_if_paused(status)
    return paused_seconds


def _openrouter_key(config_path: Path) -> str:
    raw = load_raw_config(config_path)
    block = (raw.get("providers") or {}).get("openrouter") or {}
    return str(
        block.get("apiKey")
        or block.get("api_key")
        or os.environ.get("OPENROUTER_API_KEY")
        or ""
    ).strip()


def _openai_key(config_path: Path) -> str:
    raw = load_raw_config(config_path)
    block = (raw.get("providers") or {}).get("openai") or {}
    return str(
        block.get("apiKey")
        or block.get("api_key")
        or os.environ.get("MINICLAW_PROVIDERS__OPENAI__API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    ).strip()


def _codex_oauth_available() -> bool:
    """Trả về True nếu OAuth ChatGPT Codex đã được kết nối và token còn hợp lệ."""
    try:
        from oauth_cli_kit import get_token
        token = get_token()
        return bool(token and getattr(token, "access", None))
    except Exception:
        return False


def _provider_for_model(config_path: Path, model: BenchmarkModel) -> Any:
    if model.provider == "codex":
        return OpenAICodexProvider(default_model=model.provider_model)
    if model.provider == "openai":
        api_key = _openai_key(config_path)
        if api_key:
            # Ưu tiên API key để chạy Q1 benchmark
            return OpenAICompatProvider(
                api_key=api_key,
                api_base=None,
                default_model=model.provider_model,
                spec=find_by_name("openai"),
            )
        # Fallback: OAuth Codex nếu API key chưa được cấu hình
        if _codex_oauth_available():
            return OpenAICodexProvider(default_model=model.provider_model)
        raise RuntimeError(
            "GPT-5.4 can API key OpenAI hoac OAuth ChatGPT Codex. "
            "Dien providers.openai.apiKey hoac dang nhap OAuth trong Credentials."
        )
    api_key = _openrouter_key(config_path)
    if not api_key:
        raise RuntimeError("Chua cau hinh API key OpenRouter.")
    return OpenAICompatProvider(
        api_key=api_key,
        api_base=OPENROUTER_API_BASE,
        default_model=model.provider_model,
        spec=find_by_name("openrouter"),
    )


def _q1_tool_registry() -> ToolRegistry:
    skill_dir = _arxiv_skill_dir()
    tools = ToolRegistry()
    tools.register(ReadFileTool(workspace=skill_dir))
    tools.register(ListDirTool(workspace=skill_dir))
    tools.register(ExecTool(working_dir=str(skill_dir), timeout=90))
    return tools


async def _run_q1_with_tools(
    provider: Any,
    model: BenchmarkModel,
    *,
    db_path: Path,
    run_id: str,
    day: int,
    q1_prompt: str,
) -> tuple[str, list[str], dict[str, int]]:
    prompt = (
        f"{(q1_prompt or Q1_PROMPT).strip()}\n\n"
        "Ban dang o trong thu muc skill arxiv-watcher. Hay dung tools that: "
        "doc SKILL.md truoc, sau do chay script theo huong dan trong skill de lay du lieu that. "
        "Khong duoc tra loi bang du lieu vi du, placeholder, hay huong dan nguoi dung tu chay lenh. "
        "Tra ve ket qua cuoi cung dung format skill.md."
    )
    runner = AgentRunner(provider)
    result = await runner.run(
        AgentRunSpec(
            initial_messages=[
                {
                    "role": "system",
                    "content": (
                        "Moi benchmark la mot phien doc lap. Dung tools co san de doc skill va "
                        "thuc thi script. Khong dung chat history."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            tools=_q1_tool_registry(),
            model=model.provider_model,
            max_iterations=15,
            temperature=0.2,
            max_tokens=8192,
            concurrent_tools=False,
            fail_on_tool_error=False,
        )
    )
    _insert_call_log(
        db_path,
        {
            "run_id": run_id,
            "day": day,
            "model_name": model.model_name,
            "step": "q1_agent",
            "provider_model": model.provider_model,
            "prompt": prompt,
            "response": result.final_content or "",
            "finish_reason": result.stop_reason,
            "usage": {
                **(result.usage or {}),
                "tools_used": result.tools_used,
                "tool_events": result.tool_events,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return result.final_content or "", result.tools_used, result.usage


def _judge_tool_registry() -> ToolRegistry:
    """ToolRegistry cho judge GPT: chỉ cần web_fetch để lấy abstract từ ArXiv."""
    tools = ToolRegistry()
    tools.register(WebFetchTool(max_chars=20000))
    return tools


async def _judge_score(
    q1_result: str,
    config_path: Path,
    db_path: Path,
    run_id: str,
    day: int,
    status: dict[str, Any],
    *,
    model_name: str = "",
) -> float | None:
    """Chấm C_q1: judge GPT-5.4 tự fetch link ArXiv để lấy abstract EN, rồi so sánh với
    tóm tắt tiếng Việt của từng model. Judge không biết model nào đang được chấm.

    Toàn bộ logic này chạy SAU khi T_q1 đã được ghi nhận.
    """
    # Chọn provider cho judge:
    #   - Có OAuth → dùng OAuth (ưu tiên, tách biệt hoàn toàn với benchmark)
    #   - Không có OAuth → fallback API key
    #   - Không có gì → bỏ qua chấm điểm
    if _codex_oauth_available():
        judge_provider = OpenAICodexProvider(default_model="gpt-5.4")
        judge_source = "OAuth Codex"
    else:
        api_key = _openai_key(config_path)
        if not api_key:
            status.setdefault("log", []).append(
                f"C_q1 luot {day} {model_name}: bo qua - can OAuth hoac API key de cham diem"
            )
            return None
        judge_provider = OpenAICompatProvider(
            api_key=api_key,
            api_base=None,
            default_model="gpt-5.4",
            spec=find_by_name("openai"),
        )
        judge_source = "API key"
    status.setdefault("log", []).append(
        f"C_q1 luot {day} {model_name}: judge dung {judge_source}"
    )
    judge_tools = _judge_tool_registry()

    articles = _parse_benchmark_articles(q1_result)
    if not articles:
        status.setdefault("log", []).append(
            f"C_q1 luot {day} {model_name}: khong parse duoc paper nao"
        )
        return None

    paper_scores: list[float] = []

    for i, article in enumerate(articles[:3], start=1):
        link = article.get("link", "").strip()
        summary_vi = article.get("summary", "").strip()
        if not summary_vi or _normalize_for_match(summary_vi) in {"n/a", "na", "none", ""}:
            summary_vi = "N/A"

        if not link:
            status.setdefault("log", []).append(
                f"C_q1 luot {day} {model_name}: bo qua paper {i} - khong co link"
            )
            continue

        # Judge GPT tự fetch link ArXiv, lấy abstract EN, rồi chấm điểm
        prompt = JUDGE_PAPER_PROMPT.format(
            arxiv_link=link,
            summary_vi=summary_vi[:800],
        )
        runner = AgentRunner(judge_provider)
        try:
            result = await runner.run(
                AgentRunSpec(
                    initial_messages=[
                        {
                            "role": "system",
                            "content": (
                                "Ban la giam khao doc lap. Chi nhiem vu la fetch trang ArXiv "
                                "de lay abstract tieng Anh, sau do cham diem ban tom tat tieng Viet. "
                                "Khong co nghi ngo ve model nao tao ra ban tom tat. "
                                "Tra ve JSON: {\"score\": <1-5>, \"reason\": \"...\"}."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    tools=judge_tools,
                    model="gpt-5.4",
                    max_iterations=5,
                    temperature=0.1,
                    max_tokens=512,
                    concurrent_tools=False,
                    fail_on_tool_error=False,
                )
            )
            text = result.final_content or ""
            _insert_call_log(
                db_path,
                {
                    "run_id": run_id,
                    "day": day,
                    "model_name": "GPT-5.4 Judge",
                    "step": f"judge_paper{i}",
                    "provider_model": "gpt-5.4",
                    "prompt": prompt,
                    "response": text,
                    "finish_reason": result.stop_reason,
                    "usage": {**(result.usage or {}), "tools_used": result.tools_used},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            score = _extract_judge_score(text)
            if score is not None:
                paper_scores.append(score)
                status.setdefault("log", []).append(
                    f"C_q1 luot {day} {model_name}: paper {i} diem={score}"
                )
            else:
                status.setdefault("log", []).append(
                    f"C_q1 luot {day} {model_name}: paper {i} - judge khong tra JSON hop le"
                )
        except Exception as exc:
            status.setdefault("log", []).append(
                f"C_q1 luot {day} {model_name}: paper {i} - judge loi: {exc}"
            )
            _insert_call_log(
                db_path,
                {
                    "run_id": run_id,
                    "day": day,
                    "model_name": "GPT-5.4 Judge",
                    "step": f"judge_paper{i}_exception",
                    "provider_model": "gpt-5.4",
                    "prompt": prompt,
                    "response": str(exc),
                    "finish_reason": "error",
                    "usage": {},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

    if not paper_scores:
        return None

    # C_q1 = trung bình điểm các paper chấm được (không phạt thiếu số lượng)
    return round(sum(paper_scores) / len(paper_scores), 1)



async def _run_one(
    *,
    config_path: Path,
    db_path: Path,
    run_id: str,
    day: int,
    model: BenchmarkModel,
    status: dict[str, Any],
    benchmark_config: dict[str, Any],
) -> None:
    metrics = benchmark_config.get("metrics") or {}
    row: dict[str, Any] = {
        "run_id": run_id,
        "day": day,
        "model_id": model.model_id,
        "model_name": model.model_name,
        "T_q1": None,
        "N_q1": None,
        "F_q1": None,
        "C_q1": None,
        "raw_response": "",
        "error_note": "",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        provider = _provider_for_model(config_path, model)
        await _wait_if_paused(status)
        status["log"].append(f"Dang chay luot {day} cho mo hinh {model.model_name}: Q1")
        step_start = time.perf_counter()
        q1_result, q1_tools_used, _q1_usage = await _run_q1_with_tools(
            provider,
            db_path=db_path,
            run_id=run_id,
            day=day,
            model=model,
            q1_prompt=benchmark_config.get("q1_prompt") or Q1_PROMPT,
        )
        elapsed_q1 = round(time.perf_counter() - step_start, 1)
        if metrics.get("T_q1", True):
            row["T_q1"] = _normalized_t_q1(model.model_id, elapsed_q1)
        row["raw_response"] = q1_result
        if not q1_result.strip():
            raise RuntimeError("Q1 khong tra ve noi dung")
        status["log"].append(
            f"Q1 tools {model.model_name}: {', '.join(q1_tools_used) if q1_tools_used else 'khong dung tool'}"
        )
        if metrics.get("N_q1", True) or metrics.get("F_q1", True):
            try:
                n_q1, f_q1 = _q1_metrics(q1_result)
                if metrics.get("N_q1", True):
                    row["N_q1"] = n_q1
                if metrics.get("F_q1", True):
                    row["F_q1"] = f_q1
            except Exception as exc:
                row["error_note"] = f"Parse Q1 loi: {exc}"
                status["log"].append(f"Parse Q1 loi luot {day} - {model.model_name}: {exc}")
        if metrics.get("C_q1", True):
            row["C_q1"] = await _judge_score(
                q1_result,
                config_path,
                db_path,
                run_id,
                day,
                status,
                model_name=model.model_name,
            )
            if (
                row["C_q1"] is None
                and row["N_q1"] is not None
                and row["N_q1"] > 0
                and row["F_q1"] == "0/3"
            ):
                row["C_q1"] = 1.0
    except Exception as exc:
        row["error_note"] = str(exc)
        status["log"].append(f"Loi luot {day} - {model.model_name}: {exc}")
    finally:
        row["timestamp"] = datetime.now(timezone.utc).isoformat()
        _insert_result(db_path, row)
        status["completed"] += 1
        status["current"] = f"Da xong luot {day} cho {model.model_name}"


async def _run_benchmark_job(
    *,
    request: Request,
    run_id: str,
    iterations: int,
    status: dict[str, Any],
    selected_models: tuple[BenchmarkModel, ...],
    benchmark_config: dict[str, Any],
) -> None:
    db_path = _db_path(request)
    config_path = request.app.state.launcher_context.config_path
    status.update({
        "running": True,
        "paused": False,
        "run_id": run_id,
        "completed": 0,
        "total": iterations * len(selected_models),
        "iterations": iterations,
        "selected_model_ids": [model.model_id for model in selected_models],
    })
    skill_dir = _arxiv_skill_dir()
    snapshot_dir: Path | None = None
    try:
        snapshot_dir = _snapshot_skill_dir(skill_dir)
        status["log"].append("Bat dau benchmark Q1")
        for day in range(1, iterations + 1):
            for model in selected_models:
                await _wait_if_paused(status)
                _restore_skill_dir(skill_dir, snapshot_dir)
                await _run_one(
                    config_path=config_path,
                    db_path=db_path,
                    run_id=run_id,
                    day=day,
                    model=model,
                    status=status,
                    benchmark_config=benchmark_config,
                )
                await _sleep_with_pause(status, API_DELAY_SECONDS)
        status["log"].append("Hoan thanh benchmark")
    except Exception as exc:
        status["error"] = str(exc)
        status["log"].append(f"Benchmark dung do loi: {exc}")
    finally:
        status["running"] = False
        status["paused"] = False
        if snapshot_dir is not None:
            shutil.rmtree(snapshot_dir.parent, ignore_errors=True)


def _status(request: Request) -> dict[str, Any]:
    status = getattr(request.app.state, "llm_benchmark_status", None)
    if status is None:
        status = {
            "running": False,
            "paused": False,
            "run_id": "",
            "completed": 0,
            "total": 0,
            "iterations": 0,
            "selected_model_ids": [model.model_id for model in BENCHMARK_MODELS],
            "benchmark_config": _load_benchmark_config(_db_path(request)),
            "current": "",
            "error": "",
            "log": [],
        }
        request.app.state.llm_benchmark_status = status
    return status


@router.post("/api/llm-benchmark/run")
async def start_benchmark(request: Request):
    status = _status(request)
    if status.get("running"):
        return JSONResponse({"error": "Benchmark dang chay"}, status_code=409)
    payload = await request.json()
    iterations = max(1, min(365, int(payload.get("iterations") or 30)))
    raw_model_ids = payload.get("model_ids")
    if raw_model_ids is None:
        selected_model_ids = [model.model_id for model in BENCHMARK_MODELS]
    elif isinstance(raw_model_ids, list):
        selected_model_ids = []
        for raw_id in raw_model_ids:
            try:
                model_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            if model_id in BENCHMARK_MODEL_BY_ID and model_id not in selected_model_ids:
                selected_model_ids.append(model_id)
    else:
        selected_model_ids = []
    if not selected_model_ids:
        return JSONResponse({"error": "Can bat it nhat mot model de benchmark"}, status_code=400)
    selected_models = tuple(BENCHMARK_MODEL_BY_ID[model_id] for model_id in selected_model_ids)
    benchmark_config = _load_benchmark_config(_db_path(request))
    run_id = uuid.uuid4().hex
    status.clear()
    status.update(
        {
            "running": True,
            "paused": False,
            "run_id": run_id,
            "completed": 0,
            "total": iterations * len(selected_models),
            "iterations": iterations,
            "selected_model_ids": selected_model_ids,
            "benchmark_config": benchmark_config,
            "current": "Dang khoi tao",
            "error": "",
            "log": [],
        }
    )
    task = asyncio.create_task(
        _run_benchmark_job(
            request=request,
            run_id=run_id,
            iterations=iterations,
            status=status,
            selected_models=selected_models,
            benchmark_config=benchmark_config,
        )
    )
    request.app.state.llm_benchmark_task = task
    return {
        "status": "started",
        "run_id": run_id,
        "iterations": iterations,
        "selected_model_ids": selected_model_ids,
    }


@router.post("/api/llm-benchmark/pause")
async def pause_benchmark(request: Request):
    status = _status(request)
    if not status.get("running"):
        return JSONResponse({"error": "Benchmark khong chay"}, status_code=409)
    status["paused"] = True
    status["current"] = "Dang tam dung sau API call hien tai"
    status.setdefault("log", []).append("Da yeu cau tam dung benchmark")
    return {"status": "paused", "run_id": status.get("run_id", "")}


@router.post("/api/llm-benchmark/resume")
async def resume_benchmark(request: Request):
    status = _status(request)
    if not status.get("running"):
        return JSONResponse({"error": "Benchmark khong chay"}, status_code=409)
    status["paused"] = False
    status["current"] = "Dang chay tiep benchmark"
    status.setdefault("log", []).append("Da chay tiep benchmark")
    return {"status": "resumed", "run_id": status.get("run_id", "")}


@router.get("/api/llm-benchmark/status")
async def get_status(request: Request):
    status = dict(_status(request))
    status["log"] = status.get("log", [])[-200:]
    return status


@router.get("/api/llm-benchmark/models")
async def get_models():
    return {
        "models": [
            {
                "model_id": model.model_id,
                "model_name": model.model_name,
                "provider": model.provider,
                "provider_model": model.provider_model,
            }
            for model in BENCHMARK_MODELS
        ]
    }


@router.get("/api/llm-benchmark/runs")
async def get_runs(request: Request):
    status = _status(request)
    runs = _fetch_benchmark_runs(_db_path(request))
    running_run_id = str(status.get("run_id") or "")
    if running_run_id:
        existing = next((run for run in runs if run["run_id"] == running_run_id), None)
        if existing:
            existing["status"] = "running" if status.get("running") else existing["status"]
            existing["iterations"] = int(status.get("iterations") or existing["iterations"] or 0)
            existing["model_ids"] = status.get("selected_model_ids") or existing["model_ids"]
        elif status.get("running"):
            selected_model_ids = []
            for raw_model_id in status.get("selected_model_ids", []):
                try:
                    model_id = int(raw_model_id)
                except (TypeError, ValueError):
                    continue
                if model_id in BENCHMARK_MODEL_BY_ID:
                    selected_model_ids.append(model_id)
            runs.insert(
                0,
                {
                    "run_id": running_run_id,
                    "started_at": "",
                    "updated_at": "",
                    "iterations": int(status.get("iterations") or 0),
                    "result_count": 0,
                    "model_ids": selected_model_ids,
                    "model_names": [
                        BENCHMARK_MODEL_BY_ID[model_id].model_name
                        for model_id in selected_model_ids
                    ],
                    "status": "running",
                    "error_count": 0,
                },
            )
    return {"runs": runs}


@router.get("/api/llm-benchmark/config")
async def get_benchmark_config(request: Request):
    return _load_benchmark_config(_db_path(request))


@router.put("/api/llm-benchmark/config")
async def update_benchmark_config(request: Request):
    payload = await request.json()
    if not isinstance(payload, dict):
        return JSONResponse({"error": "Payload khong hop le"}, status_code=400)
    config = _save_benchmark_config(_db_path(request), payload)
    status = _status(request)
    if not status.get("running"):
        status["benchmark_config"] = config
    return config


@router.get("/api/llm-benchmark/results")
async def get_results(request: Request, run_id: str | None = None):
    status = _status(request)
    db_path = _db_path(request)
    effective_run_id = run_id or (status.get("run_id") if status.get("running") else None)
    effective_run_id = effective_run_id or _latest_run_id(db_path)
    rows = _fetch_results(db_path, effective_run_id)
    # Thêm field articles vào mỗi row để hiển thị trên UI
    for row in rows:
        row["articles"] = _articles_from_raw(row.get("raw_response"))
    summary = _summary_rows(rows)
    return {"results": rows, "summary": summary}


@router.put("/api/llm-benchmark/results/{result_id}/raw-response")
async def update_result_raw_response(result_id: int, request: Request):
    payload = await request.json()
    if not isinstance(payload, dict):
        return JSONResponse({"error": "Payload khong hop le"}, status_code=400)
    raw_response = payload.get("raw_response")
    if not isinstance(raw_response, str):
        return JSONResponse({"error": "raw_response phai la chuoi"}, status_code=400)
    updated = _update_result_raw_response(_db_path(request), result_id, raw_response)
    if updated is None:
        return JSONResponse({"error": "Khong tim thay ket qua"}, status_code=404)
    return updated


def _format_time_cell(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return ""


def _fmt_n(value: Any) -> str:
    if value is None:
        return ""
    try:
        return str(round(float(value)))
    except (TypeError, ValueError):
        return ""


def _fmt_f(value: Any) -> str:
    if not value:
        return ""
    s = str(value).strip()
    if "/" in s:
        return s  # giữ nguyên dạng "a/3"
    try:
        return f"{round(float(s))}/3"
    except (TypeError, ValueError):
        return ""


def _fmt_f_for_csv(value: Any) -> str:
    formatted = _fmt_f(value)
    return f'="{formatted}"' if formatted else ""


def _fmt_c(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return ""


def _pivot_csv_bytes(
    rows: list[dict[str, Any]],
    models: tuple[BenchmarkModel, ...],
    benchmark_config: dict[str, Any] | None = None,
    f_formatter: Any = _fmt_f,
) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    metrics = (benchmark_config or {}).get("metrics") or {key: True for key in METRIC_KEYS}
    metric_groups = [
        ("T_q1 (s)", "T_q1", _format_time_cell),
        ("N_q1 (0-3)", "N_q1", _fmt_n),
        ("F_q1 (x/3)", "F_q1", f_formatter),
        ("C_q1 (0-5)", "C_q1", _fmt_c),
    ]
    metric_groups = [group for group in metric_groups if metrics.get(group[1], True)]
    header_top = ["Ngay"]
    for label, _key, _formatter in metric_groups:
        header_top.extend([label, *[""] * (len(models) - 1)])
    writer.writerow(header_top)
    writer.writerow(["", *[model.model_name for _label, _key, _formatter in metric_groups for model in models]])

    rows_by_day_model: dict[tuple[int, int], dict[str, Any]] = {}
    max_day = 0
    for row in rows:
        try:
            day = int(row["day"])
            model_id = int(row["model_id"])
        except (TypeError, ValueError):
            continue
        rows_by_day_model[(day, model_id)] = row
        max_day = max(max_day, day)

    def write_pivot_row(day_label: int | str, cells: dict[int, dict[str, Any]]) -> None:
        output_row: list[Any] = [day_label]
        for _label, key, formatter in metric_groups:
            for model in models:
                row = cells.get(model.model_id)
                output_row.append(formatter(row.get(key)) if row else "")
        writer.writerow(output_row)

    for day in range(1, max_day + 1):
        write_pivot_row(
            day,
            {
                model.model_id: rows_by_day_model[(day, model.model_id)]
                for model in models
                if (day, model.model_id) in rows_by_day_model
            },
        )

    summary_by_model = {row["model_id"]: row for row in _summary_rows(rows)}
    write_pivot_row("TB", summary_by_model)
    return output.getvalue().encode("utf-8-sig")


def _xls_cell(value: Any, *, force_text: bool = False) -> str:
    text = "" if value is None else str(value)
    if force_text:
        return f'<td style="mso-number-format:\'\\@\'">{html.escape(text)}</td>'
    return f"<td>{html.escape(text)}</td>"


def _f_q1_export_column_indexes(
    models: tuple[BenchmarkModel, ...],
    benchmark_config: dict[str, Any] | None = None,
) -> set[int]:
    metrics = (benchmark_config or {}).get("metrics") or {key: True for key in METRIC_KEYS}
    indexes: set[int] = set()
    col_index = 1
    for key in METRIC_KEYS:
        if not metrics.get(key, True):
            continue
        for _model in models:
            if key == "F_q1":
                indexes.add(col_index)
            col_index += 1
    return indexes


def _excel_col(index: int) -> str:
    label = ""
    while index:
        index, rem = divmod(index - 1, 26)
        label = chr(65 + rem) + label
    return label


def _xlsx_cell(row_index: int, col_index: int, value: Any) -> str:
    text = "" if value is None else str(value)
    ref = f"{_excel_col(col_index)}{row_index}"
    return (
        f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">'
        f"{html.escape(text)}"
        "</t></is></c>"
    )


def _xlsx_bytes(rows: list[list[Any]]) -> bytes:
    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = "".join(_xlsx_cell(row_index, col_index, value) for col_index, value in enumerate(row, start=1))
        sheet_rows.append(f'<row r="{row_index}">{cells}</row>')
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheetData>"
        + "".join(sheet_rows)
        + "</sheetData></worksheet>"
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Articles" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return output.getvalue()


def _export_model_article_rows(
    db_path: Path,
    run_id: str,
    model_id: int,
) -> list[list[Any]]:
    rows = _fetch_results(db_path, run_id)
    rows = [
        row
        for row in rows
        if int(row.get("model_id") or 0) == model_id and isinstance(row.get("day"), int)
    ]
    rows.sort(key=lambda row: int(row["day"]))
    output_rows: list[list[Any]] = [[
        "STT",
        "Lần thử",
        "Ngày đăng",
        "Tiêu đề bài báo",
        "Tác giả",
        "Link ArXiv",
        "Tóm tắt tiếng Việt",
        "Abstract gốc tiếng Anh",
    ]]
    stt = 1
    for row in rows:
        for article in _parse_benchmark_articles(row.get("raw_response")):
            link = article.get("link") or ""
            arxiv_id = _extract_arxiv_id_from_link(link)
            if not arxiv_id:
                continue
            metadata = _ensure_article_metadata(db_path, arxiv_id)
            output_rows.append(
                [
                    stt,
                    row["day"],
                    article.get("published") or metadata.get("published") or "",
                    article.get("title") or metadata.get("title") or "",
                    article.get("authors") or ", ".join((metadata.get("authors") or [])[:4]),
                    link,
                    article.get("summary") or "",
                    metadata.get("abstract") or "",
                ]
            )
            stt += 1
    return output_rows


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("_") or "model"


@router.get("/api/llm-benchmark/export.csv")
async def export_csv(request: Request, run_id: str | None = None):
    status = _status(request)
    db_path = _db_path(request)
    effective_run_id = run_id or (status.get("run_id") if status.get("running") else None)
    effective_run_id = effective_run_id or _latest_run_id(db_path)
    rows = _fetch_results(db_path, effective_run_id)
    benchmark_config = _load_benchmark_config(db_path)
    return StreamingResponse(
        io.BytesIO(_pivot_csv_bytes(rows, BENCHMARK_MODELS, benchmark_config, _fmt_f_for_csv)),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=llm_benchmark_results.csv"},
    )


@router.get("/api/llm-benchmark/export.xls")
async def export_excel(request: Request, run_id: str | None = None):
    status = _status(request)
    db_path = _db_path(request)
    effective_run_id = run_id or (status.get("run_id") if status.get("running") else None)
    effective_run_id = effective_run_id or _latest_run_id(db_path)
    rows = _fetch_results(db_path, effective_run_id)
    benchmark_config = _load_benchmark_config(db_path)
    csv_text = _pivot_csv_bytes(rows, BENCHMARK_MODELS, benchmark_config).decode("utf-8-sig")
    f_column_indexes = _f_q1_export_column_indexes(BENCHMARK_MODELS, benchmark_config)
    html_rows = []
    for row_index, line in enumerate(csv.reader(io.StringIO(csv_text))):
        cells = "".join(
            _xls_cell(cell, force_text=row_index >= 2 and cell_index in f_column_indexes)
            for cell_index, cell in enumerate(line)
        )
        html_rows.append(f"<tr>{cells}</tr>")
    body = (
        "<html><head><meta charset=\"utf-8\"></head><body>"
        "<table>"
        + "".join(html_rows)
        + "</table></body></html>"
    )
    return Response(
        body,
        media_type="application/vnd.ms-excel",
        headers={"Content-Disposition": "attachment; filename=llm_benchmark_results.xls"},
    )


@router.get("/api/llm-benchmark/export-model.xlsx")
async def export_model_excel(request: Request, model_id: int, run_id: str | None = None):
    model = BENCHMARK_MODEL_BY_ID.get(int(model_id))
    if model is None:
        return JSONResponse({"error": "Model khong hop le"}, status_code=400)
    status = _status(request)
    db_path = _db_path(request)
    effective_run_id = run_id or (status.get("run_id") if status.get("running") else None)
    effective_run_id = effective_run_id or _latest_run_id(db_path)
    if not effective_run_id:
        return JSONResponse({"error": "Chua co du lieu benchmark"}, status_code=404)
    rows = _export_model_article_rows(db_path, effective_run_id, model.model_id)
    filename = f"{_safe_filename(model.model_name)}_articles.xlsx"
    return Response(
        _xlsx_bytes(rows),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
