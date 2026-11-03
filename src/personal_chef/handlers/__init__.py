from aiogram import Router

from personal_chef.handlers.base import router as base_router
from personal_chef.handlers.chat import router as chat_router
from personal_chef.handlers.fridge import router as fridge_router
from personal_chef.handlers.onboarding import router as onboarding_router
from personal_chef.handlers.preferences import router as preferences_router
from personal_chef.handlers.recipes import router as recipes_router


def get_root_router() -> Router:
    root_router = Router(name="root")
    # Регистрируем роутеры в строгом порядке приоритета
    root_router.include_router(base_router)
    root_router.include_router(onboarding_router)
    root_router.include_router(fridge_router)
    root_router.include_router(preferences_router)
    root_router.include_router(recipes_router)
    # Чат-агент ловит все остальные произвольные текстовые сообщения в конце
    root_router.include_router(chat_router)
    return root_router


__all__ = ["get_root_router"]
