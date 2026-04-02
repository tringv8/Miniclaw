import { launcherFetch } from "@/api/http"

// API client for Miniclaw web chat configuration.

interface MiniTokenResponse {
  token: string
  ws_url: string
  enabled: boolean
}

interface MiniSetupResponse {
  token: string
  ws_url: string
  enabled: boolean
  changed: boolean
}

const BASE_URL = ""

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await launcherFetch(`${BASE_URL}${path}`, options)
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export async function getMiniToken(): Promise<MiniTokenResponse> {
  return request<MiniTokenResponse>("/api/mini/token")
}

export async function regenMiniToken(): Promise<MiniTokenResponse> {
  return request<MiniTokenResponse>("/api/mini/token", { method: "POST" })
}

export async function setupMini(): Promise<MiniSetupResponse> {
  return request<MiniSetupResponse>("/api/mini/setup", { method: "POST" })
}

export type { MiniTokenResponse, MiniSetupResponse }
