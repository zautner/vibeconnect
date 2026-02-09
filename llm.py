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
The following are also legitimate key words: "family life design", "going balls", "hole it", "unravel master", "screw guru". Use them as is in the keyword search if mentioned.
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
    file_results: list[dict] | None = None,
) -> dict:
    """
    Feed search result metadata to the LLM and get structured Experts + Hot Channels + Relevant Files.
    search_results: list of {"user_id", "user_name", "channel_id", "channel_name", "snippet", "permalink"}.
    file_results: list of {"file_id", "file_name", "file_type", "uploader_name", "permalink"}.
    Returns {"summary": str, "experts": [...], "channels": [...], "files": [...]}.
    """
    if not search_results and not file_results:
        return {"summary": "", "experts": [], "channels": [], "files": []}

    messages_summary = json.dumps(
        [
            {
                "user_id": r.get("user_id") or "",
                "user": r.get("user_name") or "unknown",
                "channel_id": r.get("channel_id") or "",
                "channel": r.get("channel_name") or "unknown",
                "snippet": (r.get("snippet") or "")[:300],
            }
            for r in search_results[:50]
        ],
        indent=2,
    )

    files_summary = ""
    if file_results:
        files_summary = json.dumps(
            [
                {
                    "file_name": f.get("file_name") or "Untitled",
                    "file_type": f.get("file_type") or "",
                    "uploader": f.get("uploader_name") or "unknown",
                    "permalink": f.get("permalink") or "",
                }
                for f in file_results[:15]
            ],
            indent=2,
        )

    files_instruction = ""
    files_output_shape = ""
    if file_results:
        files_instruction = """4. List up to 5 FILES that are most relevant for this topic. Include their file_name and permalink from the data."""
        files_output_shape = ', "files": [{"file_name": "doc.pdf", "permalink": "https://...", "reason": "one short phrase why"}, ...]'

    prompt = f"""You analyze Slack search results to build a "Collaboration Map" for someone who asked or posted this:

Query / message context: {query[:500]}

Search results (user_id, user, channel_id, channel, snippet):
{messages_summary}
"""
    if files_summary:
        prompt += f"""
Files found (file_name, file_type, uploader, permalink):
{files_summary}
"""

    prompt += f"""
From these results,
1. First add 1-2 sentences summarizing the information most relevant to the query from the search results.
2. List up to 3 PEOPLE who appear to be subject matter experts or active collaborators. Deduplicate. Prefer people who appear multiple times or in substantive messages, not just in short replies. Include their user_id from the data. 
3. List up to 3 CHANNELS that are most relevant for this topic. Deduplicate. Prefer channels with multiple relevant hits. Include their channel_id from the data. If these terms appear in the keywords: "family life design", "going balls", "hole it", "unravel master", "screw guru", note that those are games from our catalog and they might have their dedicated channels. Unless the query content asks for it, do not suggest channels of other games in the query result of a specific game.
{files_instruction}

Output ONLY a single JSON object with exactly this shape (no markdown, no extra text):
{{"summary": "the information most relevant to the query from the search results", "experts": [{{"user_id": "U...", "name": "Full Name", "reason": "one short phrase why"}}, ...], "channels": [{{"channel_id": "C...", "name": "#channel-name", "reason": "one short phrase why"}}, ...]{files_output_shape}}}
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
        files = out.get("files") or []
        if not isinstance(experts, list):
            experts = []
        if not isinstance(channels, list):
            channels = []
        if not isinstance(files, list):
            files = []
        return {
            "summary": out.get("summary") or "",
            "experts": [e if isinstance(e, dict) else {"name": str(e), "reason": ""} for e in experts[:8]],
            "channels": [c if isinstance(c, dict) else {"name": str(c), "reason": ""} for c in channels[:8]],
            "files": [f if isinstance(f, dict) else {"file_name": str(f), "reason": ""} for f in files[:5]],
        }
    except json.JSONDecodeError:
        return {"summary": "", "experts": [], "channels": [], "files": []}
