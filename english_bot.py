import os
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)

from config import TELEGRAM_TOKEN
from handlers import (
    start,
    lang_choice,
    level_choice,
    style_choice,
    chat,
    cancel,
    voice_handler,
    device_lang_choice,
    manual_lang_choice,
    learn_lang_choice,
    DEVICE_LANG,
    LEARN_LANG,
    LANG,
    LEVEL,
    STYLE
)

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "English Talking Bot is running."}

bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        DEVICE_LANG: [
            MessageHandler(filters.Regex("^Use device language$"), device_lang_choice),
            MessageHandler(filters.Regex("^Choose manually$"), manual_lang_choice),
        ],
        LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, lang_choice)],
        LEARN_LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, learn_lang_choice)],
        LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, level_choice)],
        STYLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, style_choice)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

bot_app.add_handler(conv_handler)
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
bot_app.add_handler(MessageHandler(filters.VOICE, voice_handler))

@app.on_event("startup")
async def startup_event():
    await bot_app.initialize()
    await bot_app.start()

@app.on_event("shutdown")
async def shutdown_event():
    await bot_app.stop()
    await bot_app.shutdown()

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}

