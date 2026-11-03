import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from personal_chef.db.models.recipe import Recipe


async def create_recipe(
    session: AsyncSession,
    title: str,
    instructions: str,
    ingredients_text: str,
    description: str | None = None,
    cooking_time_minutes: int | None = None,
    portions: int = 1,
    source_type: str = "ai_generated",
) -> Recipe:
    recipe = Recipe(
        title=title.strip(),
        instructions=instructions.strip(),
        ingredients_text=ingredients_text.strip(),
        description=description.strip() if description else None,
        cooking_time_minutes=cooking_time_minutes,
        portions=portions,
        source_type=source_type,
    )
    session.add(recipe)
    await session.commit()
    await session.refresh(recipe)
    return recipe


async def get_recipe(session: AsyncSession, recipe_id: uuid.UUID) -> Recipe | None:
    result = await session.execute(select(Recipe).where(Recipe.id == recipe_id))
    return result.scalar_one_or_none()
