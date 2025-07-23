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

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    context.user_data["voice_mode"] = True
    context.user_data["system_prompt"] = generate_system_prompt(
        interface_lang=context.user_data.get("language", "English"),
        level=context.user_data.get("level", "B1-B2"),
        style=context.user_data.get("style", "Casual"),
        learn_lang=context.user_data.get("learn_lang", "English"),
        voice_mode=True
    )

    lang_code = LANG_CODES.get(context.user_data.get("learn_lang", "English"), "en")
    if lang_code not in WHISPER_SUPPORTED_LANGS:
        lang = context.user_data.get("language", "English")
        await update.message.reply_text(UNSUPPORTED_LANGUAGE_MESSAGE.get(lang, UNSUPPORTED_LANGUAGE_MESSAGE["English"]))
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        ogg_path = f"{tmpdir}/voice.ogg"
        mp3_path = f"{tmpdir}/voice.mp3"

        file = await context.bot.get_file(voice.file_id)
        await file.download_to_drive(ogg_path)
        subprocess.run(["ffmpeg", "-i", ogg_path, mp3_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        try:
            with open(mp3_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text",
                    language=lang_code
                )

            class FakeMessage:
                def __init__(self, text, original):
                    self.text = text
                    self.chat_id = original.chat_id
                    self.chat = original.chat
                    self.from_user = original.from_user
                    self.message_id = original.message_id
                    self._original = original

                async def reply_text(self, *args, **kwargs):
                    return await self._original.reply_text(*args, **kwargs)

                async def reply_voice(self, *args, **kwargs):
                    return await self._original.reply_voice(*args, **kwargs)

            fake_message = FakeMessage(transcript.strip(), update.message)
            fake_update = Update(update.update_id, message=fake_message)
            await chat(fake_update, context)

        except Exception as e:
            await update.message.reply_text(f"Ошибка распознавания речи: {e}")
