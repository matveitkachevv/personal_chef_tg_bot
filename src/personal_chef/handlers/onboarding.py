import logging
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from personal_chef.db.repositories import inventory_repo, preference_repo
from personal_chef.fsm.states import OnboardingStates
from personal_chef.keyboards import (
    get_main_keyboard,
    get_onboarding_fridge_kb,
    get_onboarding_preferences_kb,
)

logger = logging.getLogger(__name__)
router = Router(name="onboarding")


# --- ШАГ 1: АЛЛЕРГИИ ---

@router.callback_query(OnboardingStates.allergies, F.data == "onboarding_skip_allergies")
async def onboarding_skip_allergies(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(OnboardingStates.preferences)
    text = (
        "👌 Принято, аллергии не зафиксированы.\n\n"
        "<b>Шаг 2 из 3:</b> Какую кухню предпочитаете или каких принципов питания придерживаетесь "
        "(вегетарианство, кето, ПП, любимые или нелюбимые продукты)?"
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=get_onboarding_preferences_kb())


@router.message(OnboardingStates.allergies, F.text)
async def onboarding_save_allergies(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    user_id = message.from_user.id if message.from_user else 0
    raw_text = message.text or ""
    # Разделяем по запятым или переводам строк
    items = [item.strip() for item in raw_text.replace("\n", ",").split(",") if item.strip()]
    if items:
        await preference_repo.add_preferences_bulk(session, user_id, "allergy", items)

    await state.set_state(OnboardingStates.preferences)
    saved_items_str = ", ".join(items) if items else "зафиксированы"
    text = (
        f"✅ Аллергии сохранены ({saved_items_str}). Шеф никогда не добавит их в рецепты!\n\n"
        "<b>Шаг 2 из 3:</b> Какую кухню предпочитаете или каких принципов питания придерживаетесь "
        "(вегетарианство, кето, ПП, средиземноморская и др.)?"
    )
    await message.answer(text, reply_markup=get_onboarding_preferences_kb())


# --- ШАГ 2: ВКУСОВЫЕ ПРЕДПОЧТЕНИЯ И ДИЕТЫ ---

@router.callback_query(OnboardingStates.preferences, F.data == "onboarding_skip_preferences")
async def onboarding_skip_preferences(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(OnboardingStates.fridge)
    text = (
        "👌 Отлично, ограничений по диете нет.\n\n"
        "<b>Шаг 3 из 3:</b> Какие продукты сейчас есть у вас дома? Напишите списком через запятую или построчно:"
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=get_onboarding_fridge_kb())


@router.message(OnboardingStates.preferences, F.text)
async def onboarding_save_preferences(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    user_id = message.from_user.id if message.from_user else 0
    raw_text = message.text or ""
    items = [item.strip() for item in raw_text.replace("\n", ",").split(",") if item.strip()]
    if items:
        await preference_repo.add_preferences_bulk(session, user_id, "diet", items)

    await state.set_state(OnboardingStates.fridge)
    text = (
        "✅ Предпочтения сохранены!\n\n"
        "<b>Шаг 3 из 3:</b> Какие продукты сейчас есть у вас дома? "
        "Напишите списком через запятую или построчно (например: <i>«яйца, молоко, сыр, помидоры»</i>):"
    )
    await message.answer(text, reply_markup=get_onboarding_fridge_kb())


# --- ШАГ 3: СТАРТОВЫЙ ХОЛОДИЛЬНИК И ЗАВЕРШЕНИЕ ---

async def _finish_onboarding(target: Message, state: FSMContext) -> None:
    await state.clear()
    text = (
        "🎉 <b>Онбординг успешно завершен!</b>\n\n"
        "Теперь я ваш личный шеф-повар 👨‍🍳\n"
        "Вы можете:\n"
        "• Нажать <b>«🍽 Подобрать рецепт»</b> для подбора блюда из имеющихся продуктов\n"
        "• Открыть <b>«🧊 Мой холодильник»</b> для просмотра запасов\n"
        "• Или просто написать мне сообщение в свободной форме (например: <i>«Я купил сливки и пасту»</i>)"
    )
    await target.answer(text, reply_markup=get_main_keyboard())


@router.callback_query(OnboardingStates.fridge, F.data == "onboarding_skip_fridge")
async def onboarding_skip_fridge(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if callback.message:
        await callback.message.delete()
        await _finish_onboarding(callback.message, state)


@router.message(OnboardingStates.fridge, F.text)
async def onboarding_save_fridge(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    user_id = message.from_user.id if message.from_user else 0
    raw_text = message.text or ""
    raw_items = [item.strip() for item in raw_text.replace("\n", ",").split(",") if item.strip()]
    items_to_add: list[tuple[str, str | None]] = [(item, None) for item in raw_items]
    if items_to_add:
        await inventory_repo.add_inventory_items(session, user_id, items_to_add)

    await _finish_onboarding(message, state)
