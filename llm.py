"""
LLM layer: keyword extraction and collaboration map analysis using Google Gemini.
"""

import os
import json
from google import genai
from google.genai import types

_gemini_client: genai.Client | None = None


def _client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is not set")
        _gemini_client = genai.Client(api_key=key)
    return _gemini_client


def get_model() -> str:
    return os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


def _strip_code_fence(text: str) -> str:
    if text.startswith("```"):
        lines = text.split("\n")
        return "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return text


def extract_search_keywords(message_text: str) -> list[str]:
    """
    Send message text to the LLM and get 3–4 high-intent search keywords
    suitable for Slack search.messages.
    """
    if not message_text or not message_text.strip():
        return []

    prompt = """You are a search query expert for workplace chat (e.g. Slack).
Given the following message, output exactly 3 to 4 search keywords that would best find related past conversations and experts in Slack's search.
Each keyword should be a SINGLE word or at most a two-word term. Do NOT use long phrases. Keep them short and specific.
Output ONLY a JSON array of strings, no other text. Example: ["deployment", "CI pipeline", "testing"].

Message:
""" + message_text.strip()[:2000]

    response = _client().models.generate_content(
        model=get_model(),
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction="You output only valid JSON arrays of search keywords.",
            temperature=0.3,
            response_mime_type="application/json",
        ),
    )
    text = (response.text or "").strip()
    try:
        out = json.loads(text)
        if isinstance(out, list) and all(isinstance(x, str) for x in out):
            return out[:6]
        return []
    except json.JSONDecodeError:
        return []


def analyze_to_collaboration_map(
    query: str,
    search_results: list[dict],
) -> dict:
    """
    Feed search result metadata to the LLM and get structured Experts + Hot Channels.
    search_results: list of {"user_name", "channel_name", "snippet", "permalink"}.
    Returns {"experts": [{"name", "reason"}], "channels": [{"name", "reason"}]}.
    """
    if not search_results:
        return {"experts": [], "channels": []}

    summary = json.dumps(
        [
            {
                "user": r.get("user_name") or "unknown",
                "channel": r.get("channel_name") or "unknown",
                "snippet": (r.get("snippet") or "")[:300],
            }
            for r in search_results[:50]
        ],
        indent=2,
    )

    prompt = f"""You analyze Slack search results to build a "Collaboration Map" for someone who asked or posted this:

Query / message context: {query[:500]}

Search results (user, channel, snippet):
{summary}

From these results:
1. List 3–6 PEOPLE who appear to be subject matter experts or active collaborators (name only, no @). Deduplicate. Prefer people who appear multiple times or in substantive messages.
2. List 3–6 CHANNELS that are most relevant for this topic (channel name only). Deduplicate. Prefer channels with multiple relevant hits.

Output ONLY a single JSON object with exactly this shape (no markdown, no extra text):
{{"experts": [{{"name": "Full Name", "reason": "one short phrase why"}}, ...], "channels": [{{"name": "#channel-name", "reason": "one short phrase why"}}, ...]}}
"""

    response = _client().models.generate_content(
        model=get_model(),
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction="You output only valid JSON. No markdown code fences.",
            temperature=0.3,
            response_mime_type="application/json",
        ),
    )
    text = (response.text or "").strip()
    try:
        out = json.loads(text)
        experts = out.get("experts") or []
        channels = out.get("channels") or []
        if not isinstance(experts, list):
            experts = []
        if not isinstance(channels, list):
            channels = []
        return {
            "experts": [e if isinstance(e, dict) else {"name": str(e), "reason": ""} for e in experts[:8]],
            "channels": [c if isinstance(c, dict) else {"name": str(c), "reason": ""} for c in channels[:8]],
        }
    except json.JSONDecodeError:
        return {"experts": [], "channels": []}
