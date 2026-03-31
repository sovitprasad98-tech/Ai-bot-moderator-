from telegram import Update
from telegram.ext import (
    Application, MessageHandler, CommandHandler,
    CallbackQueryHandler, filters
)
from http.server import BaseHTTPRequestHandler
import json, os, asyncio, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import (
    start_command, help_command, warnings_command,
    reset_warn_command, group_moderator, private_chat_handler,
    button_callback, BOT_TOKEN
)


async def process_update(update_data):
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",     start_command))
    app.add_handler(CommandHandler("help",      help_command))
    app.add_handler(CommandHandler("warnings",  warnings_command,   filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("resetwarn", reset_warn_command, filters=filters.ChatType.GROUPS))
    app.add_handler(CallbackQueryHandler(button_callback))

    # Private chat AI
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & ~filters.COMMAND,
        private_chat_handler
    ))

    # Group moderation
    app.add_handler(MessageHandler(
        filters.ChatType.GROUPS & ~filters.COMMAND,
        group_moderator
    ))

    await app.initialize()
    update = Update.de_json(update_data, app.bot)
    await app.process_update(update)
    await app.shutdown()


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        update_data = json.loads(body.decode('utf-8'))
        asyncio.run(process_update(update_data))
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'SentinelAI Bot is running!')
