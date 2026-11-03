from unittest.mock import AsyncMock, MagicMock
import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage, StorageKey
from aiogram.types import CallbackQuery, Chat, Message, User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import personal_chef.db.session as session_mod
from personal_chef.db.base import Base
from personal_chef.db.repositories import inventory_repo, preference_repo, user_repo
from personal_chef.fsm.states import FridgeStates, OnboardingStates
from personal_chef.handlers.base import cmd_help, cmd_reset, cmd_start
from personal_chef.handlers.fridge import (
    fridge_clear_execute,
    fridge_process_add,
    show_fridge,
)
from personal_chef.handlers.onboarding import (
    onboarding_save_allergies,
    onboarding_save_preferences,
    onboarding_skip_allergies,
    onboarding_skip_fridge,
    onboarding_skip_preferences,
)
from personal_chef.handlers.preferences import (
    clear_all_preferences,
    process_add_allergy,
    show_preferences,
)
from personal_chef.handlers.recipes import (
    process_confirm_deduct,
    process_cooked_dish,
    process_dish_selection,
    process_meal_type_selection,
)


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    session_mod._engine = engine
    session_mod._sessionmaker = maker

    async with maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def fsm_context():
    storage = MemoryStorage()
    key = StorageKey(bot_id=123, chat_id=100, user_id=100)
    return FSMContext(storage=storage, key=key)


def make_message(text: str, user_id: int = 100, first_name: str = "Алексей") -> MagicMock:
    msg = MagicMock()
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    msg.from_user.first_name = first_name
    msg.from_user.username = "alex"
    msg.text = text
    msg.answer = AsyncMock()
    msg.edit_text = AsyncMock()
    msg.delete = AsyncMock()
    msg.chat = MagicMock()
    msg.chat.id = user_id
    msg.bot = MagicMock()
    msg.bot.send_chat_action = AsyncMock()
    return msg


def make_callback(data: str, user_id: int = 100) -> MagicMock:
    cb = MagicMock()
    cb.from_user = MagicMock()
    cb.from_user.id = user_id
    cb.from_user.first_name = "Алексей"
    cb.from_user.username = "alex"
    cb.data = data
    cb.message = make_message("", user_id=user_id)
    cb.answer = AsyncMock()
    return cb


@pytest.mark.asyncio
async def test_onboarding_full_flow(db_session: AsyncSession, fsm_context: FSMContext):
    user_id = 201

    # 1. /start для нового пользователя
    msg_start = make_message("/start", user_id=user_id, first_name="Мария")
    await cmd_start(msg_start, fsm_context, db_session)

    state = await fsm_context.get_state()
    assert state == OnboardingStates.allergies.state
    assert "Шаг 1 из 3" in msg_start.answer.call_args[0][0]

    # Проверяем создание пользователя в БД
    user = await user_repo.get_user(db_session, user_id)
    assert user is not None
    assert user.first_name == "Мария"

    # 2. Шаг 1: ввод аллергий
    msg_allergies = make_message("арахис, креветки", user_id=user_id)
    await onboarding_save_allergies(msg_allergies, fsm_context, db_session)

    state = await fsm_context.get_state()
    assert state == OnboardingStates.preferences.state
    assert "Шаг 2 из 3" in msg_allergies.answer.call_args[0][0]

    allergies = await preference_repo.get_user_preferences(db_session, user_id, "allergy")
    assert len(allergies) == 2
    assert {a.item_name for a in allergies} == {"арахис", "креветки"}

    # 3. Шаг 2: ввод диеты
    msg_pref = make_message("вегетарианство, кето", user_id=user_id)
    await onboarding_save_preferences(msg_pref, fsm_context, db_session)

    state = await fsm_context.get_state()
    assert state == OnboardingStates.fridge.state
    assert "Шаг 3 из 3" in msg_pref.answer.call_args[0][0]

    diets = await preference_repo.get_user_preferences(db_session, user_id, "diet")
    assert len(diets) == 2

    # 4. Шаг 3: пропуск холодильника
    cb_fridge = make_callback("onboarding_skip_fridge", user_id=user_id)
    await onboarding_skip_fridge(cb_fridge, fsm_context)

    state = await fsm_context.get_state()
    assert state is None  # FSM завершен


@pytest.mark.asyncio
async def test_onboarding_skip_buttons(db_session: AsyncSession, fsm_context: FSMContext):
    user_id = 202
    await user_repo.create_or_update_user(db_session, user_id, "Иван")

    # Пропуск аллергий
    cb_allergies = make_callback("onboarding_skip_allergies", user_id=user_id)
    await onboarding_skip_allergies(cb_allergies, fsm_context)
    state = await fsm_context.get_state()
    assert state == OnboardingStates.preferences.state

    # Пропуск диет
    cb_pref = make_callback("onboarding_skip_preferences", user_id=user_id)
    await onboarding_skip_preferences(cb_pref, fsm_context)
    state = await fsm_context.get_state()
    assert state == OnboardingStates.fridge.state


@pytest.mark.asyncio
async def test_existing_user_start_and_reset(db_session: AsyncSession, fsm_context: FSMContext):
    user_id = 203
    await user_repo.create_or_update_user(db_session, user_id, "Петр")

    msg_start = make_message("/start", user_id=user_id, first_name="Петр")
    await cmd_start(msg_start, fsm_context, db_session)

    state = await fsm_context.get_state()
    assert state is None
    assert "С возвращением" in msg_start.answer.call_args[0][0]

    # /reset
    msg_reset = make_message("/reset", user_id=user_id)
    await cmd_reset(msg_reset, fsm_context)
    assert "Диалог с шефом сброшен" in msg_reset.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_fridge_handlers(db_session: AsyncSession, fsm_context: FSMContext):
    user_id = 204
    await user_repo.create_or_update_user(db_session, user_id, "Сергей")

    # Пустой холодильник
    msg_view = make_message("🧊 Мой холодильник", user_id=user_id)
    await show_fridge(msg_view, db_session)
    assert "холодильник пуст" in msg_view.answer.call_args[0][0]

    # Добавление продуктов через FSM
    msg_add = make_message("сыр, яйца, томаты", user_id=user_id)
    await fridge_process_add(msg_add, fsm_context, db_session)
    assert "Добавлено продуктов: 3" in msg_add.answer.call_args[0][0]

    inv = await inventory_repo.get_user_inventory(db_session, user_id)
    assert len(inv) == 3

    # Очистка холодильника
    cb_clear = make_callback("fridge_confirm_clear", user_id=user_id)
    await fridge_clear_execute(cb_clear, db_session)
    inv_after = await inventory_repo.get_user_inventory(db_session, user_id)
    assert len(inv_after) == 0


@pytest.mark.asyncio
async def test_preferences_handlers(db_session: AsyncSession, fsm_context: FSMContext):
    user_id = 205
    await user_repo.create_or_update_user(db_session, user_id, "Ольга")

    # Показ пустого профиля
    msg = make_message("⚙️ Предпочтения", user_id=user_id)
    await show_preferences(msg, db_session)
    assert "не указаны" in msg.answer.call_args[0][0]

    # Добавление аллергии
    msg_add_all = make_message("глютен, соя", user_id=user_id)
    await process_add_allergy(msg_add_all, fsm_context, db_session)
    assert "глютен" in msg_add_all.answer.call_args[0][0]

    # Очистка
    cb_clear = make_callback("pref_clear_all", user_id=user_id)
    await clear_all_preferences(cb_clear, db_session)
    prefs = await preference_repo.get_user_preferences(db_session, user_id)
    assert len(prefs) == 0


@pytest.mark.asyncio
async def test_recipe_generation_and_deduction_flow(db_session: AsyncSession):
    user_id = 206
    await user_repo.create_or_update_user(db_session, user_id, "Дмитрий")
    await inventory_repo.add_inventory_items(
        db_session,
        user_id,
        [("куриное филе", "400г"), ("сыр", "100г"), ("помидоры", "2 шт")],
    )

    # 1. Выбор типа приема пищи -> 2-3 варианта
    cb_meal = make_callback("meal_type:dinner", user_id=user_id)
    await process_meal_type_selection(cb_meal, db_session)

    # 2. Выбор первого блюда
    cb_dish = make_callback("select_dish:0", user_id=user_id)
    await process_dish_selection(cb_dish, db_session)

    # 3. Фиксация приготовления (cooked)
    from personal_chef.db.models.recipe import Recipe
    from sqlalchemy import select
    res = await db_session.execute(select(Recipe))
    recipe = res.scalars().first()
    assert recipe is not None

    cb_cooked = make_callback(f"cooked:{recipe.id}", user_id=user_id)
    await process_cooked_dish(cb_cooked, db_session)
    assert "отмечено как приготовленное" in cb_cooked.message.answer.call_args[0][0]

    # 4. Подтверждение списания продуктов
    cb_deduct = make_callback(f"confirm_deduct:{recipe.id}", user_id=user_id)
    await process_confirm_deduct(cb_deduct, db_session)
    assert "списаны из холодильника" in cb_deduct.message.edit_text.call_args[0][0]
