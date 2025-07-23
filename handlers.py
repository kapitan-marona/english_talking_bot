# Импортируем необходимые модули Telegram Bot API и другие утилиты
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

# Словарь языков для преобразования названия в код ISO
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

# Настройки тона, грамматики и стиля для генерации системного промпта
TONE_CONFIG = {
    "A1-A2": {
        "casual": {
            "text": {
                "tone": "Friendly and humorous. Use emojis and slang, explain slang in {native_lang}.",
                "grammar": "Use simple grammar and short sentences in {learn_lang}.",
                "correction": "Explain mistakes in {native_lang}."
            },
            "voice": {
                "tone": "Friendly and humorous. Use slang, no emojis.",
                "grammar": "Use simple grammar and short sentences in {learn_lang}.",
                "correction": "Correct mistakes gently and explain in {learn_lang}."
            }
        },
        "formal": {
            "text": {
                "tone": "Relaxed, modern, open to dialogue, confident and formal. No slang or emojis.",
                "grammar": "Use simple grammar and short sentences in {learn_lang}.",
                "correction": "Explain mistakes in {native_lang}."
            },
            "voice": {
                "tone": "Relaxed, modern, open to dialogue, confident and formal. No slang or emojis.",
                "grammar": "Use simple grammar and short sentences in {learn_lang}.",
                "correction": "Correct mistakes gently and explain in {learn_lang}."
            }
        }
    },
    "B1-B2": {
        "casual": {
            "text": {
                "tone": "Friendly and humorous. Use emojis and slang.",
                "grammar": "Use richer grammar and vocabulary in {learn_lang}.",
                "correction": "Correct and explain mistakes in {learn_lang}."
            },
            "voice": {
                "tone": "Friendly and humorous. Use slang, no emojis.",
                "grammar": "Use richer grammar and vocabulary in {learn_lang}.",
                "correction": "Correct and explain mistakes in {learn_lang}."
            }
        },
        "formal": {
            "text": {
                "tone": "Relaxed, modern, open to dialogue, confident and formal. No slang or emojis.",
                "grammar": "Use richer grammar and vocabulary in {learn_lang}.",
                "correction": "Correct and explain mistakes in {learn_lang}."
            },
            "voice": {
                "tone": "Relaxed, modern, open to dialogue, confident and formal. No slang or emojis.",
                "grammar": "Use richer grammar and vocabulary in {learn_lang}.",
                "correction": "Correct and explain mistakes in {learn_lang}."
            }
        }
    }
}

# Генерация инструкций (system prompt) для ChatGPT в зависимости от настроек пользователя
def generate_system_prompt(interface_lang, level, style, learn_lang, voice_mode=False):
    native_lang = "Russian" if interface_lang == "Русский" else "English"
    mode = "voice" if voice_mode else "text"
    style_key = style.lower()

    config = TONE_CONFIG.get(level, {}).get(style_key, {}).get(mode)
    if not config:
        return f"You are a helpful assistant for learning {learn_lang}. Always respond in {learn_lang}."

    tone = config["tone"].format(native_lang=native_lang, learn_lang=learn_lang)
    grammar = config["grammar"].format(native_lang=native_lang, learn_lang=learn_lang)
    correction = config["correction"].format(native_lang=native_lang, learn_lang=learn_lang)

    return (
        f"You are a helpful assistant for learning {learn_lang}. "
        f"{tone} {grammar} {correction} "
        f"Always respond in {learn_lang}. Keep the conversation going with questions in context."
    )

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


# Основная логика общения: обрабатывает текстовые запросы и отвечает в зависимости от режима
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()

    if user_text == "📢 Voice mode":
    context.user_data["voice_mode"] = True

    # Обновляем system_prompt под голосовой режим
    context.user_data["system_prompt"] = generate_system_prompt(
        interface_lang=context.user_data.get("language", "English"),
        level=context.user_data.get("level", "B1-B2"),
        style=context.user_data.get("style", "Casual"),
        learn_lang=context.user_data.get("learn_lang", "English"),
        voice_mode=True
    )

    await update.message.reply_text("Voice mode enabled.", reply_markup=text_mode_button)
    return

elif user_text == "⌨️ Text mode":
    context.user_data["voice_mode"] = False

    # Обновляем system_prompt под текстовый режим
    context.user_data["system_prompt"] = generate_system_prompt(
        interface_lang=context.user_data.get("language", "English"),
        level=context.user_data.get("level", "B1-B2"),
        style=context.user_data.get("style", "Casual"),
        learn_lang=context.user_data.get("learn_lang", "English"),
        voice_mode=False
    )

    await update.message.reply_text("Text mode enabled.", reply_markup=voice_mode_button)
    return

    elif user_text == "⌨️ Text mode":
    context.user_data["voice_mode"] = False

    # Обновляем system_prompt под текстовый режим
    context.user_data["system_prompt"] = generate_system_prompt(
        interface_lang=context.user_data.get("language", "English"),
        level=context.user_data.get("level", "B1-B2"),
        style=context.user_data.get("style", "Casual"),
        learn_lang=context.user_data.get("learn_lang", "English"),
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
    chat_history.append({"role": "user", "content": user_text})
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
                print("[Voice mode] sending audio reply...")
                await speak_and_reply_google_tts(answer, update, context)
            except Exception:
                await update.message.reply_text(answer)
        else:
            await update.message.reply_text(answer, reply_markup=voice_mode_button if show_voice_button else None)

    except Exception as e:
        await update.message.reply_text(f"Ошибка генерации ответа: {e}")


async def speak_and_reply_google_tts(text: str, update: Update, context):
    level = context.user_data.get("level", "B1-B2")
    learn_lang = context.user_data.get("learn_lang", "English")
    speaking_rate = 0.85 if level == "A1-A2" else 1.0

    language_code = {
        "en": "en-US",
        "fr": "fr-FR",
        "es": "es-ES",
        "de": "de-DE",
        "it": "it-IT",
        "pt": "pt-PT",
        "sv": "sv-SE",
        "ru": "ru-RU"
    }.get(LANG_CODES.get(learn_lang, "en"), "en-US")
    voice_name = pick_best_voice(language_code)
    if not voice_name:
        language_code = "en-US"
        voice_name = pick_best_voice(language_code)

    print(f"[TTS] Using voice: {voice_name} for language_code: {language_code}")
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=voice_name,
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=speaking_rate
    )
    response = google_tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    print("[TTS] Audio response generated.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmpfile:
        tmpfile.write(response.audio_content)
        tmpfile_path = tmpfile.name

    async with aiofiles.open(tmpfile_path, "rb") as audio_file:
        await update.message.reply_voice(voice=audio_file)
    os.remove(tmpfile_path)


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


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Отмена.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END
