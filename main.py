import os
import json
import re
import httpx
from collections import defaultdict

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
BOT_TOKEN   = os.environ.get("BOT_TOKEN", "8301928989:AAGw1b58x9NCDf51hDRl650PP8ges0UhS8Q")
GROQ_KEY    = os.environ.get("GROQ_API_KEY", "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")
TG_API      = f"https://api.telegram.org/bot{BOT_TOKEN}"
GROQ_URL    = "https://api.groq.com/openai/v1/chat/completions"
WARN_LIMIT  = 5   # mute after this many warnings

# ─────────────────────────────────────────────
#  IN-MEMORY WARNING STORE  { chat_id: { user_id: count } }
# ─────────────────────────────────────────────
warnings: dict = defaultdict(lambda: defaultdict(int))


# ═════════════════════════════════════════════
#  TELEGRAM HELPERS
# ═════════════════════════════════════════════
def tg(method: str, payload: dict):
    with httpx.Client(timeout=10) as client:
        r = client.post(f"{TG_API}/{method}", json=payload)
    return r.json()


def delete_message(chat_id, message_id):
    tg("deleteMessage", {"chat_id": chat_id, "message_id": message_id})


def send_message(chat_id, text, reply_to=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    tg("sendMessage", payload)


def mute_user(chat_id, user_id):
    """Restrict user — no messages allowed."""
    tg("restrictChatMember", {
        "chat_id": chat_id,
        "user_id": user_id,
        "permissions": {
            "can_send_messages":       False,
            "can_send_audios":         False,
            "can_send_documents":      False,
            "can_send_photos":         False,
            "can_send_videos":         False,
            "can_send_video_notes":    False,
            "can_send_voice_notes":    False,
            "can_send_polls":          False,
            "can_send_other_messages": False,
            "can_add_web_page_previews": False,
        }
    })


def get_admins(chat_id) -> set:
    """Return set of admin/owner user IDs."""
    res = tg("getChatAdministrators", {"chat_id": chat_id})
    if not res.get("ok"):
        return set()
    return {m["user"]["id"] for m in res.get("result", [])}


def user_display(user: dict) -> str:
    name = user.get("first_name", "")
    if user.get("last_name"):
        name += " " + user["last_name"]
    return name.strip() or "User"


def username_tag(user: dict) -> str:
    if user.get("username"):
        return f"@{user['username']}"
    return f'<a href="tg://user?id={user["id"]}">{user_display(user)}</a>'


# ═════════════════════════════════════════════
#  GROQ AI CLASSIFIER
# ═════════════════════════════════════════════
SYSTEM_PROMPT = """You are a Telegram group moderation AI.
Classify the given message into one or more of these violation categories.
Reply with ONLY a valid JSON object — no extra text, no markdown.

Categories:
- selling      : user is selling something, promoting a product/service, or asking others to buy
- money_lure   : user is luring others with money-making schemes, "earn fast", referral spam, or asking to DM for financial offers
- forward      : message appears to be forwarded from another group/channel (check context clue)
- abusive      : message contains abusive language, slurs, profanity, or hate speech in ANY language
- spam         : repetitive/irrelevant message, flood, or promotional link spam
- clean        : none of the above violations

Output format:
{
  "violations": ["selling", "abusive"],
  "reason": "Short English explanation of what was detected"
}

If clean, output: {"violations": ["clean"], "reason": "No violation detected"}
"""


def classify_message(text: str, is_forwarded: bool) -> dict:
    context = ""
    if is_forwarded:
        context = "[NOTE: This message was forwarded from another chat.]\n\n"

    prompt = f"{context}Message to classify:\n\"\"\"\n{text}\n\"\"\""

    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type":  "application/json",
    }
    body = {
        "model":    "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        "max_tokens":  200,
        "temperature": 0.1,
    }
    try:
        with httpx.Client(timeout=15) as client:
            r = client.post(GROQ_URL, headers=headers, json=body)
        raw = r.json()["choices"][0]["message"]["content"].strip()
        # Strip possible markdown fences
        raw = re.sub(r"^```json|^```|```$", "", raw, flags=re.MULTILINE).strip()
        return json.loads(raw)
    except Exception as e:
        print(f"[Groq Error] {e}")
        return {"violations": ["clean"], "reason": "AI unavailable"}


# ═════════════════════════════════════════════
#  WARNING + MUTE LOGIC
# ═════════════════════════════════════════════
def handle_violation(chat_id, user_id, user: dict, message_id: int, violations: list, reason: str):
    """Delete message, issue warning, mute if limit reached."""

    delete_message(chat_id, message_id)

    warnings[chat_id][user_id] += 1
    count = warnings[chat_id][user_id]
    remaining = WARN_LIMIT - count

    tag = username_tag(user)
    viol_labels = {
        "selling":    "🚫 Selling / Promotion",
        "money_lure": "💰 Money Luring / DM Scam",
        "forward":    "📤 Forwarding Not Allowed",
        "abusive":    "🤬 Abusive Language",
        "spam":       "🔁 Spam / Flood",
    }

    detected = [viol_labels.get(v, v) for v in violations if v != "clean"]
    viol_text = "\n".join(f"  • {d}" for d in detected)

    if count >= WARN_LIMIT:
        # Mute the user
        mute_user(chat_id, user_id)
        warnings[chat_id][user_id] = 0  # reset after mute

        msg = (
            f"⚠️ <b>Community Guidelines Violation</b>\n\n"
            f"👤 {tag}\n\n"
            f"<b>Detected Violation(s):</b>\n{viol_text}\n\n"
            f"🔇 <b>You have been muted.</b>\n"
            f"You have violated our community guidelines <b>{WARN_LIMIT} times</b>. "
            f"Your messaging privileges have been restricted by <b>@Rules_Ai_SovitX_Bot</b>.\n\n"
            f"📩 Please contact a group admin to appeal."
        )
    else:
        msg = (
            f"⚠️ <b>Community Guidelines Violation</b>\n\n"
            f"👤 {tag}, your message was removed.\n\n"
            f"<b>Reason:</b>\n{viol_text}\n\n"
            f"📋 <b>This is Warning {count} of {WARN_LIMIT}.</b> "
            f"You have <b>{remaining} warning(s)</b> remaining before you are muted.\n\n"
            f"Please review our group rules and ensure your messages comply with our community guidelines. "
            f"Repeated violations will result in a mute. — <b>@Rules_Ai_SovitX_Bot</b>"
        )

    send_message(chat_id, msg)


# ═════════════════════════════════════════════
#  MAIN UPDATE HANDLER
# ═════════════════════════════════════════════
def process_update(update: dict):
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat      = message.get("chat", {})
    chat_id   = chat.get("id")
    chat_type = chat.get("type", "private")

    # Only handle group / supergroup
    if chat_type not in ("group", "supergroup"):
        return

    user     = message.get("from", {})
    user_id  = user.get("id")
    msg_id   = message.get("message_id")

    if not user_id or user.get("is_bot"):
        return

    # Skip admins and owner
    admins = get_admins(chat_id)
    if user_id in admins:
        return

    # ── Check forwarded ──────────────────────
    is_forwarded = (
        "forward_from" in message
        or "forward_from_chat" in message
        or "forward_origin" in message
    )

    # ── Get text ─────────────────────────────
    text = (
        message.get("text")
        or message.get("caption")
        or ""
    ).strip()

    # Forward with no text — still a violation
    if is_forwarded and not text:
        delete_message(chat_id, msg_id)
        tag = username_tag(user)
        send_message(chat_id,
            f"⚠️ <b>Community Guidelines Violation</b>\n\n"
            f"👤 {tag}\n\n"
            f"  • 📤 Forwarding Not Allowed\n\n"
            f"Forwarding messages from other groups or channels is <b>not permitted</b> in this community. "
            f"— <b>@Rules_Ai_SovitX_Bot</b>"
        )
        return

    if not text:
        return

    # ── AI Classification ────────────────────
    result     = classify_message(text, is_forwarded)
    violations = result.get("violations", ["clean"])
    reason     = result.get("reason", "")

    if "clean" in violations and len(violations) == 1:
        return  # Message is fine

    handle_violation(chat_id, user_id, user, msg_id, violations, reason)
