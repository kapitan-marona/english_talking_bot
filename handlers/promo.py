from telegram import Update
from telegram.ext import ContextTypes
from handlers.conversation import promo_completed

from datetime import datetime

PROMO_EXPIRATION = datetime(2025, 8, 26)

def is_expired():
    return datetime.now() > PROMO_EXPIRATION

VALID_PROMOCODES = {
    "друг": "Промокод принят! 🎁 Дружеский бонус активирован до 26.08!",
    "тестовый": "🧪 Тестовый режим включён",
    "0917": "🔓 Персональный доступ активирован! Добро пожаловать 👑"
}
USED_PROMOCODES = set()

async def promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Если у тебя есть промокод, введи его после команды /promo.\n"
            "Например: /promo code"
        )
        return

    code = update.message.text.replace("/promo", "").strip().lower()
    user_id = update.effective_user.id
    promo_key = f"{user_id}:{code}"

    if code not in ["0917", "тестовый"] and is_expired():
        await update.message.reply_text("⏰ Срок действия промокода истёк. Но не переживай — скоро будут новые!")
        return

    if code not in ["0917", "тестовый"] and promo_key in USED_PROMOCODES:
        await update.message.reply_text("⚠️ Этот промокод уже использован.")
        return

    USED_PROMOCODES.add(promo_key)
    await update.message.reply_text(f"✅ {VALID_PROMOCODES.get(code, '🎉')}")

    user_lang = update.effective_user.language_code or "en"
    if user_lang.startswith("ru"):
        await update.message.reply_text("""Привет, друг! 🖖
    Через минуту начнётся твоя захватывающая беседа с ботом-компаньоном. Очень надеюсь, вы подружитесь — он старается не зря!

    Вот что он умеет (и даже немного больше):

    • 💬 поддержит разговор на любые темы — от «привет» до «а в чём смысл жизни?»
    • ✍️ исправит, подскажет и не осудит, если напишешь с мисскликом или ошибкой
    • 📚 старается аккуратно заносить новые слова в словарик (сам, между прочим!)
    • 🌍 может быть твоим переводчиком — слов, фраз или целых абзацев
    • 🇷🇺 поможет подтянуть русский — особенно если он тебе не родной
    • 🧠 может придумывать задания — как личный тренер, любя
    • 🎙 общается голосом почти на всех языках (финский и норвежский пока отдыхают, sorry)
    • 🎭 шутит и поднимает настроение, если вы в режиме casual), но может быть строг и деловит — для режима formal
    • 🧪 умеет много больше, чем ты думаешь. Не бойся проверять — ты его не сломаешь.

    Он не любит торопиться, поэтому принимает 1 сообщение или команду за 3 секунды.
    Оможет ошибаться. Но с каждым разом всё меньше. 
    """)
    else:
        await update.message.reply_text("""Hey there, friend! 🖖
    You're just moments away from chatting with your new companion bot. I hope you two get along — he's really trying his best!

    Here's what he can do (and even more):

    • 💬 Chat with you on any topic — from “hi” to “what's the meaning of life?”
    • ✍️ Gently correct and explain mistakes — no judgment if you mistype
    • 📚 Automatically keeps a personal dictionary of new words for you (yes, by himself!)
    • 🌍 Act as your personal translator — words, phrases, or whole paragraphs
    • 🇬🇧 Help you improve your English — especially if it’s not your first language
    • 🧠 Invent learning tasks like a loving personal coach
    • 🎙 Speak in almost every language (except Finnish and Norwegian — they’re on vacation)
    • 🎭 Be playful and fun in casual mode, or serious and formal if you prefer
    • 🧪 Do way more than you expect. Don’t be afraid to test him — you won’t break anything.

    He’s slow and steady — one message or command every 3 seconds.
    And yes, he might make mistakes. But he gets better every time.
    """)

    return await promo_completed(update, context)

