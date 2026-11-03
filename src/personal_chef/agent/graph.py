import json
import logging
import re
from typing import Any
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from personal_chef.agent.prompts import CHEF_SYSTEM_PROMPT, OFFTOPIC_REFUSAL
from personal_chef.agent.tools import (
    add_to_fridge,
    get_fridge_inventory,
    remove_from_fridge,
    save_recipe,
)
from personal_chef.config import get_settings

logger = logging.getLogger(__name__)

# Хранилище версий тредов для мгновенного сброса контекста диалога (/reset)
_thread_versions: dict[int, int] = {}
_memory_saver = MemorySaver()

# Кэш предложенных вариантов блюд для каждого пользователя (для выбора по кнопке)
_user_dish_proposals: dict[int, list[dict[str, Any]]] = {}

TOOLS = [get_fridge_inventory, add_to_fridge, remove_from_fridge, save_recipe]


def get_thread_id(user_id: int) -> str:
    version = _thread_versions.get(user_id, 1)
    return f"tg_{user_id}_v{version}"


def reset_user_thread(user_id: int) -> None:
    """Сбросить диалоговый поток пользователя (/reset)."""
    current = _thread_versions.get(user_id, 1)
    _thread_versions[user_id] = current + 1
    _user_dish_proposals.pop(user_id, None)
    logger.info("Сброшен диалоговый поток для user_id=%s, новая версия=%s", user_id, current + 1)


def save_user_proposals(user_id: int, proposals: list[dict[str, Any]]) -> None:
    _user_dish_proposals[user_id] = proposals


def get_user_proposals(user_id: int) -> list[dict[str, Any]]:
    return _user_dish_proposals.get(user_id, [])


def get_llm(model_name: str | None = None) -> ChatGoogleGenerativeAI | None:
    settings = get_settings()
    if not settings.gemini_api_key or not settings.gemini_api_key.get_secret_value():
        return None
    return ChatGoogleGenerativeAI(
        model=model_name or settings.gemini_model,
        google_api_key=settings.gemini_api_key.get_secret_value(),
        temperature=0.4,
    )


def get_agent_executor():
    llm = get_llm()
    if llm is None:
        return None
    return create_react_agent(
        model=llm,
        tools=TOOLS,
        checkpointer=_memory_saver,
        prompt=CHEF_SYSTEM_PROMPT,
    )


async def chat_with_agent(user_id: int, message: str) -> str:
    """Обработка свободного текстового сообщения пользователя через ReAct агента."""
    # Быстрый эвристический guardrail для явного оффтопа (погода, крипта, политика, код)
    offtopic_keywords = [
        "погода", "курс доллара", "биткоин", "крипта", "президент",
        "война", "напиши код", "напиши программу", "кто такой путин",
        "футбол счет", "новости сегодня",
    ]
    lower_msg = message.lower()
    if any(kw in lower_msg for kw in offtopic_keywords) and not any(
        food_kw in lower_msg for food_kw in ["рецепт", "еда", "приготов", "кушать", "обед", "ужин", "завтрак", "холодильник", "купил", "закончил"]
    ):
        return OFFTOPIC_REFUSAL

    executor = get_agent_executor()
    if executor is None:
        # Fallback когда ключ API Gemini не настроен
        return (
            "👨‍🍳 Шеф на связи! Я готов помочь вам на кухне.\n\n"
            "<i>(Примечание: для полноценной работы AI-агента укажите GEMINI_API_KEY в .env)</i>\n\n"
            "Вы можете управлять холодильником и смотреть предпочтения через кнопки главного меню!"
        )

    thread_id = get_thread_id(user_id)
    config = {"configurable": {"thread_id": thread_id}}

    try:
        inputs = {"messages": [HumanMessage(content=f"User ID: {user_id}\nЗапрос пользователя: {message}")]}
        result = await executor.ainvoke(inputs, config=config)
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            return str(last_message.content)
        return "Не удалось сформировать ответ от шефа. Попробуйте еще раз!"
    except Exception as exc:
        logger.error("Ошибка при общении с AI-агентом: %s", exc, exc_info=True)
        return (
            "👨‍🍳 Извините, произошла небольшая заминка на кухне.\n"
            "Попробуйте повторить запрос или воспользуйтесь кнопками меню."
        )


async def generate_meal_options(
    user_id: int,
    meal_type: str,
    preferences_summary: str,
    fridge_summary: str,
) -> list[dict[str, Any]]:
    """Генерация 2-3 вариантов блюд под содержимое холодильника и предпочтения."""
    llm = get_llm()
    if llm is None:
        # Интеллектуальный мок/фоллбэк, если API ключ не задан
        items = [i.strip() for i in fridge_summary.split(",") if i.strip()]
        first_item = items[0] if items else "яйца"
        return [
            {
                "title": f"Аппетитное блюдо из {first_item}",
                "description": f"Быстрое и сытное блюдо на {meal_type} с использованием имеющихся продуктов.",
                "cooking_time": "15-20 минут",
                "missing_ingredients": "Всё необходимое уже есть в холодильнике!",
            },
            {
                "title": "Домашний теплый омлет с сыром и зеленью",
                "description": "Легкий в приготовлении вариант с нежной текстурой.",
                "cooking_time": "10 минут",
                "missing_ingredients": "Всё необходимое есть дома",
            },
            {
                "title": "Овощное рагу на сковороде",
                "description": "Полезное и сбалансированное горячее блюдо.",
                "cooking_time": "25 минут",
                "missing_ingredients": "⚠️ Докупить: зелень и свежий хлеб",
            },
        ]

    prompt = f"""Ты — персональный шеф-повар.
Предложи ровно 2 или 3 отличных варианта блюд на {meal_type}.

ДАННЫЕ ПОЛЬЗОВАТЕЛЯ:
- Предпочтения и аллергии: {preferences_summary or 'Аллергий нет, ем всё'}
- Продукты в холодильнике: {fridge_summary or 'Холодильник пуст'}

ТРЕБОВАНИЯ:
1. Строго соблюдай аллергии (жесткий запрет).
2. Приоритет блюдам на 100% из имеющихся продуктов (+ соль, перец, вода, масло).
3. Если продуктов не хватает, укажи 1-2 недостающих ингредиента, которые нужно докупить.
4. Ответ верни СТРОГО в формате валидного JSON-массива из 2 или 3 объектов, без лишнего markdown и без текста вокруг.
Каждый объект должен иметь поля:
- "title": короткое аппетитное название блюда (до 40 символов)
- "description": краткое описание (1-2 предложения, почему это вкусно)
- "cooking_time": время приготовления (напр. "15 минут")
- "missing_ingredients": строка "Все продукты есть в наличии" ИЛИ список того, что докупить (напр. "⚠️ Докупить: сливки")

Пример формата:
[
  {{
    "title": "Омлет с томатами и сыром",
    "description": "Нежный сытный омлет на сковороде с расплавленным сыром.",
    "cooking_time": "10 минут",
    "missing_ingredients": "Все продукты есть в наличии"
  }},
  {{
    "title": "Паста с курицей",
    "description": "Классическая паста с обжаренным куриным филе.",
    "cooking_time": "20 минут",
    "missing_ingredients": "⚠️ Докупить: пармезан"
  }}
]
"""
    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = str(response.content).strip()
        # Извлекаем JSON из ответа
        match = re.search(r"\[.*\]", content, re.DOTALL)
        if match:
            raw_json = match.group(0)
            data = json.loads(raw_json)
            if isinstance(data, list) and len(data) >= 2:
                return data[:3]
    except Exception as exc:
        logger.error("Ошибка при вызове Gemini для вариантов блюд: %s", exc)

    # Дефолтный fallback
    return [
        {
            "title": "Шеф-омлет с имеющимися ингредиентами",
            "description": "Быстрый белковый завтрак/обед из продуктов холодильника.",
            "cooking_time": "15 минут",
            "missing_ingredients": "Все продукты есть в наличии",
        },
        {
            "title": "Домашняя сковорода с овощами",
            "description": "Сытное горячее блюдо из доступных ингредиентов.",
            "cooking_time": "20 минут",
            "missing_ingredients": "Все продукты есть в наличии",
        },
    ]


async def generate_full_recipe_text(
    dish_title: str,
    meal_type: str,
    preferences_summary: str,
    fridge_summary: str,
) -> dict[str, Any]:
    """Генерация пошагового рецепта с таймингом и граммовками."""
    llm = get_llm()
    if llm is None:
        items = [i.strip() for i in fridge_summary.split(",") if i.strip()]
        ing_list = [f"{it} — по вкусу" for it in items] if items else ["Основные ингредиенты", "Соль, специи, масло"]
        return {
            "title": dish_title,
            "cooking_time": 20,
            "portions": 2,
            "ingredients": ing_list,
            "instructions": (
                "1. Подготовьте все ингредиенты, промойте и нарежьте.\n"
                "2. Разогрейте сковороду с каплей масла.\n"
                "3. Обжаривайте до готовности в течение 10-15 минут.\n"
                "4. Посолите, поперчите и подавайте горячим."
            ),
        }

    prompt = f"""Ты — персональный шеф-повар.
Составь подробный пошаговый рецепт блюда: «{dish_title}» ({meal_type}).

ДАННЫЕ ПОЛЬЗОВАТЕЛЯ:
- Предпочтения и аллергии: {preferences_summary}
- Продукты в холодильнике: {fridge_summary}

ТРЕБОВАНИЯ:
1. Строго соблюдай аллергии пользователя.
2. Укажи время приготовления в минутах и количество порций.
3. Перечисли ингредиенты с понятными граммовками/штуками.
4. Опиши пошаговый процесс приготовления (3-5 четких шагов).
5. Верни ответ СТРОГО в виде JSON объекта без лишнего текста:
{{
  "title": "{dish_title}",
  "cooking_time": 20,
  "portions": 2,
  "ingredients": [
    "Куриное филе — 300 г (из холодильника)",
    "Сыр — 50 г (из холодильника)",
    "Масло оливковое — 1 ст.л."
  ],
  "instructions": "1. Нарежьте филе кубиками...\\n2. Обжарьте на среднем огне...\\n3. Посыпьте тертым сыром..."
}}
"""
    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = str(response.content).strip()
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            raw_json = match.group(0)
            data = json.loads(raw_json)
            return data
    except Exception as exc:
        logger.error("Ошибка при генерации подробного рецепта: %s", exc)

    return {
        "title": dish_title,
        "cooking_time": 20,
        "portions": 2,
        "ingredients": ["Основные ингредиенты из холодильника", "Соль, перец, масло"],
        "instructions": (
            "1. Подготовьте ингредиенты и разогрейте сковороду.\n"
            "2. Обжаривайте на среднем огне до золотистой корочки 12-15 минут.\n"
            "3. Доведите до вкуса специями и подавайте."
        ),
    }
