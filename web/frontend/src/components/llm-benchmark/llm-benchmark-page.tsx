import {
  IconDownload,
  IconPencil,
  IconPlayerPause,
  IconPlayerPlay,
  IconSettings,
} from "@tabler/icons-react"
import { useMutation, useQuery } from "@tanstack/react-query"
import * as React from "react"

import {
  benchmarkCsvUrl,
  benchmarkExcelUrl,
  benchmarkModelExcelUrl,
  getBenchmarkConfig,
  getBenchmarkModels,
  getBenchmarkResults,
  getBenchmarkStatus,
  pauseBenchmark,
  resumeBenchmark,
  startBenchmark,
  updateBenchmarkConfig,
  updateBenchmarkRawResponse,
  type BenchmarkConfig,
  type BenchmarkMetricKey,
  type BenchmarkModel,
  type BenchmarkResult,
} from "@/api/llm-benchmark"
import { PageHeader } from "@/components/page-header"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"

function formatNumber(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return ""
  }
  return value.toFixed(digits)
}

function formatN(v?: number | null): string {
  if (v == null) return ""
  return String(Math.round(v))
}

function formatF(v?: string | null): string {
  if (!v) return ""
  // v có thể là "2/3" hoặc số thập phân dạng string
  if (v.includes("/")) return v
  const num = parseFloat(v)
  if (!Number.isFinite(num)) return ""
  return `${Math.round(num)}/3`
}

function formatC(v?: number | null): string {
  if (v == null) return ""
  return v.toFixed(1)
}

function formatMetricValue(metric: BenchmarkMetricKey, row?: BenchmarkResult): string {
  if (!row) return ""
  if (metric === "T_q1") return formatNumber(row.T_q1)
  if (metric === "N_q1") return formatN(row.N_q1)
  if (metric === "F_q1") return formatF(row.F_q1)
  return formatC(row.C_q1)
}

const DEFAULT_BENCHMARK_CONFIG: BenchmarkConfig = {
  metrics: {
    T_q1: true,
    N_q1: true,
    F_q1: true,
    C_q1: true,
  },
  q1_prompt:
    "Tim 3 bai bao moi nhat ve linh vuc Materials Science tren ArXiv theo skill.md cua arxiv-watcher.",
}

const METRIC_DEFINITIONS: Array<{
  key: BenchmarkMetricKey
  label: string
  tableLabel: string
  description: string
}> = [
  {
    key: "T_q1",
    label: "T_q1",
    tableLabel: "T_q1 (s)",
    description: "Thoi gian end-to-end cua tac vu Q1, tinh bang giay.",
  },
  {
    key: "N_q1",
    label: "N_q1",
    tableLabel: "N_q1 (0-3)",
    description: "So bai bao hop le trich duoc tu ket qua Q1, toi da 3 bai.",
  },
  {
    key: "F_q1",
    label: "F_q1",
    tableLabel: "F_q1 (x/3)",
    description: "So bai trong 3 bai dau dung format cua skill arxiv-watcher.",
  },
  {
    key: "C_q1",
    label: "C_q1",
    tableLabel: "C_q1 (0-5)",
    description: "Diem chat luong tom tat tieng Viet so voi abstract goc, thang 1-5.",
  },
]

interface PivotRow {
  day: number | "TB"
  cells: Record<number, BenchmarkResult | undefined>
}

function buildPivotRows(
  results: BenchmarkResult[],
  models: BenchmarkModel[],
  iterations: number,
  summary: BenchmarkResult[] = []
): PivotRow[] {
  const maxResultDay = results.reduce(
    (max, row) => (typeof row.day === "number" ? Math.max(max, row.day) : max),
    0
  )
  const rowCount = Math.max(iterations, maxResultDay)
  const rows: PivotRow[] = Array.from({ length: rowCount }, (_, index) => ({
    day: index + 1,
    cells: {},
  }))

  for (const result of results) {
    if (typeof result.day !== "number") continue
    const targetRow = rows[result.day - 1]
    if (targetRow) {
      targetRow.cells[result.model_id] = result
    }
  }

  if (rowCount > 0 || summary.length > 0) {
    const summaryCells: Record<number, BenchmarkResult | undefined> = {}
    for (const model of models) {
      summaryCells[model.model_id] = summary.find((row) => row.model_id === model.model_id)
    }
    rows.push({ day: "TB", cells: summaryCells })
  }

  return rows
}

export function LlmBenchmarkPage() {
  const [iterations, setIterations] = React.useState(30)
  const [selectedModelIds, setSelectedModelIds] = React.useState<number[]>([])
  const [rawOpen, setRawOpen] = React.useState(false)
  const [configOpen, setConfigOpen] = React.useState(false)
  const [rawActiveModelId, setRawActiveModelId] = React.useState<number | null>(null)
  const [draftConfig, setDraftConfig] =
    React.useState<BenchmarkConfig>(DEFAULT_BENCHMARK_CONFIG)
  const initializedModelsRef = React.useRef(false)

  const statusQuery = useQuery({
    queryKey: ["llm-benchmark-status"],
    queryFn: getBenchmarkStatus,
    refetchInterval: (query) => (query.state.data?.running ? 1500 : 4000),
  })
  const status = statusQuery.data
  const runId = status?.running ? status.run_id || undefined : undefined

  const modelsQuery = useQuery({
    queryKey: ["llm-benchmark-models"],
    queryFn: getBenchmarkModels,
  })
  const benchmarkModels = modelsQuery.data?.models ?? []

  const configQuery = useQuery({
    queryKey: ["llm-benchmark-config"],
    queryFn: getBenchmarkConfig,
  })
  const benchmarkConfig = configQuery.data ?? DEFAULT_BENCHMARK_CONFIG
  const visibleMetrics = METRIC_DEFINITIONS.filter(
    (metric) => benchmarkConfig.metrics[metric.key]
  )

  React.useEffect(() => {
    if (configQuery.data) {
      setDraftConfig(configQuery.data)
    }
  }, [configQuery.data])

  React.useEffect(() => {
    if (!initializedModelsRef.current && benchmarkModels.length > 0) {
      initializedModelsRef.current = true
      setSelectedModelIds(benchmarkModels.map((model) => model.model_id))
    }
  }, [benchmarkModels])

  const resultsQuery = useQuery({
    queryKey: ["llm-benchmark-results", runId],
    queryFn: () => getBenchmarkResults(runId),
    refetchInterval: status?.running ? 1500 : false,
  })

  const startMutation = useMutation({
    mutationFn: (payload: { iterations: number; modelIds: number[] }) =>
      startBenchmark(payload.iterations, payload.modelIds),
    onSuccess: async () => {
      await Promise.all([statusQuery.refetch(), resultsQuery.refetch()])
    },
  })

  const pauseMutation = useMutation({
    mutationFn: () => (status?.paused ? resumeBenchmark() : pauseBenchmark()),
    onSuccess: async () => {
      await statusQuery.refetch()
    },
  })

  const configMutation = useMutation({
    mutationFn: (config: BenchmarkConfig) => updateBenchmarkConfig(config),
    onSuccess: async (savedConfig) => {
      setDraftConfig(savedConfig)
      await Promise.all([configQuery.refetch(), statusQuery.refetch()])
    },
  })

  const results = resultsQuery.data?.results ?? []
  const summary = resultsQuery.data?.summary ?? []
  const displayedSelectedModelIds = status?.running
    ? (status.selected_model_ids ?? selectedModelIds)
    : selectedModelIds
  const inferredRunningIterations =
    status?.running && status.total > 0 && displayedSelectedModelIds.length > 0
      ? Math.ceil(status.total / displayedSelectedModelIds.length)
      : 0
  const pivotIterations = status?.running
    ? (status.iterations || inferredRunningIterations)
    : 0
  const pivotRows = React.useMemo(
    () => buildPivotRows(results, benchmarkModels, pivotIterations, summary),
    [results, benchmarkModels, pivotIterations, summary]
  )
  const modelGroupColSpan = Math.max(1, benchmarkModels.length)
  const resultTableColSpan = 1 + modelGroupColSpan * visibleMetrics.length
  const progress =
    status && status.total > 0
      ? Math.min(100, Math.round((status.completed / status.total) * 100))
      : 0
  const canExport = !status?.running && results.length > 0
  const canPauseOrResume = Boolean(status?.running) && !pauseMutation.isPending
  const canStartBenchmark =
    !status?.running && !startMutation.isPending && selectedModelIds.length > 0

  const toggleModel = React.useCallback((modelId: number, checked: boolean) => {
    setSelectedModelIds((current) => {
      if (checked) {
        return current.includes(modelId) ? current : [...current, modelId].sort((a, b) => a - b)
      }
      return current.filter((id) => id !== modelId)
    })
  }, [])

  const toggleMetric = React.useCallback((metric: BenchmarkMetricKey, checked: boolean) => {
    setDraftConfig((current) => ({
      ...current,
      metrics: {
        ...current.metrics,
        [metric]: checked,
      },
    }))
  }, [])

  return (
    <div className="flex h-full flex-col">
      <PageHeader title="So sanh LLM" />

      <div className="flex flex-1 flex-col gap-5 overflow-auto p-4 sm:p-8">
        <section className="border-border bg-background rounded-lg border p-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="grid gap-2">
              <Label htmlFor="benchmark-iterations">
                So lan thu nghiem (tuong duong so ngay)
              </Label>
              <Input
                id="benchmark-iterations"
                type="number"
                min={1}
                max={365}
                value={iterations}
                onChange={(event) => setIterations(Number(event.target.value || 1))}
                className="w-56"
                disabled={status?.running || startMutation.isPending}
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={() =>
                  startMutation.mutate({
                    iterations,
                    modelIds: selectedModelIds,
                  })
                }
                disabled={!canStartBenchmark}
              >
                <IconPlayerPlay className="size-4" />
                Khoi chay kiem thu
              </Button>
              <Button
                variant="outline"
                onClick={() => pauseMutation.mutate()}
                disabled={!canPauseOrResume}
              >
                {status?.paused ? (
                  <IconPlayerPlay className="size-4" />
                ) : (
                  <IconPlayerPause className="size-4" />
                )}
                {status?.paused ? "Chay tiep" : "Dung"}
              </Button>
              <Button
                variant="outline"
                disabled={!canExport}
                onClick={() => {
                  if (canExport) {
                    globalThis.location.assign(benchmarkCsvUrl(runId))
                  }
                }}
              >
                <IconDownload className="size-4" />
                Xuat CSV
              </Button>
              <Button
                variant="outline"
                disabled={!canExport}
                onClick={() => {
                  if (canExport) {
                    globalThis.location.assign(benchmarkExcelUrl(runId))
                  }
                }}
              >
                <IconDownload className="size-4" />
                Xuat Excel
              </Button>
              <Button
                variant="outline"
                disabled={results.length === 0}
                onClick={() => {
                  setRawOpen((v) => !v)
                  if (!rawOpen && benchmarkModels.length > 0 && rawActiveModelId === null) {
                    setRawActiveModelId(benchmarkModels[0]?.model_id ?? null)
                  }
                }}
              >
                {rawOpen ? "An bao tim duoc" : "Du lieu bao tim duoc"}
              </Button>
              <Button variant="outline" onClick={() => setConfigOpen((v) => !v)}>
                <IconSettings className="size-4" />
                Cau hinh
              </Button>
            </div>
          </div>
          {startMutation.error ? (
            <p className="text-destructive mt-3 text-sm">
              Khong the khoi chay benchmark.
            </p>
          ) : null}
          {selectedModelIds.length === 0 ? (
            <p className="text-destructive mt-3 text-sm">
              Can bat it nhat mot model de chay benchmark.
            </p>
          ) : null}
          <div className="border-border mt-4 border-t pt-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold">Model chay kiem thu</h2>
              <span className="text-muted-foreground text-xs">
                {displayedSelectedModelIds.length}/{benchmarkModels.length || 5} model dang bat
              </span>
            </div>
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
              {benchmarkModels.map((model) => (
                <div
                  key={model.model_id}
                  className="border-border flex min-h-16 items-center gap-3 rounded-md border px-3 py-2"
                >
                  <Switch
                    id={`benchmark-model-${model.model_id}`}
                    checked={selectedModelIds.includes(model.model_id)}
                    onCheckedChange={(checked) => toggleModel(model.model_id, checked)}
                    disabled={status?.running || startMutation.isPending}
                  />
                  <Label htmlFor={`benchmark-model-${model.model_id}`} className="min-w-0">
                    <span className="block truncate text-sm font-medium">{model.model_name}</span>
                    <span className="text-muted-foreground block truncate text-xs">
                      {model.provider_model}
                    </span>
                  </Label>
                </div>
              ))}
            </div>
          </div>
        </section>

        {configOpen && (
          <BenchmarkConfigPanel
            config={draftConfig}
            isSaving={configMutation.isPending}
            isRunning={Boolean(status?.running)}
            onMetricChange={toggleMetric}
            onPromptChange={(q1Prompt) =>
              setDraftConfig((current) => ({
                ...current,
                q1_prompt: q1Prompt,
              }))
            }
            onSave={() => configMutation.mutate(draftConfig)}
          />
        )}

        <section className="border-border bg-background rounded-lg border">
          <div className="border-b px-4 py-3">
            <div className="flex items-center justify-between gap-4 text-sm">
              <span className="font-medium">{status?.current || "Chua chay"}</span>
              <span className="text-muted-foreground">
                {status?.completed ?? 0}/{status?.total ?? 0}
              </span>
            </div>
            <div className="bg-muted mt-3 h-2 overflow-hidden rounded-full">
              <div className="bg-primary h-full transition-all" style={{ width: `${progress}%` }} />
            </div>
            {status?.error ? (
              <p className="text-destructive mt-2 text-sm">{status.error}</p>
            ) : null}
          </div>
          <pre className="text-muted-foreground h-40 overflow-auto p-4 text-xs leading-5">
            {(status?.log ?? []).join("\n") || "Dang cho log..."}
          </pre>
        </section>

        <section className="border-border bg-background min-h-0 rounded-lg border">
          <div className="border-b px-4 py-3">
            <h2 className="text-sm font-semibold">Bang ket qua</h2>
          </div>
          <div className="overflow-auto">
            <table className="w-full min-w-[1800px] border-collapse text-sm">
              <thead className="bg-muted/60 text-muted-foreground">
                <tr>
                  <th className="w-20 px-3 py-2 text-left font-medium" rowSpan={2}>
                    Ngay
                  </th>
                  {visibleMetrics.map((metric) => (
                    <th
                      key={metric.key}
                      className="border-l px-3 py-2 text-center font-medium"
                      colSpan={modelGroupColSpan}
                    >
                      {metric.tableLabel}
                    </th>
                  ))}
                  {false && (
                    <>
                  <th className="border-l px-3 py-2 text-center font-medium" colSpan={modelGroupColSpan}>
                    N_q1 (0–3)
                  </th>
                  <th className="border-l px-3 py-2 text-center font-medium" colSpan={modelGroupColSpan}>
                    C_q1 (0–5)
                  </th>
                    </>
                  )}
                </tr>
                <tr>
                  {visibleMetrics.map((metric) =>
                    benchmarkModels.map((model, index) => (
                      <th
                        key={`${metric.key}-${model.model_id}`}
                        className={`min-w-24 px-3 py-2 text-right font-medium ${
                          index === 0 ? "border-l" : ""
                        }`}
                      >
                        {model.model_name}
                      </th>
                    ))
                  )}
                </tr>
              </thead>
              <tbody>
                {pivotRows.map((row) => (
                  <tr
                    key={`pivot-${row.day}`}
                    className={row.day === "TB" ? "border-t bg-muted/45 font-medium" : "border-t"}
                  >
                    <td className="px-3 py-2 text-left">{row.day}</td>
                    {visibleMetrics.map((metric) =>
                      benchmarkModels.map((model, index) => (
                        <td
                          key={`${metric.key}-${row.day}-${model.model_id}`}
                          className={`px-3 py-2 text-right ${index === 0 ? "border-l" : ""}`}
                        >
                          {formatMetricValue(metric.key, row.cells[model.model_id])}
                        </td>
                      ))
                    )}
                  </tr>
                ))}
                {pivotRows.length === 0 ? (
                  <tr>
                    <td
                      className="text-muted-foreground px-3 py-8 text-center"
                      colSpan={resultTableColSpan}
                    >
                      Chua co ket qua.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>

        {/* Panel: Du lieu bao tim duoc - raw response theo tung model */}
        {rawOpen && results.length > 0 && (
          <RawResponsePanel
            results={results}
            models={benchmarkModels}
            activeModelId={rawActiveModelId}
            metricConfig={benchmarkConfig}
            iterationCount={status?.iterations || iterations}
            runId={runId}
            onSelectModel={setRawActiveModelId}
            onSaved={() => resultsQuery.refetch()}
          />
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// BenchmarkConfigPanel
// ---------------------------------------------------------------------------

function BenchmarkConfigPanel({
  config,
  isSaving,
  isRunning,
  onMetricChange,
  onPromptChange,
  onSave,
}: {
  config: BenchmarkConfig
  isSaving: boolean
  isRunning: boolean
  onMetricChange: (metric: BenchmarkMetricKey, checked: boolean) => void
  onPromptChange: (q1Prompt: string) => void
  onSave: () => void
}) {
  return (
    <section className="border-border bg-background rounded-lg border">
      <div className="border-b px-4 py-3">
        <h2 className="text-sm font-semibold">Cau hinh</h2>
      </div>
      <div className="grid gap-5 p-4">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {METRIC_DEFINITIONS.map((metric) => (
            <div key={metric.key} className="border-border rounded-md border p-3">
              <div className="flex items-center justify-between gap-3">
                <Label htmlFor={`metric-${metric.key}`} className="text-sm font-medium">
                  {metric.label}
                </Label>
                <Switch
                  id={`metric-${metric.key}`}
                  checked={config.metrics[metric.key]}
                  onCheckedChange={(checked) => onMetricChange(metric.key, checked)}
                />
              </div>
              <p className="text-muted-foreground mt-2 text-xs leading-5">
                {metric.description}
              </p>
            </div>
          ))}
        </div>

        <div className="grid gap-2">
          <Label htmlFor="benchmark-q1-prompt">Truy van thu nghiem Q1</Label>
          <Textarea
            id="benchmark-q1-prompt"
            value={config.q1_prompt}
            onChange={(event) => onPromptChange(event.target.value)}
            className="min-h-28"
          />
        </div>

        <div className="flex items-center justify-between gap-3">
          <p className="text-muted-foreground text-xs">
            Cau hinh duoc luu vao SQLite local va benchmark dang chay dung snapshot tai luc bat dau.
          </p>
          <Button onClick={onSave} disabled={isSaving}>
            {isSaving ? "Dang luu..." : isRunning ? "Luu cho lan sau" : "Luu cau hinh"}
          </Button>
        </div>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// RawResponsePanel
// ---------------------------------------------------------------------------

const MODEL_TAB_COLORS: Record<number, string> = {
  1: "border-blue-500 text-blue-700 dark:text-blue-400",
  2: "border-green-500 text-green-700 dark:text-green-400",
  3: "border-orange-500 text-orange-700 dark:text-orange-400",
  4: "border-purple-500 text-purple-700 dark:text-purple-400",
}

function modelShortName(model: BenchmarkModel): string {
  const name = model.model_name.toLowerCase()
  if (name.includes("gemini")) return "Gemini"
  if (name.includes("deepseek")) return "Deepseek"
  if (name.includes("qwen")) return "Qwen"
  return "GPT"
}

function buildResultsByModel(
  results: BenchmarkResult[],
  models: BenchmarkModel[]
): Map<number, Map<number, BenchmarkResult>> {
  const map = new Map<number, Map<number, BenchmarkResult>>()
  for (const model of models) {
    const rowsByDay = new Map<number, BenchmarkResult>()
    for (const row of results) {
      if (row.model_id === model.model_id && typeof row.day === "number") {
        rowsByDay.set(row.day, row)
      }
    }
    map.set(model.model_id, rowsByDay)
  }
  return map
}

function RawResponsePanel({
  results,
  models,
  activeModelId,
  metricConfig,
  iterationCount,
  runId,
  onSelectModel,
  onSaved,
}: {
  results: BenchmarkResult[]
  models: BenchmarkModel[]
  activeModelId: number | null
  metricConfig: BenchmarkConfig
  iterationCount: number
  runId?: string
  onSelectModel: (id: number) => void
  onSaved: () => Promise<unknown>
}) {
  const [editingResultId, setEditingResultId] = React.useState<number | null>(null)
  const [draftRawResponse, setDraftRawResponse] = React.useState("")
  const resultsByModel = React.useMemo(
    () => buildResultsByModel(results, models),
    [results, models]
  )

  const activeId = activeModelId ?? models[0]?.model_id ?? null
  const activeRows = activeId != null ? resultsByModel.get(activeId) : undefined
  const maxResultDay = results.reduce(
    (max, row) => (typeof row.day === "number" ? Math.max(max, row.day) : max),
    0
  )
  const trialCount = Math.max(30, iterationCount || 0, maxResultDay)
  const activeModel = models.find((model) => model.model_id === activeId)
  const visibleMetrics = METRIC_DEFINITIONS.filter(
    (metric) => metricConfig.metrics[metric.key]
  )
  const saveRawMutation = useMutation({
    mutationFn: (payload: { resultId: number; rawResponse: string }) =>
      updateBenchmarkRawResponse(payload.resultId, payload.rawResponse),
    onSuccess: async () => {
      setEditingResultId(null)
      setDraftRawResponse("")
      await onSaved()
    },
  })

  const startEditing = React.useCallback((result: BenchmarkResult) => {
    if (result.id == null) return
    setEditingResultId(result.id)
    setDraftRawResponse(result.raw_response || "")
  }, [])

  const cancelEditing = React.useCallback(() => {
    setEditingResultId(null)
    setDraftRawResponse("")
  }, [])

  return (
    <section className="border-border bg-background rounded-lg border">
      <div className="border-b px-4 py-3">
        <h2 className="text-sm font-semibold">Du lieu bao tim duoc</h2>
      </div>

      <div className="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-4">
        {models.map((model) => {
          const modelRows = resultsByModel.get(model.model_id)
          const count = modelRows?.size ?? 0
          const isActive = model.model_id === activeId
          const colorCls = MODEL_TAB_COLORS[model.model_id] ?? "border-zinc-500 text-zinc-700"
          return (
            <button
              key={model.model_id}
              onClick={() => onSelectModel(model.model_id)}
              className={[
                "border-border min-h-20 rounded-md border px-4 py-3 text-left transition-colors",
                isActive ? `bg-muted/60 ${colorCls}` : "hover:bg-muted/50",
              ].join(" ")}
            >
              <span className="block text-base font-semibold">{modelShortName(model)}</span>
              <span className="text-muted-foreground mt-1 block text-xs">
                {count}/{trialCount} lan thu da luu
              </span>
            </button>
          )
        })}
      </div>

      <div className="border-t p-4">
        <div className="grid gap-3">
          {Array.from({ length: trialCount }, (_, index) => {
            const day = index + 1
            const result = activeRows?.get(day)
            const isEditing = Boolean(result?.id && editingResultId === result.id)
            return (
              <details key={`trial-${activeId}-${day}`} className="border-border rounded-md border">
                <summary className="flex cursor-pointer items-center justify-between gap-3 px-3 py-2 text-sm font-medium">
                  <span className="flex items-center gap-2">
                    <span>Lan thu {day}</span>
                    {result?.id != null ? (
                      <button
                        type="button"
                        className="text-muted-foreground hover:text-foreground rounded p-1"
                        onClick={(event) => {
                          event.preventDefault()
                          event.stopPropagation()
                          startEditing(result)
                        }}
                        aria-label={`Sua lan thu ${day}`}
                      >
                        <IconPencil className="size-4" />
                      </button>
                    ) : null}
                  </span>
                  <span className="flex items-center gap-2">
                    {isEditing ? (
                      <>
                        <Button
                          size="sm"
                          onClick={(event) => {
                            event.preventDefault()
                            event.stopPropagation()
                            if (result?.id != null) {
                              saveRawMutation.mutate({
                                resultId: result.id,
                                rawResponse: draftRawResponse,
                              })
                            }
                          }}
                          disabled={saveRawMutation.isPending}
                        >
                          Luu
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={(event) => {
                            event.preventDefault()
                            event.stopPropagation()
                            cancelEditing()
                          }}
                          disabled={saveRawMutation.isPending}
                        >
                          Huy
                        </Button>
                      </>
                    ) : null}
                    <span className="text-muted-foreground text-xs">
                      {result ? result.timestamp : "Chua co du lieu"}
                    </span>
                  </span>
                </summary>
                <div className="border-t px-3 py-3">
                  {result ? (
                    <div className="grid gap-3">
                      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                        {visibleMetrics.map((metric) => (
                          <div key={metric.key} className="bg-muted/40 rounded-md px-3 py-2">
                            <div className="text-muted-foreground text-xs">{metric.label}</div>
                            <div className="text-sm font-medium">
                              {formatMetricValue(metric.key, result) || "-"}
                            </div>
                          </div>
                        ))}
                      </div>
                      {!isEditing && result.articles && result.articles.length > 0 ? (
                        <div className="grid gap-2">
                          {result.articles.map((article, articleIndex) => (
                            <div
                              key={`${article.title}-${articleIndex}`}
                              className="bg-muted/30 rounded-md px-3 py-2 text-xs"
                            >
                              <div className="font-medium">{article.title}</div>
                              {article.link ? (
                                <a
                                  className="text-primary break-all"
                                  href={article.link}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  {article.link}
                                </a>
                              ) : null}
                              {article.summary ? (
                                <p className="text-muted-foreground mt-1">{article.summary}</p>
                              ) : null}
                            </div>
                          ))}
                        </div>
                      ) : null}
                      {result.error_note ? (
                        <p className="text-destructive text-xs">Loi: {result.error_note}</p>
                      ) : null}
                      {isEditing ? (
                        <Textarea
                          value={draftRawResponse}
                          onChange={(event) => setDraftRawResponse(event.target.value)}
                          className="min-h-96 font-mono text-xs leading-relaxed"
                          disabled={saveRawMutation.isPending}
                        />
                      ) : (
                        <pre className="text-foreground max-h-80 overflow-auto whitespace-pre-wrap break-words text-xs leading-relaxed">
                          {result.raw_response || "(Khong co du lieu)"}
                        </pre>
                      )}
                    </div>
                  ) : (
                    <p className="text-muted-foreground text-sm">
                      Chua co ket qua luu cho lan thu nay.
                    </p>
                  )}
                </div>
              </details>
            )
          })}
          {activeModel ? (
            <div className="flex justify-end pt-1">
              <Button
                variant="outline"
                onClick={() => {
                  globalThis.location.assign(benchmarkModelExcelUrl(activeModel.model_id, runId))
                }}
              >
                <IconDownload className="size-4" />
                Xuat Excel
              </Button>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  )
}
