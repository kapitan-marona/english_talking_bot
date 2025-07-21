from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ConversationHandler, ContextTypes
from google.cloud import texttospeech
import tempfile
import os
import base64
import subprocess

# Константы состояний разговора
LANG, LEVEL, STYLE = range(3)

# Клавиатуры для выбора режима и параметров
voice_mode_button = ReplyKeyboardMarkup(
    [[KeyboardButton("🗣️ Voice mode")]],
    resize_keyboard=True
)
text_mode_button = ReplyKeyboardMarkup(
    [[KeyboardButton("⌨️ Text mode")]],
    resize_keyboard=True
)

lang_keyboard = [["Русский", "عربي"]]
level_keyboard = [["A1-A2", "B1-B2"]]
style_keyboard_ru = [["Разговорный", "Деловой"]]
style_keyboard_ar = [["عامي", "رسمي"]]

lang_markup = ReplyKeyboardMarkup(lang_keyboard, one_time_keyboard=True, resize_keyboard=True)
level_markup = ReplyKeyboardMarkup(level_keyboard, one_time_keyboard=True, resize_keyboard=True)

# Инициализация клиента Google TTS из base64-переменной окружения
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

def generate_system_prompt(language, level, style):
    # Здесь твоя логика генерации системного prompt
    # Например:
    return f"System prompt for {language} language, level {level}, style {style}"

# Пример обработчиков — здесь нужно вставить твои реализации:

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Привет! Выбери язык / Choose a language:",
        reply_markup=lang_markup
    )
    return LANG

async def lang_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_lang = update.message.text
    context.user_data["language"] = user_lang
    await update.message.reply_text(
        "Выбери уровень / Choose a level:",
        reply_markup=level_markup
    )
    return LEVEL

async def level_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_level = update.message.text
    context.user_data["level"] = user_level
    language = context.user_data.get("language")
    if language == "Русский":
        style_markup = ReplyKeyboardMarkup(style_keyboard_ru, one_time_keyboard=True, resize_keyboard=True)
    else:
        style_markup = ReplyKeyboardMarkup(style_keyboard_ar, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Выбери стиль / Choose a style:",
        reply_markup=style_markup
    )
    return STYLE

async def style_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_style = update.message.text
    context.user_data["style"] = user_style
    await update.message.reply_text(
        "Теперь можешь отправить сообщение в чат!",
        reply_markup=ReplyKeyboardRemove()
    )
    # Можно инициализировать prompt и т.д. здесь
    return ConversationHandler.END

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Твоя логика общения с ботом
    await update.message.reply_text("Обработка сообщения...")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Диалог отменён.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def speak_and_reply_google_tts(text: str, update: Update):
    input_text = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="ru-RU", ssml_gender=texttospeech.SsmlVoiceGender.FEMALE)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = google_tts_client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as out:
        out.write(response.audio_content)
        audio_path = out.name
    
    with open(audio_path, "rb") as audio_file:
        await update.message.reply_voice(audio_file)
    
    os.remove(audio_path)

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обработка голосового сообщения
    await update.message.reply_text("Голосовое сообщение получено и обработано.")
