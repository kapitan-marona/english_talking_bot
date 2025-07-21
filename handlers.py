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
    start, lang_choice, level_choice, style_choice,
    chat, cancel, voice_handler, LANG, LEVEL, STYLE
)

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "English Talking Bot is running."}


bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# Диалоговый обработчик
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


