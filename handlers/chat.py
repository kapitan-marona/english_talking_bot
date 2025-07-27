async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text_override: str = None):
    user_text = user_text_override or (update.message.text if update.message else None)

    if not user_text:
        await update.message.reply_text("Не удалось обработать сообщение.")
        return

    user_text = user_text.strip()
    normalized_text = user_text.lower()

    # 🌐 Change language logic
    if "change language" in normalized_text:
        context.user_data.clear()
        await update.message.reply_text("Let's choose a new language:", reply_markup=learn_lang_markup)
        return

    # 🎨 Normalize style
    style_raw = context.user_data.get("style", "").strip().lower()
    if "casual" in style_raw:
        context.user_data["style"] = "casual"
    elif "business" in style_raw or "formal" in style_raw:
        context.user_data["style"] = "formal"

    # 🎯 Normalize level
    level = context.user_data.get("level", "B1-B2")
    if level.lower() == "beginner":
        level = "A1-A2"
        context.user_data["level"] = level
    elif level.lower() == "intermediate":
        level = "B1-B2"
        context.user_data["level"] = level

    # 🧑‍💻 Developer info
    developer_phrases = [
        "кто тебя создал", "кто твой создатель", "разработчик", "создатель",
        "отзыв", "куда написать", "как связаться", "как оставить отзыв",
        "who made you", "your creator", "feedback", "contact the developer"
    ]
    if any(phrase in normalized_text for phrase in developer_phrases):
        await update.message.reply_text(
            "🧠 Меня создала marona.\n📬 Написать ей можно здесь: @marrona"
        )
        return

    # 🤖 Bot name
    bot_name = "matt"
    name_phrases = [
        "как тебя зовут", "твоё имя", "ты кто", "кто ты", "расскажи о себе",
        "who are you", "what's your name", "your name", "tell me about yourself"
    ]
    if normalized_text == bot_name:
        witty_replies = [
            "Yes? Did someone call the smartest bot in the room? 😏",
            "Matt reporting for duty! 💼",
            "You rang? 🎩",
            "Hey, that’s me — what’s up? 😎",
            "Matt here. Always listening. Always ready. ❤️"
        ]
        await update.message.reply_text(random.choice(witty_replies))
        return

    if any(phrase in normalized_text for phrase in name_phrases):
        await update.message.reply_text(
            "Меня зовут Matt — я помогаю тебе практиковать язык в живой, весёлой и дружелюбной форме! 😊"
        )
        return

    # 📋 Menu
    if normalized_text in ["📋 menu", "menu"]:
        from .menu import show_menu
        await show_menu(update, context)
        return

    # 🎙 Voice mode triggers
    if any(trigger in normalized_text for trigger in ["скажи голосом", "озвучь", "проговори", "say it", "произнеси", "speak it"]):
        context.user_data["voice_mode"] = True
        context.user_data["system_prompt"] = generate_system_prompt(
            context.user_data.get("language", "English"),
            level,
            context.user_data.get("style", "Casual"),
            context.user_data.get("learn_lang", "English"),
            voice_mode=True
        )
        await update.message.reply_text("Переходим в голосовой режим 🎤", reply_markup=text_mode_button)
        return

    if normalized_text in ["🔊 voice mode", "voice mode"]:
        context.user_data["voice_mode"] = True
        context.user_data["system_prompt"] = generate_system_prompt(
            context.user_data.get("language", "English"),
            level,
            context.user_data.get("style", "Casual"),
            context.user_data.get("learn_lang", "English"),
            voice_mode=True
        )
        await update.message.reply_text("Voice mode enabled.", reply_markup=text_mode_button)
        return

    if normalized_text in ["⌨️ text mode", "text mode"]:
        context.user_data["voice_mode"] = False
        context.user_data["system_prompt"] = generate_system_prompt(
            context.user_data.get("language", "English"),
            level,
            context.user_data.get("style", "Casual"),
            context.user_data.get("learn_lang", "English"),
            voice_mode=False
        )
        await update.message.reply_text("Text mode enabled.", reply_markup=voice_mode_button)
        return

    # 🧠 No system prompt yet
    if "system_prompt" not in context.user_data:
        await update.message.reply_text("/start, please.")
        return

    # 🧩 Prompt + correction rules
    native_lang = context.user_data.get("language", "English")
    learn_lang = context.user_data.get("learn_lang", "English")
    correction_instruction = build_correction_instruction(native_lang, learn_lang, level)
    system_prompt = context.user_data["system_prompt"] + " " + correction_instruction

    # 💬 Chat history
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

        # 📚 Dictionary update
        dictionary = context.user_data.setdefault("dictionary", set())
        for word in extract_marked_words(answer):
            cleaned_word = word.strip()
            if not is_russian(cleaned_word):
                dictionary.add(cleaned_word)

        # 💬 Save answer to history
        context.user_data["chat_history"].append({"role": "assistant", "content": answer})
        context.user_data["chat_history"] = context.user_data["chat_history"][-40:]

        # 🗣 Voice or text response
        if context.user_data.get("voice_mode"):
            lowercase_answer = answer.lower()
            if any(phrase in lowercase_answer for phrase in [
                "i can't actually say", "text-based ai", "i can only write", "as a text model", "i cannot speak"
            ]):
                await update.message.reply_text(answer, reply_markup=voice_mode_button)
            else:
                await speak_and_reply(answer, update, context)
        else:
            await update.message.reply_text(answer, reply_markup=voice_mode_button)

    except Exception as e:
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
