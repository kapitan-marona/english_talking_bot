from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove

# Поддерживаемые языки интерфейса и изучаемые языки
SUPPORTED_LANGUAGES = {
    "en": "English",
    "ru": "Русский",
    "ar": "العربية",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "zh": "中文",
    "ja": "日本語",
    "it": "Italiano",
    "pt": "Português"
}

# Локализация основных фраз интерфейса (ключи одинаковы для всех языков)
LOCALIZATION = {
    "en": {
        "choose_native": "Choose your native language:",
        "choose_target": "Choose the language you want to learn:",
        "start_welcome": "Welcome! Let's set up your languages.",
        "invalid_choice": "Please select a language from the keyboard.",
        "cancel": "Cancelled.",
        "prompt_start": "To begin, type /start."
    },
    "ru": {
        "choose_native": "Выберите родной язык:",
        "choose_target": "Выберите язык, который хотите изучать:",
        "start_welcome": "Добро пожаловать! Давайте настроим ваши языки.",
        "invalid_choice": "Пожалуйста, выберите язык из клавиатуры.",
        "cancel": "Отмена.",
        "prompt_start": "Для начала введите /start."
    },
    "ar": {
        "choose_native": "اختر لغتك الأم:",
        "choose_target": "اختر اللغة التي تريد تعلمها:",
        "start_welcome": "مرحبًا! دعنا نحدد لغاتك.",
        "invalid_choice": "يرجى اختيار لغة من لوحة المفاتيح.",
        "cancel": "تم الإلغاء.",
        "prompt_start": "لبدء المحادثة، اكتب /start."
    },
    "es": {
        "choose_native": "Elige tu idioma nativo:",
        "choose_target": "Elige el idioma que quieres aprender:",
        "start_welcome": "¡Bienvenido! Configuraremos tus idiomas.",
        "invalid_choice": "Por favor, selecciona un idioma del teclado.",
        "cancel": "Cancelado.",
        "prompt_start": "Para comenzar, escribe /start."
    },
    "fr": {
        "choose_native": "Choisissez votre langue maternelle :",
        "choose_target": "Choisissez la langue que vous voulez apprendre :",
        "start_welcome": "Bienvenue ! Configurons vos langues.",
        "invalid_choice": "Veuillez sélectionner une langue dans le clavier.",
        "cancel": "Annulé.",
        "prompt_start": "Pour commencer, tapez /start."
    },
    "de": {
        "choose_native": "Wähle deine Muttersprache:",
        "choose_target": "Wähle die Sprache, die du lernen möchtest:",
        "start_welcome": "Willkommen! Lass uns deine Sprachen einstellen.",
        "invalid_choice": "Bitte wähle eine Sprache von der Tastatur.",
        "cancel": "Abgebrochen.",
        "prompt_start": "Zum Starten tippe /start."
    },
    "zh": {
        "choose_native": "选择你的母语：",
        "choose_target": "选择你想学习的语言：",
        "start_welcome": "欢迎！让我们设置你的语言。",
        "invalid_choice": "请选择键盘上的语言。",
        "cancel": "已取消。",
        "prompt_start": "开始请发送 /start。"
    },
    "ja": {
        "choose_native": "母国語を選んでください：",
        "choose_target": "学びたい言語を選んでください：",
        "start_welcome": "ようこそ！言語を設定しましょう。",
        "invalid_choice": "キーボードから言語を選択してください。",
        "cancel": "キャンセルされました。",
        "prompt_start": "/start と入力して開始してください。"
    },
    "it": {
        "choose_native": "Scegli la tua lingua madre:",
        "choose_target": "Scegli la lingua che vuoi imparare:",
        "start_welcome": "Benvenuto! Configuriamo le tue lingue.",
        "invalid_choice": "Seleziona una lingua dalla tastiera.",
        "cancel": "Annullato.",
        "prompt_start": "Per iniziare, digita /start."
    },
    "pt": {
        "choose_native": "Escolha seu idioma nativo:",
        "choose_target": "Escolha o idioma que você quer aprender:",
        "start_welcome": "Bem-vindo! Vamos configurar seus idiomas.",
        "invalid_choice": "Por favor, selecione um idioma no teclado.",
        "cancel": "Cancelado.",
        "prompt_start": "Para começar, digite /start."
    },
}

# States для ConversationHandler
LANG_NATIVE, LANG_TARGET = range(2)

def get_user_lang_code(update) -> str:
    """
    Получить язык устройства пользователя из Telegram API.
    Если язык не поддерживается, вернуть 'en' по умолчанию.
    """
    user_lang = update.effective_user.language_code
    if user_lang not in SUPPORTED_LANGUAGES:
        # Попытка взять только первые два символа (ru-RU -> ru)
        user_lang = user_lang[:2] if user_lang and user_lang[:2] in SUPPORTED_LANGUAGES else "en"
    return user_lang

def get_localized_text(update, key: str) -> str:
    """
    Получить локализованную строку для пользователя по ключу.
    """
    lang = get_user_lang_code(update)
    return LOCALIZATION.get(lang, LOCALIZATION["en"]).get(key, key)

def get_language_keyboard():
    """
    Клавиатура с языками (значения из SUPPORTED_LANGUAGES).
    """
    # Кнопки по 3 в ряд (пример)
    langs = list(SUPPORTED_LANGUAGES.values())
    keyboard = [langs[i:i+3] for i in range(0, len(langs), 3)]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

async def start_conversation(update, context) -> int:
    """
    Старт — спрашиваем родной язык.
    Вопрос выводится на языке устройства.
    """
    context.user_data.clear()
    welcome = get_localized_text(update, "start_welcome")
    choose_native = get_localized_text(update, "choose_native")

    await update.message.reply_text(
        f"{welcome}\n\n{choose_native}",
        reply_markup=get_language_keyboard()
    )
    return LANG_NATIVE

async def native_language_choice(update, context) -> int:
    """
    Пользователь выбрал родной язык.
    Проверяем корректность и спрашиваем изучаемый язык.
    """
    text = update.message.text.strip()
    if text not in SUPPORTED_LANGUAGES.values():
        await update.message.reply_text(get_localized_text(update, "invalid_choice"))
        return LANG_NATIVE

    context.user_data["native_language"] = text

    choose_target = get_localized_text(update, "choose_target")
    await update.message.reply_text(
        choose_target,
        reply_markup=get_language_keyboard()
    )
    return LANG_TARGET

async def target_language_choice(update, context) -> int:
    """
    Пользователь выбрал изучаемый язык.
    Проверяем корректность, сохраняем и заканчиваем диалог.
    """
    text = update.message.text.strip()
    if text not in SUPPORTED_LANGUAGES.values():
        await update.message.reply_text(get_localized_text(update, "invalid_choice"))
        return LANG_TARGET

    context.user_data["target_language"] = text

    # Здесь можно добавить стартовое сообщение на выбранном языке, пока просто убираем клавиатуру
    await update.message.reply_text(
        f"Native language: {context.user_data['native_language']}\n"
        f"Learning language: {context.user_data['target_language']}\n\n"
        "You can now start chatting.",
        reply_markup=ReplyKeyboardRemove()
    )
    return -1  # Conversation end
