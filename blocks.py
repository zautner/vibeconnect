"""
Slack Block Kit card for the Collaboration Map (Experts + Hot Channels).
"""


def collaboration_map_blocks(
    query_preview: str,
    experts: list[dict],
    channels: list[dict],
    summary: str = "",
    files: list[dict] | None = None,
) -> list[dict]:
    """
    Build Block Kit blocks for the VibeConnect response.
    experts: list of {"user_id", "name", "reason"}.
    channels: list of {"channel_id", "name", "reason"}.
    files: list of {"file_name", "permalink", "reason"}.
    summary: AI-generated summary of the most relevant information.
    """
    if files is None:
        files = []
    header = {
        "type": "header",
        "text": {"type": "plain_text", "text": "🤝 Collaboration Map", "emoji": True},
    }
    context = {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"Based on: _{query_preview[:200]}_"}],
    }
    sections = [header, context]

    if summary:
        sections.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Summary*\n{summary}"},
        })

    if experts:
        expert_lines = []
        for e in experts:
            user_id = (e.get("user_id") or "").strip()
            name = e.get("name") or "Someone"
            # Use clickable <@USER_ID> mention when available
            display = f"<@{user_id}>" if user_id else f"*{name}*"
            reason = (e.get("reason") or "").strip()
            if reason:
                expert_lines.append(f"• {display} — {reason}")
            else:
                expert_lines.append(f"• {display}")
        sections.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Experts*\n" + "\n".join(expert_lines)},
        })

    if channels:
        channel_lines = []
        for c in channels:
            channel_id = (c.get("channel_id") or "").strip()
            name = c.get("name") or "unknown"
            if not name.startswith("#"):
                name = "#" + name
            # Use clickable <#CHANNEL_ID|name> link when available
            display = f"<#{channel_id}|{name.lstrip('#')}>" if channel_id else name
            reason = (c.get("reason") or "").strip()
            if reason:
                channel_lines.append(f"• {display} — {reason}")
            else:
                channel_lines.append(f"• {display}")
        sections.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Hot channels*\n" + "\n".join(channel_lines)},
        })

    if files:
        file_lines = []
        for f in files:
            file_name = f.get("file_name") or "Untitled"
            permalink = (f.get("permalink") or "").strip()
            # Use clickable link when permalink available
            display = f"<{permalink}|{file_name}>" if permalink else file_name
            reason = (f.get("reason") or "").strip()
            if reason:
                file_lines.append(f"• 📄 {display} — {reason}")
            else:
                file_lines.append(f"• 📄 {display}")
        sections.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Relevant files*\n" + "\n".join(file_lines)},
        })

    if not experts and not channels and not files:
        sections.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "No clear experts or channels found for this topic. Try a different message or broader context."},
        })

    sections.append({"type": "divider"})
    return sections
