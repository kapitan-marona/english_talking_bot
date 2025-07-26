from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, ContextTypes
from .keyboards import learn_lang_markup, level_markup, style_keyboard_ru
from .chat import generate_system_prompt
from .messages import start_messages, level_messages, style_messages, welcome_messages

VALID_LEVELS = ["A1-A2", "B1-B2"]
VALID_STYLES = ["casual", "formal"]

def normalize(text):
    return text.strip().lower()
import random

LEARN_LANG, LEVEL, STYLE = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    user_locale = update.effective_user.language_code or "en"
    lang = "Русский" if user_locale.startswith("ru") else "English"
    context.user_data["language"] = lang

    await update.message.reply_text(
        random.choice(start_messages[lang]),
        reply_markup=learn_lang_markup
    )
    return LEARN_LANG

async def learn_lang_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["learn_lang"] = update.message.text
    lang = context.user_data["language"]
    await update.message.reply_text(
        random.choice(level_messages[lang]),
        reply_markup=level_markup
    )
    return LEVEL

async def level_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["level"] = update.message.text
    lang = context.user_data["language"]
    await update.message.reply_text(
        random.choice(style_messages[lang]),
        reply_markup=ReplyKeyboardMarkup(style_keyboard_ru, one_time_keyboard=True, resize_keyboard=True)
    )
    return STYLE

async def style_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["style"] = update.message.text
    context.user_data["voice_mode"] = False
    context.user_data["mode_button_shown"] = False

    # Вместо завершения диалога — ждём промокод
    await update.message.reply_text(
        "🎟 Перед началом — введи промокод для активации доступа:\n\n"
        "Если он у тебя есть — напиши команду /promo с кодом.\n"
        "Например: /promo code"
    )


    # ❗ Ничего не возвращаем — диалог остаётся незавершённым,
    # а обработка команды /promo происходит вне ConversationHandler
    return ConversationHandler.END  # ← сохраняем это, чтобы не зависнуть

async def promo_completed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("✅ Промокод принят! Напиши что-нибудь")
    prompt = generate_system_prompt(
        interface_lang=context.user_data["language"],
        level=context.user_data["level"],
        style=context.user_data["style"],
        learn_lang=context.user_data["learn_lang"],
        voice_mode=False
    )
    context.user_data["system_prompt"] = prompt
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Диалог отменён.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END
