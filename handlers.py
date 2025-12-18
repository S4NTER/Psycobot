import logging
import os
from datetime import timedelta, datetime
from aiogram.fsm.state import State, StatesGroup
from aiogram import types, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, ReplyKeyboardRemove

import db
import texts
import keyboards
from visualization import generate_mood_chart
from AI import ask_gpt

logger = logging.getLogger(__name__)
db.initialize_db()

class Tracking(StatesGroup):
    waiting_for_mood = State()
    waiting_for_trigger = State()
    waiting_for_thought = State()

async def command_start_handler(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    username = message.from_user.username

    db.register_user(user_id, chat_id, username)

    welcome_text = texts.WELCOME_TEXT.format(name=message.from_user.full_name)
    await message.answer(welcome_text, reply_markup=keyboards.get_main_menu_keyboard())


async def command_track_handler(message: types.Message, state: FSMContext):
    await state.set_state(Tracking.waiting_for_mood)
    await message.answer(
        texts.MOOD_QUESTION,
        reply_markup=keyboards.get_mood_keyboard()
    )


async def process_mood(message: types.Message, state: FSMContext):
    try:
        mood_score = int(message.text)
        if not 1 <= mood_score <= 10:
            await message.answer(
                texts.ERRORS["out_of_range"],
                reply_markup=ReplyKeyboardRemove()
            )
            return

        await state.update_data(mood_score=mood_score)
        await state.set_state(Tracking.waiting_for_trigger)
        await message.answer(texts.TRIGGER_QUESTION, reply_markup=ReplyKeyboardRemove())

    except ValueError:
        await message.answer(texts.ERRORS["invalid_mood"])


async def process_trigger(message: types.Message, state: FSMContext):
    trigger_text = message.text
    await state.update_data(trigger_text=trigger_text)
    await state.set_state(Tracking.waiting_for_thought)
    await message.answer(texts.THOUGHT_QUESTION)


async def process_thought(message: types.Message, state: FSMContext):
    thought_text = message.text
    user_data = await state.get_data()

    db.save_entry(
        user_id=message.from_user.id,
        mood_score=user_data["mood_score"],
        trigger_text=user_data["trigger_text"],
        thought_text=thought_text
    )

    await state.clear()

    saved_message = texts.SAVED_MESSAGE.format(
        mood=user_data['mood_score'],
        trigger=user_data['trigger_text'],
        thought=thought_text
    )

    await message.answer(saved_message, reply_markup=keyboards.get_main_menu_keyboard())


async def command_ai_advice_handler(message: types.Message, user_id: int):
    start_date = datetime.now() - timedelta(days=1)
    data = db.get_weekly_data(user_id, start_date)

    if not data:
        await message.answer(texts.NO_RECENT_DATA, reply_markup=keyboards.get_main_menu_keyboard())
        return

    latest_entry = data[-1]
    processing_msg = await message.answer(texts.PROCESSING_ADVICE, parse_mode="Markdown")

    try:
        advice = await ask_gpt(
            mood_score=latest_entry['mood_score'],
            trigger=latest_entry['trigger_text'],
            thought=latest_entry['thought_text']
        )

        timestamp = datetime.fromisoformat(latest_entry['timestamp'])
        time_str = timestamp.strftime('%d.%m.%Y %H:%M')

        response_text = texts.AI_ADVICE_TEMPLATE.format(
            time=time_str,
            mood=latest_entry['mood_score'],
            trigger=latest_entry['trigger_text'],
            thought=latest_entry['thought_text'],
            advice=advice
        )

        await message.answer(
            response_text,
            parse_mode="Markdown",
            reply_markup=keyboards.get_main_menu_keyboard()
        )

    except Exception as e:
        logger.error(f"Error in command_ai_advice_handler: {e}")
        await message.answer(texts.ERRORS["ai_error"], reply_markup=keyboards.get_main_menu_keyboard())
    finally:
        try:
            await processing_msg.delete()
        except:
            pass


async def command_report_handler(message: types.Message, user_id: int):
    start_date = datetime.now() - timedelta(days=7)
    data = db.get_weekly_data(user_id, start_date)

    if not data:
        await message.answer(texts.NO_WEEKLY_DATA, reply_markup=keyboards.get_main_menu_keyboard())
        return

    chart_path = f"/tmp/mood_chart_{user_id}.png"

    if not generate_mood_chart(data, chart_path):
        await message.answer(texts.ERRORS["chart_error"], reply_markup=keyboards.get_main_menu_keyboard())
        return

    try:
        photo = FSInputFile(chart_path)
        await message.answer_photo(
            photo,
            caption=texts.CHART_CAPTION,
            reply_markup=keyboards.get_main_menu_keyboard()
        )

        if os.path.exists(chart_path):
            os.remove(chart_path)
    except Exception as e:
        logger.error(f"Error sending chart: {e}")
        await message.answer(texts.ERRORS["send_chart_error"], reply_markup=keyboards.get_main_menu_keyboard())


async def help_handler(message: types.Message):
    await message.answer(texts.HELP_TEXT, reply_markup=keyboards.get_main_menu_keyboard())


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
        await command_ai_advice_handler(callback.message, callback.from_user.id)
    elif action == "help":
        await callback.answer("Открываю справку")
        await help_handler(callback.message)
    else:
        await callback.answer(texts.ERRORS["unknown_command"])