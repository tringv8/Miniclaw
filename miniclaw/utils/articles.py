"""Utilities for parsing, classifying, and storing articles."""

import datetime
import json
import re
import uuid
from pathlib import Path

def get_articles_file_path() -> Path:
    """Get the path to the articles JSON file."""
    return Path.home() / ".miniclaw" / "articles.json"

def load_articles_data() -> dict:
    """Load the articles data from the JSON file."""
    path = get_articles_file_path()
    if not path.exists():
        return {"google_sheets_url": "", "articles": []}
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                data = {"google_sheets_url": "", "articles": []}
            data.setdefault("google_sheets_url", "")
            data.setdefault("articles", [])
            return data
    except Exception:
        return {"google_sheets_url": "", "articles": []}

def save_articles_data(data: dict) -> None:
    """Save the articles data to the JSON file."""
    path = get_articles_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

COMPONENT_CATEGORIES = {
    "FE": {
        "name": "Tụ điện sắt điện",
        "icon": "⚡",
        "keywords": ["ferroelectric", "batio3", "pzt", "hfo2", "polarization", "ferroelectricity", "remanent", "coercive"],
    },
    "TFE": {
        "name": "Màng mỏng điện cực",
        "icon": "🧪",
        "keywords": ["thin film", "electrode", "ito", "fto", "sputtering", "deposition", "magnetron", "pvd", "cvd", "coating"],
    },
    "PVK": {
        "name": "Vật liệu perovskite",
        "icon": "🔬",
        "keywords": ["perovskite", "abx3", "halide", "methylammonium", "formamidinium", "all-inorganic", "cspbi3", "mapbi3"],
    },
    "PZ": {
        "name": "Vật liệu áp điện",
        "icon": "🎚️",
        "keywords": ["piezoelectric", "pvdf", "aln", "actuator", "energy harvesting", "vibration", "piezoresistive"],
    },
    "OXS": {
        "name": "Chất bán dẫn oxit",
        "icon": "💠",
        "keywords": ["oxide semiconductor", "wo3", "tio2", "v2o5", "sensor", "zno", "ino", "igzo", "gas sensor", "photodetector"],
    },
    "BAT": {
        "name": "Pin & lưu trữ năng lượng",
        "icon": "🔋",
        "keywords": ["battery", "lithium-ion", "cathode", "anode", "electrolyte", "supercapacitor", "solar cell", "energy storage", "li-ion", "nmc", "lfp"],
    },
}

CATEGORY_CODE_MAP = {code: data["name"] for code, data in COMPONENT_CATEGORIES.items()}
CATEGORY_NAME_MAP = {data["name"]: code for code, data in COMPONENT_CATEGORIES.items()}


def classify_category(title: str, summary: str) -> str:
    """Classify the paper into a component/material category based on title+summary keywords.

    Returns the Vietnamese category name (e.g. 'Tụ điện sắt điện') or 'Khác'.
    Title matches are weighted 3x higher than summary matches.
    """
    title_lower = title.lower()
    summary_lower = (summary or "").lower()

    scores: dict[str, int] = {code: 0 for code in COMPONENT_CATEGORIES}
    for code, data in COMPONENT_CATEGORIES.items():
        for kw in data["keywords"]:
            kw_lower = kw.lower()
            # Title match — high weight (3 per word-boundary hit)
            title_hits = len(re.findall(rf"\b{re.escape(kw_lower)}\b", title_lower))
            scores[code] += title_hits * 3
            if kw_lower in title_lower:
                scores[code] += 1  # substring bonus

            # Summary match — normal weight
            summary_hits = len(re.findall(rf"\b{re.escape(kw_lower)}\b", summary_lower))
            scores[code] += summary_hits
            if kw_lower in summary_lower:
                scores[code] += 1

    best_code = max(scores, key=lambda c: scores[c])
    if scores[best_code] == 0:
        return "Khác"
    return COMPONENT_CATEGORIES[best_code]["name"]


def parse_articles_from_text(text: str) -> list[dict]:
    """Parse article items matching the SKILL.md format from text."""
    if not text:
        return []
    
    articles = []
    lines = text.split('\n')
    current_article = None
    
    # Matches: **1. Title**, 1. **Title**, **[STT]. Title**, [STT]. **Title**
    title_start_re = re.compile(r"^\s*(?:\*\*)?(?:\d+|\[STT\])\.\s*(.+?)$")
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        m = title_start_re.match(line_stripped)
        if m:
            title_val = m.group(1).strip()
            if title_val.endswith("**"):
                title_val = title_val[:-2].strip()
            
            if current_article and current_article.get("title") and current_article.get("link"):
                articles.append(current_article)
            
            current_article = {
                "title": title_val,
                "authors": "",
                "published_date": "",
                "link": "",
                "doi": "",
                "summary": None,  # Initialize as None to detect when Tóm tắt starts
                "category": "Khác",
            }
            continue

        if not current_article:
            continue

        # If we hit the separator "---", close the current article
        if line_stripped == "---" or line_stripped.startswith("---"):
            if current_article.get("title") and current_article.get("link"):
                if current_article.get("summary") is None:
                    current_article["summary"] = ""
                articles.append(current_article)
            current_article = None
            continue

        # Field markers that signal a new field — used to break out of summary mode
        FIELD_MARKERS = ("👤", "📅", "🔗", "📌", "📝", "🏷", "- 👤", "- 📅", "- 🔗", "- 📌", "- 📝", "- 🏷")

        # If we are already collecting summary, keep appending UNLESS we hit a field marker
        if current_article.get("summary") is not None:
            is_new_field = any(line_stripped.startswith(m) or line_stripped.startswith(f"- {m}") for m in FIELD_MARKERS)
            if not is_new_field:
                if current_article["summary"] == "":
                    current_article["summary"] = line_stripped
                else:
                    if current_article["summary"].endswith("\n"):
                        current_article["summary"] += line_stripped
                    else:
                        current_article["summary"] += "\n" + line_stripped
                continue
            # else fall through to parse as a field

        # Otherwise parse standard fields
        parts = line_stripped.split(":", 1)
        if len(parts) > 1:
            label = parts[0].strip().lower()
            val = parts[1].strip().replace("**", "").strip()
            
            if "tác giả" in label or "👤" in label:
                current_article["authors"] = val
            elif "ngày đăng" in label or "📅" in label:
                current_article["published_date"] = val
            elif "link" in label or "🔗" in label:
                m_url = re.search(r"\((https?://[^\)]+)\)", val)
                if m_url:
                    val = m_url.group(1)
                else:
                    val = re.sub(r"[\[\]\(\)]", "", val).strip()
                current_article["link"] = val
            elif "doi" in label or "📌" in label:
                current_article["doi"] = val
            elif "tóm tắt" in label or "📝" in label:
                current_article["summary"] = val
            elif "danh mục" in label or "🏷" in label:
                # Accept either "CODE - Name" or just the name
                code_match = re.match(r"([A-Z]{2,5})\s*[-–]\s*(.+)", val)
                if code_match:
                    current_article["category"] = code_match.group(2).strip()
                elif val:
                    current_article["category"] = val
            
    if current_article and current_article.get("title") and current_article.get("link"):
        if current_article.get("summary") is None:
            current_article["summary"] = ""
        articles.append(current_article)
        
    return articles

def process_and_save_articles_from_text(text: str) -> int:
    """Parse, classify, and save new articles from the given text."""
    articles = parse_articles_from_text(text)
    if not articles:
        return 0
        
    data = load_articles_data()
    existing_articles = data.setdefault("articles", [])
    
    existing_links = {a.get("link") for a in existing_articles if a.get("link")}
    existing_titles = {a.get("title", "").lower() for a in existing_articles if a.get("title")}
    
    added_count = 0
    for art in articles:
        link = art.get("link")
        title = art.get("title")
        
        if link and link in existing_links:
            continue
        if title and title.lower() in existing_titles:
            continue
            
        # Use LLM-assigned category if valid; otherwise auto-classify
        llm_category = art.get("category", "")
        valid_names = {data["name"] for data in COMPONENT_CATEGORIES.values()} | {"Khác"}
        if llm_category and llm_category in valid_names:
            art["category"] = llm_category
        else:
            art["category"] = classify_category(art["title"], art.get("summary", ""))

        art["id"] = str(uuid.uuid4())
        art["saved_at"] = datetime.datetime.now().isoformat()
        
        existing_articles.append(art)
        added_count += 1
        
        if link:
            existing_links.add(link)
        if title:
            existing_titles.add(title.lower())
            
    if added_count > 0:
        save_articles_data(data)
        
    return added_count
