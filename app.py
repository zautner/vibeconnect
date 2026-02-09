"""
VibeConnect – Slack bot entrypoint.
Trigger: @mention the bot -> Collaboration Map (Experts + Hot Channels).
"""

import os
import re
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Setup-mode helpers
# ---------------------------------------------------------------------------

_PLACEHOLDERS = {
    "xoxb-your-bot-token",
    "xoxp-your-user-token",
    "your-signing-secret",
    "your-gemini-api-key",
}


def _is_placeholder(value: str | None) -> bool:
    """Return True if the env value is missing or still a placeholder."""
    if not value:
        return True
    return value.strip() in _PLACEHOLDERS


def _in_setup_mode() -> bool:
    return (
        _is_placeholder(os.environ.get("SLACK_BOT_TOKEN"))
        or _is_placeholder(os.environ.get("SLACK_SIGNING_SECRET"))
    )


# ---------------------------------------------------------------------------
# Bolt app – created lazily so the module can load even in setup mode
# ---------------------------------------------------------------------------

_app = None


def _get_app():
    """Return the slack_bolt App, creating it on first call."""
    global _app
    if _app is None:
        from slack_bolt import App
        _app = App(
            token=os.environ.get("SLACK_BOT_TOKEN"),
            signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
        )
        _register_handlers(_app)
    return _app


# ---------------------------------------------------------------------------
# Bot logic
# ---------------------------------------------------------------------------

_bot_user_id: str | None = None
_bot_user_id_fetched = False


def get_message(client, channel_id: str, ts: str) -> tuple[str, str]:
    """Fetch the message for the given channel and ts. Returns (text, user_id)."""
    from slack_sdk.errors import SlackApiError
    try:
        resp = client.conversations_history(
            channel=channel_id,
            latest=ts,
            inclusive=True,
            limit=1,
        )
        messages = resp.get("messages") or []
        if not messages:
            return "", ""
        m = messages[0]
        return (m.get("text") or "").strip(), (m.get("user") or "")
    except SlackApiError as e:
        logger.warning("conversations_history failed: %s", e)
        return "", ""


def _register_handlers(bolt_app):
    """Register all Slack event handlers on the given Bolt app."""

    @bolt_app.event("app_mention")
    def handle_app_mention(event, client, say):
        """When user @mentions the bot, build and post the Collaboration Map."""
        channel_id = event.get("channel")
        ts = event.get("ts")
        if not channel_id or not ts:
            return

        # Avoid reacting to our own bot messages
        bot_id = _get_bot_user_id(client)
        if bot_id and event.get("user") == bot_id:
            return

        # Strip the bot mention from the message text
        raw_text = (event.get("text") or "").strip()
        message_text = re.sub(r"<@[A-Za-z0-9]+>", "", raw_text).strip()

        if not message_text:
            _reply_ephemeral_or_channel(
                client, channel_id, ts,
                "Please include a message after mentioning me, e.g. `@VibeConnect how do I deploy?`",
            )
            return

        logger.info("Building Collaboration Map for: %s...", message_text[:80])

        try:
            from llm import extract_search_keywords, analyze_to_collaboration_map
            from search import search_slack_messages
            from blocks import collaboration_map_blocks

            keywords = extract_search_keywords(message_text)
            logger.info("Keywords: %s", keywords)
            if not keywords:
                _reply_ephemeral_or_channel(
                    client, channel_id, ts,
                    "I couldn't extract search keywords from this message.",
                )
                return

            search_results = search_slack_messages(keywords, count=50)
            logger.info("Search returned %d results", len(search_results))

            result = analyze_to_collaboration_map(message_text, search_results)
            summary = result.get("summary") or ""
            experts = result.get("experts") or []
            channels = result.get("channels") or []

            # Build fallback name->id maps from search results in case LLM
            # didn't return the IDs reliably.
            user_name_to_id = {}
            channel_name_to_id = {}
            for sr in search_results:
                uname = sr.get("user_name") or ""
                uid = sr.get("user_id") or ""
                if uname and uid:
                    user_name_to_id[uname.lower()] = uid
                cname = sr.get("channel_name") or ""
                cid = sr.get("channel_id") or ""
                if cname and cid:
                    channel_name_to_id[cname.lstrip("#").lower()] = cid
            
            for e in experts:
                if not e.get("user_id"):
                    name = (e.get("name") or "").lower()
                    e["user_id"] = user_name_to_id.get(name, "")

            for c in channels:
                if not c.get("channel_id"):
                    name = (c.get("name") or "").lstrip("#").lower()
                    c["channel_id"] = channel_name_to_id.get(name, "")

            # Filter out the bot itself and the searcher from experts
            searcher_user_id = event.get("user")
            experts = [
                e for e in experts 
                if e.get("user_id") != bot_id and e.get("user_id") != searcher_user_id
            ]

            blocks = collaboration_map_blocks(
                query_preview=message_text,
                summary=summary,
                experts=experts,
                channels=channels,
            )
            _post_blocks(client, channel_id, ts, blocks)
        except ValueError as e:
            _reply_ephemeral_or_channel(client, channel_id, ts, str(e))
        except Exception as e:
            logger.exception("Pipeline error")
            _reply_ephemeral_or_channel(
                client, channel_id, ts,
                f"Something went wrong building the map: {e}",
            )


def _post_blocks(client, channel_id: str, thread_ts: str, blocks: list):
    """Post the Collaboration Map as a reply in the thread."""
    client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        blocks=blocks,
        text="Collaboration Map (see blocks)",
    )


def _get_bot_user_id(client) -> str | None:
    """Return the bot's own user ID, cached for the process lifetime."""
    global _bot_user_id, _bot_user_id_fetched
    if _bot_user_id_fetched:
        return _bot_user_id
    try:
        _bot_user_id = (client.auth_test().get("user_id") or "").strip() or None
    except Exception:
        _bot_user_id = None
    _bot_user_id_fetched = True
    return _bot_user_id


def _reply_ephemeral_or_channel(client, channel_id: str, thread_ts: str, text: str):
    """Post error/fallback message; prefer thread reply."""
    from slack_sdk.errors import SlackApiError
    try:
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=text,
        )
    except SlackApiError:
        try:
            client.chat_postMessage(channel=channel_id, text=text)
        except SlackApiError as e:
            logger.warning("Failed to post fallback message to %s: %s", channel_id, e)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main():
    port = int(os.environ.get("PORT", "3000"))

    # ---- Setup mode: placeholder tokens → minimal server for URL verification ----
    if _in_setup_mode():
        logger.warning("=" * 60)
        logger.warning("  SETUP MODE - tokens are missing or still placeholders.")
        logger.warning("  The server will start so you can verify the Slack")
        logger.warning("  Request URL, but the bot won't process events yet.")
        logger.warning("  Fill in .env with real tokens and restart.")
        logger.warning("=" * 60)

        from flask import Flask, request, jsonify

        flask_app = Flask(__name__)

        @flask_app.route("/slack/events", methods=["POST"])
        def slack_events_setup():
            logger.info("Received URL verification challenge - responding.")
            body = request.get_json(silent=True) or {}
            # Handle Slack URL verification challenge
            if body.get("type") == "url_verification":
                logger.info("Received URL verification challenge - responding.")
                return jsonify({"challenge": body.get("challenge", "")})
            return jsonify({"ok": True})

        @flask_app.route("/")
        def health():
            return "VibeConnect is running (setup mode - waiting for real tokens).", 200

        logger.info("Starting setup-mode server on port %d ...", port)
        flask_app.run(host="0.0.0.0", port=port, debug=False)
        return

    # ---- Normal mode ----
    bolt_app = _get_app()
    use_socket_mode = os.environ.get("SLACK_APP_TOKEN")

    if use_socket_mode:
        from slack_bolt.adapter.socket_mode import SocketModeHandler
        handler = SocketModeHandler(bolt_app, os.environ["SLACK_APP_TOKEN"])
        handler.start()
    else:
        from slack_bolt.adapter.flask import SlackRequestHandler
        from flask import Flask, request

        flask_app = Flask(__name__)
        handler = SlackRequestHandler(bolt_app)

        @flask_app.route("/slack/events", methods=["POST"])
        def slack_events():
            logger.info("Received Slack event: %s", request.get_json())
            return handler.handle(request)

        @flask_app.route("/")
        def health():
            return "VibeConnect is running.", 200

        flask_app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
