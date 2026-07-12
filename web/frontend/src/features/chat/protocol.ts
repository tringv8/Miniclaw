import { normalizeUnixTimestamp } from "@/features/chat/state"
import { updateChatStore } from "@/store/chat"

export interface MiniclawChatMessage {
  type: string
  id?: string
  session_id?: string
  timestamp?: number | string
  payload?: Record<string, unknown>
}

function messageTimestamp(message: MiniclawChatMessage): number {
  if (
    message.timestamp !== undefined &&
    Number.isFinite(Number(message.timestamp))
  ) {
    return normalizeUnixTimestamp(Number(message.timestamp))
  }

  return Date.now()
}

function errorContent(payload: Record<string, unknown>): string {
  const rawMessage = payload.message
  if (typeof rawMessage === "string" && rawMessage.trim()) {
    return rawMessage.trim()
  }

  return "Chat request failed."
}

export function handleMiniclawChatMessage(
  message: MiniclawChatMessage,
  expectedSessionId: string,
) {
  if (message.session_id && message.session_id !== expectedSessionId) {
    return
  }

  const payload = message.payload || {}

  switch (message.type) {
    case "message.create": {
      const content = (payload.content as string) || ""
      const messageId = (payload.message_id as string) || `mini-${Date.now()}`
      const timestamp = messageTimestamp(message)

      updateChatStore((prev) => ({
        messages: [
          ...prev.messages,
          {
            id: messageId,
            role: "assistant",
            content,
            timestamp,
          },
        ],
        isTyping: false,
      }))
      break
    }

    case "message.update": {
      const content = (payload.content as string) || ""
      const messageId = payload.message_id as string
      if (!messageId) {
        break
      }

      updateChatStore((prev) => ({
        messages: prev.messages.map((msg) =>
          msg.id === messageId ? { ...msg, content } : msg,
        ),
      }))
      break
    }

    case "typing.start":
      updateChatStore({ isTyping: true })
      break

    case "typing.stop":
      updateChatStore({ isTyping: false })
      break

    case "error":
      console.error("Miniclaw chat error:", payload)
      updateChatStore((prev) => ({
        messages: [
          ...prev.messages,
          {
            id: message.id || `mini-error-${Date.now()}`,
            role: "assistant",
            content: errorContent(payload),
            timestamp: messageTimestamp(message),
          },
        ],
        isTyping: false,
      }))
      break

    case "pong":
      break

    default:
      console.log("Unknown miniclaw chat message type:", message.type)
  }
}
