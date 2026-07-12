import { IconDeviceDesktop, IconKey, IconLoader2 } from "@tabler/icons-react"
import { useTranslation } from "react-i18next"

import type { OAuthProviderStatus } from "@/api/oauth"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

import { CredentialCard } from "./credential-card"

interface OllamaCredentialCardProps {
  status?: OAuthProviderStatus
  activeAction: string
  apiBase: string
  onApiBaseChange: (value: string) => void
  username?: string
  onUsernameChange?: (value: string) => void
  password?: string
  onPasswordChange?: (value: string) => void
  onSave: () => void
  onAskLogout: () => void
}

export function OllamaCredentialCard({
  status,
  activeAction,
  apiBase,
  onApiBaseChange,
  username,
  onUsernameChange,
  password,
  onPasswordChange,
  onSave,
  onAskLogout,
}: OllamaCredentialCardProps) {
  const { t } = useTranslation()
  const actionBusy = activeAction !== ""
  const saveLoading = activeAction === "ollama:local"

  return (
    <CredentialCard
      title={
        <span className="inline-flex items-center gap-2">
          <span className="border-muted inline-flex size-6 items-center justify-center rounded-full border">
            <IconDeviceDesktop className="size-3.5" />
          </span>
          <span>Ollama (Local)</span>
        </span>
      }
      description={status?.help_text || t("credentials.providers.ollama.description")}
      status={status?.status ?? "not_logged_in"}
      authMethod={status?.auth_method}
      actions={
        <div className="border-muted flex flex-col justify-center rounded-lg border p-3">
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                {t("credentials.fields.ollamaBase") || "API Base URL"}
              </label>
              <Input
                value={apiBase}
                onChange={(e) => onApiBaseChange(e.target.value)}
                placeholder="http://localhost:11434/v1"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <label className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                  {t("credentials.fields.username", "Username")}
                </label>
                <Input
                  value={username || ""}
                  onChange={(e) => onUsernameChange?.(e.target.value)}
                  placeholder="admin"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                  {t("credentials.fields.password", "Password")}
                </label>
                <Input
                  value={password || ""}
                  onChange={(e) => onPasswordChange?.(e.target.value)}
                  type="password"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <div className="flex justify-end mt-1">
              <Button
                size="sm"
                className="w-full sm:w-fit"
                disabled={actionBusy || !apiBase.trim()}
                onClick={onSave}
              >
                {saveLoading && (
                  <IconLoader2 className="size-4 animate-spin mr-1.5" />
                )}
                <IconKey className="size-4" />
                {t("common.save")}
              </Button>
            </div>
          </div>
        </div>
      }
      footer={
        status?.logged_in && status?.supports_logout ? (
          <Button
            variant="ghost"
            size="sm"
            disabled={actionBusy}
            onClick={onAskLogout}
            className="text-destructive hover:bg-destructive/10 hover:text-destructive"
          >
            {activeAction === "ollama:logout" && (
              <IconLoader2 className="size-4 animate-spin" />
            )}
            {t("credentials.actions.logout")}
          </Button>
        ) : null
      }
    />
  )
}
