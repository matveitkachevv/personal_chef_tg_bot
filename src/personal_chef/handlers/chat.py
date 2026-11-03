import logging
from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.types import Message

from personal_chef.agent import chat_with_agent

logger = logging.getLogger(__name__)
router = Router(name="chat")


@router.message(F.text)
async def handle_agent_chat(message: Message) -> None:
    """Обработка свободного текстового сообщения через AI-агента (LangGraph)."""
    user_id = message.from_user.id if message.from_user else 0
    user_text = message.text or ""

    if message.bot:
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    response = await chat_with_agent(user_id=user_id, message=user_text)
    await message.answer(response)
