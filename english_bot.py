import os
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)
from config import TELEGRAM_TOKEN
from handlers import start, lang_choice, level_choice, style_choice, chat, cancel, voice_handler, LANG, LEVEL, STYLE

# Получаем порт и URL от Render
PORT = int(os.environ.get("PORT", 8443))
APP_URL = os.environ.get("RENDER_EXTERNAL_URL")

# Создаём Telegram приложение
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# Настраиваем ConversationHandler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, lang_choice)],
        LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, level_choice)],
        STYLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, style_choice)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Добавляем все обработчики
app.add_handler(conv_handler)
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
app.add_handler(MessageHandler(filters.VOICE, voice_handler))

# Запускаем webhook (БЕЗ if __name__ == "__main__")
print(f"🌐 Listening for Telegram updates at: {APP_URL}/webhook")

app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    webhook_url=f"{APP_URL}/webhook"
)


app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    webhook_url=f"{APP_URL}/webhook"
)
