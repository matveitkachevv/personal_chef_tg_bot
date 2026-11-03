import logging
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from personal_chef.agent import reset_user_thread
from personal_chef.db.repositories import preference_repo, user_repo
from personal_chef.fsm.states import OnboardingStates
from personal_chef.keyboards import (
    get_help_inline_keyboard,
    get_main_keyboard,
    get_onboarding_allergies_kb,
)

logger = logging.getLogger(__name__)
router = Router(name="base")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Обработчик /start: регистрация, онбординг или главное меню."""
    await state.clear()
    telegram_id = message.from_user.id if message.from_user else 0
    first_name = message.from_user.first_name if message.from_user else "друг"
    username = message.from_user.username if message.from_user else None

    # Проверяем наличие пользователя в БД
    existing_user = await user_repo.get_user(session, telegram_id)
    if existing_user is None:
        await user_repo.create_or_update_user(
            session=session,
            telegram_id=telegram_id,
            first_name=first_name,
            username=username,
        )
        # Запускаем FSM-онбординг для нового пользователя
        await state.set_state(OnboardingStates.allergies)
        welcome_text = (
            f"👋 <b>Привет, {first_name}!</b>\n\n"
            "Я — твой <b>Персональный повар</b> 👨‍🍳\n"
            "Я помогу готовить вкусные блюда из того, что уже есть в твоем холодильнике, "
            "строго учитывая твои аллергии и вкусы.\n\n"
            "Давай настроим твой профиль за пару быстрых шагов!\n\n"
            "<b>Шаг 1 из 3:</b> Есть ли у тебя аллергии или продукты, которые ты строго не употребляешь?"
        )
        await message.answer(welcome_text, reply_markup=get_onboarding_allergies_kb())
        return

    # Существующий пользователь: выводим приветствие и главное меню
    await user_repo.create_or_update_user(
        session=session,
        telegram_id=telegram_id,
        first_name=first_name,
        username=username,
    )
    text = (
        f"👋 <b>С возвращением, {first_name}!</b> 👨‍🍳\n\n"
        "Чем займемся сегодня? Выберите действие в меню ниже или просто напишите мне, "
        "что у вас на уме (например: <i>«купил сыр и пасту»</i> или <i>«что приготовить на обед?»</i>)."
    )
    await message.answer(text, reply_markup=get_main_keyboard())


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message) -> None:
    """Справка по функциям бота."""
    text = (
        "📋 <b>Справка по «Персональному повару»</b> 👨‍🍳\n\n"
        "<b>Команды:</b>\n"
        "• /start — Запуск бота, онбординг и вызов главного меню\n"
        "• /help — Справка и подсказки по работе\n"
        "• /reset — Сброс текущего диалога с AI-шефом (профиль и холодильник сохраняются)\n\n"
        "<b>Разделы меню:</b>\n"
        "• 🍽 <b>Подобрать рецепт</b> — выбор приема пищи и генерация 2-3 вариантов блюд под холодильник\n"
        "• 🧊 <b>Мой холодильник</b> — просмотр, добавление продуктов и очистка\n"
        "• ⚙️ <b>Предпочтения</b> — настройка аллергий, диет и нелюбимых продуктов\n\n"
        "💬 <b>Свободный чат с шефом:</b>\n"
        "Вы можете писать боту человеческим языком:\n"
        "<i>«Купил 10 яиц, пачку спагетти и бекон»</i> — шеф добавит их в холодильник.\n"
        "<i>«Закончилось молоко»</i> — шеф уберет его из наличия.\n"
        "<i>«Придумай быстрый десерт»</i> — шеф предложит блюдо!"
    )
    await message.answer(text, reply_markup=get_help_inline_keyboard())


@router.message(Command("reset"))
async def cmd_reset(message: Message, state: FSMContext) -> None:
    """Сброс диалоговой истории с AI-агентом."""
    await state.clear()
    user_id = message.from_user.id if message.from_user else 0
    reset_user_thread(user_id)
    text = (
        "🧹 <b>Диалог с шефом сброшен!</b>\n\n"
        "Контекст беседы очищен, но ваши предпочтения и продукты в холодильнике в полной сохранности. "
        "Готов к новым кулинарным задачам!"
    )
    await message.answer(text, reply_markup=get_main_keyboard())


@router.callback_query(F.data == "about_project")
async def cb_about_project(callback: CallbackQuery) -> None:
    text = (
        "🍳 <b>О проекте «Персональный повар»</b>\n\n"
        "Умный ассистент на базе AI (Google Gemini + LangGraph), который подбирает блюда под содержимое "
        "вашего холодильника, исключает аллергены и помогает готовить пошагово без лишних хлопот!"
    )
    if callback.message:
        await callback.message.answer(text)
    await callback.answer()
