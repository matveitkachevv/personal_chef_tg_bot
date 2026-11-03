import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import personal_chef.db.session as session_mod
from personal_chef.agent.graph import (
    chat_with_agent,
    generate_full_recipe_text,
    generate_meal_options,
    get_thread_id,
    get_user_proposals,
    reset_user_thread,
    save_user_proposals,
)
from personal_chef.agent.prompts import OFFTOPIC_REFUSAL
from personal_chef.agent.tools import (
    add_to_fridge,
    get_fridge_inventory,
    remove_from_fridge,
    save_recipe,
)
from personal_chef.db.base import Base
from personal_chef.db.repositories import inventory_repo, user_repo


@pytest.fixture(autouse=True)
async def setup_test_db(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    monkeypatch.setattr(session_mod, "_engine", engine)
    monkeypatch.setattr(session_mod, "_sessionmaker", maker)

    yield

    await engine.dispose()


@pytest.mark.asyncio
async def test_agent_tools():
    maker = session_mod.get_sessionmaker()
    async with maker() as session:
        await user_repo.create_or_update_user(session, 1001, "ШефТест")

    # 1. get_fridge_inventory when empty
    empty_result = await get_fridge_inventory.ainvoke({"user_id": 1001})
    assert "пусто" in empty_result

    # 2. add_to_fridge
    add_result = await add_to_fridge.ainvoke(
        {"user_id": 1001, "products": ["куриное филе (500г)", "сыр", "яйца (10 шт)"]}
    )
    assert "Успешно добавлено" in add_result

    # 3. get_fridge_inventory with items
    inv_result = await get_fridge_inventory.ainvoke({"user_id": 1001})
    assert "куриное филе" in inv_result
    assert "сыр" in inv_result
    assert "яйца" in inv_result

    # 4. remove_from_fridge
    rem_result = await remove_from_fridge.ainvoke(
        {"user_id": 1001, "products": ["сыр"]}
    )
    assert "Успешно удалено" in rem_result

    inv_after = await get_fridge_inventory.ainvoke({"user_id": 1001})
    assert "сыр" not in inv_after

    # 5. save_recipe
    save_result = await save_recipe.ainvoke(
        {
            "user_id": 1001,
            "title": "Курица на сковороде",
            "instructions": "1. Обжарить курицу.",
            "ingredients": ["Куриное филе — 500г", "Масло"],
            "meal_type": "dinner",
            "cooking_time_minutes": 25,
        }
    )
    assert "сохранен" in save_result


@pytest.mark.asyncio
async def test_agent_guardrails_offtopic():
    # Проверка быстрого guardrail на оффтоп без обращения к LLM
    response = await chat_with_agent(
        user_id=1002,
        message="Какая завтра погода в Париже и кто президент США?",
    )
    assert response == OFFTOPIC_REFUSAL


@pytest.mark.asyncio
async def test_thread_reset():
    user_id = 1003
    t1 = get_thread_id(user_id)
    reset_user_thread(user_id)
    t2 = get_thread_id(user_id)
    assert t1 != t2


@pytest.mark.asyncio
async def test_generate_meal_options_and_proposals_cache():
    user_id = 1004
    proposals = await generate_meal_options(
        user_id=user_id,
        meal_type="Завтрак",
        preferences_summary="Без аллергий",
        fridge_summary="яйца, молоко, сыр",
    )
    assert len(proposals) in (2, 3)
    assert "title" in proposals[0]

    save_user_proposals(user_id, proposals)
    cached = get_user_proposals(user_id)
    assert len(cached) == len(proposals)
    assert cached[0]["title"] == proposals[0]["title"]


@pytest.mark.asyncio
async def test_generate_full_recipe():
    recipe = await generate_full_recipe_text(
        dish_title="Быстрый омлет",
        meal_type="Завтрак",
        preferences_summary="Нет аллергий",
        fridge_summary="яйца, сыр",
    )
    assert "title" in recipe
    assert "instructions" in recipe
    assert "ingredients" in recipe
