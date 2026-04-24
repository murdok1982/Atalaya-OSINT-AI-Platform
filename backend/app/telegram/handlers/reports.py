from __future__ import annotations

import os


async def report_handler(update, context) -> None:
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /report <case_id> [report_type]\nTypes: executive_summary, domain_investigation, entity_profile, technical_report")
        return

    case_id = args[0]
    report_type = args[1] if len(args) > 1 else "executive_summary"

    try:
        import httpx  # noqa: PLC0415
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
            r = await client.post(
                "/api/v1/reports/generate",
                json={"case_id": case_id, "report_type": report_type, "format": "MARKDOWN", "entity_ids": []},
                headers={"X-Bot-Source": "telegram"},
            )
            r.raise_for_status()
            data = r.json()

        await update.message.reply_text(
            f"📄 *Report generation queued*\nJob ID: `{data['job_id'][:8]}`\nType: {report_type}\n\nCheck `/status {data['job_id'][:8]}` for progress.",
            parse_mode="Markdown",
        )
    except Exception as exc:
        await update.message.reply_text(f"Error generating report: {exc}")
