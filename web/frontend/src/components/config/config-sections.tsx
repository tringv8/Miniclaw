import type { ReactNode } from "react"

import {
  type CoreConfigForm,
  type LauncherForm,
} from "@/components/config/form-model"
import { Field, SwitchCardField } from "@/components/shared-form"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"

type UpdateCoreField = <K extends keyof CoreConfigForm>(
  key: K,
  value: CoreConfigForm[K],
) => void

type UpdateLauncherField = <K extends keyof LauncherForm>(
  key: K,
  value: LauncherForm[K],
) => void

interface ConfigSectionCardProps {
  title: string
  description?: string
  children: ReactNode
}

function ConfigSectionCard({
  title,
  description,
  children,
}: ConfigSectionCardProps) {
  return (
    <Card size="sm">
      <CardHeader className="border-border border-b">
        <CardTitle>{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent className="pt-0">
        <div className="divide-border/70 divide-y">{children}</div>
      </CardContent>
    </Card>
  )
}

interface AgentSectionProps {
  form: CoreConfigForm
  onFieldChange: UpdateCoreField
}

export function AgentSection({ form, onFieldChange }: AgentSectionProps) {
  return (
    <ConfigSectionCard
      title="Agent defaults"
      description="Core runtime settings used by miniclaw when it starts a loop."
    >
      <Field
        label="Workspace"
        hint="Base workspace path used by miniclaw."
        layout="setting-row"
      >
        <Input
          value={form.workspace}
          onChange={(e) => onFieldChange("workspace", e.target.value)}
          placeholder="~/.miniclaw/workspace"
        />
      </Field>

      <SwitchCardField
        label="Restrict tools to workspace"
        hint="Apply workspace sandboxing to filesystem and exec tools."
        layout="setting-row"
        checked={form.restrictToWorkspace}
        onCheckedChange={(checked) =>
          onFieldChange("restrictToWorkspace", checked)
        }
      />

      <SwitchCardField
        label="Split on marker"
        hint="Split long assistant replies on channel markers when supported."
        layout="setting-row"
        checked={form.splitOnMarker}
        onCheckedChange={(checked) => onFieldChange("splitOnMarker", checked)}
      />

      <SwitchCardField
        label="Tool feedback"
        hint="Include concise tool-call feedback in the assistant transcript."
        layout="setting-row"
        checked={form.toolFeedbackEnabled}
        onCheckedChange={(checked) =>
          onFieldChange("toolFeedbackEnabled", checked)
        }
      />

      {form.toolFeedbackEnabled ? (
        <Field
          label="Tool feedback max args length"
          hint="Maximum argument preview length shown in tool feedback."
          layout="setting-row"
        >
          <Input
            type="number"
            min={0}
            value={form.toolFeedbackMaxArgsLength}
            onChange={(e) =>
              onFieldChange("toolFeedbackMaxArgsLength", e.target.value)
            }
          />
        </Field>
      ) : null}

      <Field
        label="Max tokens"
        hint="Completion token budget for a single model response."
        layout="setting-row"
      >
        <Input
          type="number"
          min={1}
          value={form.maxTokens}
          onChange={(e) => onFieldChange("maxTokens", e.target.value)}
        />
      </Field>

      <Field
        label="Context window tokens"
        hint="Approximate total context budget available to the loop."
        layout="setting-row"
      >
        <Input
          type="number"
          min={1}
          value={form.contextWindowTokens}
          onChange={(e) => onFieldChange("contextWindowTokens", e.target.value)}
        />
      </Field>

      <Field
        label="Max tool iterations"
        hint="Maximum number of tool rounds before the loop stops."
        layout="setting-row"
      >
        <Input
          type="number"
          min={1}
          value={form.maxToolIterations}
          onChange={(e) => onFieldChange("maxToolIterations", e.target.value)}
        />
      </Field>

      <Field
        label="Summarize message threshold"
        hint="Start summarizing after this many messages in a session."
        layout="setting-row"
      >
        <Input
          type="number"
          min={1}
          value={form.summarizeMessageThreshold}
          onChange={(e) =>
            onFieldChange("summarizeMessageThreshold", e.target.value)
          }
        />
      </Field>

      <Field
        label="Summarize token percent"
        hint="How aggressively old context should be summarized."
        layout="setting-row"
      >
        <Input
          type="number"
          min={1}
          max={100}
          value={form.summarizeTokenPercent}
          onChange={(e) =>
            onFieldChange("summarizeTokenPercent", e.target.value)
          }
        />
      </Field>

      <Field
        label="Temperature"
        hint="Sampling temperature used by compatible providers."
        layout="setting-row"
      >
        <Input
          value={form.temperature}
          onChange={(e) => onFieldChange("temperature", e.target.value)}
        />
      </Field>

      <Field
        label="Reasoning effort"
        hint="Optional provider hint such as low, medium, or high."
        layout="setting-row"
      >
        <Input
          value={form.reasoningEffort}
          onChange={(e) => onFieldChange("reasoningEffort", e.target.value)}
          placeholder="medium"
        />
      </Field>

      <Field
        label="Timezone"
        hint="IANA timezone name used by cron and runtime context."
        layout="setting-row"
      >
        <Input
          value={form.timezone}
          onChange={(e) => onFieldChange("timezone", e.target.value)}
          placeholder="Asia/Saigon"
        />
      </Field>
    </ConfigSectionCard>
  )
}

interface GatewaySectionProps {
  form: CoreConfigForm
  onFieldChange: UpdateCoreField
}

export function GatewaySection({
  form,
  onFieldChange,
}: GatewaySectionProps) {
  return (
    <ConfigSectionCard
      title="Gateway"
      description="Network listener and background heartbeat settings."
    >
      <Field
        label="Gateway host"
        hint="Interface that the miniclaw gateway binds to."
        layout="setting-row"
      >
        <Input
          value={form.gatewayHost}
          onChange={(e) => onFieldChange("gatewayHost", e.target.value)}
          placeholder="0.0.0.0"
        />
      </Field>

      <Field
        label="Gateway port"
        hint="HTTP port exposed by the miniclaw gateway."
        layout="setting-row"
      >
        <Input
          type="number"
          min={1}
          max={65535}
          value={form.gatewayPort}
          onChange={(e) => onFieldChange("gatewayPort", e.target.value)}
        />
      </Field>

      <SwitchCardField
        label="Heartbeat enabled"
        hint="Run periodic background checks using HEARTBEAT.md."
        layout="setting-row"
        checked={form.heartbeatEnabled}
        onCheckedChange={(checked) =>
          onFieldChange("heartbeatEnabled", checked)
        }
      />

      {form.heartbeatEnabled ? (
        <>
          <Field
            label="Heartbeat interval seconds"
            hint="Delay between heartbeat checks."
            layout="setting-row"
          >
            <Input
              type="number"
              min={1}
              value={form.heartbeatIntervalSeconds}
              onChange={(e) =>
                onFieldChange("heartbeatIntervalSeconds", e.target.value)
              }
            />
          </Field>

          <Field
            label="Keep recent messages"
            hint="Number of recent messages retained for heartbeat execution."
            layout="setting-row"
          >
            <Input
              type="number"
              min={0}
              value={form.heartbeatKeepRecentMessages}
              onChange={(e) =>
                onFieldChange("heartbeatKeepRecentMessages", e.target.value)
              }
            />
          </Field>
        </>
      ) : null}
    </ConfigSectionCard>
  )
}

interface ExecSectionProps {
  form: CoreConfigForm
  onFieldChange: UpdateCoreField
}

export function ExecSection({ form, onFieldChange }: ExecSectionProps) {
  return (
    <ConfigSectionCard
      title="Exec tool"
      description="Shell execution policy used by the exec tool."
    >
      <SwitchCardField
        label="Enable exec"
        hint="Allow the agent to run shell commands."
        layout="setting-row"
        checked={form.execEnabled}
        onCheckedChange={(checked) => onFieldChange("execEnabled", checked)}
      />

      <Field
        label="Exec timeout seconds"
        hint="Maximum runtime for a single exec command."
        layout="setting-row"
      >
        <Input
          type="number"
          min={0}
          value={form.execTimeout}
          disabled={!form.execEnabled}
          onChange={(e) => onFieldChange("execTimeout", e.target.value)}
        />
      </Field>

      <Field
        label="PATH append"
        hint="Extra directories appended to PATH when exec runs."
        layout="setting-row"
      >
        <Textarea
          value={form.execPathAppend}
          disabled={!form.execEnabled}
          className="min-h-[88px]"
          onChange={(e) => onFieldChange("execPathAppend", e.target.value)}
          placeholder="C:\\Tools\\bin"
        />
      </Field>
    </ConfigSectionCard>
  )
}

interface WebSearchSectionProps {
  form: CoreConfigForm
  onFieldChange: UpdateCoreField
}

export function WebSearchSection({
  form,
  onFieldChange,
}: WebSearchSectionProps) {
  return (
    <ConfigSectionCard
      title="Web tools"
      description="Proxy and search provider settings used by web_search and web_fetch."
    >
      <Field
        label="Proxy"
        hint="Optional HTTP or SOCKS proxy."
        layout="setting-row"
      >
        <Input
          value={form.webProxy}
          onChange={(e) => onFieldChange("webProxy", e.target.value)}
          placeholder="http://127.0.0.1:7890"
        />
      </Field>

      <Field
        label="Search provider"
        hint="One of brave, tavily, duckduckgo, searxng, or jina."
        layout="setting-row"
      >
        <Input
          value={form.webSearchProvider}
          onChange={(e) => onFieldChange("webSearchProvider", e.target.value)}
          placeholder="brave"
        />
      </Field>

      <Field
        label="Search API key"
        hint="Leave blank for providers that do not require an API key."
        layout="setting-row"
      >
        <Input
          value={form.webSearchApiKey}
          onChange={(e) => onFieldChange("webSearchApiKey", e.target.value)}
          placeholder="Search API key"
        />
      </Field>

      <Field
        label="Search base URL"
        hint="Used for providers such as SearXNG."
        layout="setting-row"
      >
        <Input
          value={form.webSearchBaseUrl}
          onChange={(e) => onFieldChange("webSearchBaseUrl", e.target.value)}
          placeholder="https://search.example.com"
        />
      </Field>

      <Field
        label="Max results"
        hint="Maximum number of search results returned to the agent."
        layout="setting-row"
      >
        <Input
          type="number"
          min={1}
          value={form.webSearchMaxResults}
          onChange={(e) => onFieldChange("webSearchMaxResults", e.target.value)}
        />
      </Field>
    </ConfigSectionCard>
  )
}

interface LauncherSectionProps {
  launcherForm: LauncherForm
  onFieldChange: UpdateLauncherField
  disabled: boolean
}

export function LauncherSection({
  launcherForm,
  onFieldChange,
  disabled,
}: LauncherSectionProps) {
  return (
    <ConfigSectionCard
      title="Launcher access"
      description="Settings for the FastAPI dashboard service itself."
    >
      <SwitchCardField
        label="Public access"
        hint="Allow access from non-local network interfaces."
        layout="setting-row"
        checked={launcherForm.publicAccess}
        disabled={disabled}
        onCheckedChange={(checked) => onFieldChange("publicAccess", checked)}
      />

      <Field
        label="Launcher port"
        hint="Port used by the Python dashboard server."
        layout="setting-row"
      >
        <Input
          type="number"
          min={1}
          max={65535}
          value={launcherForm.port}
          disabled={disabled}
          onChange={(e) => onFieldChange("port", e.target.value)}
        />
      </Field>

      <Field
        label="Allowed CIDRs"
        hint="Optional client IP ranges that may access the dashboard."
        layout="setting-row"
      >
        <Textarea
          value={launcherForm.allowedCIDRsText}
          disabled={disabled}
          placeholder="127.0.0.1/32"
          className="min-h-[88px]"
          onChange={(e) => onFieldChange("allowedCIDRsText", e.target.value)}
        />
      </Field>
    </ConfigSectionCard>
  )
}

interface AutoStartSectionProps {
  enabled: boolean
  hint: string
  disabled: boolean
  onChange: (checked: boolean) => void
}

export function AutoStartSection({
  enabled,
  hint,
  disabled,
  onChange,
}: AutoStartSectionProps) {
  return (
    <ConfigSectionCard
      title="Auto start"
      description="Launch the dashboard automatically when you sign in to the OS."
    >
      <SwitchCardField
        label="Start launcher on login"
        hint={hint}
        layout="setting-row"
        checked={enabled}
        disabled={disabled}
        onCheckedChange={onChange}
      />
    </ConfigSectionCard>
  )
}
