import { launcherFetch } from "@/api/http"

export interface BenchmarkStatus {
  running: boolean
  paused: boolean
  run_id: string
  completed: number
  total: number
  iterations?: number
  selected_model_ids?: number[]
  benchmark_config?: BenchmarkConfig
  current: string
  error: string
  log: string[]
}

export interface BenchmarkModel {
  model_id: number
  model_name: string
  provider: string
  provider_model: string
}

export interface BenchmarkArticle {
  title: string
  authors?: string
  published?: string
  link: string
  doi?: string
  summary: string
}

export interface BenchmarkResult {
  id?: number
  run_id: string
  day: number | "TB"
  model_id: number
  model_name: string
  T_q1?: number | null
  N_q1?: number | null
  F_q1?: string | null
  C_q1?: number | null
  raw_response?: string
  error_note?: string
  timestamp: string
  articles?: BenchmarkArticle[]
}

export type BenchmarkMetricKey = "T_q1" | "N_q1" | "F_q1" | "C_q1"

export interface BenchmarkConfig {
  metrics: Record<BenchmarkMetricKey, boolean>
  q1_prompt: string
  updated_at?: string
}

export interface BenchmarkResultsResponse {
  results: BenchmarkResult[]
  summary: BenchmarkResult[]
}

export interface BenchmarkModelsResponse {
  models: BenchmarkModel[]
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await launcherFetch(path, options)
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export async function startBenchmark(
  iterations: number,
  modelIds?: number[]
): Promise<{
  status: string
  run_id: string
  iterations: number
  selected_model_ids: number[]
}> {
  return request<{
    status: string
    run_id: string
    iterations: number
    selected_model_ids: number[]
  }>(
    "/api/llm-benchmark/run",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        iterations,
        model_ids: modelIds,
      }),
    }
  )
}

export async function getBenchmarkModels(): Promise<BenchmarkModelsResponse> {
  return request<BenchmarkModelsResponse>("/api/llm-benchmark/models")
}

export async function getBenchmarkStatus(): Promise<BenchmarkStatus> {
  return request<BenchmarkStatus>("/api/llm-benchmark/status")
}

export async function getBenchmarkConfig(): Promise<BenchmarkConfig> {
  return request<BenchmarkConfig>("/api/llm-benchmark/config")
}

export async function updateBenchmarkConfig(config: BenchmarkConfig): Promise<BenchmarkConfig> {
  return request<BenchmarkConfig>("/api/llm-benchmark/config", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(config),
  })
}

export async function pauseBenchmark(): Promise<{ status: string; run_id: string }> {
  return request<{ status: string; run_id: string }>("/api/llm-benchmark/pause", {
    method: "POST",
  })
}

export async function resumeBenchmark(): Promise<{ status: string; run_id: string }> {
  return request<{ status: string; run_id: string }>("/api/llm-benchmark/resume", {
    method: "POST",
  })
}

export async function getBenchmarkResults(runId?: string): Promise<BenchmarkResultsResponse> {
  const query = runId ? `?run_id=${encodeURIComponent(runId)}` : ""
  return request<BenchmarkResultsResponse>(`/api/llm-benchmark/results${query}`)
}

export async function updateBenchmarkRawResponse(
  resultId: number,
  rawResponse: string
): Promise<BenchmarkResult> {
  return request<BenchmarkResult>(`/api/llm-benchmark/results/${resultId}/raw-response`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ raw_response: rawResponse }),
  })
}

function benchmarkExportQuery(runId: string | undefined): string {
  const params = new URLSearchParams()
  if (runId) params.set("run_id", runId)
  return `?${params.toString()}`
}

export function benchmarkCsvUrl(runId?: string): string {
  return `/api/llm-benchmark/export.csv${benchmarkExportQuery(runId)}`
}

export function benchmarkExcelUrl(runId?: string): string {
  return `/api/llm-benchmark/export.xls${benchmarkExportQuery(runId)}`
}

export function benchmarkModelExcelUrl(modelId: number, runId?: string): string {
  const params = new URLSearchParams()
  params.set("model_id", String(modelId))
  if (runId) params.set("run_id", runId)
  return `/api/llm-benchmark/export-model.xlsx?${params.toString()}`
}
