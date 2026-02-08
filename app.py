"""
VibeConnect – Slack bot entrypoint.
Trigger: :handshake: on a message → Collaboration Map (Experts + Hot Channels).
"""

import os
import logging
from dotenv import load_dotenv

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError

from llm import extract_search_keywords, analyze_to_collaboration_map
from search import search_slack_messages
from blocks import collaboration_map_blocks

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TRIGGER_EMOJI = "handshake"

app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)

_bot_user_id: str | None = None
_bot_user_id_fetched = False


def get_message(client, channel_id: str, ts: str) -> tuple[str, str]:
    """Fetch the message for the given channel and ts. Returns (text, user_id)."""
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


@app.event("reaction_added")
def handle_reaction_added(event, client, say, logger_):
    """When user adds the trigger emoji to a message, build and post the Collaboration Map."""
    if event.get("reaction") != TRIGGER_EMOJI:
        return

    item = event.get("item") or {}
    if item.get("type") != "message":
        return

    channel_id = item.get("channel")
    ts = item.get("ts")
    if not channel_id or not ts:
        return

    # Avoid reacting to our own bot messages
    if event.get("user") == event.get("bot_id"):
        return

    try:
        message_text, message_user = get_message(client, channel_id, ts)
    except Exception as e:
        logger_.exception("Failed to fetch message")
        _reply_ephemeral_or_channel(client, channel_id, ts, f"Could not read the message: {e}")
        return

    # Don't build a map for our own bot messages
    bot_id = _get_bot_user_id(client)
    if bot_id and message_user == bot_id:
        return

    if not message_text:
        _reply_ephemeral_or_channel(
            client, channel_id, ts,
            "I couldn't read the message content (e.g. file-only or no history access).",
        )
        return

    logger_.info("Building Collaboration Map for: %s...", message_text[:80])

    try:
        keywords = extract_search_keywords(message_text)
        logger_.info("Keywords: %s", keywords)
        if not keywords:
            _reply_ephemeral_or_channel(
                client, channel_id, ts,
                "I couldn't extract search keywords from this message.",
            )
            return

        search_results = search_slack_messages(keywords, count=50)
        logger_.info("Search returned %d results", len(search_results))

        result = analyze_to_collaboration_map(message_text, search_results)
        experts = result.get("experts") or []
        channels = result.get("channels") or []

        blocks = collaboration_map_blocks(
            query_preview=message_text,
            experts=experts,
            channels=channels,
        )
        _post_blocks(client, channel_id, ts, blocks)
    except ValueError as e:
        _reply_ephemeral_or_channel(client, channel_id, ts, str(e))
    except Exception as e:
        logger_.exception("Pipeline error")
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
    """Post error/fallback message; prefer thread reply (no ephemeral for reactions)."""
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


def main():
    port = int(os.environ.get("PORT", "3000"))
    use_socket_mode = os.environ.get("SLACK_APP_TOKEN")

    if use_socket_mode:
        # Socket Mode: no ngrok needed
        handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
        handler.start()
    else:
        # HTTP + ngrok: start Flask
        from slack_bolt.adapter.flask import SlackRequestHandler
        from flask import Flask, request

        flask_app = Flask(__name__)
        handler = SlackRequestHandler(app)

        @flask_app.route("/slack/events", methods=["POST"])
        def slack_events():
            return handler.handle(request)

        @flask_app.route("/")
        def health():
            return "VibeConnect is running.", 200

        flask_app.run(port=port, debug=False)


if __name__ == "__main__":
    main()
