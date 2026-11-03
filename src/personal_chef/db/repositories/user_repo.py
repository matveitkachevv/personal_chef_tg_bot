from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from personal_chef.db.models.user import User


async def get_user(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def create_or_update_user(
    session: AsyncSession,
    telegram_id: int,
    first_name: str,
    username: str | None = None,
) -> User:
    user = await get_user(session, telegram_id)
    if user is None:
        user = User(
            telegram_id=telegram_id,
            first_name=first_name,
            username=username,
        )
        session.add(user)
    else:
        user.first_name = first_name
        if username is not None:
            user.username = username
    await session.commit()
    await session.refresh(user)
    return user
