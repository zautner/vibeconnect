# VibeConnect – Expert & Collaboration Discovery

An AI-powered Slack bot that turns a project description or question into a **Collaboration Map**: it identifies subject matter experts and relevant channels when you react to a message with :handshake:.

## How it works

1. **Trigger** – Add the :handshake: reaction to any message.
2. **NLP** – The message text is sent to Gemini to extract 3–4 high-intent search keywords.
3. **Retrieval** – Slack `search.messages` (with your user token) finds up to 50 relevant posts from across all channels the installing user can access.
4. **Analysis** – Metadata (usernames, channel names, snippets) is analyzed by the LLM.
5. **Delivery** – The bot posts a Block Kit card with **Experts** and **Hot Channels**.

## Setup

> **📖 For detailed step-by-step instructions**, see **[docs/SETUP.md](docs/SETUP.md)**.

### 1. Slack app

1. Create an app at [api.slack.com/apps](https://api.slack.com/apps).
2. **OAuth & Permissions**
   - Bot token scopes: `channels:history`, `chat:write`, `reactions:read`, `users:read`, `groups:history`, `im:history`, `mpim:history`.
   - User token scopes: `search:read`.
3. **Event Subscriptions** – Enable, set Request URL to your ngrok URL (e.g. `https://xxx.ngrok.io/slack/events`).
   - Subscribe to bot events: `reaction_added`.
4. Install to workspace (Bot + "Act as user" for search — both required). Copy **Bot User OAuth Token** (`xoxb-...`) and **User OAuth Token** (`xoxp-...`).
5. **Basic Information** – copy **Signing Secret**.

### 2. Environment

```bash
cp .env.example .env
# Edit .env with your tokens and GEMINI_API_KEY.
```

### 3. Run locally

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python app.py
```

### 4. Expose with ngrok

```bash
ngrok http 3000
```

Use the ngrok HTTPS URL as your Slack Event Subscriptions Request URL: `https://YOUR_SUBDOMAIN.ngrok.io/slack/events`.

## Stack

| Component | Tool |
|-----------|------|
| Language | Python |
| Slack | slack_bolt |
| Auth | Bot token (xoxb) + User token (xoxp) for search |
| LLM | Google Gemini API |
| Deployment | Ngrok / Replit |

## Configuration

- **Reaction** – Trigger emoji is `handshake`. Change `TRIGGER_EMOJI` in `app.py` if needed.
- **Model** – Set `GEMINI_MODEL` in `.env` (default `gemini-2.0-flash`).
