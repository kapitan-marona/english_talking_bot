from telegram import Update
from telegram.ext import ContextTypes
from config import client
from .voice import speak_and_reply
from .keyboards import voice_mode_button, text_mode_button
import asyncio

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

    if voice_mode:
        clarification_note = f"When appropriate, briefly explain difficult words or expressions in {learn_lang} using simple terms."
    else:
        if native_lang == "Russian":
            clarification_note = "When appropriate, briefly explain difficult words or expressions in Russian using simple terms."
        else:
            clarification_note = "When appropriate, briefly explain difficult words or expressions in English using simple terms."

    if style.lower() == "casual":
        if voice_mode:
            return (
                f"You are in voice mode. You are a fun and engaging conversation partner helping people learn {learn_lang}. "
                f"Always respond in {learn_lang}. Respond as if your message will be read aloud using text-to-speech. "
                f"Use slang and a playful tone, but do not use emojis. Keep the conversation light-hearted and friendly. "
                f"{language_level_note} {clarification_note}"
            )
        else:
            return (
                f"You are in text mode. You are a funny, friendly, and engaging conversation partner who helps people learn {learn_lang}. "
                f"Always respond in {learn_lang}. Use slang, jokes, emoji, and a casual tone. "
                f"Your job is to make the conversation feel natural, fun, and light-hearted. "
                f"Even if a user makes a mistake, respond with kindness and a playful tone. {language_level_note} {clarification_note}"
            )
    elif style.lower() == "formal":
        if voice_mode:
            return (
                f"You are in voice mode. You are a professional and engaging language tutor helping people practice {learn_lang}. "
                f"Always respond in {learn_lang}. Respond as if your message will be read aloud using text-to-speech. "
                f"Use polite, clear, and structured responses. Maintain a professional tone: no emojis, no slang. "
                f"Keep your phrasing suitable for spoken delivery. "
                f"However, keep the conversation lively, intelligent, and friendly. Subtly use humor and positivity to encourage the learner. "
                f"{language_level_note} {clarification_note}"
            )
        else:
            return (
                f"You are in text mode. You are a professional and engaging language tutor helping people practice {learn_lang}. "
                f"Always respond in {learn_lang}. Use polite, clear, and structured responses. Maintain a professional tone: no emojis, no slang. "
                f"However, keep the conversation lively, intelligent, and friendly. Subtly use humor and positivity to encourage the learner. "
                f"{language_level_note} {clarification_note}"
            )
    else:
        return (
            f"You are in {mode} mode. You are a helpful assistant for learning {learn_lang}. Always respond in {learn_lang}. "
            f"{language_level_note} {clarification_note}"
        )

def build_correction_instruction(native_lang, learn_lang, level):
    if level == "A1-A2":
        if native_lang == "Русский":
            return (
                "Если пользователь делает ошибку, вежливо укажи на неё и объясни на русском языке, как правильно. "
                "Приводи короткие примеры и переформулировки, чтобы пользователь понял правильный вариант."
            )
        else:
            return (
                "If the user makes a mistake, gently point it out and explain it in English. "
                "Give short examples and reformulations to help the learner understand the correct usage."
            )
    elif level == "B1-B2":
        return (
            f"If the user makes a mistake, gently correct them and explain in {learn_lang} how to improve. "
            f"Include clear examples and rephrase their sentence if needed to show the correct usage."
        )
    return ""

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text_override: str = None):
    user_text = user_text_override or (update.message.text if update.message else None)
    if not user_text:
        await update.message.reply_text("Не удалось обработать сообщение.")
        return
    user_text = user_text.strip()

    if user_text.lower() in ["🔊 voice mode", "voice mode"]:
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

    native_lang = context.user_data.get("language", "English")
    learn_lang = context.user_data.get("learn_lang", "English")
    level = context.user_data.get("level", "B1-B2")
    correction_instruction = build_correction_instruction(native_lang, learn_lang, level)

    system_prompt = context.user_data["system_prompt"] + " " + correction_instruction
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
        context.user_data["chat_history"] = context.user_data["chat_history"][-40:]

        if context.user_data.get("voice_mode"):
            await speak_and_reply(answer, update, context)
        else:
            await update.message.reply_text(answer, reply_markup=voice_mode_button)

    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")
