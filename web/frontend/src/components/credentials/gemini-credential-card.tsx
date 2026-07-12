import {
  IconBrandGoogle,
  IconKey,
  IconLoader2,
  IconPlayerStopFilled,
} from "@tabler/icons-react"
import { useTranslation } from "react-i18next"

import type { OAuthProviderStatus } from "@/api/oauth"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

import { CredentialCard } from "./credential-card"

interface GeminiCredentialCardProps {
  status?: OAuthProviderStatus
  activeAction: string
  token: string
  onTokenChange: (value: string) => void
  onStartBrowserOAuth: () => void
  onStopLoading: () => void
  onSaveToken: () => void
  onAskLogout: () => void
}

export function GeminiCredentialCard({
  status,
  activeAction,
  token,
  onTokenChange,
  onStartBrowserOAuth,
  onStopLoading,
  onSaveToken,
  onAskLogout,
}: GeminiCredentialCardProps) {
  const { t } = useTranslation()
  const actionBusy = activeAction !== ""
  const browserLoading = activeAction === "gemini:browser"
  const tokenLoading = activeAction === "gemini:token"

  return (
    <CredentialCard
      title={
        <span className="inline-flex items-center gap-2">
          <span className="border-muted inline-flex size-6 items-center justify-center rounded-full border">
            <IconBrandGoogle className="size-3.5" />
          </span>
          <span>Google Gemini</span>
        </span>
      }
      description={status?.help_text || t("credentials.providers.gemini.description")}
      status={status?.status ?? "not_logged_in"}
      authMethod={status?.auth_method}
      details={
        status?.account_id ? (
          <p>
            {t("credentials.labels.account")}: {status.account_id}
          </p>
        ) : null
      }
      actions={
        <div className="border-muted flex h-[120px] flex-col rounded-lg border p-3">
          <div className="flex h-full flex-col gap-3">
            <div className="min-h-8">
              <div className="flex flex-nowrap items-center gap-2 overflow-x-auto">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={actionBusy}
                  onClick={onStartBrowserOAuth}
                >
                  {browserLoading && (
                    <IconLoader2 className="size-4 animate-spin" />
                  )}
                  <IconBrandGoogle className="size-4" />
                  {t("credentials.actions.browser")}
                </Button>

                {browserLoading && (
                  <Button
                    size="icon-xs"
                    variant="secondary"
                    onClick={onStopLoading}
                    className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                  >
                    <IconPlayerStopFilled className="size-4" />
                  </Button>
                )}
              </div>
            </div>

            <div className="min-h-9 flex-1">
              <div className="flex h-full items-center gap-2">
                <Input
                  value={token}
                  onChange={(e) => onTokenChange(e.target.value)}
                  type="password"
                  placeholder={t("credentials.fields.geminiToken")}
                />
                <Button
                  size="sm"
                  disabled={actionBusy || !token.trim()}
                  onClick={onSaveToken}
                >
                  {tokenLoading && (
                    <IconLoader2 className="size-4 animate-spin" />
                  )}
                  <IconKey className="size-4" />
                  {t("credentials.actions.saveToken")}
                </Button>
                {tokenLoading && (
                  <Button
                    size="icon-sm"
                    variant="ghost"
                    onClick={onStopLoading}
                    className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                  >
                    <IconPlayerStopFilled className="size-4" />
                  </Button>
                )}
              </div>
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
            {activeAction === "gemini:logout" && (
              <IconLoader2 className="size-4 animate-spin" />
            )}
            {t("credentials.actions.logout")}
          </Button>
        ) : null
      }
    />
  )
}
