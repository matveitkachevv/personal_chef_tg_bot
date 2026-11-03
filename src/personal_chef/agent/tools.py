import logging
from langchain_core.tools import tool
from personal_chef.db.repositories import inventory_repo, meal_plan_repo, recipe_repo
from personal_chef.db.session import get_sessionmaker

logger = logging.getLogger(__name__)


@tool
async def get_fridge_inventory(user_id: int) -> str:
    """Получить актуальный список продуктов, имеющихся в холодильнике пользователя."""
    maker = get_sessionmaker()
    async with maker() as session:
        items = await inventory_repo.get_user_inventory(session, user_id)
        if not items:
            return "В холодильнике пользователя пока пусто."
        formatted = []
        for idx, item in enumerate(items, 1):
            if item.amount:
                formatted.append(f"{idx}. {item.product_name} ({item.amount})")
            else:
                formatted.append(f"{idx}. {item.product_name}")
        return "Продукты в холодильнике:\n" + "\n".join(formatted)


@tool
async def add_to_fridge(user_id: int, products: list[str]) -> str:
    """Добавить новые продукты в холодильник пользователя.
    
    products: список названий продуктов, например ['куриное филе', 'сыр 200г', 'яйца 10 шт']
    """
    maker = get_sessionmaker()
    async with maker() as session:
        items_to_add: list[tuple[str, str | None]] = []
        for p in products:
            clean = p.strip()
            if not clean:
                continue
            # Разделяем на имя и количество, если указано в скобках
            if "(" in clean and clean.endswith(")"):
                name, rest = clean[:-1].split("(", 1)
                items_to_add.append((name.strip(), rest.strip()))
            else:
                items_to_add.append((clean, None))

        created = await inventory_repo.add_inventory_items(session, user_id, items_to_add)
        names = [item.product_name for item in created]
        return f"Успешно добавлено в холодильник ({len(names)} шт.): {', '.join(names)}"


@tool
async def remove_from_fridge(user_id: int, products: list[str]) -> str:
    """Удалить продукты из холодильника пользователя (когда они закончились или испортились).
    
    products: список названий продуктов, например ['молоко', 'сыр']
    """
    maker = get_sessionmaker()
    async with maker() as session:
        removed = await inventory_repo.remove_inventory_items(session, user_id, products)
        if not removed:
            return f"Продукты {products} не были найдены в холодильнике."
        return f"Успешно удалено из холодильника: {', '.join(removed)}"


@tool
async def save_recipe(
    user_id: int,
    title: str,
    instructions: str,
    ingredients: list[str],
    meal_type: str = "dinner",
    cooking_time_minutes: int | None = None,
) -> str:
    """Сохранить детальный рецепт в БД и привязать его к плану питания со статусом 'planned'.
    
    title: название блюда
    instructions: пошаговый процесс приготовления
    ingredients: список ингредиентов с граммовками
    meal_type: тип приема пищи ('breakfast', 'lunch', 'dinner', 'snack')
    cooking_time_minutes: время готовки в минутах
    """
    maker = get_sessionmaker()
    async with maker() as session:
        ingredients_text = "\n".join(f"• {i.strip()}" for i in ingredients if i.strip())
        recipe = await recipe_repo.create_recipe(
            session=session,
            title=title,
            instructions=instructions,
            ingredients_text=ingredients_text,
            cooking_time_minutes=cooking_time_minutes,
        )
        plan = await meal_plan_repo.create_meal_plan(
            session=session,
            user_id=user_id,
            recipe_id=recipe.id,
            meal_type=meal_type,
            status="planned",
        )
        return f"Рецепт '{recipe.title}' сохранен! ID рецепта: {recipe.id}, ID плана: {plan.id}"
