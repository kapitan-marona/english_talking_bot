from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ConversationHandler, ContextTypes
from config import client
from google.cloud import texttospeech
import aiofiles
import tempfile
import os
import base64
import subprocess
from io import BytesIO

# Conversation steps
LEARN_LANG, LEVEL, STYLE = range(3)

# Interface and language selection
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
}  # Whisper reliably supports these

UNSUPPORTED_LANGUAGE_MESSAGE = {
    "Русский": "Этот язык пока не поддерживается для распознавания речи. Вы можете продолжать использовать голосовой режим, но отправлять вопросы нужно в текстовом виде. Попробуйте голосовой ввод на клавиатуре — он преобразует вашу речь в текст, а бот ответит голосом!",
    "English": "This language is not yet supported for voice recognition. You can keep using voice mode, but please send your questions as text. Try using voice input on your keyboard — it will convert your speech to text, and the bot will reply with voice!"
}

# ... остальной код остаётся без изменений ...
