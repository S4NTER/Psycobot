import os
import logging
import aiohttp
from datetime import timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db import *
from visualization import generate_mood_chart
from aiogram.types import FSInputFile, InlineKeyboardButton, KeyboardButton,ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
initialize_db()
class Tracking(StatesGroup):
    waiting_for_mood = State()
    waiting_for_trigger = State()
    waiting_for_thought = State()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

YANDEX_GPT_API_KEY = os.getenv("YANDEX_GPT_API_KEY")
YANDEX_GPT_FOLDER_ID = os.getenv("YANDEX_GPT_FOLDER_ID")
TOKEN = os.getenv("BOT_TOKEN")
YANDEX_GPT_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
SYSTEM_PROMPT = "Ты - профессиональный психолог. Отвечай по-русски. Будь вежлив и структурно отвечай."

async def ask_gpt(mood_score: int, trigger: str, thought: str):
    headers = {
        "Authorization": f"Api-Key {YANDEX_GPT_API_KEY}",
        "x-folder-id": YANDEX_GPT_FOLDER_ID,
        "Content-Type": "application/json"
    }

    user_prompt = f"""Информация о состоянии пользователя: Оценка настроения: {mood_score}/10 Что произошло: {trigger}Мысль по этому поводу: {thought}Пожалуйста, дай краткий психологический совет, исходя из этой информации."""
    payload = {
        "modelUri": f"gpt://{YANDEX_GPT_FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.7,
            "maxTokens": "300"
        },
        "messages": [
            {"role": "system", "text": SYSTEM_PROMPT},
            {"role": "user", "text": user_prompt}
        ]
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(YANDEX_GPT_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()

                    if 'result' in result and 'alternatives' in result['result'] and result['result']['alternatives']:
                        advice = result['result']['alternatives'][0]['message']['text']
                        return advice
                    else:
                        logger.error(f"YandexGPT API returned unexpected structure: {result}")
                        return "Произошла ошибка при обработке ответа от YandexGPT."
                else:
                    error_text = await response.text()
                    logger.error(f"YandexGPT API error {response.status}: {error_text}")
                    return "Произошла ошибка при обращении к YandexGPT. Проверьте ключ API и Folder ID."

        except aiohttp.ClientConnectorError:
            return "Проблема с подключением к сервису YandexGPT. Проверьте интернет-соединение."
        except Exception as e:
            logger.error(f"Unexpected error in ask_gpt: {e}")
            return "Произошла непредвиденная ошибка."

def get_main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Записать настроение", callback_data="track"))
    builder.row(InlineKeyboardButton(text="Отчёт за неделю", callback_data="report"),
                InlineKeyboardButton(text="Совет AI", callback_data="ai_advice"))
    builder.row(InlineKeyboardButton(text="ℹПомощь", callback_data="help"))
    return builder.as_markup()

async def process_mood(message: types.Message, state: FSMContext):
    try:
        mood_score = int(message.text)
        if not 1 <= mood_score <= 10:
            await message.answer(
                "Пожалуйста, выбери цифру от 1 до 10.",
                reply_markup=ReplyKeyboardRemove()
            )
            return

        await state.update_data(mood_score=mood_score)
        await state.set_state(Tracking.waiting_for_trigger)

        await message.answer(f"Опиши коротко событие, человека или мысль, которая повлияла на тебя.",
                             reply_markup=ReplyKeyboardRemove())
    except ValueError:
        await message.answer("Пожалуйста, введи число от 1 до 10.")

async def process_trigger(message: types.Message, state: FSMContext):
    trigger_text = message.text
    await state.update_data(trigger_text=trigger_text)
    await state.set_state(Tracking.waiting_for_thought)
    await message.answer("Запиши одну мысль, которая крутилась в голове сегодня.")

async def process_thought(message: types.Message, state: FSMContext):
    thought_text = message.text
    user_data = await state.get_data()

    save_entry(user_id=message.from_user.id, mood_score=user_data["mood_score"], trigger_text=user_data["trigger_text"],
               thought_text=thought_text)
    await state.clear()

    await message.answer(
        f" Запись сохранена! Настроение: {user_data['mood_score']} Событие: {user_data['trigger_text']} Мысль: {thought_text}",
        reply_markup=get_main_menu_keyboard())

async def command_start_handler(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    username = message.from_user.username
    register_user(user_id, chat_id, username)

    await message.answer(
        f"Привет, {message.from_user.full_name}! Ты зарегистрирован в системе.",
        reply_markup = get_main_menu_keyboard()
    )

async def command_track_handler(message: types.Message, state: FSMContext):
    await state.set_state(Tracking.waiting_for_mood)
    builder = ReplyKeyboardBuilder()
    for i in range(1, 11):
        builder.add(KeyboardButton(text=str(i)))
    builder.adjust(5, 5)
    await message.answer(
        "Как твоё настроение прямо сейчас по шкале от 1 до 10?\n"
        "1 — очень плохо, нет сил\n"
        "5 — нейтрально\n"
        "10 — отлично, полон энергии\n"
        "Выбери цифру на клавиатуре ",
        reply_markup=builder.as_markup(resize_keyboard=True))

async def command_ai_advice_handler(message: types.Message, user_id: int):
    start_date = datetime.now() - timedelta(days=1)
    data = get_weekly_data(user_id, start_date)

    if not data:
        await message.answer(
            "У тебя пока нет недавних записей.", reply_markup=get_main_menu_keyboard())
        return

    latest_entry = data[-1]

    processing_msg = await message.answer(
        "Подожди немного, готовлю персональный совет...",
        parse_mode="Markdown"
    )

    try:
        advice = await ask_gpt(
            mood_score=latest_entry['mood_score'],
            trigger=latest_entry['trigger_text'],
            thought=latest_entry['thought_text']
        )

        timestamp = datetime.fromisoformat(latest_entry['timestamp'])
        time_str = timestamp.strftime('%d.%m.%Y %H:%M')

        response_text = (
            f"**Психологический совет**\n\n"
            f"*Запись от {time_str}:*\n"
            f"Настроение: {latest_entry['mood_score']}\n"
            f"Событие: {latest_entry['trigger_text']}\n"
            f"Мысль: {latest_entry['thought_text']}\n\n"
            f"Совет психолога:\n{advice}\n\n"
            f"Помни: регулярный трекинг помогает лучше понимать себя!"
        )

        await message.answer(
            response_text,
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard()
        )

    except Exception as e:
        logger.error(f"Error in command_ai_advice_handler: {e}")
        await message.answer(
            "Не удалось получить совет. Пожалуйста, попробуй позже или создай новую запись.",
            reply_markup=get_main_menu_keyboard()
        )
    finally:
        try:
            await processing_msg.delete()
        except:
            pass

async def command_report_handler(message: types.Message, user_id: int):
    start_date = datetime.now() - timedelta(days=7)
    data = get_weekly_data(user_id, start_date)

    if not data:
        await message.answer("У тебя пока нет записей за последнюю неделю.", reply_markup=get_main_menu_keyboard())
        return

    chart_path = f"/tmp/mood_chart_{user_id}.png"

    if not generate_mood_chart(data, chart_path):
        await message.answer("Не удалось создать график. Проверь данные.", reply_markup=get_main_menu_keyboard())
        return

    try:
        photo = FSInputFile(chart_path)
        await message.answer_photo(photo, caption="Твой недельный отчет настроения. Посмотри, есть ли корреляции!")

        if os.path.exists(chart_path):
            os.remove(chart_path)
    except Exception as e:
        logger.error(f"Error sending chart: {e}")
        await message.answer("Не удалось отправить график. Попробуй позже.", reply_markup=get_main_menu_keyboard())

async def help_handler(message: types.Message):
    help_text = (
        "Помощь по боту\n"
        "Доступные команды:\n"
        "• /start - Главное меню\n"
        "• /track - Начать запись настроения\n"
        "• /report - Получить недельный отчёт\n"
        "• /ai_advice - Получить совет от AI\n"
        "Используй кнопки в меню для удобства!\n"
        "Как это работает:\n"
        "1. Записываешь настроение (1-10)\n"
        "2. Описываешь причину\n"
        "3. Записываешь мысль\n"
        "4. Получаешь статистику и советы!\n"
        "Регулярное использование поможет лучше понимать себя!"
    )

    await message.answer(help_text, reply_markup=get_main_menu_keyboard())

async def callback_query_handler(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data

    if action == "track":
        await callback.answer("Начинаю запись настроения")
        await command_track_handler(callback.message, state)
    elif action == "report":
        await callback.answer("Формирую отчёт")
        await command_report_handler(callback.message, callback.from_user.id)
    elif action == "ai_advice":
        await callback.answer("Анализирую записи и готовлю совет")
        await command_ai_advice_handler(callback.message,callback.from_user.id)
    elif action == "help":
        await callback.answer("Открываю справку")
        await help_handler(callback.message)
    else:
        await callback.answer("Неизвестная команда")

async def main():
    bot_instance = Bot(TOKEN)
    dp_instance = Dispatcher()

    dp_instance.message.register(command_start_handler, CommandStart())
    dp_instance.message.register(command_track_handler, Command("track"))
    dp_instance.message.register(command_report_handler, Command("report"))
    dp_instance.message.register(command_ai_advice_handler, Command("ai_advice"))
    dp_instance.message.register(help_handler, Command("help"))

    dp_instance.message.register(process_mood, StateFilter(Tracking.waiting_for_mood), F.text.regexp(r'^(10|[1-9])$'))
    dp_instance.message.register(process_trigger, StateFilter(Tracking.waiting_for_trigger))
    dp_instance.message.register(process_thought, StateFilter(Tracking.waiting_for_thought))
    dp_instance.callback_query.register(callback_query_handler)

    await dp_instance.start_polling(bot_instance)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())