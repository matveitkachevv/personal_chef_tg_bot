import logging
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from personal_chef.db.repositories import inventory_repo
from personal_chef.fsm.states import FridgeStates
from personal_chef.keyboards import (
    get_fridge_actions_kb,
    get_fridge_clear_confirm_kb,
)

logger = logging.getLogger(__name__)
router = Router(name="fridge")


def _format_inventory(items) -> str:
    if not items:
        return (
            "🧊 <b>Ваш холодильник пуст.</b>\n\n"
            "Нажмите кнопку <b>«➕ Добавить продукты»</b> ниже или просто напишите мне в чат: "
            "<i>«Купил курицу, яйца, молоко»</i>."
        )
    lines = ["🧊 <b>Продукты в вашем холодильнике:</b>\n"]
    for idx, item in enumerate(items, 1):
        if item.amount:
            lines.append(f"{idx}. {item.product_name} — <i>{item.amount}</i>")
        else:
            lines.append(f"{idx}. {item.product_name}")
    lines.append("\nЧто хотите сделать?")
    return "\n".join(lines)


@router.message(F.text == "🧊 Мой холодильник")
async def show_fridge(message: Message, session: AsyncSession) -> None:
    user_id = message.from_user.id if message.from_user else 0
    items = await inventory_repo.get_user_inventory(session, user_id)
    text = _format_inventory(items)
    await message.answer(text, reply_markup=get_fridge_actions_kb())


@router.callback_query(F.data == "fridge_add")
async def fridge_add_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(FridgeStates.waiting_for_products)
    text = (
        "➕ <b>Добавление продуктов в холодильник</b>\n\n"
        "Напишите продукты списком через запятую или с новой строки.\n"
        "<i>Пример: яйца 10 шт, сыр пармезан, помидоры 500г, молоко</i>"
    )
    if callback.message:
        await callback.message.answer(text)


@router.message(FridgeStates.waiting_for_products, F.text)
async def fridge_process_add(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    user_id = message.from_user.id if message.from_user else 0
    raw_text = message.text or ""
    raw_lines = [item.strip() for item in raw_text.replace("\n", ",").split(",") if item.strip()]

    items_to_add: list[tuple[str, str | None]] = []
    for line in raw_lines:
        items_to_add.append((line, None))

    if items_to_add:
        await inventory_repo.add_inventory_items(session, user_id, items_to_add)

    await state.clear()
    items = await inventory_repo.get_user_inventory(session, user_id)
    text = (
        f"✅ <b>Добавлено продуктов: {len(items_to_add)}!</b>\n\n"
        f"{_format_inventory(items)}"
    )
    await message.answer(text, reply_markup=get_fridge_actions_kb())


@router.callback_query(F.data == "fridge_clear")
async def fridge_clear_confirm(callback: CallbackQuery) -> None:
    await callback.answer()
    text = "⚠️ <b>Вы уверены, что хотите полностью очистить список продуктов в холодильнике?</b>"
    if callback.message:
        await callback.message.edit_text(text, reply_markup=get_fridge_clear_confirm_kb())


@router.callback_query(F.data == "fridge_cancel_clear")
async def fridge_clear_cancel(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    user_id = callback.from_user.id
    items = await inventory_repo.get_user_inventory(session, user_id)
    text = _format_inventory(items)
    if callback.message:
        await callback.message.edit_text(text, reply_markup=get_fridge_actions_kb())


@router.callback_query(F.data == "fridge_confirm_clear")
async def fridge_clear_execute(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    user_id = callback.from_user.id
    await inventory_repo.clear_user_inventory(session, user_id)
    text = (
        "🧼 <b>Холодильник полностью очищен.</b>\n\n"
        "Вы можете добавить новые продукты в любой момент!"
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=get_fridge_actions_kb())
