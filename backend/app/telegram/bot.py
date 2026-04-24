from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _is_authorized(chat_id: int) -> bool:
    return chat_id in settings.TELEGRAM_ALLOWED_CHATS


def create_bot():
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("telegram_bot_disabled", reason="TELEGRAM_BOT_TOKEN not configured")
        return None

    try:
        from telegram.ext import Application, CommandHandler, CallbackQueryHandler  # noqa: PLC0415
        from app.telegram.handlers.cases import new_case_handler, list_cases_handler  # noqa: PLC0415
        from app.telegram.handlers.jobs import run_job_handler, status_handler  # noqa: PLC0415
        from app.telegram.handlers.reports import report_handler  # noqa: PLC0415
        from app.telegram.handlers.config import models_handler, sources_handler, find_handler  # noqa: PLC0415
    except ImportError as exc:
        logger.error("telegram_import_failed", error=str(exc))
        return None

    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    async def start_handler(update, context):
        if not _is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        await update.message.reply_text(
            "⬡ *Atalaya OSINT Platform*\n\n"
            "Available commands:\n"
            "/newcase — Create new investigation\n"
            "/cases — List active cases\n"
            "/run <case_id> <task> — Launch investigation\n"
            "/status [job_id] — Check job status\n"
            "/report <case_id> — Generate report\n"
            "/find <query> — Search entities\n"
            "/sources — Show configured sources\n"
            "/models — Show LLM providers\n"
            "/help — This message",
            parse_mode="Markdown",
        )

    async def auth_guard(handler):
        async def wrapper(update, context):
            if not _is_authorized(update.effective_chat.id):
                await update.message.reply_text("Unauthorized.")
                return
            return await handler(update, context)
        return wrapper

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", start_handler))
    app.add_handler(CommandHandler("newcase", new_case_handler))
    app.add_handler(CommandHandler("cases", list_cases_handler))
    app.add_handler(CommandHandler("run", run_job_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("report", report_handler))
    app.add_handler(CommandHandler("find", find_handler))
    app.add_handler(CommandHandler("sources", sources_handler))
    app.add_handler(CommandHandler("models", models_handler))

    logger.info("telegram_bot_configured", allowed_chats=len(settings.TELEGRAM_ALLOWED_CHATS))
    return app


async def run_bot() -> None:
    bot = create_bot()
    if not bot:
        return
    logger.info("telegram_bot_starting")
    await bot.initialize()
    await bot.start()
    await bot.updater.start_polling(drop_pending_updates=True)
    logger.info("telegram_bot_running")
    import asyncio  # noqa: PLC0415
    try:
        await asyncio.Event().wait()
    finally:
        await bot.updater.stop()
        await bot.stop()
        await bot.shutdown()


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_bot())
