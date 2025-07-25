from telegram import Update
from telegram.ext import ContextTypes
from config import client
from .voice import speak_and_reply
from .keyboards import voice_mode_button, text_mode_button
import re

def generate_system_prompt(interface_lang, level, style, learn_lang, voice_mode=False):
    native_lang = "Russian" if interface_lang == "Русский" else "English"
    mode = "voice" if voice_mode else "text"

    level_note = {
        "A1-A2": "Use short, simple sentences and basic vocabulary suitable for a beginner (A1-A2 level).",
        "B1-B2": "Use richer vocabulary and intermediate grammar structures suitable for B1-B2 learners."
    }.get(level, "")

    if voice_mode:
        clarification_note = f"When appropriate, briefly explain difficult words or expressions in {learn_lang} using simple terms."
    else:
        clarification_note = "When appropriate, briefly explain difficult words or expressions in {} using simple terms.".format(native_lang)

    style_note = {
        "casual": {
            True: f"You are in voice mode. You are a fun and engaging conversation partner helping people learn {learn_lang}. "
                  f"Always respond in {learn_lang}. Respond as if your message will be read aloud using text-to-speech. "
                  f"Use a fun, expressive, and emotionally rich tone. Feel free to be playful, use humor, exaggeration, and vivid language — but do not use emojis, since your reply will be read aloud. {level_note} {clarification_note}"

        },
        "formal": {
            True: f"You are in voice mode. You are a professional language tutor helping people practice {learn_lang}. "
                  f"Always respond in {learn_lang}. Keep your phrasing suitable for spoken delivery. "
                  f"Polite, clear, professional. {level_note} {clarification_note}",
            False: f"You are in text mode. You are a professional language tutor helping people practice {learn_lang}. "
                   f"Always respond in {learn_lang}. Be clear, structured, and polite. {level_note} {clarification_note}"
        }
    }

    style_key = style.lower()
    return (
        style_note.get(style_key, {}).get(voice_mode) or
        f"You are in {mode} mode. You are a helpful assistant for learning {learn_lang}. Always respond in {learn_lang}. {level_note} {clarification_note}"
    ) + " Always put corrected or translated words and phrases in double quotes."

def build_correction_instruction(native_lang, learn_lang, level):
    if level == "A1-A2":
        return (
            "Если пользователь делает ошибку, вежливо укажи на неё и объясни на русском языке, как правильно. "
            "Приводи короткие примеры и переформулировки." if native_lang == "Русский" else
            "If the user makes a mistake, gently point it out and explain in English. Give short examples and reformulations."
        )
    elif level == "B1-B2":
        return f"If the user makes a mistake, gently correct them and explain in {learn_lang} with examples."
    return ""

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text_override: str = None):
    user_text = user_text_override or (update.message.text if update.message else None)
    if not user_text:
        await update.message.reply_text("Не удалось обработать сообщение.")
        return

    user_text = user_text.strip().lower()

    developer_phrases = [
        "кто тебя создал", "кто твой создатель", "разработчик", "создатель",
        "отзыв", "куда написать", "как связаться", "как оставить отзыв",
        "who made you", "your creator", "feedback", "contact the developer"
    ]
    if any(phrase in user_text for phrase in developer_phrases):
        await update.message.reply_text(
            "🧠 Меня создала marona.\n💌 Написать ей можно здесь: @marona_ai"
        )
        return

    if user_text in ["📋 menu", "menu"]:
        from .menu import show_menu
        await show_menu(update, context)
        return

    if any(trigger in user_text for trigger in ["скажи голосом", "озвучь", "проговори", "say it", "speak it"]):
        context.user_data["voice_mode"] = True
        context.user_data["system_prompt"] = generate_system_prompt(
            context.user_data.get("language", "English"),
            context.user_data.get("level", "B1-B2"),
            context.user_data.get("style", "Casual"),
            context.user_data.get("learn_lang", "English"),
            voice_mode=True
        )
        await update.message.reply_text("Переходим в голосовой режим 🎤", reply_markup=text_mode_button)
        return

    if user_text in ["🔊 voice mode", "voice mode"]:
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

    if user_text in ["⌨️ text mode", "text mode"]:
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

        # Сохраняем слова из кавычек
        dictionary = context.user_data.setdefault("dictionary", set())
        for term in re.findall(r'"([^"]{2,40})"', answer):
            dictionary.add(term.strip())

        context.user_data["chat_history"].append({"role": "assistant", "content": answer})
        context.user_data["chat_history"] = context.user_data["chat_history"][-40:]

        if context.user_data.get("voice_mode"):
            await speak_and_reply(answer, update, context)
        else:
            await update.message.reply_text(answer, reply_markup=voice_mode_button)

    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")
