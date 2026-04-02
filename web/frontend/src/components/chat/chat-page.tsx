import { IconLoader2, IconPlus } from "@tabler/icons-react"
import { useQuery } from "@tanstack/react-query"
import { useEffect, useLayoutEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"

import { getModels } from "@/api/models"
import { AssistantMessage } from "@/components/chat/assistant-message"
import { ChatComposer } from "@/components/chat/chat-composer"
import { ChatEmptyState } from "@/components/chat/chat-empty-state"
import { SessionHistoryMenu } from "@/components/chat/session-history-menu"
import { TypingIndicator } from "@/components/chat/typing-indicator"
import { UserMessage } from "@/components/chat/user-message"
import { PageHeader } from "@/components/page-header"
import { Button } from "@/components/ui/button"
import {
  initializeChatStore,
  teardownChatStore,
} from "@/features/chat/controller"
import { useMiniclawChat } from "@/hooks/use-miniclaw-chat"
import { useSessionHistory } from "@/hooks/use-session-history"

function connectionLabel(state: string) {
  switch (state) {
    case "connected":
      return "Connected"
    case "connecting":
      return "Connecting"
    case "error":
      return "Connection error"
    default:
      return "Disconnected"
  }
}

export function ChatPage() {
  const { t } = useTranslation()
  const [input, setInput] = useState("")
  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const {
    messages,
    connectionState,
    isTyping,
    activeSessionId,
    sendMessage,
    switchSession,
    newChat,
  } = useMiniclawChat()

  const { data: modelData, isLoading: modelsLoading } = useQuery({
    queryKey: ["models", "chat"],
    queryFn: getModels,
  })

  const {
    sessions,
    hasMore,
    loadError,
    loadErrorMessage,
    observerRef,
    loadSessions,
    handleDeleteSession,
  } = useSessionHistory({
    activeSessionId,
    onDeletedActiveSession: () => {
      void newChat()
    },
  })

  useLayoutEffect(() => {
    initializeChatStore()
    return () => {
      teardownChatStore()
    }
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      block: "end",
      behavior: messages.length > 0 ? "smooth" : "auto",
    })
  }, [isTyping, messages])

  const configuredModels =
    modelData?.models.filter((model) => model.configured).length ?? 0
  const hasConfiguredModels = configuredModels > 0
  const defaultModelName = modelData?.default_model || ""
  const usableDefaultModel = modelData?.models.find(
    (model) =>
      model.model_name === defaultModelName && model.configured === true,
  )
  const hasUsableDefaultModel = Boolean(usableDefaultModel)
  const isConnected = connectionState === "connected"

  const handleSend = () => {
    const content = input.trim()
    if (!content) {
      return
    }
    if (!sendMessage(content)) {
      return
    }
    setInput("")
    void loadSessions(true)
  }

  const handleNewChat = async () => {
    setInput("")
    await newChat()
    await loadSessions(true)
  }

  const handleSwitchSession = async (sessionId: string) => {
    setInput("")
    await switchSession(sessionId)
  }

  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title={t("navigation.chat")}
        titleExtra={
          <span className="text-muted-foreground hidden text-sm sm:inline">
            {connectionLabel(connectionState)}
          </span>
        }
      >
        <SessionHistoryMenu
          sessions={sessions}
          activeSessionId={activeSessionId}
          hasMore={hasMore}
          loadError={loadError}
          loadErrorMessage={loadErrorMessage}
          observerRef={observerRef}
          onOpenChange={(open) => {
            if (open) {
              void loadSessions(true)
            }
          }}
          onSwitchSession={(sessionId) => {
            void handleSwitchSession(sessionId)
          }}
          onDeleteSession={(sessionId) => {
            void handleDeleteSession(sessionId)
          }}
        />
        <Button
          variant="secondary"
          size="sm"
          className="h-9 gap-2"
          onClick={() => void handleNewChat()}
        >
          <IconPlus className="size-4" />
          <span className="hidden sm:inline">{t("chat.newChat")}</span>
        </Button>
      </PageHeader>

      <div className="min-h-0 flex-1 px-4 pb-4 sm:px-6">
        <div className="bg-card/80 border-border/60 mx-auto flex h-full w-full max-w-5xl flex-col overflow-hidden rounded-3xl border shadow-sm">
          <div className="border-border/60 flex items-center justify-between border-b px-4 py-3 text-sm sm:px-6">
            <div className="text-muted-foreground">
              {modelsLoading ? (
                <span className="flex items-center gap-2">
                  <IconLoader2 className="size-4 animate-spin" />
                  Loading models
                </span>
              ) : defaultModelName ? (
                <>Default model: {defaultModelName}</>
              ) : (
                <>No default model selected</>
              )}
            </div>
            <div className="text-muted-foreground hidden text-xs sm:block">
              Session {activeSessionId.slice(0, 8)}
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6">
            <div className="mx-auto flex max-w-4xl flex-col gap-4">
              {messages.length === 0 ? (
                connectionState === "connecting" ? (
                  <div className="text-muted-foreground flex flex-col items-center justify-center gap-3 py-20">
                    <IconLoader2 className="size-6 animate-spin" />
                    <span>Connecting chat...</span>
                  </div>
                ) : (
                  <ChatEmptyState
                    hasConfiguredModels={hasConfiguredModels}
                    defaultModelName={
                      hasUsableDefaultModel ? defaultModelName : ""
                    }
                    isConnected={isConnected}
                  />
                )
              ) : (
                <>
                  {messages.map((message) =>
                    message.role === "assistant" ? (
                      <AssistantMessage
                        key={message.id}
                        content={message.content}
                        timestamp={message.timestamp}
                      />
                    ) : (
                      <UserMessage key={message.id} content={message.content} />
                    ),
                  )}
                  {isTyping ? <TypingIndicator /> : null}
                  <div ref={messagesEndRef} />
                </>
              )}
            </div>
          </div>

          <ChatComposer
            input={input}
            onInputChange={setInput}
            onSend={handleSend}
            isConnected={isConnected}
            hasDefaultModel={hasUsableDefaultModel}
          />
        </div>
      </div>
    </div>
  )
}
