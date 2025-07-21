from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler
from handlers import (
    start, lang_choice, level_choice, style_choice,
    chat, cancel, voice_handler, LANG, LEVEL, STYLE
)
import os

TOKEN = os.getenv("BOT_TOKEN")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

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

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
