# SentinelAI Moderation Bot
### @Rules_Ai_SovitX_Bot

---

## Features
- Detects & deletes selling / promotion messages
- Detects & deletes money-luring / DM scam messages
- Deletes forwarded messages from other groups/channels
- Deletes abusive language in ANY language
- Detects spam / flood
- Warning system: 5 warnings → auto mute
- Skips admins & owner automatically
- Professional warning messages in Hindi + English
- Powered by Groq AI (Llama 3.3 70B)

---

## Files
```
sentinelbot/
├── main.py              ← Core bot logic
├── api/
│   └── webhook.py       ← Vercel serverless handler
├── vercel.json          ← Vercel config
├── requirements.txt     ← Python dependencies
├── setup_webhook.py     ← Run once to register webhook
└── README.md
```

---

## Deployment Steps

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "SentinelAI Bot"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### Step 2 — Deploy on Vercel
1. Go to https://vercel.com
2. Click **Add New Project** → Import your GitHub repo
3. Framework: **Other**
4. Click **Deploy**

### Step 3 — Add Environment Variables in Vercel
Go to **Project Settings → Environment Variables** and add:

| Name | Value |
|------|-------|
| `BOT_TOKEN` | `8301928989:AAGw1b58x9NCDf51hDRl650PP8ges0UhS8Q` |
| `GROQ_API_KEY` | `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` |

Then **Redeploy** once after adding env vars.

### Step 4 — Register Webhook
After deploy, run this locally (one time only):
```bash
pip install httpx
python setup_webhook.py https://YOUR-PROJECT.vercel.app
```

---

## Add Bot to Group
1. Add **@Rules_Ai_SovitX_Bot** to your Telegram group
2. Make it **Admin** with these permissions:
   - Delete messages ✅
   - Restrict members ✅
   - Read messages ✅
3. Done — bot is live!

---

## Warning System
| Warnings | Action |
|----------|--------|
| 1–4 | Message deleted + warning sent |
| 5th | Message deleted + user muted |

Muted users must contact an admin to be unmuted.

---

## Note
- Warnings reset to 0 after a mute
- Bot restarts clear in-memory warnings (upgrade to Redis/Firebase for persistence)
- Admins and group owner are always exempt
