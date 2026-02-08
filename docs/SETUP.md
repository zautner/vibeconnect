# VibeConnect – Full Setup Guide

This document describes everything you need to do in **Slack** (app and bot) and **Google AI Studio** to run VibeConnect.

---

## Part 1: Slack App & Bot

### 1.1 Create the Slack app

1. Go to **[api.slack.com/apps](https://api.slack.com/apps)** and sign in with your Slack workspace.
2. Click **Create New App**.
3. Choose **From scratch**.
4. Enter an **App Name** (e.g. `VibeConnect`) and select the **Workspace** where you want to install it.
5. Click **Create App**.

You’ll land on the app’s **Basic Information** page. Keep this tab open; you’ll need the **Signing Secret** later.

---

### 1.2 Configure Bot Token Scopes

The bot needs permission to read messages, read reactions, and post replies.

1. In the left sidebar, open **OAuth & Permissions**.
2. Scroll to **Scopes**.
3. Under **Bot Token Scopes**, click **Add an OAuth Scope** and add these one by one:

   | Scope | Purpose |
   |-------|--------|
   | `channels:history` | Read messages in public channels the bot is in |
   | `chat:write` | Post the Collaboration Map reply in the channel/thread |
   | `reactions:read` | See when someone adds the :handshake: reaction |
   | `users:read` | Resolve user IDs to display names in the map |
   | `groups:history` | Read messages in private channels the bot is in |
   | `im:history` | Read messages in DMs with the bot (optional) |
   | `mpim:history` | Read messages in group DMs (optional) |

4. Leave **User Token Scopes** for the next section.

---

### 1.3 Configure User Token Scopes (for search)

VibeConnect uses Slack’s **search** to find relevant messages. The Search API requires a **user** token, not a bot token. With that user token, search runs across **all channels and DMs the installing user can access** — not limited to channels the bot is in.

1. Still in **OAuth & Permissions**, scroll to **User Token Scopes**.
2. Click **Add an OAuth Scope** under **User Token Scopes**.
3. Add:

   | Scope | Purpose |
   |-------|--------|
   | `search:read` | Run `search.messages` to find past messages by keyword |

4. Save. You’ll get the user token only **after** you install the app and enable “Act as user” (see below).

---

### 1.4 Enable Event Subscriptions

The bot must receive Slack events (e.g. `reaction_added`). You can use **HTTP** (with ngrok) or **Socket Mode**.

#### Option A: HTTP + ngrok (recommended for local/dev)

1. In the left sidebar, open **Event Subscriptions**.
2. Turn **Enable Events** **On**.
3. **Request URL** will show “Waiting…” until your server is reachable:
   - Start your app: `python app.py` (see Part 3).
   - In another terminal run: `ngrok http 3000`.
   - Copy the **HTTPS** URL ngrok shows (e.g. `https://abc123.ngrok-free.app`).
4. In Slack, set **Request URL** to:
   ```text
   https://YOUR_NGROK_SUBDOMAIN.ngrok-free.app/slack/events
   ```
   Replace `YOUR_NGROK_SUBDOMAIN` with your actual ngrok subdomain.
5. When the URL is verified, Slack shows a green checkmark.
6. Under **Subscribe to bot events**, click **Add Bot User Event** and add:
   - **`reaction_added`** — fired when anyone adds an emoji (including :handshake:) to a message.
7. Click **Save Changes**.

If you change the ngrok URL (e.g. after restarting ngrok), update the Request URL in Slack and save again.

#### Option B: Socket Mode (no ngrok)

1. In the left sidebar, open **Socket Mode**.
2. Turn **Enable Socket Mode** **On**.
3. Create an **App-Level Token**:
   - Name: e.g. `VibeConnect Socket`.
   - Scopes: add **`connections:write`**.
   - Click **Generate**.
4. **Copy the token** (`xapp-...`) once; it’s shown only once. Put it in `.env` as `SLACK_APP_TOKEN`.
5. In **Event Subscriptions**:
   - Turn **Enable Events** **On**.
   - You do **not** set a Request URL when using Socket Mode; the app connects to Slack via WebSocket.
   - Under **Subscribe to bot events**, add **`reaction_added`** as above.
6. Save.

---

### 1.5 Install the app and get tokens

1. Open **OAuth & Permissions** again.
2. At the top, click **Install to Workspace** (or **Reinstall to Workspace** if you already installed).
3. Review the permission list and click **Allow**.
4. After installation you’ll see:
   - **Bot User OAuth Token** (starts with `xoxb-`). Copy it → this is **`SLACK_BOT_TOKEN`** in `.env`.
5. To get the **User OAuth Token** (for search):
   - In **OAuth & Permissions**, find **User OAuth Token**.
   - If you don’t see it, you may need to enable **Act as user** (or similar) in your app’s install flow or in **Manage Distribution** so that the app requests user-level permissions.
   - After reinstalling (if needed), copy the token that starts with `xoxp-` → this is **`SLACK_USER_TOKEN`** in `.env`.

If your workspace doesn’t allow “Act as user” or user tokens, the app will fail when calling `search.messages`; the user token with `search:read` is required for VibeConnect’s search step.

---

### 1.6 Get the Signing Secret

1. In the left sidebar, open **Basic Information**.
2. Under **App Credentials**, find **Signing Secret**.
3. Click **Show** and copy the value → this is **`SLACK_SIGNING_SECRET`** in `.env**.

This is used to verify that incoming HTTP requests (when using ngrok) really come from Slack.

---

### 1.7 Add the bot to a channel

For the bot to receive the :handshake: reaction event, read the specific message being reacted to, and post the Collaboration Map reply, it must be **in** that channel.

**Important**: The bot only needs to be in the channel where you're adding reactions. The **search** step (which finds relevant experts and channels) uses the **user token** and searches across **all channels the installing user can access**, not just channels the bot is in.

**How to add the bot to a channel**

1. Open the channel in Slack (public or private) where you want to use the :handshake: reaction.
2. Click the **channel name** at the top of the channel to open the channel details.
3. Open the **Integrations** tab (or **Apps** / **Add apps**, depending on your Slack version).
4. Click **Add apps** (or **Add an app**).
5. Find **VibeConnect** (or whatever you named your app) in the list and click **Add**.
6. Confirm if prompted. The bot will join the channel and appear in the member list.

**Alternative: invite by name**

- In the channel, type: `/invite @VibeConnect` (replace with your app’s display name) and send. Slack will add the app to the channel if the command is allowed in your workspace.

**Notes**

- **Public channels**: Any member can usually add the bot. You need `channels:history` for the bot to read the message being reacted to.
- **Private channels**: Someone with permission to add members must add the bot (Integrations → Add apps, or `/invite @VibeConnect`). You need `groups:history` for the bot to read the message there.
- **Add the bot to every channel where you want to use :handshake:** reactions. The search for experts and channels will still cover the entire workspace (all channels the installing user can access), but the bot must be present to receive the reaction event and read the specific message.

---

### 1.8 Slack setup checklist

- [ ] App created at api.slack.com/apps  
- [ ] Bot Token Scopes: `channels:history`, `chat:write`, `reactions:read`, `users:read`, `groups:history` (and optionally `im:history`, `mpim:history`)  
- [ ] User Token Scopes: `search:read`  
- [ ] Event Subscriptions enabled; **`reaction_added`** subscribed  
- [ ] Request URL set (HTTP + ngrok) **or** Socket Mode enabled with app-level token  
- [ ] App installed to workspace  
- [ ] **Bot User OAuth Token** (`xoxb-...`) and **User OAuth Token** (`xoxp-...`) copied  
- [ ] **Signing Secret** copied  
- [ ] Bot invited to the channels where you want to use :handshake:  

---

## Part 2: Google AI Studio (Gemini API)

VibeConnect uses Google’s Gemini API for:

1. Extracting 3–4 search keywords from the message text.  
2. Analyzing search results to produce the Collaboration Map (experts + channels).

### 2.1 Get a Gemini API key

1. Go to **[Google AI Studio](https://aistudio.google.com/)** and sign in with your Google account.
2. Open the **API key** area:
   - Either use the direct link: **[aistudio.google.com/apikey](https://aistudio.google.com/apikey)**  
   - Or from the AI Studio home: look for **Get API key** or **API keys** in the menu or on the landing page.
3. Click **Create API key**.
4. Choose an existing Google Cloud project or **Create a new project** (Google AI Studio can create one for you for the free tier).
5. After the key is created, click **Copy** to copy the key.
6. Store it in your `.env` file as **`GEMINI_API_KEY`** (see Part 3). Do not commit this key to version control.

No other configuration in Google AI Studio is required for VibeConnect. The app uses the key to call the Gemini API (default model: `gemini-2.0-flash`).

### 2.2 Optional: model and quotas

- **Model**: The app uses the model set in **`GEMINI_MODEL`** (default: `gemini-2.0-flash`). You can change it in `.env` (e.g. to another Gemini model name if available in the API).
- **Quotas and limits**: In Google AI Studio / Google Cloud Console you can view usage and quotas for the Gemini API. Free tier has rate and usage limits; for heavy use you may need to enable billing or adjust limits.

### 2.3 Google AI Studio checklist

- [ ] Signed in at aistudio.google.com  
- [ ] API key created and copied  
- [ ] Key saved as `GEMINI_API_KEY` in `.env`  

---

## Part 3: Tying it together

### 3.1 Environment variables

In the project root, copy the example env file and edit it:

```bash
cp .env.example .env
```

Fill in every required value (replace placeholders, don’t leave `xoxb-your-bot-token` etc.):

| Variable | Where you got it | Required |
|----------|-------------------|----------|
| `SLACK_BOT_TOKEN` | Slack → OAuth & Permissions → Bot User OAuth Token (`xoxb-...`) | Yes |
| `SLACK_USER_TOKEN` | Slack → OAuth & Permissions → User OAuth Token (`xoxp-...`) | Yes |
| `SLACK_SIGNING_SECRET` | Slack → Basic Information → Signing Secret | Yes (for HTTP/ngrok) |
| `GEMINI_API_KEY` | Google AI Studio → API key | Yes |
| `SLACK_APP_TOKEN` | Slack → Socket Mode → App-Level Token (`xapp-...`) | Only if using Socket Mode |
| `GEMINI_MODEL` | Optional; default `gemini-2.0-flash` | No |
| `PORT` | Optional; default `3000` | No |

### 3.2 Run the app

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

- **If you use ngrok**: In another terminal run `ngrok http 3000` and set the Events Request URL in Slack to `https://YOUR_NGROK_HOST/slack/events` (see 1.4).
- **If you use Socket Mode**: Set `SLACK_APP_TOKEN` in `.env`; no ngrok or Request URL needed.

### 3.3 Test the bot

1. In a channel where the bot is added, post a message (e.g. “Who knows about our CI pipeline?”).
2. Add the **:handshake:** reaction to that message.
3. The bot should reply in the thread with a Collaboration Map (Experts and Hot Channels). If it doesn’t, check the app logs and the Slack Event Subscriptions / Socket Mode setup.

---

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| “Could not read the message” | Bot not in channel; missing `channels:history` / `groups:history`; or channel is private and bot wasn’t invited. |
| “Slack user token must have search:read scope” | Add `search:read` under **User Token Scopes**, reinstall the app, and use the new **User OAuth Token** in `SLACK_USER_TOKEN`. |
| “GEMINI_API_KEY is not set” | Add `GEMINI_API_KEY=...` to `.env` and restart the app. |
| Request URL not verified (ngrok) | App must be running and ngrok must be forwarding to the same port; URL must be exactly `https://.../slack/events`. |
| No response to :handshake: | Event Subscriptions enabled and `reaction_added` subscribed; Request URL (ngrok) or Socket Mode configured; app running and no errors in logs. |

---

## Summary

1. **Slack**: Create app → add Bot and User OAuth scopes → enable Events (HTTP + ngrok or Socket Mode) → subscribe to `reaction_added` → install app → copy Bot token, User token, and Signing Secret.  
2. **Google AI Studio**: Create API key → copy key → set `GEMINI_API_KEY` in `.env`.  
3. **App**: Put all tokens and secrets in `.env`, run `python app.py`, and (if using ngrok) point Slack’s Request URL to `https://YOUR_NGROK_HOST/slack/events`.

After that, reacting with :handshake: in a channel where the bot is present will trigger the Collaboration Map.
