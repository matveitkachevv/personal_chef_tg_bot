from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from personal_chef.db.base import Base

if TYPE_CHECKING:
    from personal_chef.db.models.inventory import UserInventory
    from personal_chef.db.models.meal_plan import MealPlan
    from personal_chef.db.models.preference import UserPreference


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    preferences: Mapped[List["UserPreference"]] = relationship(
        "UserPreference",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    inventory: Mapped[List["UserInventory"]] = relationship(
        "UserInventory",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    meal_plans: Mapped[List["MealPlan"]] = relationship(
        "MealPlan",
        back_populates="user",
        cascade="all, delete-orphan",
    )
