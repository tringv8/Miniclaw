import { PageHeader } from "@/components/page-header"

import { DeviceCodeSheet } from "./device-code-sheet"
import { LogoutConfirmDialog } from "./logout-confirm-dialog"
import { OpenAICredentialCard } from "./openai-credential-card"
import { GeminiCredentialCard } from "./gemini-credential-card"
import { GithubCopilotCredentialCard } from "./github-copilot-credential-card"
import { AnthropicCredentialCard } from "./anthropic-credential-card"
import { KimiCredentialCard } from "./kimi-credential-card"
import { DeepseekCredentialCard } from "./deepseek-credential-card"
import { OpenrouterCredentialCard } from "./openrouter-credential-card"
import { OllamaCredentialCard } from "./ollama-credential-card"
import { useCredentialsPage } from "@/hooks/use-credentials-page"

export function CredentialsPage() {
  const {
    loading,
    error,
    activeAction,
    flowHint,
    openAIToken,
    anthropicToken,
    geminiToken,
    kimiToken,
    deepseekToken,
    openrouterToken,
    ollamaBase,
    ollamaUsername,
    ollamaPassword,
    openaiStatus,
    geminiStatus,
    copilotStatus,
    anthropicStatus,
    kimiStatus,
    deepseekStatus,
    openrouterStatus,
    ollamaStatus,
    logoutDialogOpen,
    logoutProviderLabel,
    deviceSheetOpen,
    deviceFlow,
    setOpenAIToken,
    setAnthropicToken,
    setGeminiToken,
    setKimiToken,
    setDeepseekToken,
    setOpenrouterToken,
    setOllamaBase,
    setOllamaUsername,
    setOllamaPassword,
    startBrowserOAuth,
    startOpenAIDeviceCode,
    startCopilotDeviceCode,
    stopLoading,
    saveToken,
    saveOllamaLocal,
    askLogout,
    handleConfirmLogout,
    handleLogoutDialogOpenChange,
    handleDeviceSheetOpenChange,
  } = useCredentialsPage()

  return (
    <div className="flex h-full flex-col">
      <PageHeader title="Credentials" />

      <div className="min-h-0 flex-1 overflow-y-auto px-4 sm:px-6">
        <div className="pt-2">
          <p className="text-muted-foreground text-sm">
            Manage OAuth and token-based credentials for supported providers.
          </p>
        </div>

        {error ? (
          <div className="text-destructive bg-destructive/10 mt-4 rounded-lg px-4 py-3 text-sm">
            {error}
          </div>
        ) : null}

        {loading ? (
          <div className="text-muted-foreground py-8 text-sm">Loading...</div>
        ) : (
          <div className="grid grid-cols-1 gap-6 py-5 md:grid-cols-2 lg:grid-cols-3">
            <OpenAICredentialCard
              status={openaiStatus}
              activeAction={activeAction}
              token={openAIToken}
              onTokenChange={setOpenAIToken}
              onStartBrowserOAuth={() => void startBrowserOAuth("openai")}
              onStartDeviceCode={() => void startOpenAIDeviceCode()}
              onStopLoading={stopLoading}
              onSaveToken={() => void saveToken("openai", openAIToken)}
              onAskLogout={() => askLogout("openai")}
            />

            <GeminiCredentialCard
              status={geminiStatus}
              activeAction={activeAction}
              token={geminiToken}
              onTokenChange={setGeminiToken}
              onStartBrowserOAuth={() => void startBrowserOAuth("gemini")}
              onStopLoading={stopLoading}
              onSaveToken={() => void saveToken("gemini", geminiToken)}
              onAskLogout={() => askLogout("gemini")}
            />

            <GithubCopilotCredentialCard
              status={copilotStatus}
              activeAction={activeAction}
              onStartDeviceCode={() => void startCopilotDeviceCode()}
              onAskLogout={() => askLogout("github_copilot")}
            />

            <AnthropicCredentialCard
              status={anthropicStatus}
              activeAction={activeAction}
              token={anthropicToken}
              onTokenChange={setAnthropicToken}
              onStopLoading={stopLoading}
              onSaveToken={() => void saveToken("anthropic", anthropicToken)}
              onAskLogout={() => askLogout("anthropic")}
            />

            <KimiCredentialCard
              status={kimiStatus}
              activeAction={activeAction}
              token={kimiToken}
              onTokenChange={setKimiToken}
              onStopLoading={stopLoading}
              onSaveToken={() => void saveToken("moonshot", kimiToken)}
              onAskLogout={() => askLogout("moonshot")}
            />

            <DeepseekCredentialCard
              status={deepseekStatus}
              activeAction={activeAction}
              token={deepseekToken}
              onTokenChange={setDeepseekToken}
              onStopLoading={stopLoading}
              onSaveToken={() => void saveToken("deepseek", deepseekToken)}
              onAskLogout={() => askLogout("deepseek")}
            />

            <OpenrouterCredentialCard
              status={openrouterStatus}
              activeAction={activeAction}
              token={openrouterToken}
              onTokenChange={setOpenrouterToken}
              onStopLoading={stopLoading}
              onSaveToken={() => void saveToken("openrouter", openrouterToken)}
              onAskLogout={() => askLogout("openrouter")}
            />

            <OllamaCredentialCard
              status={ollamaStatus}
              activeAction={activeAction}
              apiBase={ollamaBase}
              onApiBaseChange={setOllamaBase}
              username={ollamaUsername}
              onUsernameChange={setOllamaUsername}
              password={ollamaPassword}
              onPasswordChange={setOllamaPassword}
              onSave={() => void saveOllamaLocal(ollamaBase, ollamaUsername, ollamaPassword)}
              onAskLogout={() => askLogout("ollama")}
            />
          </div>
        )}
      </div>

      <LogoutConfirmDialog
        open={logoutDialogOpen}
        providerLabel={logoutProviderLabel}
        isSubmitting={activeAction.endsWith(":logout")}
        onOpenChange={handleLogoutDialogOpenChange}
        onConfirm={handleConfirmLogout}
      />

      <DeviceCodeSheet
        open={deviceSheetOpen}
        flow={deviceFlow}
        flowHint={flowHint}
        onOpenChange={handleDeviceSheetOpenChange}
      />
    </div>
  )
}
