from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from miniclaw.utils.articles import load_articles_data, save_articles_data

router = APIRouter()


@router.get("/api/articles")
async def get_articles():
    """Get all saved articles and Google Sheets URL."""
    try:
        data = load_articles_data()
        return data
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.post("/api/articles/sheets-url")
async def update_sheets_url(request: Request):
    """Update Google Sheets URL."""
    try:
        payload = await request.json()
        url = str(payload.get("url", "")).strip()
        
        data = load_articles_data()
        data["google_sheets_url"] = url
        save_articles_data(data)
        
        return {"status": "ok", "google_sheets_url": url}
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.delete("/api/articles/{article_id}")
async def delete_article(article_id: str):
    """Delete a specific article by ID."""
    try:
        data = load_articles_data()
        articles = data.get("articles", [])
        
        # Filter out the article with target ID
        original_len = len(articles)
        filtered_articles = [a for a in articles if a.get("id") != article_id]
        
        if len(filtered_articles) == original_len:
            return JSONResponse({"error": "Article not found"}, status_code=404)
            
        data["articles"] = filtered_articles
        save_articles_data(data)
        
        return {"status": "ok", "id": article_id}
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
