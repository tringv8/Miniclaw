export interface CoreConfigForm {
  workspace: string
  restrictToWorkspace: boolean
  splitOnMarker: boolean
  toolFeedbackEnabled: boolean
  toolFeedbackMaxArgsLength: string
  maxTokens: string
  contextWindowTokens: string
  maxToolIterations: string
  summarizeMessageThreshold: string
  summarizeTokenPercent: string
  temperature: string
  reasoningEffort: string
  timezone: string
  gatewayHost: string
  gatewayPort: string
  heartbeatEnabled: boolean
  heartbeatIntervalSeconds: string
  heartbeatKeepRecentMessages: string
  execEnabled: boolean
  execTimeout: string
  execPathAppend: string
  webProxy: string
  webSearchProvider: string
  webSearchApiKey: string
  webSearchBaseUrl: string
  webSearchMaxResults: string
}

export interface LauncherForm {
  port: string
  publicAccess: boolean
  allowedCIDRsText: string
}

export const EMPTY_FORM: CoreConfigForm = {
  workspace: "~/.miniclaw/workspace",
  restrictToWorkspace: false,
  splitOnMarker: false,
  toolFeedbackEnabled: false,
  toolFeedbackMaxArgsLength: "300",
  maxTokens: "8192",
  contextWindowTokens: "131072",
  maxToolIterations: "20",
  summarizeMessageThreshold: "20",
  summarizeTokenPercent: "75",
  temperature: "0.7",
  reasoningEffort: "",
  timezone: "UTC",
  gatewayHost: "0.0.0.0",
  gatewayPort: "18790",
  heartbeatEnabled: true,
  heartbeatIntervalSeconds: "1800",
  heartbeatKeepRecentMessages: "8",
  execEnabled: true,
  execTimeout: "60",
  execPathAppend: "",
  webProxy: "",
  webSearchProvider: "brave",
  webSearchApiKey: "",
  webSearchBaseUrl: "",
  webSearchMaxResults: "5",
}

export const EMPTY_LAUNCHER_FORM: LauncherForm = {
  port: "18800",
  publicAccess: false,
  allowedCIDRsText: "",
}

type JsonRecord = Record<string, unknown>

function asRecord(value: unknown): JsonRecord {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as JsonRecord
  }
  return {}
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback
}

function asBool(value: unknown, fallback = false): boolean {
  return value === undefined ? fallback : value === true
}

function asNumberString(value: unknown, fallback: string): string {
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value)
  }
  if (typeof value === "string" && value.trim() !== "") {
    return value
  }
  return fallback
}

export function buildFormFromConfig(config: unknown): CoreConfigForm {
  const root = asRecord(config)
  const agents = asRecord(root.agents)
  const defaults = asRecord(agents.defaults)
  const gateway = asRecord(root.gateway)
  const heartbeat = asRecord(gateway.heartbeat)
  const tools = asRecord(root.tools)
  const exec = asRecord(tools.exec)
  const web = asRecord(tools.web)
  const webSearch = asRecord(web.search)
  const toolFeedback = asRecord(defaults.toolFeedback)

  return {
    workspace: asString(defaults.workspace, EMPTY_FORM.workspace),
    restrictToWorkspace: asBool(
      tools.restrictToWorkspace,
      EMPTY_FORM.restrictToWorkspace,
    ),
    splitOnMarker: asBool(defaults.splitOnMarker, EMPTY_FORM.splitOnMarker),
    toolFeedbackEnabled: asBool(
      toolFeedback.enabled,
      EMPTY_FORM.toolFeedbackEnabled,
    ),
    toolFeedbackMaxArgsLength: asNumberString(
      toolFeedback.max_args_length,
      EMPTY_FORM.toolFeedbackMaxArgsLength,
    ),
    maxTokens: asNumberString(defaults.maxTokens, EMPTY_FORM.maxTokens),
    contextWindowTokens: asNumberString(
      defaults.contextWindowTokens,
      EMPTY_FORM.contextWindowTokens,
    ),
    maxToolIterations: asNumberString(
      defaults.maxToolIterations,
      EMPTY_FORM.maxToolIterations,
    ),
    summarizeMessageThreshold: asNumberString(
      defaults.summarizeMessageThreshold,
      EMPTY_FORM.summarizeMessageThreshold,
    ),
    summarizeTokenPercent: asNumberString(
      defaults.summarizeTokenPercent,
      EMPTY_FORM.summarizeTokenPercent,
    ),
    temperature: asNumberString(defaults.temperature, EMPTY_FORM.temperature),
    reasoningEffort: asString(
      defaults.reasoningEffort,
      EMPTY_FORM.reasoningEffort,
    ),
    timezone: asString(defaults.timezone, EMPTY_FORM.timezone),
    gatewayHost: asString(gateway.host, EMPTY_FORM.gatewayHost),
    gatewayPort: asNumberString(gateway.port, EMPTY_FORM.gatewayPort),
    heartbeatEnabled: asBool(heartbeat.enabled, EMPTY_FORM.heartbeatEnabled),
    heartbeatIntervalSeconds: asNumberString(
      heartbeat.intervalS,
      EMPTY_FORM.heartbeatIntervalSeconds,
    ),
    heartbeatKeepRecentMessages: asNumberString(
      heartbeat.keepRecentMessages,
      EMPTY_FORM.heartbeatKeepRecentMessages,
    ),
    execEnabled: asBool(exec.enable, EMPTY_FORM.execEnabled),
    execTimeout: asNumberString(exec.timeout, EMPTY_FORM.execTimeout),
    execPathAppend: asString(exec.pathAppend, EMPTY_FORM.execPathAppend),
    webProxy: asString(web.proxy, EMPTY_FORM.webProxy),
    webSearchProvider: asString(
      webSearch.provider,
      EMPTY_FORM.webSearchProvider,
    ),
    webSearchApiKey: asString(webSearch.apiKey, EMPTY_FORM.webSearchApiKey),
    webSearchBaseUrl: asString(
      webSearch.baseUrl,
      EMPTY_FORM.webSearchBaseUrl,
    ),
    webSearchMaxResults: asNumberString(
      webSearch.maxResults,
      EMPTY_FORM.webSearchMaxResults,
    ),
  }
}

export function parseIntField(
  rawValue: string,
  label: string,
  options: { min?: number; max?: number } = {},
): number {
  const value = Number(rawValue)
  if (!Number.isInteger(value)) {
    throw new Error(`${label} must be an integer.`)
  }
  if (options.min !== undefined && value < options.min) {
    throw new Error(`${label} must be >= ${options.min}.`)
  }
  if (options.max !== undefined && value > options.max) {
    throw new Error(`${label} must be <= ${options.max}.`)
  }
  return value
}

export function parseFloatField(
  rawValue: string,
  label: string,
  options: { min?: number; max?: number } = {},
): number {
  const value = Number(rawValue)
  if (!Number.isFinite(value)) {
    throw new Error(`${label} must be a number.`)
  }
  if (options.min !== undefined && value < options.min) {
    throw new Error(`${label} must be >= ${options.min}.`)
  }
  if (options.max !== undefined && value > options.max) {
    throw new Error(`${label} must be <= ${options.max}.`)
  }
  return value
}

export function parseCIDRText(raw: string): string[] {
  if (!raw.trim()) {
    return []
  }
  return raw
    .split(/[\n,]/)
    .map((value) => value.trim())
    .filter((value) => value.length > 0)
}
