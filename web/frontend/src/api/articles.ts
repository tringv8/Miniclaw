import { launcherFetch } from "@/api/http"

export interface ArticleItem {
  id: string
  title: string
  authors: string
  published_date: string
  link: string
  doi: string
  summary: string
  category: string
  saved_at: string
}

export interface ArticlesResponse {
  google_sheets_url: string
  articles: ArticleItem[]
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await launcherFetch(path, options)
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export async function getArticles(): Promise<ArticlesResponse> {
  return request<ArticlesResponse>("/api/articles")
}

export async function updateSheetsUrl(url: string): Promise<{ status: string; google_sheets_url: string }> {
  return request<{ status: string; google_sheets_url: string }>("/api/articles/sheets-url", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ url }),
  })
}

export async function deleteArticle(id: string): Promise<{ status: string; id: string }> {
  return request<{ status: string; id: string }>(`/api/articles/${encodeURIComponent(id)}`, {
    method: "DELETE",
  })
}
