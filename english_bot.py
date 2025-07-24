from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
from handlers import (
    start, learn_lang_choice, level_choice, style_choice,
    chat, voice_handler, cancel
)
from config import token

application = Application.builder().token(token).build()
app = FastAPI()

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
application.add_handler(MessageHandler(filters.VOICE, voice_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

@app.post("/webhook")
async def webhook_handler(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"status": "ok"}
