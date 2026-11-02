from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_help_inline_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-кнопки для раздела помощи."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📖 О проекте",
                    callback_data="about_project",
                ),
            ],
        ]
    )
