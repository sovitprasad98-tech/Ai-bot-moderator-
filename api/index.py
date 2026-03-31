from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, MessageHandler, CommandHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from http.server import BaseHTTPRequestHandler
from collections import defaultdict
import logging, os, json, re, asyncio
import httpx

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================== CONFIG =====================
BOT_TOKEN = os.environ.get("BOT_TOKEN",    "8301928989:AAGw1b58x9NCDf51hDRl650PP8ges0UhS8Q")
GROQ_KEY  = os.environ.get("GROQ_API_KEY", "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")
GROQ_URL  = "https://api.groq.com/openai/v1/chat/completions"

MAX_WARNINGS = 5
DEVELOPER    = "SovitX"
BOT_NAME     = "@Rules_Ai_SovitX_Bot"
CREDIT       = f"\n\n💎 *Powered by SentinelAI — {BOT_NAME}*"

# In-memory state (resets on cold start — serverless limitation)
user_data       = defaultdict(lambda: {'warnings': 0, 'muted': False})
private_history = defaultdict(list)


# =================== HELPERS ====================
def esc(text: str) -> str:
    if not text:
        return ""
    for ch in r'\_*[]()~`>#+-=|{}.!':
        text = str(text).replace(ch, f'\\{ch}')
    return text


async def is_admin(bot, chat_id: int, user_id: int) -> bool:
    try:
        admins = await bot.get_chat_administrators(chat_id)
        return any(a.user.id == user_id for a in admins)
    except Exception:
        return False


async def mute_user(bot, chat_id: int, user_id: int):
    await bot.restrict_chat_member(
        chat_id=chat_id, user_id=user_id,
        permissions=ChatPermissions(
            can_send_messages=False, can_send_polls=False,
            can_send_other_messages=False, can_add_web_page_previews=False,
        )
    )


async def unmute_user(bot, chat_id: int, user_id: int):
    await bot.restrict_chat_member(
        chat_id=chat_id, user_id=user_id,
        permissions=ChatPermissions(
            can_send_messages=True, can_send_polls=True,
            can_send_other_messages=True, can_add_web_page_previews=True,
            can_invite_users=True,
        )
    )


# =================== GROQ AI ====================
SYSTEM_PROMPT = """You are a Telegram group moderation AI.
Classify the message into violation categories.
Reply ONLY with valid JSON — no extra text, no markdown fences.

Categories:
- selling      : selling product/service, promoting business, buy/sell offers
- money_lure   : money-making schemes, "earn fast", asking to DM for financial offers, referral spam
- forward      : message is forwarded from another group or channel
- abusive      : abusive language, slurs, profanity, hate speech in ANY language (Hindi, English, etc.)
- spam         : repetitive messages, flood, irrelevant promotional links
- clean        : no violation

Output:
{"violations": ["category1"], "reason": "short explanation"}

If clean: {"violations": ["clean"], "reason": "No violation"}"""


# FIX #3: httpx.AsyncClient (was blocking httpx.Client before)
async def classify_message_async(text: str, is_forwarded: bool) -> dict:
    context = "[FORWARDED MESSAGE]\n\n" if is_forwarded else ""
    prompt  = f"{context}Message:\n\"\"\"\n{text}\n\"\"\""
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type":  "application/json",
    }
    body = {
        "model":       "llama-3.3-70b-versatile",
        "messages":    [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        "max_tokens":  150,
        "temperature": 0.1,
    }
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            r = await client.post(GROQ_URL, headers=headers, json=body)
        raw = r.json()["choices"][0]["message"]["content"].strip()
        raw = re.sub(r"^```json|^```|```$", "", raw, flags=re.MULTILINE).strip()
        return json.loads(raw)
    except Exception as e:
        logger.error(f"Groq error: {e}")
        return {"violations": ["clean"], "reason": "AI unavailable"}


# =================== COMMANDS ===================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type

    if chat_type == "private":
        text = (
            f"👋 *Namaste\\! Main hoon SentinelAI\\!*\n"
            f"💎 *Developed by {esc(DEVELOPER)}*\n\n"
            f"{'─'*32}\n\n"
            f"🛡️ *Main kya karta hoon \\(Groups mein\\):*\n"
            f"├─ 🚫 Selling/Promotion messages delete\n"
            f"├─ 💰 Money luring/DM scam detect karna\n"
            f"├─ 📤 Forward messages turant delete\n"
            f"├─ 🤬 Abusive language \\(kisi bhi language mein\\)\n"
            f"├─ 🔁 Spam/Flood detect karna\n"
            f"└─ ⚠️ {MAX_WARNINGS} warnings ke baad auto\\-mute\n\n"
            f"{'─'*32}\n\n"
            f"⚙️ *Group Setup:*\n\n"
            f"*Step 1:* Mujhe apne group mein add karo\n\n"
            f"*Step 2:* Mujhe Admin banao with:\n"
            f"├─ ✅ Delete Messages\n"
            f"└─ ✅ Restrict Members\n\n"
            f"*Step 3:* Done\\! 🎉\n\n"
            f"{'─'*32}\n\n"
            f"💬 *Private Chat:*\n"
            f"Tum mujhse koi bhi sawaal pooch sakte ho\\!\n"
            f"Main AI se powered hoon — bas type karo\\!\n\n"
            f"_Group admins ke messages kabhi affect nahi honge\\._"
            f"{CREDIT}"
        )
    else:
        text = (
            f"⚡ *SENTINELAI — ACTIVE*\n"
            f"💎 *Developed by {esc(DEVELOPER)}*\n\n"
            f"{'─'*32}\n\n"
            f"✅ *Is group ki raksha ho rahi hai\\!*\n\n"
            f"📋 *Rules:*\n"
            f"├─ Selling/Promotion = ⚠️ Warning\n"
            f"├─ Money luring/Scam = ⚠️ Warning\n"
            f"├─ Forward message = ⚠️ Warning\n"
            f"├─ Abusive language = ⚠️ Warning\n"
            f"└─ {MAX_WARNINGS} warnings = 🔇 Permanent Mute\n\n"
            f"👮 *Admin Commands:*\n"
            f"├─ `/warnings` — User ki warnings dekho\n"
            f"├─ `/resetwarn` — Warnings reset karo\n"
            f"└─ `/help` — Help\n\n"
            f"_Admins exempt hain ✅_"
            f"{CREDIT}"
        )

    await update.message.reply_text(text, parse_mode='MarkdownV2')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"📖 *HELP — SENTINELAI*\n\n"
        f"{'─'*32}\n\n"
        f"🤖 *Bot Kya Detect Karta Hai:*\n"
        f"├─ Selling / Business Promotion\n"
        f"├─ Paise kamane ke lure / DM scam\n"
        f"├─ Forward messages\n"
        f"├─ Abusive language \\(Hindi/English/Any\\)\n"
        f"└─ Spam / Flood\n\n"
        f"⚠️ *Warning System:*\n"
        f"├─ Har violation = 1 warning\n"
        f"├─ {MAX_WARNINGS} warnings = Permanent mute\n"
        f"└─ Admin unmute kar sakta hai\n\n"
        f"👮 *Admin Commands:*\n"
        f"├─ `/warnings` — Reply karke warnings dekho\n"
        f"├─ `/resetwarn` — Reply karke warnings reset karo\n"
        f"└─ `/help` — Ye message\n\n"
        f"_Admins hamesha exempt hain\\._"
        f"{CREDIT}"
    )
    await update.message.reply_text(text, parse_mode='MarkdownV2')


async def warnings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id      = update.effective_chat.id
    requester_id = update.effective_user.id

    if not await is_admin(context.bot, chat_id, requester_id):
        await update.message.reply_text("❌ Sirf admins ye command use kar sakte hain.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("ℹ️ Kisi message ko reply karke `/warnings` use karo.")
        return

    target = update.message.reply_to_message.from_user
    count  = user_data[target.id]['warnings']
    muted  = user_data[target.id]['muted']

    text = (
        f"📊 *Warnings — {esc(target.full_name)}*\n\n"
        f"⚠️ Warnings: *{count}/{MAX_WARNINGS}*\n"
        f"🔇 Muted: *{'Yes' if muted else 'No'}*"
        f"{CREDIT}"
    )
    await update.message.reply_text(text, parse_mode='MarkdownV2')


async def reset_warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id      = update.effective_chat.id
    requester_id = update.effective_user.id

    if not await is_admin(context.bot, chat_id, requester_id):
        await update.message.reply_text("❌ Sirf admins ye command use kar sakte hain.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("ℹ️ Kisi message ko reply karke `/resetwarn` use karo.")
        return

    target = update.message.reply_to_message.from_user
    user_data[target.id]['warnings'] = 0
    user_data[target.id]['muted']    = False

    text = (
        f"✅ *Warnings Reset\\!*\n\n"
        f"👤 User: {esc(target.full_name)}\n"
        f"⚠️ Warnings: *0/{MAX_WARNINGS}*"
        f"{CREDIT}"
    )
    await update.message.reply_text(text, parse_mode='MarkdownV2')


async def private_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    chat_id = update.effective_chat.id
    text    = update.message.text or ""
    if not text:
        return

    private_history[user.id].append({"role": "user", "content": text})
    if len(private_history[user.id]) > 20:
        private_history[user.id] = private_history[user.id][-20:]

    PRIVATE_SYS = (
        "You are SentinelAI, a helpful Telegram bot created by SovitX. "
        "Answer clearly and helpfully. Keep replies short. "
        "Do NOT use **, ##, or markdown symbols — plain text only."
    )
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    body = {
        "model":       "llama-3.3-70b-versatile",
        "messages":    [{"role": "system", "content": PRIVATE_SYS}] + private_history[user.id],
        "max_tokens":  400,
        "temperature": 0.7,
    }
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        # FIX #3: AsyncClient instead of blocking Client
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(GROQ_URL, headers=headers, json=body)
        reply = r.json()["choices"][0]["message"]["content"].strip()
        reply = re.sub(r"\*\*|__|##|\*", "", reply).strip()
    except Exception as e:
        logger.error(f"Private AI error: {e}")
        reply = "Sorry, AI abhi available nahi hai. Thodi der baad try karo."

    private_history[user.id].append({"role": "assistant", "content": reply})
    await update.message.reply_text(reply)


# =============== GROUP MODERATION ===============
async def group_moderator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    user    = message.from_user
    chat_id = message.chat_id

    if not user or user.is_bot:
        return

    if await is_admin(context.bot, chat_id, user.id):
        return

    is_forwarded = (
        message.forward_origin      is not None or
        message.forward_from        is not None or
        message.forward_from_chat   is not None or
        message.forward_sender_name is not None
    )

    text = (message.text or message.caption or "").strip()

    if is_forwarded and not text:
        await _handle_violation(context, message, user, chat_id, ["forward"], "Forwarded message from another chat")
        return

    if not text:
        return

    # FIX #3: await async version
    result     = await classify_message_async(text, is_forwarded)
    violations = result.get("violations", ["clean"])

    if "clean" in violations and len(violations) == 1:
        return

    await _handle_violation(context, message, user, chat_id, violations, result.get("reason", ""))


async def _handle_violation(context, message, user, chat_id, violations, reason):
    viol_labels = {
        "selling":    "🚫 Selling / Promotion",
        "money_lure": "💰 Money Luring / DM Scam",
        "forward":    "📤 Forwarding Not Allowed",
        "abusive":    "🤬 Abusive Language",
        "spam":       "🔁 Spam / Flood",
    }

    try:
        await message.delete()
    except Exception as e:
        logger.error(f"Delete error: {e}")
        return

    user_data[user.id]['warnings'] += 1
    count     = user_data[user.id]['warnings']
    remaining = max(MAX_WARNINGS - count, 0)
    safe_name = esc(user.full_name)
    detected  = "\n".join(f"  ├─ {viol_labels.get(v, v)}" for v in violations if v != "clean")

    if count >= MAX_WARNINGS:
        try:
            await mute_user(context.bot, chat_id, user.id)
            user_data[user.id]['muted']    = True
            user_data[user.id]['warnings'] = 0

            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔓 Unmute", callback_data=f"unmute_{user.id}"),
                InlineKeyboardButton("🚫 Ban",    callback_data=f"ban_{user.id}"),
            ]])
            mute_text = (
                f"🔇 *USER MUTE HO GAYA\\!*\n\n"
                f"👤 User: {safe_name}\n\n"
                f"*Violations:*\n{detected}\n\n"
                f"📋 *{MAX_WARNINGS} violations complete* — permanent mute laga diya gaya\\!\n"
                f"_Admins neeche se action le sakte hain\\._"
                f"{CREDIT}"
            )
            await context.bot.send_message(
                chat_id=chat_id, text=mute_text,
                parse_mode='MarkdownV2', reply_markup=keyboard
            )
            logger.info(f"MUTED: {user.full_name} ({user.id})")
        except Exception as e:
            logger.error(f"Mute error: {e}")
    else:
        warn_text = (
            f"⚠️ *COMMUNITY GUIDELINES VIOLATION*\n\n"
            f"👤 User: {safe_name}\n\n"
            f"*Detected:*\n{detected}\n\n"
            f"📊 Warning: *{count}/{MAX_WARNINGS}* — {remaining} bacha\\!\n\n"
            f"_Apne messages community guidelines ke andar rakhein\\._"
            f"{CREDIT}"
        )
        await context.bot.send_message(chat_id=chat_id, text=warn_text, parse_mode='MarkdownV2')
        logger.info(f"WARNING {count}/{MAX_WARNINGS}: {user.full_name} — {violations}")


# ================ CALLBACKS =====================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query      = update.callback_query
    await query.answer()
    chat_id    = query.message.chat_id
    admin_id   = query.from_user.id
    admin_name = esc(query.from_user.first_name)

    if not await is_admin(context.bot, chat_id, admin_id):
        await query.answer("❌ Sirf admins ye kar sakte hain!", show_alert=True)
        return

    action, user_id_str = query.data.split('_', 1)
    user_id = int(user_id_str)

    if action == "unmute":
        try:
            await unmute_user(context.bot, chat_id, user_id)
            user_data[user_id]['muted']    = False
            user_data[user_id]['warnings'] = 0
            await query.edit_message_text(
                f"✅ *USER UNMUTE HO GAYA\\!*\n\n"
                f"👮 Admin: {admin_name}\n"
                f"🔄 Warnings bhi clear ho gayi\\!"
                f"{CREDIT}",
                parse_mode='MarkdownV2'
            )
        except Exception as e:
            await query.answer(f"Error: {e}", show_alert=True)

    elif action == "ban":
        try:
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            user_data.pop(user_id, None)
            await query.edit_message_text(
                f"🚫 *USER BAN HO GAYA\\!*\n\n"
                f"👮 Admin: {admin_name}\n"
                f"📋 Reason: Community guidelines violation"
                f"{CREDIT}",
                parse_mode='MarkdownV2'
            )
        except Exception as e:
            await query.answer(f"Error: {e}", show_alert=True)


# =========== VERCEL SERVERLESS HANDLER ===========
async def process_update(update_data: dict):
    """Build app fresh per request (serverless requirement)"""
    app = Application.builder().token(BOT_TOKEN).updater(None).build()

    app.add_handler(CommandHandler("start",     start_command))
    app.add_handler(CommandHandler("help",      help_command))
    app.add_handler(CommandHandler("warnings",  warnings_command,   filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("resetwarn", reset_warn_command, filters=filters.ChatType.GROUPS))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, private_chat_handler))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS  & ~filters.COMMAND, group_moderator))

    await app.initialize()
    update = Update.de_json(update_data, app.bot)
    await app.process_update(update)
    await app.shutdown()


class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        try:
            length = int(self.headers['Content-Length'])
            body   = self.rfile.read(length)
            data   = json.loads(body.decode('utf-8'))
            asyncio.run(process_update(data))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        except Exception as e:
            logger.error(f"POST error: {e}")
            self.send_response(200)   # Always 200 to Telegram
            self.end_headers()

    def do_GET(self):
        import urllib.parse
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        # Setup webhook: GET /api/webhook?setup=1&url=https://your-app.vercel.app/api/webhook
        if 'setup' in params or 'url' in params:
            webhook_url = params.get('url', [None])[0]
            if webhook_url:
                import httpx as _h
                r = _h.get(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
                    params={"url": webhook_url, "allowed_updates": '["message","callback_query"]'}
                )
                resp = r.text.encode()
            else:
                resp = b'Pass ?url=https://your-app.vercel.app/api/webhook'
        else:
            resp = b'SentinelAI is running! Visit /api/webhook?url=YOUR_VERCEL_URL/api/webhook to setup.'

        self.send_response(200)
        self.end_headers()
        self.wfile.write(resp)

    def log_message(self, format, *args):
        pass  # Suppress verbose server logs
