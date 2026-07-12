#!/usr/bin/env python3
"""
Migrate existing articles from old general-science categories to new
component/material categories for the Electronics Materials Lab.

Run from the Miniclaw repo root:
    python scripts/migrate_categories.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from miniclaw.utils.articles import (
    load_articles_data,
    save_articles_data,
    classify_category,
    COMPONENT_CATEGORIES,
)

OLD_CATEGORIES = {
    "Khoa hoc vat lieu",
    "Cong nghe thong tin",
    "Vat ly",
    "Hoa hoc",
    "Sinh hoc",
    "Khoa học vật liệu",
    "Công nghệ thông tin",
    "Vật lý",
    "Hóa học",
    "Sinh học",
    "Khác",
}

VALID_NEW = {data["name"] for data in COMPONENT_CATEGORIES.values()} | {"Khác"}


def migrate():
    data = load_articles_data()
    articles = data.get("articles", [])

    if not articles:
        print("Khong tim thay bai bao nao trong articles.json.")
        return

    updated = 0
    for art in articles:
        old_cat = art.get("category", "")
        if old_cat in OLD_CATEGORIES or old_cat not in VALID_NEW:
            new_cat = classify_category(art.get("title", ""), art.get("summary", ""))
            art["category"] = new_cat
            if old_cat != new_cat:
                print(f"  [{old_cat}] -> [{new_cat}]  {art.get('title', '')[:70]}")
                updated += 1
        else:
            print(f"  [GIU NGUYEN: {old_cat}]  {art.get('title', '')[:70]}")

    save_articles_data(data)
    print(f"\nHoan tat: {updated}/{len(articles)} bai duoc phan loai lai.")


if __name__ == "__main__":
    migrate()
