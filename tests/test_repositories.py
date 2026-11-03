import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from personal_chef.db.base import Base
from personal_chef.db.repositories import (
    inventory_repo,
    meal_plan_repo,
    preference_repo,
    recipe_repo,
    user_repo,
)


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as sess:
        yield sess

    await engine.dispose()


@pytest.mark.asyncio
async def test_user_repo(session: AsyncSession):
    user = await user_repo.create_or_update_user(
        session=session,
        telegram_id=123456,
        first_name="Тест",
        username="test_user",
    )
    assert user.telegram_id == 123456
    assert user.first_name == "Тест"
    assert user.username == "test_user"

    fetched = await user_repo.get_user(session, 123456)
    assert fetched is not None
    assert fetched.first_name == "Тест"

    # Update
    updated = await user_repo.create_or_update_user(
        session=session,
        telegram_id=123456,
        first_name="Обновлен",
    )
    assert updated.first_name == "Обновлен"


@pytest.mark.asyncio
async def test_preference_repo(session: AsyncSession):
    await user_repo.create_or_update_user(session, 123, "Иван")

    # Add single & bulk
    await preference_repo.add_preference(session, 123, "allergy", "арахис")
    await preference_repo.add_preferences_bulk(session, 123, "diet", ["кето", "без сахара"])

    prefs = await preference_repo.get_user_preferences(session, 123)
    assert len(prefs) == 3

    allergies = await preference_repo.get_user_preferences(session, 123, preference_type="allergy")
    assert len(allergies) == 1
    assert allergies[0].item_name == "арахис"

    # Clear
    await preference_repo.clear_preferences(session, 123, preference_type="diet")
    remaining = await preference_repo.get_user_preferences(session, 123)
    assert len(remaining) == 1
    assert remaining[0].preference_type == "allergy"


@pytest.mark.asyncio
async def test_inventory_repo(session: AsyncSession):
    await user_repo.create_or_update_user(session, 456, "Анна")

    # Add items
    items = [("молоко", "1 литр"), ("яйца", "10 шт"), ("сыр пармезан", None)]
    added = await inventory_repo.add_inventory_items(session, 456, items)
    assert len(added) == 3

    inv = await inventory_repo.get_user_inventory(session, 456)
    assert len(inv) == 3

    # Remove items by matching name
    removed = await inventory_repo.remove_inventory_items(session, 456, ["сыр", "молоко"])
    assert "молоко" in removed
    assert "сыр пармезан" in removed

    remaining = await inventory_repo.get_user_inventory(session, 456)
    assert len(remaining) == 1
    assert remaining[0].product_name == "яйца"

    # Clear
    await inventory_repo.clear_user_inventory(session, 456)
    cleared = await inventory_repo.get_user_inventory(session, 456)
    assert len(cleared) == 0


@pytest.mark.asyncio
async def test_recipe_and_meal_plan_repo(session: AsyncSession):
    await user_repo.create_or_update_user(session, 789, "Олег")

    recipe = await recipe_repo.create_recipe(
        session=session,
        title="Омлет с сыром",
        instructions="1. Взбейте яйца.\n2. Жарьте 5 минут.",
        ingredients_text="• Яйца — 3 шт\n• Сыр — 50 г",
        cooking_time_minutes=10,
        portions=1,
    )
    assert recipe.id is not None
    assert recipe.title == "Омлет с сыром"

    plan = await meal_plan_repo.create_meal_plan(
        session=session,
        user_id=789,
        recipe_id=recipe.id,
        meal_type="breakfast",
        status="planned",
    )
    assert plan.status == "planned"

    # Update status to cooked
    updated_plan = await meal_plan_repo.update_meal_plan_status(session, plan.id, "cooked")
    assert updated_plan is not None
    assert updated_plan.status == "cooked"

    fetched_plan = await meal_plan_repo.get_latest_meal_plan_by_recipe(session, 789, recipe.id)
    assert fetched_plan is not None
    assert fetched_plan.status == "cooked"
