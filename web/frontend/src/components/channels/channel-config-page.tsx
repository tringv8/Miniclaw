import { IconLoader2 } from "@tabler/icons-react"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"

import {
  type ChannelConfig,
  type SupportedChannel,
  getAppConfig,
  getChannelsCatalog,
  patchAppConfig,
} from "@/api/channels"
import { getChannelDisplayName } from "@/components/channels/channel-display-name"
import { GenericForm } from "@/components/channels/channel-forms/generic-form"
import { TelegramForm } from "@/components/channels/channel-forms/telegram-form"
import { PageHeader } from "@/components/page-header"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { useGateway } from "@/hooks/use-gateway"

interface ChannelConfigPageProps {
  channelName: string
}

const SECRET_FIELD_MAP: Record<string, string> = {
  token: "_token",
}

function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>
  }
  return {}
}

function asString(value: unknown): string {
  return typeof value === "string" ? value : ""
}

function asBool(value: unknown): boolean {
  return value === true
}

function buildEditConfig(config: ChannelConfig): ChannelConfig {
  const edit: ChannelConfig = { ...config }
  for (const editKey of Object.values(SECRET_FIELD_MAP)) {
    edit[editKey] = ""
  }
  return edit
}

function normalizeConfig(
  _channel: SupportedChannel,
  rawConfig: ChannelConfig,
): ChannelConfig {
  return { ...rawConfig }
}

function mergeConfigDefaults(
  defaults: ChannelConfig,
  rawConfig: ChannelConfig,
): ChannelConfig {
  const merged: ChannelConfig = { ...defaults, ...rawConfig }
  for (const key of Object.keys(defaults)) {
    const defaultValue = defaults[key]
    const incomingValue = rawConfig[key]
    if (
      defaultValue &&
      incomingValue &&
      typeof defaultValue === "object" &&
      typeof incomingValue === "object" &&
      !Array.isArray(defaultValue) &&
      !Array.isArray(incomingValue)
    ) {
      merged[key] = {
        ...(defaultValue as Record<string, unknown>),
        ...(incomingValue as Record<string, unknown>),
      }
    }
  }
  return merged
}

function buildSavePayload(
  editConfig: ChannelConfig,
  enabled: boolean,
): ChannelConfig {
  const payload: ChannelConfig = { enabled }

  for (const [key, value] of Object.entries(editConfig)) {
    if (key.startsWith("_")) continue
    if (key === "enabled") continue
    if (key in SECRET_FIELD_MAP) continue

    payload[key] = value
  }

  for (const [secretKey, editKey] of Object.entries(SECRET_FIELD_MAP)) {
    const incoming = asString(editConfig[editKey])
    if (incoming !== "") {
      payload[secretKey] = incoming
      continue
    }
    if (secretKey in editConfig) {
      payload[secretKey] = editConfig[secretKey]
    }
  }

  return payload
}

function isConfigured(
  channel: SupportedChannel,
  config: ChannelConfig,
): boolean {
  switch (channel.name) {
    case "telegram":
      return asString(config.token) !== ""
    case "web":
      return true
    default:
      return false
  }
}

function getRequiredFieldKeys(channelName: string): string[] {
  switch (channelName) {
    case "telegram":
      return ["token"]
    default:
      return []
  }
}

function isMissingRequiredValue(value: unknown): boolean {
  if (value === null || value === undefined) {
    return true
  }
  if (typeof value === "string") {
    return value.trim() === ""
  }
  if (Array.isArray(value)) {
    return value.length === 0
  }
  return false
}

const CHANNELS_WITHOUT_DOCS = new Set(["web"])

export function ChannelConfigPage({ channelName }: ChannelConfigPageProps) {
  const { t } = useTranslation()
  const { state: gatewayState } = useGateway()

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [fetchError, setFetchError] = useState("")
  const [serverError, setServerError] = useState("")
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const [channel, setChannel] = useState<SupportedChannel | null>(null)
  const [baseConfig, setBaseConfig] = useState<ChannelConfig>({})
  const [editConfig, setEditConfig] = useState<ChannelConfig>({})
  const [enabled, setEnabled] = useState(false)

  const loadData = useCallback(
    async (silent = false) => {
      if (!silent) setLoading(true)
      try {
        const [catalog, appConfig] = await Promise.all([
          getChannelsCatalog(),
          getAppConfig(),
        ])
        const matched =
          catalog.channels.find((item) => item.name === channelName) ?? null

        if (!matched) {
          setChannel(null)
          setFetchError(
            t("channels.page.notFound", {
              name: channelName,
            }),
          )
          return
        }

        const channelsConfig = asRecord(asRecord(appConfig).channels)
        const raw = asRecord(channelsConfig[matched.config_key])
        const defaults = asRecord(matched.defaults)
        const normalized = normalizeConfig(
          matched,
          mergeConfigDefaults(defaults, raw),
        )

        setChannel(matched)
        setBaseConfig(normalized)
        setEditConfig(buildEditConfig(normalized))
        setEnabled(asBool(normalized.enabled))
        setFetchError("")
        setServerError("")
        setFieldErrors({})
      } catch (e) {
        setFetchError(e instanceof Error ? e.message : t("channels.loadError"))
      } finally {
        if (!silent) setLoading(false)
      }
    },
    [channelName, t],
  )

  useEffect(() => {
    loadData()
  }, [loadData])

  const previousGatewayStatusRef = useRef(gatewayState)
  useEffect(() => {
    const previousStatus = previousGatewayStatusRef.current
    if (previousStatus !== "running" && gatewayState === "running") {
      void loadData()
    }
    previousGatewayStatusRef.current = gatewayState
  }, [gatewayState, loadData])

  const savePayload = useMemo(() => {
    if (!channel) return null
    return buildSavePayload(editConfig, enabled)
  }, [channel, editConfig, enabled])

  const configured = useMemo(() => {
    if (!channel || !savePayload) return false
    return isConfigured(channel, savePayload)
  }, [channel, savePayload])

  const docsUrl = useMemo(() => {
    if (!channel) return ""
    if (CHANNELS_WITHOUT_DOCS.has(channel.name)) return ""
    return "https://github.com/tringv8/Miniclaw/blob/main/docs/huongdansudung.md"
  }, [channel])

  const channelDisplayName = useMemo(() => {
    if (!channel) return channelName
    return getChannelDisplayName(channel, t)
  }, [channel, channelName, t])

  const requiredKeys = useMemo(
    () => getRequiredFieldKeys(channelName),
    [channelName],
  )

  const handleChange = useCallback((key: string, value: unknown) => {
    const normalizedKey = key.startsWith("_") ? key.slice(1) : key
    setEditConfig((prev) => ({ ...prev, [key]: value }))
    setFieldErrors((prev) => {
      if (!(key in prev) && !(normalizedKey in prev)) {
        return prev
      }
      const next = { ...prev }
      delete next[key]
      delete next[normalizedKey]
      return next
    })
  }, [])

  const handleReset = () => {
    setEditConfig(buildEditConfig(baseConfig))
    setEnabled(asBool(baseConfig.enabled))
    setServerError("")
    setFieldErrors({})
  }

  const handleSave = async () => {
    if (!channel || !savePayload) return

    const missingRequiredFields = requiredKeys.filter((key) =>
      isMissingRequiredValue(savePayload[key]),
    )
    if (missingRequiredFields.length > 0) {
      const requiredFieldError = t("channels.validation.requiredField")
      const nextFieldErrors: Record<string, string> = {}
      for (const key of missingRequiredFields) {
        nextFieldErrors[key] = requiredFieldError
      }
      setFieldErrors(nextFieldErrors)
      setServerError("")
      return
    }

    setSaving(true)
    setServerError("")
    setFieldErrors({})
    try {
      await patchAppConfig({
        channels: {
          [channel.config_key]: savePayload,
        },
      })
      await loadData()
    } catch (e) {
      const message =
        e instanceof Error ? e.message : t("channels.page.saveError")
      setServerError(message)
    } finally {
      setSaving(false)
    }
  }

  const renderForm = () => {
    if (!channel) return null
    const isEdit = configured

    switch (channel.name) {
      case "telegram":
        return (
          <TelegramForm
            config={editConfig}
            onChange={handleChange}
            isEdit={isEdit}
            fieldErrors={fieldErrors}
          />
        )

      default:
        return (
          <GenericForm
            config={editConfig}
            onChange={handleChange}
            hiddenKeys={[]}
            requiredKeys={requiredKeys}
            fieldErrors={fieldErrors}
          />
        )
    }
  }

  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title={channelDisplayName}
        titleExtra={
          channel ? (
            <div className="flex items-center gap-1.5">
              {enabled ? (
                <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
                  {t("channels.page.enabled")}
                </span>
              ) : configured ? (
                <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-600 dark:text-amber-400">
                  {t("channels.status.configured")}
                </span>
              ) : null}
            </div>
          ) : undefined
        }
      />

      <div className="flex min-h-0 flex-1 justify-center overflow-y-auto px-4 pb-8 sm:px-6">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <IconLoader2 className="text-muted-foreground size-6 animate-spin" />
          </div>
        ) : fetchError ? (
          <div className="text-destructive bg-destructive/10 rounded-lg px-4 py-3 text-sm">
            {fetchError}
          </div>
        ) : (
          <div className="w-full max-w-250 space-y-5 pt-2">
            <div className="flex items-center gap-2 text-sm">
              <p className="font-medium">
                {t("channels.edit", {
                  name: channelDisplayName,
                })}
              </p>
              {channel && docsUrl && (
                <a
                  href={docsUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-muted-foreground hover:text-foreground text-xs underline underline-offset-2"
                >
                  {t("channels.page.docLink")}
                </a>
              )}
            </div>

            <div className="border-border/60 bg-background flex items-center justify-between rounded-lg border px-4 py-3">
              <p className="text-sm font-medium">
                {t("channels.page.enableLabel")}
              </p>
              <Switch checked={enabled} onCheckedChange={setEnabled} />
            </div>

            {renderForm()}

            {serverError && (
              <p className="text-destructive text-sm">{serverError}</p>
            )}

            <div className="border-border/60 flex justify-end gap-2 border-t py-4">
              <Button variant="outline" onClick={handleReset} disabled={saving}>
                {t("common.reset")}
              </Button>
              <Button onClick={handleSave} disabled={saving}>
                {saving ? t("common.saving") : t("common.save")}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
