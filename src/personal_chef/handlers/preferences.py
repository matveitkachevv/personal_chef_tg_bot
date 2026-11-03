import logging
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from personal_chef.db.repositories import preference_repo
from personal_chef.fsm.states import PreferenceStates
from personal_chef.keyboards import get_preferences_kb

logger = logging.getLogger(__name__)
router = Router(name="preferences")


def _format_preferences(preferences) -> str:
    allergies = [p.item_name for p in preferences if p.preference_type == "allergy"]
    diets = [p.item_name for p in preferences if p.preference_type in ("diet", "favorite")]
    dislikes = [p.item_name for p in preferences if p.preference_type == "dislike"]

    lines = ["⚙️ <b>Ваш кулинарный профиль:</b>\n"]
    if allergies:
        lines.append(f"🚫 <b>Аллергии и непереносимости (жесткий бан):</b>\n• {', '.join(allergies)}")
    else:
        lines.append("🚫 <b>Аллергии и непереносимости:</b> <i>не указаны</i>")

    lines.append("")
    if diets:
        lines.append(f"🥗 <b>Диеты и вкусовые предпочтения:</b>\n• {', '.join(diets)}")
    else:
        lines.append("🥗 <b>Диеты и вкусовые предпочтения:</b> <i>ем всё</i>")

    if dislikes:
        lines.append("")
        lines.append(f"👎 <b>Нелюбимые продукты:</b>\n• {', '.join(dislikes)}")

    lines.append("\nВы можете дополнить или очистить свои настройки кнопками ниже:")
    return "\n".join(lines)


@router.message(F.text == "⚙️ Предпочтения")
async def show_preferences(message: Message, session: AsyncSession) -> None:
    user_id = message.from_user.id if message.from_user else 0
    prefs = await preference_repo.get_user_preferences(session, user_id)
    text = _format_preferences(prefs)
    await message.answer(text, reply_markup=get_preferences_kb())


@router.callback_query(F.data == "pref_add_allergy")
async def prompt_add_allergy(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(PreferenceStates.waiting_for_allergy)
    text = (
        "🚫 <b>Добавление аллергенов / стоп-продуктов</b>\n\n"
        "Напишите названия продуктов, которые вам категорически нельзя (через запятую):\n"
        "<i>Пример: арахис, мёд, креветки</i>"
    )
    if callback.message:
        await callback.message.answer(text)


@router.message(PreferenceStates.waiting_for_allergy, F.text)
async def process_add_allergy(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    user_id = message.from_user.id if message.from_user else 0
    raw_text = message.text or ""
    items = [item.strip() for item in raw_text.replace("\n", ",").split(",") if item.strip()]
    if items:
        await preference_repo.add_preferences_bulk(session, user_id, "allergy", items)

    await state.clear()
    prefs = await preference_repo.get_user_preferences(session, user_id)
    await message.answer(
        f"✅ Аллергии обновлены!\n\n{_format_preferences(prefs)}",
        reply_markup=get_preferences_kb(),
    )


@router.callback_query(F.data == "pref_add_diet")
async def prompt_add_diet(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(PreferenceStates.waiting_for_preference)
    text = (
        "🥗 <b>Добавление диеты или вкусового предпочтения</b>\n\n"
        "Напишите диеты или любимые кухни (через запятую):\n"
        "<i>Пример: кето, без сахара, итальянская кухня, больше рыбы</i>"
    )
    if callback.message:
        await callback.message.answer(text)


@router.message(PreferenceStates.waiting_for_preference, F.text)
async def process_add_diet(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    user_id = message.from_user.id if message.from_user else 0
    raw_text = message.text or ""
    items = [item.strip() for item in raw_text.replace("\n", ",").split(",") if item.strip()]
    if items:
        await preference_repo.add_preferences_bulk(session, user_id, "diet", items)

    await state.clear()
    prefs = await preference_repo.get_user_preferences(session, user_id)
    await message.answer(
        f"✅ Предпочтения сохранены!\n\n{_format_preferences(prefs)}",
        reply_markup=get_preferences_kb(),
    )


@router.callback_query(F.data == "pref_clear_all")
async def clear_all_preferences(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    user_id = callback.from_user.id
    await preference_repo.clear_preferences(session, user_id)
    text = "🗑 <b>Все ваши предпочтения и аллергии были очищены.</b>"
    if callback.message:
        await callback.message.edit_text(text, reply_markup=get_preferences_kb())
