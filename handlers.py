from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ConversationHandler, ContextTypes
from config import client
from google.cloud import texttospeech
import aiofiles
import tempfile
import os
import subprocess

LEARN_LANG, LEVEL, STYLE = range(3)

voice_mode_button = ReplyKeyboardMarkup(
    [[KeyboardButton("🔊 Voice mode")]], resize_keyboard=True
)
text_mode_button = ReplyKeyboardMarkup(
    [[KeyboardButton("⌨️ Text mode")]], resize_keyboard=True
)

learn_lang_keyboard = [
    ["English", "French", "Spanish", "German", "Italian"],
    ["Finnish", "Norwegian", "Swedish", "Russian", "Portuguese"]
]
learn_lang_markup = ReplyKeyboardMarkup(learn_lang_keyboard, one_time_keyboard=True, resize_keyboard=True)

level_keyboard = [["A1-A2", "B1-B2"]]
level_markup = ReplyKeyboardMarkup(level_keyboard, one_time_keyboard=True, resize_keyboard=True)

style_keyboard_ru = [["Casual", "Formal"]]

LANG_CODES = {
    "English": "en", "French": "fr", "Spanish": "es", "German": "de", "Italian": "it",
    "Portuguese": "pt", "Finnish": "fi", "Norwegian": "no", "Swedish": "sv", "Russian": "ru"
}

WHISPER_SUPPORTED_LANGS = {
    "en", "fr", "es", "de", "it", "pt", "sv", "ru"
}

UNSUPPORTED_LANGUAGE_MESSAGE = {
    "Русский": "Этот язык пока не поддерживается для распознавания речи. Вы можете продолжать использовать голосовой режим, но отправлять вопросы нужно в текстовом виде. Попробуйте голосовой ввод на клавиатуре — он преобразует вашу речь в текст, а бот ответит голосом!",
    "English": "This language is not yet supported for voice recognition. You can keep using voice mode, but please send your questions as text. Try using voice input on your keyboard — it will convert your speech to text, and the bot will reply with voice!"
}

def generate_system_prompt(interface_lang, level, style, learn_lang, voice_mode=False):
    native_lang = "Russian" if interface_lang == "Русский" else "English"
    mode = "voice" if voice_mode else "text"
    return f"You are a helpful assistant for learning {learn_lang}. Always respond in {learn_lang}."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    user_locale = update.effective_user.language_code or "en"
    lang = "Русский" if user_locale.startswith("ru") else "English"
    context.user_data["language"] = lang

    await update.message.reply_text(
        "Выбери изучаемый язык:" if lang == "Русский" else "Choose a language to learn:",
        reply_markup=learn_lang_markup
    )
    return LEARN_LANG

async def learn_lang_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["learn_lang"] = update.message.text
    lang = context.user_data["language"]
    await update.message.reply_text(
        "Выбери уровень языка:" if lang == "Русский" else "Choose your level:",
        reply_markup=level_markup
    )
    return LEVEL

async def level_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["level"] = update.message.text
    lang = context.user_data["language"]
    await update.message.reply_text(
        "Выбери стиль общения:" if lang == "Русский" else "Choose your conversation style:",
        reply_markup=ReplyKeyboardMarkup(style_keyboard_ru, one_time_keyboard=True, resize_keyboard=True)
    )
    return STYLE

async def style_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["style"] = update.message.text
    context.user_data["voice_mode"] = False
    context.user_data["mode_button_shown"] = False

    lang = context.user_data["language"]
    msg = (
        "Отлично, давай просто поболтаем! 😎 С чего хочешь начать?"
        if lang == "Русский" else
        "Great! Let's chat. What would you like to start with?"
    )
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

    prompt = generate_system_prompt(
        interface_lang=context.user_data["language"],
        level=context.user_data["level"],
        style=context.user_data["style"],
        learn_lang=context.user_data["learn_lang"],
        voice_mode=False
    )
    context.user_data["system_prompt"] = prompt
    return ConversationHandler.END

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip().lower()

    if user_text in ["📢 voice mode", "🔊 voice mode", "voice mode"]:
        context.user_data["voice_mode"] = True
        context.user_data["mode_button_shown"] = True
        context.user_data["system_prompt"] = generate_system_prompt(
            context.user_data.get("language", "English"),
            context.user_data.get("level", "B1-B2"),
            context.user_data.get("style", "Casual"),
            context.user_data.get("learn_lang", "English"),
            voice_mode=True
        )
        await update.message.reply_text("Voice mode enabled.", reply_markup=text_mode_button)
        return

    elif user_text in ["⌨️ text mode", "text mode"]:
        context.user_data["voice_mode"] = False
        context.user_data["mode_button_shown"] = True
        context.user_data["system_prompt"] = generate_system_prompt(
            context.user_data.get("language", "English"),
            context.user_data.get("level", "B1-B2"),
            context.user_data.get("style", "Casual"),
            context.user_data.get("learn_lang", "English"),
            voice_mode=False
        )
        await update.message.reply_text("Text mode enabled.", reply_markup=voice_mode_button)
        return

    if "system_prompt" not in context.user_data:
        await update.message.reply_text("/start, please.")
        return

    show_voice_button = False
    if not context.user_data.get("voice_mode") and not context.user_data.get("mode_button_shown", False):
        context.user_data["mode_button_shown"] = True
        show_voice_button = True

    system_prompt = context.user_data["system_prompt"]
    chat_history = context.user_data.setdefault("chat_history", [])
    chat_history.append({"role": "user", "content": update.message.text.strip()})
    context.user_data["chat_history"] = chat_history[-40:]

    messages = [{"role": "system", "content": system_prompt}] + context.user_data["chat_history"]

    try:
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7
        )
        answer = completion.choices[0].message.content
        context.user_data["chat_history"].append({"role": "assistant", "content": answer})

        if context.user_data.get("voice_mode"):
            try:
                await speak_and_reply_google_tts(answer, update, context)
            except Exception:
                await update.message.reply_text(answer)
        else:
            await update.message.reply_text(answer, reply_markup=voice_mode_button if show_voice_button else None)

    except Exception as e:
        await update.message.reply_text(f"Ошибка генерации ответа: {e}")
