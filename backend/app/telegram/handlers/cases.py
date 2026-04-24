from __future__ import annotations


async def list_cases_handler(update, context) -> None:
    import httpx  # noqa: PLC0415

    try:
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
            r = await client.get("/api/v1/cases?limit=10", headers=_bot_headers())
            r.raise_for_status()
            cases = r.json()
    except Exception as exc:
        await update.message.reply_text(f"Error fetching cases: {exc}")
        return

    if not cases:
        await update.message.reply_text("No active cases.")
        return

    lines = ["📁 *Active Cases*\n"]
    for c in cases:
        status_icon = {"OPEN": "🔵", "ACTIVE": "🟢", "CLOSED": "⚪", "ARCHIVED": "🗄️"}.get(c["status"], "❓")
        priority_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(c["priority"], "")
        lines.append(f"{status_icon}{priority_icon} `{c['id'][:8]}` — *{c['title']}*")
        lines.append(f"   Entities: {c.get('entity_count', 0)} | Evidence: {c.get('evidence_count', 0)}\n")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def new_case_handler(update, context) -> None:
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /newcase <title>\nExample: /newcase Investigación dominio example.com")
        return

    title = " ".join(args)
    try:
        import httpx  # noqa: PLC0415
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
            r = await client.post(
                "/api/v1/cases",
                json={"title": title, "description": "", "priority": "MEDIUM"},
                headers=_bot_headers(),
            )
            r.raise_for_status()
            case = r.json()
        await update.message.reply_text(
            f"✅ Case created\n`{case['id'][:8]}` — *{case['title']}*\n\nUse `/run {case['id'][:8]} <task>` to launch an investigation.",
            parse_mode="Markdown",
        )
    except Exception as exc:
        await update.message.reply_text(f"Error creating case: {exc}")


def _bot_headers() -> dict:
    # Uses internal bot token for API auth — configure via BOT_API_TOKEN env or use admin token
    from app.core.config import settings  # noqa: PLC0415
    return {"X-Bot-Source": "telegram"}
