from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_onboarding_allergies_kb() -> InlineKeyboardMarkup:
    """Шаг онбординга: аллергии."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚫 Нет аллергий / Пропустить",
                    callback_data="onboarding_skip_allergies",
                ),
            ],
        ]
    )


def get_onboarding_preferences_kb() -> InlineKeyboardMarkup:
    """Шаг онбординга: вкусовые предпочтения и диеты."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👌 Ем всё / Пропустить",
                    callback_data="onboarding_skip_preferences",
                ),
            ],
        ]
    )


def get_onboarding_fridge_kb() -> InlineKeyboardMarkup:
    """Шаг онбординга: стартовый холодильник."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏩ Заполню позже",
                    callback_data="onboarding_skip_fridge",
                ),
            ],
        ]
    )


def get_fridge_actions_kb() -> InlineKeyboardMarkup:
    """Инлайн-кнопки меню холодильника."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить продукты",
                    callback_data="fridge_add",
                ),
                InlineKeyboardButton(
                    text="🗑 Очистить всё",
                    callback_data="fridge_clear",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🍽 Подобрать блюдо",
                    callback_data="meal_select_type",
                ),
            ],
        ]
    )


def get_fridge_clear_confirm_kb() -> InlineKeyboardMarkup:
    """Подтверждение очистки холодильника."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, очистить всё",
                    callback_data="fridge_confirm_clear",
                ),
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="fridge_cancel_clear",
                ),
            ],
        ]
    )


def get_meal_types_kb() -> InlineKeyboardMarkup:
    """Инлайн-выбор типа приема пищи."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🥞 Завтрак", callback_data="meal_type:breakfast"),
                InlineKeyboardButton(text="🍲 Обед", callback_data="meal_type:lunch"),
            ],
            [
                InlineKeyboardButton(text="🍝 Ужин", callback_data="meal_type:dinner"),
                InlineKeyboardButton(text="🥪 Перекус", callback_data="meal_type:snack"),
            ],
            [
                InlineKeyboardButton(text="🎲 На усмотрение шефа", callback_data="meal_type:chef_choice"),
            ],
        ]
    )


def get_dish_options_kb(dish_titles: list[str]) -> InlineKeyboardMarkup:
    """Инлайн-кнопки выбора одного из предложенных вариантов блюд."""
    buttons = []
    digits = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    for idx, title in enumerate(dish_titles):
        icon = digits[idx] if idx < len(digits) else f"{idx+1}."
        # Обрезаем заголовок если слишком длинный для кнопки
        btn_text = f"{icon} {title[:35]}"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"select_dish:{idx}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_recipe_actions_kb(recipe_id: str) -> InlineKeyboardMarkup:
    """Кнопка под детальным рецептом блюда."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Приготовлено (списать продукты)",
                    callback_data=f"cooked:{recipe_id}",
                ),
            ],
        ]
    )


def get_confirm_deduct_kb(recipe_id: str) -> InlineKeyboardMarkup:
    """Кнопки подтверждения списания ингредиентов."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Списать использованные продукты",
                    callback_data=f"confirm_deduct:{recipe_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Не списывать",
                    callback_data="cancel_deduct",
                ),
            ],
        ]
    )


def get_preferences_kb() -> InlineKeyboardMarkup:
    """Кнопки в разделе предпочтений."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚫 Добавить аллергию",
                    callback_data="pref_add_allergy",
                ),
                InlineKeyboardButton(
                    text="🥗 Добавить диету/вкус",
                    callback_data="pref_add_diet",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Сбросить предпочтения",
                    callback_data="pref_clear_all",
                ),
            ],
        ]
    )


def get_help_inline_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-кнопки для раздела помощи."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📖 О проекте",
                    callback_data="about_project",
                ),
            ],
        ]
    )
