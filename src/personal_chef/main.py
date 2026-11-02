import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from personal_chef.config import get_settings
from personal_chef.handlers import get_root_router

logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot) -> None:
    """Установка списка команд в меню Telegram."""
    commands = [
        BotCommand(command="start", description="Запустить бота и главное меню"),
        BotCommand(command="help", description="Справка по функциям бота"),
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    try:
        settings = get_settings()
    except Exception as exc:
        print(
            "❌ Ошибка конфигурации: не удалось загрузить настройки.\n"
            "Убедитесь, что переменная BOT_TOKEN задана в .env или в переменных окружения.\n"
            "Пример: cp .env.example .env && nano .env",
            file=sys.stderr,
        )
        sys.exit(1)

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    logger.info("Инициализация Telegram бота 'Персональный повар'...")

    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация роутеров
    dp.include_router(get_root_router())

    try:
        await set_bot_commands(bot)
        # Сбрасываем ожидающие обновления, накопившиеся во время отключения
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Бот успешно запущен в режиме polling.")
        await dp.start_polling(bot)
    finally:
        logger.info("Завершение работы бота...")
        await bot.session.close()


def run() -> None:
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем.")
    except SystemExit as exc:
        sys.exit(exc.code)


if __name__ == "__main__":
    run()
