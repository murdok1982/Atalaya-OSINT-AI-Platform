from __future__ import annotations


async def models_handler(update, context) -> None:
    try:
        import httpx  # noqa: PLC0415
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
            r = await client.get("/api/v1/config/providers", headers={"X-Bot-Source": "telegram"})
            r.raise_for_status()
            providers = r.json()

        lines = ["🤖 *LLM Providers*\n"]
        for p in providers:
            enabled_icon = "✅" if p.get("enabled") else "❌"
            default_mark = " ⭐" if p.get("is_default") else ""
            lines.append(f"{enabled_icon} *{p['name']}*{default_mark}")
            lines.append(f"   Model: `{p.get('default_model', 'N/A')}`")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as exc:
        await update.message.reply_text(f"Error: {exc}")


async def sources_handler(update, context) -> None:
    try:
        import httpx  # noqa: PLC0415
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
            r = await client.get("/api/v1/config/integrations", headers={"X-Bot-Source": "telegram"})
            r.raise_for_status()
            integrations = r.json()

        lines = ["🔌 *Configured Integrations*\n"]
        for name, enabled in integrations.items():
            icon = "✅" if enabled else "⬜"
            lines.append(f"{icon} {name}")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as exc:
        await update.message.reply_text(f"Error: {exc}")


async def find_handler(update, context) -> None:
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /find <query>\nExample: /find example.com")
        return

    query = " ".join(args)
    try:
        import httpx  # noqa: PLC0415
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
            r = await client.get(f"/api/v1/entities?limit=10", headers={"X-Bot-Source": "telegram"})
            r.raise_for_status()
            entities = r.json()

        matching = [e for e in entities if query.lower() in e.get("value", "").lower() or query.lower() in e.get("display_name", "").lower()]
        if not matching:
            await update.message.reply_text(f"No entities found matching: `{query}`", parse_mode="Markdown")
            return

        lines = [f"🔍 *Results for '{query}'*\n"]
        for e in matching[:10]:
            lines.append(f"• `{e['entity_type']}` — {e['value']}")
            if e.get('display_name') and e['display_name'] != e['value']:
                lines.append(f"  _{e['display_name']}_")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as exc:
        await update.message.reply_text(f"Error: {exc}")
