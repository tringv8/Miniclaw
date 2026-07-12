"""
ArXiv Search Script
Usage:
    python search_arxiv.py "<query>" [max_results]
    python search_arxiv.py "LLM reasoning" 5
    python search_arxiv.py "2512.08769"     # Tra cứu theo paper ID

Output gồm: tiêu đề, tác giả, ngày đăng, DOI (nếu có), abstract.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
import ssl
import re
import time
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime

BASE_URL = "https://export.arxiv.org/api/query"
NS = {
    "atom":   "http://www.w3.org/2005/Atom",
    "arxiv":  "http://arxiv.org/schemas/atom",
}

FIELD_PREFIX_RE = re.compile(r"^(all|ti|au|abs|co|jr|cat|rn|id):", re.I)
OPERATOR_RE = re.compile(r"\s+(ANDNOT|AND|OR)\s+", re.I)


def normalize_user_query(query: str) -> str:
    """Normalize whitespace copied from chat clients before building an API query."""
    return " ".join(query.replace("\u00a0", " ").split())


def _prefix_arxiv_term(term: str) -> str:
    term = term.strip()
    leading = ""
    trailing = ""

    while term.startswith("("):
        leading += "("
        term = term[1:].strip()
    while term.endswith(")"):
        trailing = ")" + trailing
        term = term[:-1].strip()

    if not term:
        return leading + trailing
    if FIELD_PREFIX_RE.match(term):
        return leading + term + trailing
    if not (term.startswith('"') and term.endswith('"')) and " " in term:
        term = f'"{term}"'
    return f"{leading}all:{term}{trailing}"


def build_search_query(query: str) -> str:
    """Build a valid ArXiv API search_query from a human query."""
    query = normalize_user_query(query)
    parts = OPERATOR_RE.split(query)
    if len(parts) == 1:
        return _prefix_arxiv_term(query)

    normalized = []
    for i, part in enumerate(parts):
        normalized.append(part.upper() if i % 2 else _prefix_arxiv_term(part))
    return " ".join(normalized)


def search(query: str, max_results: int = 3) -> list[dict]:
    query = normalize_user_query(query)
    cleaned = query.lower().replace("arxiv:", "")
    is_id = len(cleaned) <= 15 and "." in cleaned and cleaned.replace(".", "").replace("/", "").replace("v", "").isdigit()

    params = {"id_list": cleaned, "max_results": max_results} if is_id else {
        "search_query": build_search_query(query),
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    import json
    from pathlib import Path

    proxy_url = None
    try:
        config_path = Path.home() / ".miniclaw" / "config.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                proxy_url = config.get("tools", {}).get("web", {}).get("proxy")
    except Exception:
        pass

    # Ignore HTTP_PROXY/HTTPS_PROXY from the parent process unless Miniclaw
    # explicitly configures a proxy for web tools.
    proxy_handler = urllib.request.ProxyHandler(
        {"http": proxy_url, "https": proxy_url} if proxy_url else {}
    )
    opener = urllib.request.build_opener(
        proxy_handler,
        urllib.request.HTTPSHandler(context=ssl_ctx),
    )
    if proxy_url:
        try:
            print(f"[THÔNG TIN] Đang sử dụng proxy cấu hình từ miniclaw: {proxy_url}", file=sys.stderr)
        except Exception as e:
            print(f"[CẢNH BÁO] Lỗi thiết lập proxy {proxy_url}: {e}", file=sys.stderr)

    max_retries = 3
    retry_delay = 5
    root = None

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            with opener.open(req, timeout=30) as r:
                root = ET.fromstring(r.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries - 1:
                print(f"[CẢNH BÁO] Gặp lỗi 429 (Too Many Requests), đang thử lại sau {retry_delay} giây...", file=sys.stderr)
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            try:
                body = e.read().decode("utf-8", errors="replace")[:1000]
            except Exception:
                body = ""
            print(f"[LỖI] Lỗi HTTP khi kết nối ArXiv API: {e.code} - {e.reason}", file=sys.stderr)
            if not is_id:
                print(f"[LỖI] ArXiv search_query: {params['search_query']}", file=sys.stderr)
            print(f"[LỖI] URL: {url}", file=sys.stderr)
            if body:
                print(f"[LỖI] Phản hồi ArXiv: {body}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"[CẢNH BÁO] Không kết nối được ArXiv API: {e}. Đang thử lại sau {retry_delay} giây...", file=sys.stderr)
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            print(f"[LỖI] Không kết nối được ArXiv API sau {max_retries} lần thử: {e}", file=sys.stderr)
            sys.exit(1)

    if root is None:
        print("[LỖI] Dữ liệu XML từ ArXiv API trống hoặc lỗi.", file=sys.stderr)
        sys.exit(1)

    papers = []
    for entry in root.findall("atom:entry", NS):
        title   = (entry.findtext("atom:title",     default="", namespaces=NS) or "").strip()
        abstract= (entry.findtext("atom:summary",   default="", namespaces=NS) or "").strip()
        pub_raw = (entry.findtext("atom:published", default="", namespaces=NS) or "").strip()
        doi     = (entry.findtext("arxiv:doi",      default="", namespaces=NS) or "").strip()

        authors = [
            (a.findtext("atom:name", default="", namespaces=NS) or "").strip()
            for a in entry.findall("atom:author", NS)
        ]

        # Link trang abstract trên arxiv
        abs_url = next(
            (lk.get("href", "") for lk in entry.findall("atom:link", NS)
             if lk.get("rel") == "alternate"),
            ""
        )

        try:
            date = datetime.fromisoformat(pub_raw.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except Exception:
            date = pub_raw[:10]

        papers.append({
            "title":    title,
            "authors":  authors,
            "date":     date,
            "doi":      f"https://doi.org/{doi}" if doi else "",
            "link":     abs_url,
            "abstract": abstract,
        })

    return papers


def print_results(papers: list[dict], query: str):
    print(f"\n=== KẾT QUẢ TÌM KIẾM: \"{query}\" ({len(papers)} bài) ===\n")
    for i, p in enumerate(papers, 1):
        print(f"[{i}] {p['title']}")
        print(f"    Tác giả : {', '.join(p['authors'][:4])}{'...' if len(p['authors']) > 4 else ''}")
        print(f"    Ngày    : {p['date']}")
        print(f"    Link    : {p['link']}")
        if p['doi']:
            print(f"    DOI     : {p['doi']}")
        print(f"    Abstract:")
        # In full abstract để bot tóm tắt
        print(f"    {p['abstract']}")
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    query = sys.argv[1]
    max_results = int(sys.argv[2]) if len(sys.argv) >= 3 else 5
    papers = search(query, max_results)
    if papers:
        print_results(papers, query)
    else:
        print("Không tìm thấy kết quả nào.")
