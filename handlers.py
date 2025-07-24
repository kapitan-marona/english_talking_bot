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

    if level == "A1-A2":
        language_level_note = "Use short, simple sentences and basic vocabulary suitable for a beginner (A1-A2 level)."
    elif level == "B1-B2":
        language_level_note = "Use richer vocabulary and intermediate grammar structures suitable for B1-B2 learners."
    else:
        language_level_note = ""

    if native_lang == "Russian":
        clarification_note = "When appropriate, briefly explain difficult words or expressions in Russian using simple terms."
    elif native_lang == "English":
        clarification_note = "When appropriate, briefly explain difficult words or expressions in English using simple terms."
    else:
        clarification_note = ""

    if style.lower() == "casual":
        return (
            f"You are a funny, friendly, and engaging conversation partner who helps people learn {learn_lang}. "
            f"Always respond in {learn_lang}. Use slang, jokes, emoji, and a casual tone. Your job is to make the conversation feel natural, fun, and light-hearted. "
            f"Even if a user makes a mistake, respond with kindness and a playful tone. {language_level_note} {clarification_note}"
        )
    elif style.lower() == "formal":
        return (
            f"You are a professional and engaging language tutor helping people practice {learn_lang}. "
            f"Always respond in {learn_lang}. Use polite, clear, and structured responses. Maintain a professional tone: no emojis, no slang. "
            f"However, keep the conversation lively, intelligent, and friendly. Subtly use humor and positivity to encourage the learner. {language_level_note} {clarification_note}"
        )
    else:
        return (
            f"You are a helpful assistant for learning {learn_lang}. Always respond in {learn_lang}. {language_level_note} {clarification_note}"
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

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Диалог отменён.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()

    if user_text.lower() in ["🔊 voice mode", "📢 voice mode", "voice mode"]:
        context.user_data["voice_mode"] = True
        context.user_data["system_prompt"] = generate_system_prompt(
            context.user_data.get("language", "English"),
            context.user_data.get("level", "B1-B2"),
            context.user_data.get("style", "Casual"),
            context.user_data.get("learn_lang", "English"),
            voice_mode=True
        )
        await update.message.reply_text("Voice mode enabled.", reply_markup=text_mode_button)
        return

    if user_text.lower() in ["⌨️ text mode", "text mode"]:
        context.user_data["voice_mode"] = False
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
            await speak_and_reply(answer, update, context)
        else:
            await update.message.reply_text(answer, reply_markup=text_mode_button if context.user_data.get("voice_mode") else voice_mode_button)

    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

async def speak_and_reply(text, update, context):
    lang_code = LANG_CODES.get(context.user_data.get("learn_lang", "English"), "en")
    language_code = {
        "en": "en-US", "fr": "fr-FR", "es": "es-ES", "de": "de-DE", "it": "it-IT",
        "pt": "pt-PT", "sv": "sv-SE", "ru": "ru-RU"
    }.get(lang_code, "en-US")
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code=language_code, ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    tts_client = texttospeech.TextToSpeechClient()
    response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tmp.write(response.audio_content)
        path = tmp.name

    async with aiofiles.open(path, "rb") as audio:
        await update.message.reply_voice(voice=audio)
    os.remove(path)

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    lang_code = LANG_CODES.get(context.user_data.get("learn_lang", "English"), "en")

    if lang_code not in WHISPER_SUPPORTED_LANGS:
        lang = context.user_data.get("language", "English")
        await update.message.reply_text(UNSUPPORTED_LANGUAGE_MESSAGE.get(lang))
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        ogg_path = f"{tmpdir}/voice.ogg"
        mp3_path = f"{tmpdir}/voice.mp3"
        file = await context.bot.get_file(voice.file_id)
        await file.download_to_drive(ogg_path)
        subprocess.run(["ffmpeg", "-i", ogg_path, mp3_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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

        fake_update = Update(update.update_id, message=FakeMessage(transcript.strip(), update.message))
        await chat(fake_update, context)
