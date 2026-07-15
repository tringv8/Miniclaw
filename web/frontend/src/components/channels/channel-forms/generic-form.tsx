import { useTranslation } from "react-i18next"

import type { ChannelConfig } from "@/api/channels"
import { Field, SwitchCardField } from "@/components/shared-form"
import { Input } from "@/components/ui/input"

interface GenericFormProps {
  config: ChannelConfig
  onChange: (key: string, value: unknown) => void
  hiddenKeys?: string[]
  requiredKeys?: string[]
  fieldErrors?: Record<string, string>
}

// Fields to skip in the generic form (handled by enabled toggle or internal).
const SKIP_FIELDS = new Set(["enabled", "reasoning_channel_id"])

// Fields that are objects/nested — show as JSON or skip.
const OBJECT_FIELDS = new Set([
  "typing",
  "placeholder",
  "allow_token_query",
  "allowFrom",
  "allow_origins",
  "groups",
])

function formatLabel(key: string): string {
  return key
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ")
}

function formatSentenceFieldName(key: string): string {
  const label = formatLabel(key)
  return label.charAt(0).toLowerCase() + label.slice(1)
}

function asString(value: unknown): string {
  return typeof value === "string" ? value : ""
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value.filter((item): item is string => typeof item === "string")
}

function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>
  }
  return {}
}

function asBool(value: unknown): boolean {
  return value === true
}

export function GenericForm({
  config,
  onChange,
  hiddenKeys = [],
  requiredKeys = [],
  fieldErrors = {},
}: GenericFormProps) {
  const { t } = useTranslation()
  const hiddenFieldSet = new Set(hiddenKeys)
  const requiredFieldSet = new Set(requiredKeys)
  const typingConfig = asRecord(config.typing)
  const placeholderConfig = asRecord(config.placeholder)
  const placeholderEnabled = asBool(placeholderConfig.enabled)

  const fields = Object.keys(config).filter(
    (k) =>
      !k.startsWith("_") &&
      !SKIP_FIELDS.has(k) &&
      !OBJECT_FIELDS.has(k) &&
      !hiddenFieldSet.has(k),
  )

  const buildHint = (key: string): string => {
    const descriptions: Record<string, string> = {
      port: t("channels.form.desc.port"),
      allow_token_query: t("channels.form.desc.allowTokenQuery"),
    }
    return (
      descriptions[key] ??
      t("channels.form.desc.genericField", {
        field: formatSentenceFieldName(key),
      })
    )
  }

  return (
    <div className="space-y-5">
      {fields.map((key) => {
        const isRequired = requiredFieldSet.has(key)
        const value = config[key]
        if (typeof value === "boolean") {
          return (
            <SwitchCardField
              key={key}
              label={formatLabel(key)}
              hint={buildHint(key)}
              error={fieldErrors[key]}
              checked={value}
              onCheckedChange={(checked) => onChange(key, checked)}
              ariaLabel={formatLabel(key)}
            />
          )
        }

        if (Array.isArray(value)) {
          return (
            <Field
              key={key}
              label={formatLabel(key)}
              required={isRequired}
              hint={buildHint(key)}
              error={fieldErrors[key]}
            >
              <Input
                value={asStringArray(value).join(", ")}
                onChange={(e) =>
                  onChange(
                    key,
                    e.target.value
                      .split(",")
                      .map((s: string) => s.trim())
                      .filter(Boolean),
                  )
                }
              />
            </Field>
          )
        }

        return (
          <Field
            key={key}
            label={formatLabel(key)}
            required={isRequired}
            hint={buildHint(key)}
            error={fieldErrors[key]}
          >
            <Input
              value={String(value ?? "")}
              onChange={(e) => {
                // Attempt to preserve number types
                const v = e.target.value
                if (typeof config[key] === "number") {
                  onChange(key, v === "" ? 0 : Number(v))
                } else {
                  onChange(key, v)
                }
              }}
            />
          </Field>
        )
      })}

      {/* Allow From field */}
      {config.allowFrom !== undefined && !hiddenFieldSet.has("allowFrom") && (
        <Field
          label={t("channels.field.allowFrom")}
          hint={t("channels.form.desc.allowFrom")}
        >
          <Input
            value={asStringArray(config.allowFrom).join(", ")}
            onChange={(e) =>
              onChange(
                "allowFrom",
                e.target.value
                  .split(",")
                  .map((s: string) => s.trim())
                  .filter(Boolean),
              )
            }
            placeholder={t("channels.field.allowFromPlaceholder")}
          />
        </Field>
      )}

      {config.allow_origins !== undefined &&
        !hiddenFieldSet.has("allow_origins") && (
          <Field
            label={t("channels.field.allowOrigins")}
            hint={t("channels.form.desc.allowOrigins")}
          >
            <Input
              value={asStringArray(config.allow_origins).join(", ")}
              onChange={(e) =>
                onChange(
                  "allow_origins",
                  e.target.value
                    .split(",")
                    .map((s: string) => s.trim())
                    .filter(Boolean),
                )
              }
              placeholder={t("channels.field.allowOriginsPlaceholder")}
            />
          </Field>
        )}

      {config.allow_token_query !== undefined &&
        !hiddenFieldSet.has("allow_token_query") && (
          <SwitchCardField
            label={formatLabel("allow_token_query")}
            hint={buildHint("allow_token_query")}
            checked={asBool(config.allow_token_query)}
            onCheckedChange={(checked) =>
              onChange("allow_token_query", checked)
            }
            ariaLabel={formatLabel("allow_token_query")}
          />
        )}

      {config.typing !== undefined && !hiddenFieldSet.has("typing") && (
        <SwitchCardField
          label={t("channels.field.typingEnabled")}
          hint={t("channels.form.desc.typingEnabled")}
          checked={asBool(typingConfig.enabled)}
          onCheckedChange={(checked) =>
            onChange("typing", { ...typingConfig, enabled: checked })
          }
          ariaLabel={t("channels.field.typingEnabled")}
        />
      )}

      {config.placeholder !== undefined &&
        !hiddenFieldSet.has("placeholder") && (
          <SwitchCardField
            label={t("channels.field.placeholderEnabled")}
            hint={t("channels.form.desc.placeholderEnabled")}
            checked={placeholderEnabled}
            onCheckedChange={(checked) =>
              onChange("placeholder", {
                ...placeholderConfig,
                enabled: checked,
              })
            }
            ariaLabel={t("channels.field.placeholderEnabled")}
          >
            {placeholderEnabled && (
              <div className="space-y-1">
                <Input
                  value={asString(placeholderConfig.text)}
                  onChange={(e) =>
                    onChange("placeholder", {
                      ...placeholderConfig,
                      text: e.target.value,
                    })
                  }
                  placeholder={t("channels.field.placeholderText")}
                  aria-label={t("channels.field.placeholderText")}
                />
              </div>
            )}
          </SwitchCardField>
        )}
    </div>
  )
}
