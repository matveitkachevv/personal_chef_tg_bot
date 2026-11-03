import logging
import uuid
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from personal_chef.agent import (
    generate_full_recipe_text,
    generate_meal_options,
    get_user_proposals,
    save_user_proposals,
)
from personal_chef.db.repositories import (
    inventory_repo,
    meal_plan_repo,
    preference_repo,
    recipe_repo,
)
from personal_chef.keyboards import (
    get_confirm_deduct_kb,
    get_dish_options_kb,
    get_meal_types_kb,
    get_recipe_actions_kb,
)

logger = logging.getLogger(__name__)
router = Router(name="recipes")

MEAL_NAMES = {
    "breakfast": "🥞 Завтрак",
    "lunch": "🍲 Обед",
    "dinner": "🍝 Ужин",
    "snack": "🥪 Перекус",
    "chef_choice": "🎲 На усмотрение шефа",
}


@router.message(F.text == "🍽 Подобрать рецепт")
async def choose_meal_type_message(message: Message) -> None:
    text = (
        "🍽 <b>Подбор блюда от шефа</b>\n\n"
        "Выберите прием пищи, и я предложу 2-3 отличных варианта из продуктов в вашем холодильнике:"
    )
    await message.answer(text, reply_markup=get_meal_types_kb())


@router.callback_query(F.data == "meal_select_type")
async def choose_meal_type_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    text = (
        "🍽 <b>Подбор блюда от шефа</b>\n\n"
        "Выберите прием пищи, и я предложу 2-3 отличных варианта из продуктов в вашем холодильнике:"
    )
    if callback.message:
        await callback.message.answer(text, reply_markup=get_meal_types_kb())


@router.callback_query(F.data.startswith("meal_type:"))
async def process_meal_type_selection(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    await callback.answer()
    user_id = callback.from_user.id
    raw_meal_code = callback.data.split(":", 1)[1] if callback.data else "chef_choice"
    meal_title = MEAL_NAMES.get(raw_meal_code, "Прием пищи")

    status_msg = None
    if callback.message:
        status_msg = await callback.message.answer(
            f"👨‍🍳 <i>Шеф заглядывает в ваш холодильник и подбирает лучшие варианты на {meal_title.lower()}...</i>"
        )

    # Загружаем инвентарь и предпочтения
    inv_items = await inventory_repo.get_user_inventory(session, user_id)
    prefs = await preference_repo.get_user_preferences(session, user_id)

    fridge_summary = ", ".join(
        [f"{i.product_name} ({i.amount})" if i.amount else i.product_name for i in inv_items]
    )
    pref_summary = ", ".join([f"{p.preference_type}: {p.item_name}" for p in prefs])

    # Генерируем 2-3 варианта
    proposals = await generate_meal_options(
        user_id=user_id,
        meal_type=meal_title,
        preferences_summary=pref_summary,
        fridge_summary=fridge_summary,
    )
    save_user_proposals(user_id, proposals)

    # Формируем текст сообщения
    lines = [f"🍽 <b>Варианты блюд на {meal_title.lower()}:</b>\n"]
    digits = ["1️⃣", "2️⃣", "3️⃣"]
    dish_titles: list[str] = []

    for idx, prop in enumerate(proposals):
        icon = digits[idx] if idx < len(digits) else f"{idx+1}."
        title = prop.get("title", f"Блюдо {idx+1}")
        dish_titles.append(title)
        desc = prop.get("description", "")
        ctime = prop.get("cooking_time", "15-20 мин")
        missing = prop.get("missing_ingredients", "Все продукты в наличии")

        lines.append(f"{icon} <b>{title}</b>")
        lines.append(f"   <i>{desc}</i>")
        lines.append(f"   ⏱ Время: {ctime}")
        lines.append(f"   📦 Состав: {missing}\n")

    lines.append("Выберите блюдо, чтобы получить пошаговый рецепт:")
    full_text = "\n".join(lines)

    kb = get_dish_options_kb(dish_titles)
    if status_msg:
        await status_msg.edit_text(full_text, reply_markup=kb)
    elif callback.message:
        await callback.message.answer(full_text, reply_markup=kb)


@router.callback_query(F.data.startswith("select_dish:"))
async def process_dish_selection(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    await callback.answer()
    user_id = callback.from_user.id
    dish_idx = int(callback.data.split(":", 1)[1]) if callback.data else 0

    proposals = get_user_proposals(user_id)
    if not proposals or dish_idx >= len(proposals):
        if callback.message:
            await callback.message.answer(
                "Время действия вариантов истекло. Нажмите «🍽 Подобрать рецепт» заново!"
            )
        return

    selected = proposals[dish_idx]
    dish_title = selected.get("title", "Выбранное блюдо")

    status_msg = None
    if callback.message:
        status_msg = await callback.message.answer(
            f"👨‍🍳 <i>Шеф расписывает пошаговый рецепт для «{dish_title}»...</i>"
        )

    # Загружаем данные пользователя
    inv_items = await inventory_repo.get_user_inventory(session, user_id)
    prefs = await preference_repo.get_user_preferences(session, user_id)
    fridge_summary = ", ".join([i.product_name for i in inv_items])
    pref_summary = ", ".join([f"{p.preference_type}: {p.item_name}" for p in prefs])

    recipe_data = await generate_full_recipe_text(
        dish_title=dish_title,
        meal_type="прием пищи",
        preferences_summary=pref_summary,
        fridge_summary=fridge_summary,
    )

    ingredients_list = recipe_data.get("ingredients", [])
    ingredients_text = "\n".join(f"• {i}" for i in ingredients_list)
    instructions = recipe_data.get("instructions", "Готовьте с удовольствием!")
    cooking_time = recipe_data.get("cooking_time", 20)
    portions = recipe_data.get("portions", 1)

    # Сохраняем рецепт в БД
    recipe = await recipe_repo.create_recipe(
        session=session,
        title=dish_title,
        instructions=instructions,
        ingredients_text=ingredients_text,
        cooking_time_minutes=cooking_time if isinstance(cooking_time, int) else None,
        portions=portions if isinstance(portions, int) else 1,
    )

    # Создаем запись в meal_plans со статусом planned
    await meal_plan_repo.create_meal_plan(
        session=session,
        user_id=user_id,
        recipe_id=recipe.id,
        meal_type="recipe",
        status="planned",
    )

    recipe_card = (
        f"📖 <b>{recipe.title}</b>\n\n"
        f"⏱ <b>Время приготовления:</b> {cooking_time} мин\n"
        f"🍽 <b>Порций:</b> {portions}\n\n"
        f"🛒 <b>Ингредиенты:</b>\n{ingredients_text}\n\n"
        f"👨‍🍳 <b>Инструкция приготовления:</b>\n{instructions}\n\n"
        f"Когда приготовите, нажмите кнопку ниже, чтобы зафиксировать блюдо и списать продукты:"
    )

    kb = get_recipe_actions_kb(str(recipe.id))
    if status_msg:
        await status_msg.edit_text(recipe_card, reply_markup=kb)
    elif callback.message:
        await callback.message.answer(recipe_card, reply_markup=kb)


@router.callback_query(F.data.startswith("cooked:"))
async def process_cooked_dish(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    await callback.answer()
    user_id = callback.from_user.id
    recipe_id_str = callback.data.split(":", 1)[1] if callback.data else ""

    try:
        recipe_uuid = uuid.UUID(recipe_id_str)
    except ValueError:
        return

    # Находим план питания и обновляем статус на 'cooked'
    meal_plan = await meal_plan_repo.get_latest_meal_plan_by_recipe(
        session=session,
        user_id=user_id,
        recipe_id=recipe_uuid,
    )
    if meal_plan:
        await meal_plan_repo.update_meal_plan_status(session, meal_plan.id, "cooked")

    recipe = await recipe_repo.get_recipe(session, recipe_uuid)
    recipe_title = recipe.title if recipe else "блюдо"

    text = (
        f"🎉 <b>«{recipe_title}» отмечено как приготовленное!</b>\n\n"
        "Статус блюда переведен в <b>cooked</b>.\n"
        "Хотите списать использованные продукты из вашего холодильника в один клик?"
    )
    if callback.message:
        await callback.message.answer(text, reply_markup=get_confirm_deduct_kb(recipe_id_str))


@router.callback_query(F.data.startswith("confirm_deduct:"))
async def process_confirm_deduct(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    await callback.answer()
    user_id = callback.from_user.id
    recipe_id_str = callback.data.split(":", 1)[1] if callback.data else ""

    try:
        recipe_uuid = uuid.UUID(recipe_id_str)
    except ValueError:
        return

    recipe = await recipe_repo.get_recipe(session, recipe_uuid)
    if not recipe:
        if callback.message:
            await callback.message.answer("Рецепт не найден в базе данных.")
        return

    # Извлекаем ингредиенты из текста рецепта
    ingredients = [
        line.lstrip("•- 0123456789.").split("—")[0].split("-")[0].strip()
        for line in recipe.ingredients_text.splitlines()
        if line.strip()
    ]

    removed = await inventory_repo.remove_inventory_items(session, user_id, ingredients)

    if removed:
        text = (
            f"✅ <b>Ингредиенты успешно списаны из холодильника!</b>\n\n"
            f"Удалено: <i>{', '.join(removed)}</i>\n\n"
            "Приятного аппетита! 👨‍🍳"
        )
    else:
        text = (
            "✅ <b>Блюдо зафиксировано!</b>\n\n"
            "В холодильнике не найдено точных совпадений для автоматического списания. "
            "Приятного аппетита! 👨‍🍳"
        )

    if callback.message:
        await callback.message.edit_text(text)


@router.callback_query(F.data == "cancel_deduct")
async def process_cancel_deduct(callback: CallbackQuery) -> None:
    await callback.answer()
    text = "👌 Хорошо, продукты оставлены в холодильнике без изменений. Приятного аппетита! 👨‍🍳"
    if callback.message:
        await callback.message.edit_text(text)
