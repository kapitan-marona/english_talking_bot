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
    await query.edit_message_text("Меню пока пустое. Скоро тут появятся новые возможности! 🛠️")
    return ConversationHandler.END

