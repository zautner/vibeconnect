"""
Slack search using the user token (required for search.messages).
"""

import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

_user_client: WebClient | None = None
_user_name_cache: dict[str, str] = {}  # persistent across invocations


def get_user_client() -> WebClient:
    global _user_client
    if _user_client is None:
        token = os.environ.get("SLACK_USER_TOKEN")
        if not token:
            raise ValueError("SLACK_USER_TOKEN is required for search.messages")
        _user_client = WebClient(token=token)
    return _user_client


def search_slack_messages(keywords: list[str], count: int = 100) -> list[dict]:
    """
    Run Slack search.messages with the given keywords.

    Uses the user token (SLACK_USER_TOKEN), so search runs across all channels
    and DMs that the installing user can access — not limited to channels
    the bot is in.

    Returns a list of dicts with user_name, channel_name, snippet, permalink, ts.
    """
    if not keywords:
        return []

    # Build query: OR of keywords (no quoting – let Slack match flexibly)
    query = " OR ".join(keywords[:4])

    client = get_user_client()
    per_page = min(count, 100)  # Slack max is 100 per page
    all_matches: list[dict] = []

    try:
        for page in range(1, 4):  # up to 3 pages if count demands it
            response = client.search_messages(
                query=query,
                count=per_page,
                page=page,
            )
            messages_obj = response.get("messages") or {}
            matches = messages_obj.get("matches") or []
            all_matches.extend(matches)

            # Stop early: enough raw results, last page, or short page
            if len(all_matches) >= count:
                break
            paging = messages_obj.get("paging") or {}
            current_page = paging.get("page", page)
            total_pages = paging.get("pages", 1)
            if current_page >= total_pages or len(matches) < per_page:
                break
    except SlackApiError as e:
        if e.response.get("error") == "missing_scope":
            raise ValueError(
                "Slack user token must have search:read scope. "
                "Reinstall the app with user token scopes."
            ) from e
        raise

    # Deduplicate by ts+channel (API can return duplicates across pages)
    seen = set()
    unique_matches = []
    for m in all_matches:
        key = (m.get("channel", {}).get("id") if isinstance(m.get("channel"), dict) else "", m.get("ts"))
        if key in seen:
            continue
        seen.add(key)
        unique_matches.append(m)

    messages = unique_matches[:count]
    out = []

    for m in messages:
        user_id = m.get("user") or m.get("username") or ""
        channel_id = m.get("channel", {}).get("id") if isinstance(m.get("channel"), dict) else ""
        channel_name = ""
        if isinstance(m.get("channel"), dict):
            channel_name = m.get("channel", {}).get("name") or ""
            if channel_name and not channel_name.startswith("#"):
                channel_name = "#" + channel_name
        text = (m.get("text") or "")[:400]
        permalink = m.get("permalink") or ""

        if user_id and user_id not in _user_name_cache:
            _user_name_cache[user_id] = _get_user_name(client, user_id)
        user_name = _user_name_cache.get(user_id, "Unknown") if user_id else "Unknown"

        out.append({
            "user_id": user_id,
            "user_name": user_name,
            "channel_id": channel_id,
            "channel_name": channel_name or (("#" + str(channel_id)) if channel_id else "unknown"),
            "snippet": text,
            "permalink": permalink,
            "ts": m.get("ts"),
        })

    return out


def _get_user_name(client: WebClient, user_id: str) -> str:
    """Resolve user ID to display name; cache in memory for the request."""
    try:
        resp = client.users_info(user=user_id)
        u = (resp.get("user") or {})
        return u.get("real_name") or u.get("name") or user_id
    except Exception:
        return user_id


def search_slack_files(keywords: list[str], count: int = 20) -> list[dict]:
    """
    Search Slack files with the given keywords.

    Uses the user token (SLACK_USER_TOKEN), so search runs across all channels
    and DMs that the installing user can access.

    Returns a list of dicts with file_id, file_name, file_type, uploader_name, permalink, etc.
    """
    if not keywords:
        return []

    query = " OR ".join(keywords[:4])
    client = get_user_client()

    try:
        response = client.search_files(query=query, count=min(count, 100))
        files_obj = response.get("files") or {}
        matches = files_obj.get("matches") or []
    except SlackApiError as e:
        if e.response.get("error") == "missing_scope":
            raise ValueError(
                "Slack user token must have search:read scope. "
                "Reinstall the app with user token scopes."
            ) from e
        raise

    out = []
    for f in matches[:count]:
        user_id = f.get("user") or ""
        if user_id and user_id not in _user_name_cache:
            _user_name_cache[user_id] = _get_user_name(client, user_id)

        # Get channel names where file is shared
        channels = f.get("channels") or []
        
        out.append({
            "file_id": f.get("id") or "",
            "file_name": f.get("name") or f.get("title") or "Untitled",
            "file_type": f.get("filetype") or "",
            "uploader_id": user_id,
            "uploader_name": _user_name_cache.get(user_id, "Unknown") if user_id else "Unknown",
            "permalink": f.get("permalink") or "",
            "channels": channels,
            "timestamp": f.get("timestamp"),
        })

    return out
