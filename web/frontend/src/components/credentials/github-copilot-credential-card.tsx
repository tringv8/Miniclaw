import { IconBrandGithub, IconLoader2 } from "@tabler/icons-react"
import { useTranslation } from "react-i18next"

import type { OAuthProviderStatus } from "@/api/oauth"
import { Button } from "@/components/ui/button"

import { CredentialCard } from "./credential-card"

interface GithubCopilotCredentialCardProps {
  status?: OAuthProviderStatus
  activeAction: string
  onStartDeviceCode: () => void
  onAskLogout: () => void
}

export function GithubCopilotCredentialCard({
  status,
  activeAction,
  onStartDeviceCode,
  onAskLogout,
}: GithubCopilotCredentialCardProps) {
  const { t } = useTranslation()
  const actionBusy = activeAction !== ""
  const deviceLoading = activeAction === "github_copilot:device"

  return (
    <CredentialCard
      title={
        <span className="inline-flex items-center gap-2">
          <span className="border-muted inline-flex size-6 items-center justify-center rounded-full border">
            <IconBrandGithub className="size-3.5" />
          </span>
          <span>GitHub Copilot</span>
        </span>
      }
      description={status?.help_text || t("credentials.providers.github_copilot.description")}
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
        <div className="border-muted flex h-[120px] flex-col justify-center rounded-lg border p-3">
          <div className="flex h-full flex-col justify-center gap-3">
            <div className="flex justify-center">
              <Button
                size="sm"
                variant="outline"
                disabled={actionBusy}
                onClick={onStartDeviceCode}
                className="w-full max-w-[200px]"
              >
                {deviceLoading && (
                  <IconLoader2 className="size-4 animate-spin" />
                )}
                <IconBrandGithub className="size-4" />
                {t("credentials.actions.deviceCode")}
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
            {activeAction === "github_copilot:logout" && (
              <IconLoader2 className="size-4 animate-spin" />
            )}
            {t("credentials.actions.logout")}
          </Button>
        ) : null
      }
    />
  )
}
