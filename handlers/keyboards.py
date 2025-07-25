from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup

# Кнопки режимов + меню
voice_mode_button = ReplyKeyboardMarkup(
    [[KeyboardButton("🔊 Voice mode")], [KeyboardButton("📋 Menu")]],
    resize_keyboard=True
)

text_mode_button = ReplyKeyboardMarkup(
    [[KeyboardButton("⌨️ Text mode")], [KeyboardButton("📋 Menu")]],
    resize_keyboard=True
)

# Выбор изучаемого языка
learn_lang_keyboard = [
    ["English", "French", "Spanish", "German", "Italian"],
    ["Finnish", "Norwegian", "Swedish", "Russian", "Portuguese"]
]
learn_lang_markup = ReplyKeyboardMarkup(
    learn_lang_keyboard, one_time_keyboard=True, resize_keyboard=True
)

# Уровень
level_keyboard = [["A1-A2", "B1-B2"]]
level_markup = ReplyKeyboardMarkup(
    level_keyboard, one_time_keyboard=True, resize_keyboard=True
)

# Стиль общения
style_keyboard_ru = [["Casual", "Formal"]]

# Главное меню (в будущем можно добавить больше кнопок)
main_menu_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("📖 Словарь", callback_data="dictionary")]
])
