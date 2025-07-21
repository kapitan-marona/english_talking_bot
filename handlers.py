from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ConversationHandler, ContextTypes
from config import client
from google.cloud import texttospeech
import tempfile
import os
import base64
import subprocess

LANG, LEVEL, STYLE = range(3)

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

# Инициализация Google TTS клиента через Base64 ключ из переменной окружения
def init_google_tts_client():
    encoded_key = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_BASE64")
    if not encoded_key:
        raise EnvironmentError("Environment variable GOOGLE_APPLICATION_CREDENTIALS_BASE64 is not set")
    json_key = base64.b64decode(encoded_key)
    # Временный файл с ключом
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmpfile:
        tmpfile.write(json_key)
        tmpfile_path = tmpfile.name
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmpfile_path
    client = texttospeech.TextToSpeechClient()
    return client, tmpfile_path

google_tts_client, tmp_key_path = init_google_tts_client()


def generate_system_prompt(language, level, style):
    base = "You are an English language assistant helping a user practice English."
    native_lang = "Russian" if language == "Русский" else "Arabic"

    tone_instruction = ""
    grammar_instruction = ""
    correction_instruction = ""

    if style.lower() in ["разговорный", "عامي"]:
        tone_instruction = (
            "Your tone is relaxed, friendly, like an old friend. "
            "Use slang, emojis, and contractions where appropriate. "
            "At level A1-A2, keep slang minimal and explain it in the user's native language."
        )
        correction_instruction = (
            "If the user makes mistakes in English, gently correct them in a friendly way, "
            "explaining corrections clearly."
        )
    elif style.lower() in ["деловой", "رسمي"]:
        tone_instruction = (
            "Your tone is formal, polite, and professional. "
            "Avoid slang and contractions."
        )
        correction_instruction = (
            "If the user makes mistakes in English, correct them formally and politely."
        )

    if level == "A1-A2":
        grammar_instruction = (
            "Use short, simple sentences. Avoid complex grammar. "
            "Keep responses easy to understand for a beginner."
        )
    elif level == "B1-B2":
        grammar_instruction = (
            "You may use more advanced grammar, longer sentences, and richer vocabulary. "
            "Adjust your tone accordingly."
        )

    return (
        f"{base} The user's native language is {native_lang}. "
        f"{tone_instruction} {grammar_instruction} {correction_instruction} "
        "Always respond in English unless you need to explain something in the user's native language. "
        "Ask follow-up questions to keep the conversation going."
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()  # очищаем всё
    await update.message.reply_text(
        "Выбери язык интерфейса /اختر لغة الواجهة:",
        reply_markup=lang_markup
    )
    return LANG


async def lang_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = update.message.text
    context.user_data["language"] = lang

    context.user_data["style_markup"] = ReplyKeyboardMarkup(
        style_keyboard_ru if lang == "Русский" else style_keyboard_ar,
        one_time_keyboard=True, resize_keyboard=True
    )

    await update.message.reply_text(
        "Выбери уровень языка:" if lang == "Русский" else "اختر مستوى اللغة:",
        reply_markup=level_markup
    )
    return LEVEL


async def level_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["level"] = update.message.text

    await update.message.reply_text(
        "Выбери стиль общения:" if context.user_data["language"] == "Русский" else "اختر أسلوب المحادثة:",
        reply_markup=context.user_data["style_markup"]
    )
    return STYLE


async def style_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    style = update.message.text
    context.user_data["style"] = style

    language = context.user_data["language"]

    welcome_msg = (
        "Отлично, давай просто поболтаем! 😎 С чего хочешь начать?"
        if language == "Русский" and style.lower() == "разговорный" else
        "Круто! Намечается деловой разговор. С чего начнем?"
        if language == "Русский" else
        "تمام! هنتكلم بأسلوب عامي ومرِح. 😎 تحب نتكلم عن ايه بالإنجليزي؟"
        if style.lower() == "عامي" else
        "حسناً، سنتحدث بأسلوب رسمي. ما الموضوع الذي تود البدء به باللغة الإنجليزية؟"
    )

    context.user_data["voice_mode"] = False  # режим по умолчанию — текст
    context.user_data["mode_button_shown"] = False  # кнопка голосового режима ещё не показана

    await update.message.reply_text(
        welcome_msg,
        reply_markup=ReplyKeyboardRemove()  # ⬅️ удаляем клавиатуру с кнопками стиля
    )

    system_prompt = generate_system_prompt(language, context.user_data["level"], style)
    context.user_data["system_prompt"] = system_prompt

    return ConversationHandler.END


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()

    # Переключение режима
    if user_text == "🗣️ Voice mode":
        context.user_data["voice_mode"] = True
        await update.message.reply_text(
            "Voice mode enabled. Talk to me! I will respond with voice.",
            reply_markup=text_mode_button
        )
        return
    elif user_text == "⌨️ Text mode":
        context.user_data["voice_mode"] = False
        await update.message.reply_text(
            "Text mode enabled. Talk to me! I will respond with text.",
            reply_markup=voice_mode_button
        )
        return

    # Проверка на наличие system_prompt
    if "system_prompt" not in context.user_data:
        await update.message.reply_text(
            "Пожалуйста, начни сначала с команды / يرجى البدء بالأمر /start."
        )
        return

    # Добавляем кнопку голосового режима после первого ответа пользователя в текстовом режиме
    if not context.user_data.get("voice_mode") and not context.user_data.get("mode_button_shown", False):
        context.user_data["mode_button_shown"] = True
        show_voice_button = True
    else:
        show_voice_button = False

    # Сбор сообщений
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

        # Отправка ответа — голосом или текстом
        if context.user_data.get("voice_mode"):
            # Голосовой ответ с кнопкой "⌨️ Text mode"
            try:
                await speak_and_reply_google_tts(answer, update)
            except Exception:
                await update.message.reply_text(answer)
            # Убрали вопрос "Хочешь вернуться в текстовый режим?"
        else:
            # Текстовый ответ, показываем кнопку голосового режима, если ещё не показывали
            if show_voice_button:
                await update.message.reply_text(answer, reply_markup=voice_mode_button)
            else:
                await update.message.reply_text(answer)

    except Exception as e:
        await update.message.reply_text(f"Ошибка генерации ответа: {e}")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Отмена.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def speak_and_reply_google_tts(text: str, update: Update):
    try:
        synthesis_input = texttospeech.SynthesisInput(text=text)

        # Настройки голоса и аудио
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        response = google_tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmpfile:
            tmpfile.write(response.audio_content)
            tmpfile_path = tmpfile.name

        with open(tmpfile_path, "rb") as voice_file:
            await update.message.reply_voice(voice=voice_file)

        os.remove(tmpfile_path)

    except Exception as e:
        await update.message.reply_text(f"Ошибка генерации голоса: {e}")


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice

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
                    response_format="text"
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

            fake_message = FakeMessage(transcript, update.message)
            fake_update = Update(update.update_id, message=fake_message)

            await chat(fake_update, context)

        except Exception as e:
            await update.message.reply_text(f"Ошибка распознавания речи: {e}")

