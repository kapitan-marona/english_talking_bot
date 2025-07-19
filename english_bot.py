from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)
from config import TELEGRAM_TOKEN
from handlers import start, lang_choice, level_choice, style_choice, chat, cancel, voice_handler, LANG, LEVEL, STYLE

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, lang_choice)],
            LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, level_choice)],
            STYLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, style_choice)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))

    print("Бот запущен...")
    app.run_polling()
