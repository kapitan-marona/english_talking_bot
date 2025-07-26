
from telegram import Update
from telegram.ext import ContextTypes
from handlers.conversation import promo_completed

from datetime import datetime

PROMO_EXPIRATION = datetime(2025, 8, 26)

def is_expired():
    return datetime.now() > PROMO_EXPIRATION

VALID_PROMOCODES = {
    "друг": "Промокод принят! 🎁 Дружеский бонус активирован до 26.08!",
    "ТЕСТОВЫЙ": "🧪 Тестовый режим включён",
    "0917": "🔓 Вход выполнен 👑"
}
USED_PROMOCODES = set()

async def promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Если у тебя есть промокод, введи его после команды /promo.\n"
            "Например: /promo code"
        )
        return

    code = update.message.text.replace("/promo", "").strip().upper()
    user_id = update.effective_user.id
    promo_key = f"{user_id}:{code}"

    if code not in ["0917", "ТЕСТОВЫЙ"] and is_expired():
        await update.message.reply_text("⏰ Срок действия промокода истёк. Но не переживай — скоро будут новые!")
        return

    if code not in ["0917", "ТЕСТОВЫЙ"] and promo_key in USED_PROMOCODES:
        await update.message.reply_text("⚠️ Этот промокод уже использован.")
        return

    USED_PROMOCODES.add(promo_key)
    await update.message.reply_text(f"✅ {VALID_PROMOCODES.get(code, '🎉')}")

    await update.message.reply_text("""Привет, друг! 🖖
Через минуту начнётся твоя захватывающая беседа с ботом-компаньоном. Очень надеюсь, вы подружитесь — он старается не зря!

Вот что он умеет (и даже немного больше):

• 💬 поддержит разговор на любые темы — от «привет» до «а в чём смысл жизни?»
• ✍️ исправит, подскажет и не осудит, если напишешь с мисскликом или ошибкой
• 📚 аккуратно заносит новые слова в словарик (сам, между прочим!)
• 🌍 может быть твоим переводчиком — слов, фраз или целых абзацев
• 🇷🇺 поможет подтянуть русский — особенно если он тебе не родной
• 🧠 может придумывать задания — как личный тренер, любя
• 🎙 общается голосом почти на всех языках (финский и норвежский пока отдыхают, sorry)
• 🎭 умеет шутить и флиртовать (если вы в режиме casual), но может быть строг и деловит — для режима formal
• 🧪 умеет много больше, чем ты думаешь. Не бойся проверять — ты его не сломаешь.

И главное: он может ошибаться. Но с каждым разом всё меньше.
""")

    return await promo_completed(update, context)
