from telegram import Update
from telegram.ext import ContextTypes

VALID_PROMOCODES = {
    "БРАТСКИЙ_ЧЕК": "🎁 Дружеский бонус активирован!"
}
USED_PROMOCODES = set()

async def promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Введите промокод после команды, например: /promo БРАТСКИЙ_ЧЕК")
        return

    code = context.args[0].strip().upper()
    user_id = update.effective_user.id
    promo_key = f"{user_id}:{code}"

    if code not in VALID_PROMOCODES:
        await update.message.reply_text("❌ Неверный промокод.")
        return

    if promo_key in USED_PROMOCODES:
        await update.message.reply_text("⚠️ Этот промокод уже использован.")
        return

    USED_PROMOCODES.add(promo_key)
    await update.message.reply_text(f"✅ Промокод активирован: {VALID_PROMOCODES[code]}")
