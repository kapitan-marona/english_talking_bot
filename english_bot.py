import os
from aiohttp import web
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from config import TELEGRAM_TOKEN
from handlers import start, lang_choice, level_choice, style_choice, chat, cancel, voice_handler, LANG, LEVEL, STYLE

PORT = int(os.environ.get("PORT", 8443))
APP_URL = os.environ.get("RENDER_EXTERNAL_URL")

# Создаем Telegram приложение
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# Conversation handler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, lang_choice)],
        LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, level_choice)],
        STYLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, style_choice)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Обработчики
app.add_handler(conv_handler)
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
app.add_handler(MessageHandler(filters.VOICE, voice_handler))


# Aiohttp webhook handler
async def handle_webhook(request: web.Request) -> web.Response:
    await app.update_queue.put(await request.json())
    return web.Response(text="OK")


# Aiohttp сервер
async def main():
    app_ = web.Application()
    app_.add_routes([web.post("/webhook", handle_webhook)])

    await app.initialize()
    await app.start()
    await web._run_app(app_, host="0.0.0.0", port=PORT)
    await app.stop()
    await app.shutdown()
    await app.post_shutdown()

import asyncio
asyncio.run(main())
