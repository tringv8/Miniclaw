import { createFileRoute } from "@tanstack/react-router"

import { LlmBenchmarkPage } from "@/components/llm-benchmark/llm-benchmark-page"

export const Route = createFileRoute("/llm-benchmark")({
  component: LlmBenchmarkPage,
})
