from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup

voice_mode_button = ReplyKeyboardMarkup(
    [[KeyboardButton("🔊 Voice mode")], [KeyboardButton("📋 Menu")]],
    resize_keyboard=True
)

text_mode_button = ReplyKeyboardMarkup(
    [[KeyboardButton("⌨️ Text mode")], [KeyboardButton("📋 Menu")]],
    resize_keyboard=True
)

learn_lang_keyboard = [
    ["English", "French", "Spanish", "German", "Italian"],
    ["Finnish", "Norwegian", "Swedish", "Russian", "Portuguese"]
]
learn_lang_markup = ReplyKeyboardMarkup(learn_lang_keyboard, one_time_keyboard=True, resize_keyboard=True)

level_keyboard = [["A1-A2", "B1-B2"]]
level_markup = ReplyKeyboardMarkup(level_keyboard, one_time_keyboard=True, resize_keyboard=True)

style_keyboard_ru = [["Casual", "Formal"]]

main_menu_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("📖 Словарь", callback_data="dictionary")]
])
