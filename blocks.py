"""
Slack Block Kit card for the Collaboration Map (Experts + Hot Channels).
"""


def collaboration_map_blocks(
    query_preview: str,
    experts: list[dict],
    channels: list[dict],
) -> list[dict]:
    """
    Build Block Kit blocks for the VibeConnect response.
    experts/channels: list of {"name", "reason"}.
    """
    header = {
        "type": "header",
        "text": {"type": "plain_text", "text": "🤝 Collaboration Map", "emoji": True},
    }
    context = {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"Based on: _{query_preview[:200]}_"}],
    }
    sections = [header, context]

    if experts:
        expert_lines = []
        for e in experts:
            name = e.get("name") or "Someone"
            reason = (e.get("reason") or "").strip()
            if reason:
                expert_lines.append(f"• *{name}* — {reason}")
            else:
                expert_lines.append(f"• *{name}*")
        sections.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Experts*\n" + "\n".join(expert_lines)},
        })

    if channels:
        channel_lines = []
        for c in channels:
            name = c.get("name") or "unknown"
            if not name.startswith("#"):
                name = "#" + name
            reason = (c.get("reason") or "").strip()
            if reason:
                channel_lines.append(f"• {name} — {reason}")
            else:
                channel_lines.append(f"• {name}")
        sections.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Hot channels*\n" + "\n".join(channel_lines)},
        })

    if not experts and not channels:
        sections.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "No clear experts or channels found for this topic. Try a different message or broader context."},
        })

    sections.append({"type": "divider"})
    return sections
