import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from personal_chef.db.base import Base

if TYPE_CHECKING:
    from personal_chef.db.models.meal_plan import MealPlan


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    cooking_time_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    portions: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    ingredients_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), default="ai_generated", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    meal_plans: Mapped[List["MealPlan"]] = relationship(
        "MealPlan",
        back_populates="recipe",
        cascade="all, delete-orphan",
    )
