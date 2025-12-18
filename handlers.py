import logging
import os
from datetime import timedelta, datetime
from aiogram.fsm.state import State, StatesGroup
from aiogram import types, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, ReplyKeyboardRemove
from aiogram.types import LabeledPrice, Message
from aiogram.types import PreCheckoutQuery

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
    elif action == "request_ai_advice":
        await callback.answer("Проверяем доступ")
        await show_payment_message(callback.message)
    elif action == "get_ai_advice":
        await callback.answer("Получаю совет")
        await command_ai_advice_handler(callback.message, callback.from_user.id)
    elif action == "back_to_menu":
        await callback.answer("Возвращаюсь в меню")
        await command_start_handler(callback.message)
    elif action == "payment":
        await callback.answer("Открываю оплату")
        await send_invoice_handler(callback.message)
    elif action == "ai_advice":
        await callback.answer("Анализирую записи и готовлю совет")
        await command_ai_advice_handler(callback.message, callback.from_user.id)
    elif action == "help":
        await callback.answer("Открываю справку")
        await help_handler(callback.message)
    elif action == "pay_ai":
        await callback.answer("Принимаю оплату")
        await send_invoice_handler(callback.message)
    elif action == "cancel_payment":
        await callback.answer("Оплата отменена")
        await callback.message.edit_text(
            "Оплата отменена. Что дальше?",
            reply_markup=keyboards.get_main_menu_keyboard()
        )
    else:
        await callback.answer(texts.ERRORS["unknown_command"])


async def send_invoice_handler(message: types.Message):
    prices = [LabeledPrice(label='XTR', amount=1)]
    await message.answer_invoice(
        title="Оплата за совет AI-ассистента",
        description="Поддержать канал на 1 звезду!",
        prices=prices,
        provider_token="",
        payload=f"channel_support{message.from_user.id}",
        currency="XTR",
    )


async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


async def command_ai_advice_handler(message: types.Message, user_id: int):
    start_date = datetime.now() - timedelta(days=1)
    data = db.get_weekly_data(user_id, start_date)

    if not data:
        await message.answer(texts.NO_RECENT_DATA)
        return

    latest_entry = data[-1]
    advice = await ask_gpt(
        mood_score=latest_entry['mood_score'],
        trigger=latest_entry['trigger_text'],
        thought=latest_entry['thought_text']
    )

    await message.answer(f"🤖 Совет AI:\n{advice}", reply_markup=keyboards.get_main_menu_keyboard())


async def succes_payment_handler(message: types.Message):
    await message.answer(
        "✅ Оплата прошла успешно! Теперь у вас есть доступ к AI-советам.",
        reply_markup=keyboards.get_ai_access_keyboard()
    )


async def show_payment_message(message: types.Message):
    await message.answer(
        texts.PAYMENT_REQUEST_TEXT,
        parse_mode="Markdown",
        reply_markup=keyboards.get_payment_keyboard()
    )


async def command_ai_advice_command_handler(message: types.Message):
    await show_payment_message(message)
