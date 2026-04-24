from __future__ import annotations


async def run_job_handler(update, context) -> None:
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /run <case_id> <task description>\nExample: /run abc123 investigate domain example.com")
        return

    case_id = args[0]
    task = " ".join(args[1:])

    try:
        import httpx  # noqa: PLC0415
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
            r = await client.post(
                "/api/v1/jobs",
                json={
                    "case_id": case_id,
                    "job_type": "CUSTOM",
                    "input_params": {"task_description": task},
                },
                headers={"X-Bot-Source": "telegram"},
            )
            r.raise_for_status()
            job = r.json()
        await update.message.reply_text(
            f"🚀 *Job queued*\nID: `{job['id'][:8]}`\nStatus: {job['status']}\nTask: _{task}_\n\nUse `/status {job['id'][:8]}` to check progress.",
            parse_mode="Markdown",
        )
    except Exception as exc:
        await update.message.reply_text(f"Error launching job: {exc}")


async def status_handler(update, context) -> None:
    args = context.args

    try:
        import httpx  # noqa: PLC0415
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
            if args:
                job_id = args[0]
                r = await client.get(f"/api/v1/jobs/{job_id}", headers={"X-Bot-Source": "telegram"})
                r.raise_for_status()
                job = r.json()
                status_icon = {"PENDING": "⏳", "QUEUED": "📋", "RUNNING": "🔄", "COMPLETED": "✅", "FAILED": "❌", "CANCELLED": "⚪"}.get(job["status"], "❓")
                msg = (
                    f"{status_icon} *Job {job['id'][:8]}*\n"
                    f"Status: {job['status']}\n"
                    f"Type: {job['job_type']}\n"
                    f"Findings: {job['findings_count']}\n"
                )
                if job.get("result_summary"):
                    msg += f"\nSummary: _{job['result_summary'][:200]}_"
                if job.get("error_message"):
                    msg += f"\nError: `{job['error_message'][:200]}`"
                await update.message.reply_text(msg, parse_mode="Markdown")
            else:
                r = await client.get("/api/v1/jobs?limit=5", headers={"X-Bot-Source": "telegram"})
                r.raise_for_status()
                jobs = r.json()
                lines = ["📊 *Recent Jobs*\n"]
                for j in jobs:
                    icon = {"RUNNING": "🔄", "COMPLETED": "✅", "FAILED": "❌"}.get(j["status"], "⏳")
                    lines.append(f"{icon} `{j['id'][:8]}` {j['job_type']} — {j['status']}")
                await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as exc:
        await update.message.reply_text(f"Error: {exc}")
