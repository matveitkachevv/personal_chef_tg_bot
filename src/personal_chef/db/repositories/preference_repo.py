import uuid
from typing import Sequence
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from personal_chef.db.models.preference import UserPreference


async def get_user_preferences(
    session: AsyncSession,
    user_id: int,
    preference_type: str | None = None,
) -> Sequence[UserPreference]:
    stmt = select(UserPreference).where(UserPreference.user_id == user_id)
    if preference_type:
        stmt = stmt.where(UserPreference.preference_type == preference_type)
    result = await session.execute(stmt)
    return result.scalars().all()


async def add_preference(
    session: AsyncSession,
    user_id: int,
    preference_type: str,
    item_name: str,
) -> UserPreference:
    pref = UserPreference(
        user_id=user_id,
        preference_type=preference_type,
        item_name=item_name.strip(),
    )
    session.add(pref)
    await session.commit()
    await session.refresh(pref)
    return pref


async def add_preferences_bulk(
    session: AsyncSession,
    user_id: int,
    preference_type: str,
    items: list[str],
) -> list[UserPreference]:
    created: list[UserPreference] = []
    for item in items:
        clean_item = item.strip()
        if clean_item:
            pref = UserPreference(
                user_id=user_id,
                preference_type=preference_type,
                item_name=clean_item,
            )
            session.add(pref)
            created.append(pref)
    if created:
        await session.commit()
        for p in created:
            await session.refresh(p)
    return created


async def clear_preferences(
    session: AsyncSession,
    user_id: int,
    preference_type: str | None = None,
) -> int:
    stmt = delete(UserPreference).where(UserPreference.user_id == user_id)
    if preference_type:
        stmt = stmt.where(UserPreference.preference_type == preference_type)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount or 0


async def delete_preference_by_id(
    session: AsyncSession,
    user_id: int,
    preference_id: uuid.UUID,
) -> bool:
    stmt = (
        delete(UserPreference)
        .where(UserPreference.user_id == user_id)
        .where(UserPreference.id == preference_id)
    )
    result = await session.execute(stmt)
    await session.commit()
    return (result.rowcount or 0) > 0
