from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ConversationHandler, ContextTypes
from config import client
from google.cloud import texttospeech

# === Получаем список всех доступных голосов один раз ===
ALL_VOICES = {}
def load_available_voices():
    global ALL_VOICES
    voices = google_tts_client.list_voices().voices
    for v in voices:
        for lang_code in v.language_codes:
            ALL_VOICES.setdefault(lang_code, []).append(v)

google_tts_client, tmp_key_path = init_google_tts_client()

load_available_voices()

import tempfile
import os
import base64
import subprocess

# Шаги для ConversationHandler
LEARN_LANG, LEVEL, STYLE = range(3)

# Кнопки режимов
voice_mode_button = ReplyKeyboardMarkup(
    [[KeyboardButton("🗣️ Voice mode")]],
    resize_keyboard=True
)
text_mode_button = ReplyKeyboardMarkup(
    [[KeyboardButton("⌨️ Text mode")]],
    resize_keyboard=True
)

# Изучаемые языки (без флажков)
learn_lang_keyboard = [
    ["English", "French", "Spanish", "German", "Italian"],
    ["Finnish", "Norwegian", "Swedish", "Russian", "Portuguese"]
]
learn_lang_markup = ReplyKeyboardMarkup(learn_lang_keyboard, one_time_keyboard=True, resize_keyboard=True)

level_keyboard = [["A1-A2", "B1-B2"]]
level_markup = ReplyKeyboardMarkup(level_keyboard, one_time_keyboard=True, resize_keyboard=True)

style_keyboard_ru = [["Разговорный", "Деловой"]]

# Google TTS
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


def generate_system_prompt(interface_lang, level, style, learn_lang):
    base = f"You are a {learn_lang} language assistant helping a user practice {learn_lang}."
    native_lang = "Russian" if interface_lang == "Русский" else "English"

    tone_instruction = ""
    correction_instruction = ""
    grammar_instruction = ""

    if style.lower() in ["разговорный"]:
        tone_instruction = (
            "Your tone is relaxed, friendly, like an old friend. "
            "Use slang, emojis, and contractions where appropriate. "
            f"At level A1-A2, keep slang minimal and explain it in {native_lang}."
        )
        correction_instruction = (
            f"If the user makes mistakes in {learn_lang}, gently correct them in a friendly way, "
            f"explaining corrections clearly in {native_lang}."
        )
    elif style.lower() in ["деловой"]:
        tone_instruction = (
            "Your tone is formal, polite, and professional. Avoid slang and contractions."
        )
        correction_instruction = (
            f"If the user makes mistakes in {learn_lang}, correct them formally and politely."
        )

    if level == "A1-A2":
        grammar_instruction = (
            "Use short, simple sentences. Avoid complex grammar. "
            f"Keep responses easy to understand for a beginner in {learn_lang}."
        )
    elif level == "B1-B2":
        grammar_instruction = (
            "You may use more advanced grammar, longer sentences, and richer vocabulary. "
            f"Adjust your tone accordingly in {learn_lang}."
        )

    return (
        f"{base} The user's native language is {native_lang}. "
        f"{tone_instruction} {grammar_instruction} {correction_instruction} "
        f"Always respond in {learn_lang}. Ask follow-up questions to keep the conversation going."
    )

def pick_best_voice(language_code: str) -> str:
    voices = ALL_VOICES.get(language_code, [])
    # Ищем Wavenet, потом Standard, потом любой
    for voice in voices:
        if "Wavenet" in voice.name:
            return voice.name
    for voice in voices:
        if "Standard" in voice.name:
            return voice.name
    return voices[0].name if voices else None


# === Хендлеры ===

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
    style = update.message.text
    context.user_data["style"] = style
    lang = context.user_data["language"]

    welcome_msg = (
        "Отлично, давай просто поболтаем! 😎 С чего хочешь начать?"
        if lang == "Русский" and style.lower() == "разговорный" else
        "Круто! Намечается деловой разговор. С чего начнем?"
        if lang == "Русский" else
        "Great! Let's chat. What would you like to start with?"
    )

    context.user_data["voice_mode"] = False
    context.user_data["mode_button_shown"] = False

    await update.message.reply_text(welcome_msg, reply_markup=ReplyKeyboardRemove())

    prompt = generate_system_prompt(
        context.user_data["language"],
        context.user_data["level"],
        context.user_data["style"],
        context.user_data["learn_lang"]
    )
    context.user_data["system_prompt"] = prompt
    return ConversationHandler.END

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()

    if user_text == "🗣️ Voice mode":
        context.user_data["voice_mode"] = True
        await update.message.reply_text("Voice mode enabled. Talk to me!", reply_markup=text_mode_button)
        return
    elif user_text == "⌨️ Text mode":
        context.user_data["voice_mode"] = False
        await update.message.reply_text("Text mode enabled. Talk to me!", reply_markup=voice_mode_button)
        return

    if "system_prompt" not in context.user_data:
        await update.message.reply_text("Пожалуйста, начни сначала с команды /start.")
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

    lang_map = {
        "English": "en-US", "French": "fr-FR", "Spanish": "es-ES", "German": "de-DE", "Italian": "it-IT",
        "Finnish": "fi-FI", "Norwegian": "no-NO", "Swedish": "sv-SE", "Russian": "ru-RU",
        "Portuguese": "pt-PT",  # можешь добавить "pt-BR", если нужно
    }
    language_code = lang_map.get(learn_lang, "en-US")
    voice_name = pick_best_voice(language_code)

    if not voice_name:
        print(f"[TTS] ⚠️ No voice found for {language_code}, using fallback en-US")
        language_code = "en-US"
        voice_name = pick_best_voice("en-US")

    print(f"[TTS] ✅ Using voice {voice_name} for {language_code}")

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

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmpfile:
        tmpfile.write(response.audio_content)
        tmpfile_path = tmpfile.name

    with open(tmpfile_path, "rb") as voice_file:
        await update.message.reply_voice(voice=voice_file)
    os.remove(tmpfile_path)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Отмена.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END
