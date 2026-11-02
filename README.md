# Персональный повар (Personal Chef) 👨‍🍳

Телеграм-бот на базе **aiogram 3.x** для подбора рецептов и составления персонального меню с учётом продуктов в холодильнике, предпочтений пользователя и норм КБЖУ.

---

## 🚀 Быстрый старт

### 1. Требования
- Python `>= 3.12`
- Менеджер пакетов [uv](https://github.com/astral-sh/uv) (рекомендуется)

### 2. Установка зависимостей
```bash
uv sync
```

### 3. Настройка окружения
Скопируйте файл с переменными окружения и укажите свой токен:
```bash
cp .env.example .env
```

Отредактируйте `.env`:
```env
BOT_TOKEN=ваш_токен_от_BotFather
LOG_LEVEL=INFO
```

### 4. Запуск бота
Через `uv`:
```bash
uv run personal-chef
```
Или напрямую через модуль:
```bash
uv run python -m personal_chef.main
```

---

## 📁 Структура проекта

```text
src/personal_chef/
├── config.py         # Настройки приложения и валидация через pydantic-settings
├── handlers/         # Обработчики сообщений и команд
│   ├── base.py       # Базовые команды (/start, /help, главное меню)
│   └── __init__.py   # Корневой роутер
├── keyboards/        # Клавиатуры бота
│   ├── inline.py     # Инлайн-кнопки
│   ├── reply.py      # Главная reply-клавиатура меню
│   └── __init__.py
├── middlewares/      # Промежуточные слои (middleware)
│   └── __init__.py
├── main.py           # Точка входа, запуск polling и регистрация команд
└── __init__.py
```

---

## 🛠 Технологический стек
- **Python**: 3.12+
- **Фреймворк**: [aiogram 3](https://docs.aiogram.dev/)
- **Конфигурация**: [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **Пакетный менеджер**: [uv](https://docs.astral.sh/uv/)
