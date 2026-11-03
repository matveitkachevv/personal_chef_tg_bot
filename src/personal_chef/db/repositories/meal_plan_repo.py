import datetime
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from personal_chef.db.models.meal_plan import MealPlan


async def create_meal_plan(
    session: AsyncSession,
    user_id: int,
    recipe_id: uuid.UUID,
    meal_type: str,
    plan_date: datetime.date | None = None,
    ai_notes: str | None = None,
    status: str = "planned",
) -> MealPlan:
    plan = MealPlan(
        user_id=user_id,
        recipe_id=recipe_id,
        meal_type=meal_type,
        plan_date=plan_date or datetime.date.today(),
        ai_notes=ai_notes,
        status=status,
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan


async def get_meal_plan(session: AsyncSession, meal_plan_id: uuid.UUID) -> MealPlan | None:
    stmt = (
        select(MealPlan)
        .options(selectinload(MealPlan.recipe))
        .where(MealPlan.id == meal_plan_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_latest_meal_plan_by_recipe(
    session: AsyncSession,
    user_id: int,
    recipe_id: uuid.UUID,
) -> MealPlan | None:
    stmt = (
        select(MealPlan)
        .options(selectinload(MealPlan.recipe))
        .where(MealPlan.user_id == user_id, MealPlan.recipe_id == recipe_id)
        .order_by(MealPlan.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().first()


async def update_meal_plan_status(
    session: AsyncSession,
    meal_plan_id: uuid.UUID,
    status: str,
) -> MealPlan | None:
    plan = await get_meal_plan(session, meal_plan_id)
    if plan:
        plan.status = status
        await session.commit()
        await session.refresh(plan)
    return plan
