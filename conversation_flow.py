from telegram import ReplyKeyboardMarkup

# Список изучаемых языков (10 языков)
STUDY_LANGUAGES = [
    "English", "French", "Spanish", "German", "Italian",
    "Finnish", "Norwegian", "Swedish", "Russian", "Portuguese"
]

study_lang_keyboard = [[lang] for lang in STUDY_LANGUAGES]
study_lang_markup = ReplyKeyboardMarkup(
    study_lang_keyboard, one_time_keyboard=True, resize_keyboard=True
)

level_keyboard = [["A1-A2", "B1-B2"]]
level_markup = ReplyKeyboardMarkup(level_keyboard, one_time_keyboard=True, resize_keyboard=True)

style_keyboard = [["Разговорный", "Деловой"]]
style_markup = ReplyKeyboardMarkup(style_keyboard, one_time_keyboard=True, resize_keyboard=True)
