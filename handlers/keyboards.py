from telegram import ReplyKeyboardMarkup, KeyboardButton

voice_mode_button = ReplyKeyboardMarkup(
    [[KeyboardButton("🔊 Voice mode")]], resize_keyboard=True
)

text_mode_button = ReplyKeyboardMarkup(
    [[KeyboardButton("⌨️ Text mode")]], resize_keyboard=True
)

learn_lang_keyboard = [
    ["English", "French", "Spanish", "German", "Italian"],
    ["Finnish", "Norwegian", "Swedish", "Russian", "Portuguese"]
]
learn_lang_markup = ReplyKeyboardMarkup(learn_lang_keyboard, one_time_keyboard=True, resize_keyboard=True)

level_keyboard = [["A1-A2", "B1-B2"]]
level_markup = ReplyKeyboardMarkup(level_keyboard, one_time_keyboard=True, resize_keyboard=True)

style_keyboard_ru = [["Casual", "Formal"]]

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# уже существующие...
# voice_mode_button, text_mode_button, learn_lang_markup и т.д.

main_menu_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("🌍 Сменить язык", callback_data="change_language")],
    [InlineKeyboardButton("🎚 Изменить уровень/стиль", callback_data="change_level_style")],
    [InlineKeyboardButton("🔁 Переключить режим", callback_data="toggle_mode")],
    [InlineKeyboardButton("♻️ Начать сначала", callback_data="reset")]
])

