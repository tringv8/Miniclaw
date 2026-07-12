"""Built-in slash command handlers."""

from __future__ import annotations

import asyncio
import os
import sys

from miniclaw import __version__
from miniclaw.bus.events import OutboundMessage
from miniclaw.command.router import CommandContext, CommandRouter
from miniclaw.utils.helpers import build_status_content


async def cmd_stop(ctx: CommandContext) -> OutboundMessage:
    """Cancel all active tasks and subagents for the session."""
    loop = ctx.loop
    msg = ctx.msg
    tasks = loop._active_tasks.pop(msg.session_key, [])
    cancelled = sum(1 for t in tasks if not t.done() and t.cancel())
    for t in tasks:
        try:
            await t
        except (asyncio.CancelledError, Exception):
            pass
    sub_cancelled = await loop.subagents.cancel_by_session(msg.session_key)
    total = cancelled + sub_cancelled
    content = f"Stopped {total} task(s)." if total else "No active task to stop."
    return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content=content)


async def cmd_restart(ctx: CommandContext) -> OutboundMessage:
    """Restart the process in-place via os.execv."""
    msg = ctx.msg

    async def _do_restart():
        await asyncio.sleep(1)
        os.execv(sys.executable, [sys.executable, "-m", "miniclaw"] + sys.argv[1:])

    asyncio.create_task(_do_restart())
    return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content="Restarting...")


async def cmd_status(ctx: CommandContext) -> OutboundMessage:
    """Build an outbound status message for a session."""
    loop = ctx.loop
    session = ctx.session or loop.sessions.get_or_create(ctx.key)
    ctx_est = 0
    try:
        ctx_est, _ = loop.memory_consolidator.estimate_session_prompt_tokens(session)
    except Exception:
        pass
    if ctx_est <= 0:
        ctx_est = loop._last_usage.get("prompt_tokens", 0)
    return OutboundMessage(
        channel=ctx.msg.channel,
        chat_id=ctx.msg.chat_id,
        content=build_status_content(
            version=__version__, model=loop.model,
            start_time=loop._start_time, last_usage=loop._last_usage,
            context_window_tokens=loop.context_window_tokens,
            session_msg_count=len(session.get_history(max_messages=0)),
            context_tokens_estimate=ctx_est,
        ),
        metadata={"render_as": "text"},
    )


async def cmd_new(ctx: CommandContext) -> OutboundMessage:
    """Start a fresh session."""
    loop = ctx.loop
    session = ctx.session or loop.sessions.get_or_create(ctx.key)
    snapshot = session.messages[session.last_consolidated:]
    session.clear()
    loop.sessions.save(session)
    loop.sessions.invalidate(session.key)
    if snapshot:
        loop._schedule_background(loop.memory_consolidator.archive_messages(snapshot))
    return OutboundMessage(
        channel=ctx.msg.channel, chat_id=ctx.msg.chat_id,
        content="New session started.",
    )


async def cmd_help(ctx: CommandContext) -> OutboundMessage:
    """Return available slash commands."""
    lines = [
        "🐈 miniclaw commands:",
        "/new — Bắt đầu một cuộc hội thoại mới",
        "/stop — Dừng tác vụ hiện tại",
        "/model — Chọn mô hình OpenRouter",
        "/restart — Khởi động lại bot",
        "/status — Hiển thị trạng thái của bot",
        "/help — Hiển thị các lệnh có sẵn",
    ]
    return OutboundMessage(
        channel=ctx.msg.channel,
        chat_id=ctx.msg.chat_id,
        content="\n".join(lines),
        metadata={"render_as": "text"},
    )


async def cmd_model(ctx: CommandContext) -> OutboundMessage:
    """Handle model command for displaying/selecting OpenRouter models."""
    msg = ctx.msg
    args = ctx.args.strip()

    from miniclaw.config.loader import load_config
    from miniclaw.providers.model_router import route_openrouter_model

    config = load_config()
    p = config.providers.openrouter
    has_api = bool(p and p.api_key)
    status_api = "Đã kết nối API key" if has_api else "Chưa kết nối API key"

    requested_model = args[len("select "):].strip() if args.startswith("select ") else args
    if requested_model:
        result = await route_openrouter_model(ctx.loop, requested_model)
        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=("✅ " if result.ok else "❌ ") + result.message,
            metadata={"render_as": "text"},
        )

    # If no valid arguments or args is empty, show the menu
    lines = [
        "🤖 **Cấu hình mô hình hiện tại:**",
        f"• **Mô hình hiện tại:** `{ctx.loop.model}`",
        f"• **Trạng thái OpenRouter:** {status_api}",
        "",
        "Chọn một mô hình OpenRouter dưới đây để thay đổi trực tiếp:"
    ]
    if not has_api:
        lines.append("\n⚠️ **Lưu ý:** Bạn chưa cấu hình API key cho OpenRouter. Hãy cập nhật API key trên trang web trước khi sử dụng.")

    MODELS = [
        ("Gemini 2.5 Flash", "google/gemini-2.5-flash"),
        ("Gemini 2.5 Pro", "google/gemini-2.5-pro"),
        ("Claude 3.5 Sonnet", "anthropic/claude-3.5-sonnet"),
        ("DeepSeek V3", "deepseek/deepseek-chat"),
        ("DeepSeek R1", "deepseek/deepseek-reasoner"),
        ("GPT-4o", "openai/gpt-4o"),
        ("Llama 3.3 70B", "meta-llama/llama-3.3-70b-instruct"),
        ("Qwen 2.5 72B", "qwen/qwen-2.5-72b-instruct"),
    ]

    inline_keyboard = []
    for i in range(0, len(MODELS), 2):
        row = []
        for label, name in MODELS[i:i+2]:
            row.append({
                "text": label,
                "callback_data": f"model:{name}"
            })
        inline_keyboard.append(row)

    return OutboundMessage(
        channel=msg.channel,
        chat_id=msg.chat_id,
        content="\n".join(lines),
        metadata={
            "inline_keyboard": inline_keyboard,
            "render_as": "text"
        }
    )


async def intercept_openrouter_model_id(ctx: CommandContext) -> OutboundMessage | None:
    """Treat a bare OpenRouter model ID as a request to switch models."""
    from miniclaw.providers.model_router import (
        normalize_openrouter_model_id,
        route_openrouter_model,
    )

    if ctx.raw.startswith("/") or not normalize_openrouter_model_id(ctx.raw):
        return None
    result = await route_openrouter_model(ctx.loop, ctx.raw)
    return OutboundMessage(
        channel=ctx.msg.channel,
        chat_id=ctx.msg.chat_id,
        content=("✅ " if result.ok else "❌ ") + result.message,
        metadata={"render_as": "text"},
    )


def register_builtin_commands(router: CommandRouter) -> None:
    """Register the default set of slash commands."""
    router.priority("/stop", cmd_stop)
    router.priority("/restart", cmd_restart)
    router.priority("/status", cmd_status)
    router.exact("/new", cmd_new)
    router.exact("/status", cmd_status)
    router.exact("/help", cmd_help)
    router.exact("/model", cmd_model)
    router.prefix("/model ", cmd_model)
    router.intercept(intercept_openrouter_model_id)
