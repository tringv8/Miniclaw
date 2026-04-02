# Miniclaw — Session Checkpoint
**Ngày:** 2026-04-02

---

## Tổng quan dự án miniclaw

**Miniclaw** là personal AI assistant framework, clone từ nanobot, viết bằng Python.

### Kiến trúc tổng thể

```
channel adapters (Telegram, Web, CLI)
  → ChannelManager (bus publish/subscribe)
    → AgentLoop (process_direct / run)
      → LLM Provider (OpenAI Codex / Anthropic / OpenAI Compat)
      → Tools (filesystem, web, exec, mcp, message, cron...)
      → SessionManager (workspace/sessions/*.jsonl)
      → ContextBuilder (bootstrap files + memory)
```

### Thư mục chính

| Path | Mục đích |
|------|----------|
| `miniclaw/` | Core Python package |
| `miniclaw/agent/` | AgentLoop, context, memory, skills, tools |
| `miniclaw/channels/` | Telegram, base channel |
| `miniclaw/providers/` | LLM backends (OpenAI Codex, Anthropic, Azure...) |
| `miniclaw/security/` | Credential store |
| `miniclaw/cli/` | CLI commands + launcher |
| `web/frontend_python_codex/` | Web UI (FastAPI + frontend) |
| `web/frontend_python_codex/backend/` | Web API, web_chat runtime |
| `workspace/templates/` | Template files cho workspace mới |
| `~/.miniclaw/workspace/` | Workspace thực của user |
| `~/.miniclaw/secrets/` | Secure credential store |
| `~/.miniclaw/config.json` | Config chính |

### Config chính (`~/.miniclaw/config.json`)
- Model: `openai-codex/gpt-5.1-codex`
- Gateway port: `18790`
- Web launcher port: `18801`
- Workspace: `~/.miniclaw/workspace`
- Telegram: enabled

### Shared State giữa các channels

**Dùng chung (mọi channel):**
- Bootstrap files: `AGENTS.md`, `SOUL.md`, `USER.md`, `TOOLS.md`, `TOOL_ACCOUNTS.md`
- Memory: `workspace/memory/MEMORY.md`, `HISTORY.md`
- Credential store: `~/.miniclaw/secrets/`
- Tool registry (stateless)

**Riêng theo channel:**
- Session history: `workspace/sessions/{channel}_{chat_id}.jsonl`

---

## Những thay đổi đã làm trong session này

### 1. Fix Telegram ConnectError (`miniclaw/channels/telegram.py`)
- **Vấn đề:** `httpx.ConnectError: All connection attempts failed` khi start gateway
- **Nguyên nhân:** httpx pick up proxy từ env var (HTTP_PROXY/HTTPS_PROXY)
- **Fix:** Thêm `httpx_kwargs={"trust_env": False}` vào `HTTPXRequest` khi không cấu hình proxy

### 2. Xóa test fixtures (`web/frontend_python_codex/.smoke/workspace/`)
- Removed `.smoke/workspace/` test data không cần thiết trong production

### 3. Đổi web launcher port (`web/frontend_python_codex/backend/launcherconfig/config.py`)
- `DEFAULT_PORT`: `18800` → `18801` (tránh conflict với picolaw)

### 4. Tạo Shared Credential Store (`miniclaw/security/credentials.py`)
- **Module:** `CredentialStore` — abstraction layer cho tool credentials
- **API:** `save`, `get`, `delete`, `get_status`, `get_metadata`, `list_connected`, `refresh_if_needed`, `generate_tool_accounts_md`
- **Lưu ở:** `~/.miniclaw/secrets/{provider}_{user_id}.json` (private, không commit)
- **Nguyên tắc:** LLM KHÔNG thấy raw secrets — chỉ thấy metadata

### 5. Thêm `TOOL_ACCOUNTS.md` vào bootstrap (`miniclaw/agent/context.py`)
- `BOOTSTRAP_FILES` += `"TOOL_ACCOUNTS.md"`
- File chứa metadata tool connections (account, status, scopes) — KHÔNG chứa secrets
- Loaded vào system prompt cho MỌI session, mọi channel

### 6. Tạo files mới
- `~/.miniclaw/workspace/TOOL_ACCOUNTS.md` — metadata view (đã có Google Workspace entry)
- `workspace/templates/TOOL_ACCOUNTS.md` — template cho onboard
- `~/.miniclaw/workspace/AGENTS.md` — thêm instruction về tool credentials
- `~/.miniclaw/secrets/` — thư mục secure store

---

## Kiến trúc Credential (đã implement)

```
LLM (không thấy secret)
  ↓ chỉ thấy TOOL_ACCOUNTS.md (metadata: account, status, scopes)
Tool runner
  ↓ gọi
CredentialStore.get(user_id, provider)
  ↓ đọc từ
~/.miniclaw/secrets/{provider}_{user_id}.json
  ↓ call
External service (Gmail, GitHub...)
```

**Flow refresh:**
1. `get_status` → "expired"
2. `refresh_if_needed` → try refresh_token
3. Success → update store → "connected"
4. Fail → mark "expired" → agent báo user reconnect

---

## Vấn đề còn tồn đọng

1. **Telegram ConnectError** — fix `trust_env=False` đã apply nhưng root cause chưa xác nhận rõ ràng
2. **Web chat dùng tiếng Anh** — model không follow đủ instruction. Workaround: thêm explicit Email Search Rules vào `USER.md`
3. **Tool credentials chưa wire vào tools** — `CredentialStore` đã tạo nhưng các tool cụ thể (Gmail, GitHub...) chưa được sửa để dùng store này

---

## Ghi chú quan trọng

- Web chat tạo `AgentLoop` mới mỗi message nhưng **session history vẫn persist qua disk** → không phải bug
- `user_id = "default"` cho single-user hiện tại, API thiết kế sẵn để nâng multi-user
- `TOOL_ACCOUNTS.md` là metadata view, NOT source of truth — trạng thái thực từ `CredentialStore`
