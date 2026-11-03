from typing import Sequence
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from personal_chef.db.models.inventory import UserInventory


async def get_user_inventory(session: AsyncSession, user_id: int) -> Sequence[UserInventory]:
    stmt = (
        select(UserInventory)
        .where(UserInventory.user_id == user_id)
        .order_by(UserInventory.product_name)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def add_inventory_items(
    session: AsyncSession,
    user_id: int,
    items: list[tuple[str, str | None]],
) -> list[UserInventory]:
    created: list[UserInventory] = []
    for product_name, amount in items:
        clean_name = product_name.strip()
        if not clean_name:
            continue
        clean_amount = amount.strip() if amount else None
        item = UserInventory(
            user_id=user_id,
            product_name=clean_name,
            amount=clean_amount,
        )
        session.add(item)
        created.append(item)
    if created:
        await session.commit()
        for i in created:
            await session.refresh(i)
    return created


async def remove_inventory_items(
    session: AsyncSession,
    user_id: int,
    product_names: list[str],
) -> list[str]:
    """Удаляет продукты из холодильника пользователя по списку имен (регистронезависимо).
    
    Возвращает список удаленных наименований.
    """
    current_items = await get_user_inventory(session, user_id)
    removed_names: list[str] = []
    
    clean_targets = [name.strip().lower() for name in product_names if name.strip()]
    if not clean_targets:
        return []

    for item in current_items:
        item_lower = item.product_name.lower()
        # Проверяем прямое совпадение или вхождение
        for target in clean_targets:
            if target == item_lower or target in item_lower or item_lower in target:
                await session.delete(item)
                removed_names.append(item.product_name)
                break

    if removed_names:
        await session.commit()

    return removed_names


async def clear_user_inventory(session: AsyncSession, user_id: int) -> int:
    stmt = delete(UserInventory).where(UserInventory.user_id == user_id)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount or 0
