import os
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from config import TELEGRAM_TOKEN
from handlers import (
    start, lang_choice, level_choice, style_choice,
    chat, cancel, voice_handler, LANG, LEVEL, STYLE
)

app = FastAPI()

# Telegram App
bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# Обработчики
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, lang_choice)],
        LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, level_choice)],
        STYLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, style_choice)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

bot_app.add_handler(conv_handler)
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
bot_app.add_handler(MessageHandler(filters.VOICE, voice_handler))

# FastAPI endpoint для Telegram webhook
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}


