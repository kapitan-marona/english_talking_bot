import os
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, CallbackQueryHandler, ContextTypes, filters
)
from handlers import (
    start, learn_lang_choice, level_choice, style_choice,
    chat, cancel, handle_voice_message
)
from handlers.menu import show_menu, handle_menu_selection
from config import TELEGRAM_TOKEN, WEBHOOK_SECRET_PATH
import time

app = FastAPI()

application = Application.builder().token(TELEGRAM_TOKEN).build()

# Rate limiting: user_id -> timestamp
user_last_called = {}
RATE_LIMIT_SECONDS = 3

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        0: [MessageHandler(filters.TEXT & ~filters.COMMAND, learn_lang_choice)],
        1: [MessageHandler(filters.TEXT & ~filters.COMMAND, level_choice)],
        2: [MessageHandler(filters.TEXT & ~filters.COMMAND, style_choice)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

application.add_handler(conv_handler)
application.add_handler(CommandHandler("menu", show_menu))
application.add_handler(CallbackQueryHandler(handle_menu_selection))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))

@app.post(f"/webhook/{WEBHOOK_SECRET_PATH}")
async def webhook_handler(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    user_id = update.effective_user.id if update.effective_user else None

    # Простейший rate limiter
    if user_id:
        now = time.time()
        last_call = user_last_called.get(user_id, 0)
        if now - last_call < RATE_LIMIT_SECONDS:
            return {"status": "rate_limited"}
        user_last_called[user_id] = now

    await application.initialize()
    await application.process_update(update)
    return {"status": "ok"}
