from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler, ConversationHandler
from .conversation import LEARN_LANG, LEVEL, STYLE, learn_lang_choice, level_choice, style_choice
from .keyboards import main_menu_keyboard, learn_lang_markup, level_markup, style_keyboard_ru
from .chat import generate_system_prompt

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📋 Главное меню:", reply_markup=main_menu_keyboard)

async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "change_language":
        await query.edit_message_text("Выбери язык для изучения:", reply_markup=learn_lang_markup)
        return LEARN_LANG

    if data == "change_level_style":
        await query.edit_message_text("Выбери уровень владения языком:", reply_markup=level_markup)
        return LEVEL

    if data == "toggle_mode":
        voice_mode = context.user_data.get("voice_mode", False)
        context.user_data["voice_mode"] = not voice_mode

        prompt = generate_system_prompt(
            context.user_data.get("language", "English"),
            context.user_data.get("level", "B1-B2"),
            context.user_data.get("style", "Casual"),
            context.user_data.get("learn_lang", "English"),
            voice_mode=not voice_mode
        )
        context.user_data["system_prompt"] = prompt

        await query.edit_message_text(
            "🔁 Переключено на *{} режим*.".format("Голосовой" if not voice_mode else "Текстовый"),
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    if data == "reset":
        context.user_data.clear()
        await query.edit_message_text("♻️ Настройки сброшены. Отправьте /start для начала заново.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    return ConversationHandler.END
