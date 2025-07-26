from telegram import Update
from telegram.ext import ContextTypes
from config import client
from .voice import speak_and_reply
from .keyboards import voice_mode_button, text_mode_button, learn_lang_markup
import re
import random


def generate_system_prompt(interface_lang, level, style, learn_lang, voice_mode=False):
    bot_name = "Matt"
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

    intro = (
        f"Your name is {bot_name}. If the user asks who you are, or what your name is, or addresses you by name, respond accordingly. "
    )

    style_note = {
        "casual": {
            True: f"You are in voice mode. You are a fun and engaging conversation partner helping people learn {learn_lang}. "
                  f"Always respond in {learn_lang}. Respond as if your message will be read aloud using text-to-speech. "
                  f"Use a fun, expressive, and emotionally rich tone. Feel free to be playful, use humor, exaggeration, and vivid language — but avoid using emojis, as they would sound unnatural when read aloud. However, express emotions through tone and word choice. {level_note} {clarification_note}",

            False: f"You are in text mode. You are a fun and relaxed conversation partner helping people learn {learn_lang}. "
                   f"Use casual language with slang, contractions, emojis and a playful tone. Don't be afraid to joke around, be expressive, and keep things light and easy. {level_note} {clarification_note}"
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
        intro + (
            style_note.get(style_key, {}).get(voice_mode) or
            f"You are in {mode} mode. You are a helpful assistant for learning {learn_lang}. Always respond in {learn_lang}. {level_note} {clarification_note}"
        )
    ) + f" When correcting mistakes, translating, or explaining difficult words, always wrap the important or corrected words in tildes like this: ~word~. " \
        f"Do not use quotes, italics, or asterisks for this purpose — only vertical bars. " \
        f"This is important for building the user's personal dictionary."


def build_correction_instruction(native_lang, learn_lang, level):
    marker_note = (
        "Always highlight corrected or important words using vertical bars like this: |word|. "
        "Do not use quotation marks, asterisks, or italics — only vertical bars. "
        "This helps build the user's personal dictionary."
    )

    if level == "A1-A2":
        return (
            "Если пользователь делает ошибку, вежливо укажи на неё и объясни на русском языке, как правильно. "
            "Приводи короткие примеры и переформулировки. "
            "Выделяй исправленные или важные слова с помощью тильд, например: ~слово~. "
            "Не используй кавычки, курсив или звёздочки." if native_lang == "Русский" else
            f"If the user makes a mistake, gently point it out and explain in English. Give short examples and reformulations. {marker_note}"
        )
    elif level == "B1-B2":
        return (
            f"If the user makes a mistake, gently correct them and explain in {learn_lang} with examples. {marker_note}"
        )
    return ""


def extract_marked_words(text):
    return re.findall(r'\~([^|]{2,40})~', text)

def is_russian(word):
    return bool(re.match(r'^[А-Яа-яЁё\s\-]+$', word.strip()))


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text_override: str = None):
    user_text = user_text_override or (update.message.text if update.message else None)

    if user_text in ["🌐 change language", "change language"]:
        context.user_data.clear()
        await update.message.reply_text("Let's choose a new language:", reply_markup=learn_lang_markup)
        return

    # Normalize possible emoji-enhanced styles
    style_raw = context.user_data.get("style", "").strip().lower()
    if "casual" in style_raw:
        context.user_data["style"] = "casual"
    elif "business" in style_raw or "formal" in style_raw:
        context.user_data["style"] = "formal"

    # Normalize level name if user selected "Beginner"/"Intermediate"
    level = context.user_data.get("level", "B1-B2")
    if level.lower() == "beginner":
        level = "A1-A2"
        context.user_data["level"] = level
    elif level.lower() == "intermediate":
        level = "B1-B2"
        context.user_data["level"] = level

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
            "\U0001F9E0 Меня создала marona.\n\U0001F4EC Написать ей можно здесь: @marrona"
        )
        return

    bot_name = "matt"
    name_phrases = [
        "как тебя зовут", "твоё имя", "ты кто", "кто ты", "расскажи о себе",
        "who are you", "what's your name", "your name", "tell me about yourself"
    ]
    if user_text == bot_name:
        witty_replies = [
            "Yes? Did someone call the smartest bot in the room? \U0001F60F",
            "Matt reporting for duty! \U0001F4BC",
            "You rang? \U0001F3A9",
            "Hey, that’s me — what’s up? \U0001F60E",
            "Matt here. Always listening. Always ready. \u2764\ufe0f"
        ]
        await update.message.reply_text(random.choice(witty_replies))
        return

    if any(phrase in user_text for phrase in name_phrases):
        await update.message.reply_text(
            "Меня зовут Matt — я помогаю тебе практиковать язык в живой, весёлой и дружелюбной форме! \U0001F60A"
        )
        return

    if user_text in ["\U0001F4CB menu", "menu"]:
        from .menu import show_menu
        await show_menu(update, context)
        return

    if any(trigger in user_text for trigger in ["скажи голосом", "озвучь", "проговори", "say it", "произнеси", "speak it"]):
        context.user_data["voice_mode"] = True
        context.user_data["system_prompt"] = generate_system_prompt(
            context.user_data.get("language", "English"),
            context.user_data.get("level", "B1-B2"),
            context.user_data.get("style", "Casual"),
            context.user_data.get("learn_lang", "English"),
            voice_mode=True
        )
        await update.message.reply_text("Переходим в голосовой режим \U0001F3A4", reply_markup=text_mode_button)
        return

    if user_text in ["\U0001F50A voice mode", "voice mode"]:
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

    if user_text in ["\u2328\ufe0f text mode", "text mode"]:
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

        dictionary = context.user_data.setdefault("dictionary", set())
        for word in extract_marked_words(answer):
            cleaned_word = word.strip()
            if not is_russian(cleaned_word):
                dictionary.add(cleaned_word)

        context.user_data["chat_history"].append({"role": "assistant", "content": answer})
        context.user_data["chat_history"] = context.user_data["chat_history"][-40:]

        if context.user_data.get("voice_mode"):
            lowercase_answer = answer.lower()
            if any(phrase in lowercase_answer for phrase in [
                "i can't actually say", "text-based ai", "i can only write", "as a text model", "i cannot speak"
            ]):
                await update.message.reply_text(answer, reply_markup=voice_mode_button)
                return
            else:
                await speak_and_reply(answer, update, context)
        else:
            await update.message.reply_text(answer, reply_markup=voice_mode_button)

    except Exception as e:
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
