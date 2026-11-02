from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from personal_chef.keyboards import get_help_inline_keyboard, get_main_keyboard

router = Router(name="base")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user_name = message.from_user.first_name if message.from_user else "друг"
    text = (
        f"👋 <b>Привет, {user_name}!</b>\n\n"
        "Я — <b>Персональный повар</b> 👨‍🍳\n\n"
        "Я помогу подобрать идеальные рецепты с учётом продуктов в твоём холодильнике, "
        "вкусовых предпочтений и норм КБЖУ.\n\n"
        "Воспользуйся меню ниже, чтобы начать работу:"
    )
    await message.answer(text, reply_markup=get_main_keyboard())


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message) -> None:
    text = (
        "📋 <b>Команды и возможности бота:</b>\n\n"
        "• /start — Запуск бота и вызов главного меню\n"
        "• /help — Справка по функциям бота\n\n"
        "<b>В разработке:</b>\n"
        "• 🧊 <i>Мой холодильник</i> — учёт имеющихся продуктов\n"
        "• 🍽 <i>Подбор рецептов</i> — генерация персонального меню\n"
        "• ⚙️ <i>Предпочтения</i> — настройка аллергий, диеты и целевого белка"
    )
    await message.answer(text, reply_markup=get_help_inline_keyboard())


@router.callback_query(F.data == "about_project")
async def cb_about_project(callback: CallbackQuery) -> None:
    text = (
        "🍳 <b>О проекте «Персональный повар»</b>\n\n"
        "Умный ассистент на базе AI, который планирует рацион, "
        "экономит время на покупках и помогает готовить полезную еду "
        "из того, что уже есть дома."
    )
    if callback.message:
        await callback.message.answer(text)
    await callback.answer()


@router.message(F.text == "🍽 Подобрать рецепт")
async def btn_recipes(message: Message) -> None:
    await message.answer(
        "🍽 Модуль подбора рецептов находится в разработке. Скоро здесь появится подбор блюд с учётом вашего холодильника!"
    )


@router.message(F.text == "🧊 Мой холодильник")
async def btn_fridge(message: Message) -> None:
    await message.answer(
        "🧊 Модуль управления холодильником находится в разработке. Скоро вы сможете добавлять и отмечать продукты!"
    )


@router.message(F.text == "⚙️ Предпочтения")
async def btn_preferences(message: Message) -> None:
    await message.answer(
        "⚙️ Модуль предпочтений находится в разработке. Здесь можно будет настроить аллергии, калории и норму белка!"
    )
