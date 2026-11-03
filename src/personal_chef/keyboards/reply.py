from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню бота (Reply Keyboard)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🍽 Подобрать рецепт"),
                KeyboardButton(text="🧊 Мой холодильник"),
            ],
            [
                KeyboardButton(text="⚙️ Предпочтения"),
                KeyboardButton(text="ℹ️ Помощь"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие или напишите шефу...",
    )
