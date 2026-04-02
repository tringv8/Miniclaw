import { IconCode, IconDeviceFloppy } from "@tabler/icons-react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"

import { patchAppConfig } from "@/api/channels"
import { launcherFetch } from "@/api/http"
import {
  getAutoStartStatus,
  getLauncherConfig,
  setAutoStartEnabled as updateAutoStartEnabled,
  setLauncherConfig as updateLauncherConfig,
} from "@/api/system"
import {
  AgentSection,
  AutoStartSection,
  ExecSection,
  GatewaySection,
  LauncherSection,
  WebSearchSection,
} from "@/components/config/config-sections"
import {
  type CoreConfigForm,
  EMPTY_FORM,
  EMPTY_LAUNCHER_FORM,
  type LauncherForm,
  buildFormFromConfig,
  parseCIDRText,
  parseFloatField,
  parseIntField,
} from "@/components/config/form-model"
import { PageHeader } from "@/components/page-header"
import { Button } from "@/components/ui/button"
import { refreshGatewayState } from "@/store/gateway"

export function ConfigPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [form, setForm] = useState<CoreConfigForm>(EMPTY_FORM)
  const [baseline, setBaseline] = useState<CoreConfigForm>(EMPTY_FORM)
  const [launcherForm, setLauncherForm] =
    useState<LauncherForm>(EMPTY_LAUNCHER_FORM)
  const [launcherBaseline, setLauncherBaseline] =
    useState<LauncherForm>(EMPTY_LAUNCHER_FORM)
  const [autoStartEnabled, setAutoStartEnabled] = useState(false)
  const [autoStartBaseline, setAutoStartBaseline] = useState(false)
  const [saving, setSaving] = useState(false)

  const { data, isLoading, error } = useQuery({
    queryKey: ["config"],
    queryFn: async () => {
      const res = await launcherFetch("/api/config")
      if (!res.ok) {
        throw new Error("Failed to load config")
      }
      return res.json()
    },
  })

  const { data: launcherConfig, isLoading: isLauncherLoading } = useQuery({
    queryKey: ["system", "launcher-config"],
    queryFn: getLauncherConfig,
  })

  const {
    data: autoStartStatus,
    isLoading: isAutoStartLoading,
    error: autoStartError,
  } = useQuery({
    queryKey: ["system", "autostart"],
    queryFn: getAutoStartStatus,
  })

  useEffect(() => {
    if (!data) return
    const parsed = buildFormFromConfig(data)
    setForm(parsed)
    setBaseline(parsed)
  }, [data])

  useEffect(() => {
    if (!launcherConfig) return
    const parsed: LauncherForm = {
      port: String(launcherConfig.port),
      publicAccess: launcherConfig.public,
      allowedCIDRsText: (launcherConfig.allowed_cidrs ?? []).join("\n"),
    }
    setLauncherForm(parsed)
    setLauncherBaseline(parsed)
  }, [launcherConfig])

  useEffect(() => {
    if (!autoStartStatus) return
    setAutoStartEnabled(autoStartStatus.enabled)
    setAutoStartBaseline(autoStartStatus.enabled)
  }, [autoStartStatus])

  const configDirty = JSON.stringify(form) !== JSON.stringify(baseline)
  const launcherDirty =
    JSON.stringify(launcherForm) !== JSON.stringify(launcherBaseline)
  const autoStartDirty = autoStartEnabled !== autoStartBaseline
  const isDirty = configDirty || launcherDirty || autoStartDirty

  const autoStartSupported = autoStartStatus?.supported !== false
  const autoStartHint = autoStartError
    ? "Failed to load autostart state."
    : !autoStartSupported
      ? "Autostart is not available in this Python launcher yet."
      : autoStartStatus?.message || "Changes apply on next login."

  const updateField = <K extends keyof CoreConfigForm>(
    key: K,
    value: CoreConfigForm[K],
  ) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const updateLauncherField = <K extends keyof LauncherForm>(
    key: K,
    value: LauncherForm[K],
  ) => {
    setLauncherForm((prev) => ({ ...prev, [key]: value }))
  }

  const handleReset = () => {
    setForm(baseline)
    setLauncherForm(launcherBaseline)
    setAutoStartEnabled(autoStartBaseline)
    toast.info(t("pages.config.reset_success"))
  }

  const handleSave = async () => {
    try {
      setSaving(true)

      if (configDirty) {
        const workspace = form.workspace.trim()
        if (!workspace) {
          throw new Error("Workspace path is required.")
        }

        await patchAppConfig({
          agents: {
            defaults: {
              workspace,
              restrictToWorkspace: form.restrictToWorkspace,
              splitOnMarker: form.splitOnMarker,
              toolFeedback: {
                enabled: form.toolFeedbackEnabled,
                max_args_length: parseIntField(
                  form.toolFeedbackMaxArgsLength,
                  "Tool feedback max args length",
                  { min: 0 },
                ),
              },
              maxTokens: parseIntField(form.maxTokens, "Max tokens", {
                min: 1,
              }),
              contextWindowTokens: parseIntField(
                form.contextWindowTokens,
                "Context window tokens",
                { min: 1 },
              ),
              maxToolIterations: parseIntField(
                form.maxToolIterations,
                "Max tool iterations",
                { min: 1 },
              ),
              summarizeMessageThreshold: parseIntField(
                form.summarizeMessageThreshold,
                "Summarize message threshold",
                { min: 1 },
              ),
              summarizeTokenPercent: parseIntField(
                form.summarizeTokenPercent,
                "Summarize token percent",
                { min: 1, max: 100 },
              ),
              temperature: parseFloatField(form.temperature, "Temperature", {
                min: 0,
              }),
              reasoningEffort: form.reasoningEffort.trim() || null,
              timezone: form.timezone.trim() || "UTC",
            },
          },
          gateway: {
            host: form.gatewayHost.trim() || "0.0.0.0",
            port: parseIntField(form.gatewayPort, "Gateway port", {
              min: 1,
              max: 65535,
            }),
            heartbeat: {
              enabled: form.heartbeatEnabled,
              intervalS: parseIntField(
                form.heartbeatIntervalSeconds,
                "Heartbeat interval",
                { min: 1 },
              ),
              keepRecentMessages: parseIntField(
                form.heartbeatKeepRecentMessages,
                "Keep recent messages",
                { min: 0 },
              ),
            },
          },
          tools: {
            restrictToWorkspace: form.restrictToWorkspace,
            exec: {
              enable: form.execEnabled,
              timeout: parseIntField(form.execTimeout, "Exec timeout", {
                min: 0,
              }),
              pathAppend: form.execPathAppend,
            },
            web: {
              proxy: form.webProxy.trim() || null,
              search: {
                provider: form.webSearchProvider.trim() || "brave",
                apiKey: form.webSearchApiKey.trim(),
                baseUrl: form.webSearchBaseUrl.trim(),
                maxResults: parseIntField(
                  form.webSearchMaxResults,
                  "Search max results",
                  { min: 1 },
                ),
              },
            },
          },
        })

        setBaseline(form)
        void queryClient.invalidateQueries({ queryKey: ["config"] })
      }

      if (launcherDirty) {
        const port = parseIntField(launcherForm.port, "Launcher port", {
          min: 1,
          max: 65535,
        })
        const allowedCIDRs = parseCIDRText(launcherForm.allowedCIDRsText)
        const savedLauncherConfig = await updateLauncherConfig({
          port,
          public: launcherForm.publicAccess,
          allowed_cidrs: allowedCIDRs,
        })
        const parsedLauncher: LauncherForm = {
          port: String(savedLauncherConfig.port),
          publicAccess: savedLauncherConfig.public,
          allowedCIDRsText: (savedLauncherConfig.allowed_cidrs ?? []).join(
            "\n",
          ),
        }
        setLauncherForm(parsedLauncher)
        setLauncherBaseline(parsedLauncher)
        queryClient.setQueryData(
          ["system", "launcher-config"],
          savedLauncherConfig,
        )
      }

      if (autoStartDirty) {
        if (!autoStartSupported) {
          throw new Error("Autostart is not supported in this launcher.")
        }
        const status = await updateAutoStartEnabled(autoStartEnabled)
        setAutoStartEnabled(status.enabled)
        setAutoStartBaseline(status.enabled)
        queryClient.setQueryData(["system", "autostart"], status)
      }

      toast.success(t("pages.config.save_success"))
      void refreshGatewayState({ force: true })
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : t("pages.config.save_error"),
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title={t("navigation.config")}
        children={
          <Button variant="outline" asChild>
            <Link to="/config/raw">
              <IconCode className="size-4" />
              {t("pages.config.open_raw")}
            </Link>
          </Button>
        }
      />

      <div className="flex-1 overflow-auto p-3 lg:p-6">
        <div className="mx-auto w-full max-w-[1000px] space-y-6">
          {isLoading ? (
            <div className="text-muted-foreground py-6 text-sm">
              {t("labels.loading")}
            </div>
          ) : error ? (
            <div className="text-destructive py-6 text-sm">
              Failed to load config.
            </div>
          ) : (
            <div className="space-y-6">
              {isDirty ? (
                <div className="bg-yellow-50 px-3 py-2 text-sm text-yellow-700">
                  {t("pages.config.unsaved_changes")}
                </div>
              ) : null}

              <AgentSection form={form} onFieldChange={updateField} />
              <GatewaySection form={form} onFieldChange={updateField} />
              <ExecSection form={form} onFieldChange={updateField} />
              <WebSearchSection form={form} onFieldChange={updateField} />
              <LauncherSection
                launcherForm={launcherForm}
                onFieldChange={updateLauncherField}
                disabled={saving || isLauncherLoading}
              />
              <AutoStartSection
                enabled={autoStartEnabled}
                hint={autoStartHint}
                disabled={
                  isAutoStartLoading ||
                  Boolean(autoStartError) ||
                  !autoStartSupported ||
                  saving
                }
                onChange={setAutoStartEnabled}
              />

              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={handleReset}
                  disabled={!isDirty || saving}
                >
                  {t("common.reset")}
                </Button>
                <Button onClick={handleSave} disabled={!isDirty || saving}>
                  <IconDeviceFloppy className="size-4" />
                  {saving ? t("common.saving") : t("common.save")}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
