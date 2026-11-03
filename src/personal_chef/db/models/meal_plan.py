import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from personal_chef.db.base import Base

if TYPE_CHECKING:
    from personal_chef.db.models.recipe import Recipe
    from personal_chef.db.models.user import User


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
    )
    meal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    plan_date: Mapped[date] = mapped_column(
        Date,
        server_default=func.current_date(),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False)
    ai_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="meal_plans")
    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="meal_plans")
