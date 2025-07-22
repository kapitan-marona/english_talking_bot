from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ConversationHandler, ContextTypes
from config import client
from google.cloud import texttospeech
import tempfile
import os
import base64
import subprocess
import locale

LANG_LEVEL, STYLE, TARGET_LANG = range(3)

# Языки, доступные для изучения
TARGET_LANGUAGES = [
    "English", "French", "Spanish", "German", "Italian",
    "Finnish", "Norwegian", "Swedish", "Russian", "Portuguese"
]

target_lang_keyboard = [[lang] for lang in TARGET_LANGUAGES]
target_lang_markup = ReplyKeyboardMarkup(target_lang_keyboard, one_time_keyboard=True, resize_keyboard=True)

level_keyboard = [["A1-A2", "B1-B2"]]
style_keyboard = [["Casual", "Formal"]]
level_markup = ReplyKeyboardMarkup(level_keyboard, one_time_keyboard=True, resize_keyboard=True)
style_markup = ReplyKeyboardMarkup(style_keyboard, one_time_keyboard=True, resize_keyboard=True)

voice_mode_button = ReplyKeyboardMarkup(
    [[KeyboardButton("🗣️ Voice mode")]],
    resize_keyboard=True
)
text_mode_button = ReplyKeyboardMarkup(
    [[KeyboardButton("⌨️ Text mode")]],
    resize_keyboard=True
)

def init_google_tts_client():
    encoded_key = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_BASE64")
    if not encoded_key:
        raise EnvironmentError("Environment variable GOOGLE_APPLICATION_CREDENTIALS_BASE64 is not set")
    json_key = base64.b64decode(encoded_key)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmpfile:
        tmpfile.write(json_key)
        tmpfile_path = tmpfile.name
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmpfile_path
    client = texttospeech.TextToSpeechClient()
    return client, tmpfile_path

google_tts_client, tmp_key_path = init_google_tts_client()

def get_device_language(update: Update):
    lang_code = update.effective_user.language_code or "en"
    return locale.languages.get(lang_code.split("-")[0], "English")

def generate_system_prompt(native_language, target_language, level, style):
    base = f"You are a helpful assistant helping the user practice {target_language}."

    tone_instruction = ""
    grammar_instruction = ""
    correction_instruction = ""

    if style.lower() == "casual":
        tone_instruction = (
            "Your tone is relaxed and friendly. Use informal expressions where appropriate. "
            "Be supportive and cheerful."
        )
        correction_instruction = (
            f"If the user makes mistakes in {target_language}, gently correct them. "
            f"Use {native_language} to explain only when needed."
        )
    elif style.lower() == "formal":
        tone_instruction = (
            "Your tone is professional and respectful. Avoid slang."
        )
        correction_instruction = (
            f"If the user makes mistakes in {target_language}, correct them clearly and professionally. "
            f"Use {native_language} to help them understand if needed."
        )

    if level == "A1-A2":
        grammar_instruction = (
            "Use short and simple sentences. Avoid complex grammar."
        )
    elif level == "B1-B2":
        grammar_instruction = (
            "You may use more advanced grammar, longer sentences, and richer vocabulary."
        )

    return (
        f"{base} The user's native language is {native_language}. "
        f"{tone_instruction} {grammar_instruction} {correction_instruction} "
        f"Always respond in {target_language}."
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    context.user_data["native_language"] = get_device_language(update)

    await update.message.reply_text(
        "Which language do you want to practice?",
        reply_markup=target_lang_markup
    )
    return TARGET_LANG

async def target_lang_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["target_language"] = update.message.text
    await update.message.reply_text("Choose your level:", reply_markup=level_markup)
    return LANG_LEVEL

async def level_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["level"] = update.message.text
    await update.message.reply_text("Choose your communication style:", reply_markup=style_markup)
    return STYLE

async def style_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    style = update.message.text
    context.user_data["style"] = style

    lang = context.user_data["target_language"]
    welcome_msg = {
        "Casual": "Awesome! Let's just chat 😊 What would you like to talk about?",
        "Formal": "Great! We're set for a formal conversation. What topic shall we begin with?"
    }.get(style, "Let's begin!")

    context.user_data["voice_mode"] = False
    context.user_data["mode_button_shown"] = False

    prompt = generate_system_prompt(
        context.user_data["native_language"],
        context.user_data["target_language"],
        context.user_data["level"],
        context.user_data["style"]
    )
    context.user_data["system_prompt"] = prompt

    await update.message.reply_text(welcome_msg, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END
