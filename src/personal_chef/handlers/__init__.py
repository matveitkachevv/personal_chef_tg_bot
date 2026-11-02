from aiogram import Router

from personal_chef.handlers.base import router as base_router


def get_root_router() -> Router:
    root_router = Router(name="root")
    root_router.include_router(base_router)
    return root_router


__all__ = ["get_root_router"]
