import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db import initialize_db, save_entry, register_user
initialize_db()

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Tracking(StatesGroup):
    waiting_for_mood = State()
    waiting_for_trigger = State()
    waiting_for_thought = State()

async def command_start_handler(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    username = message.from_user.username

    register_user(user_id, chat_id, username)

    await message.answer(
        f"Привет, {message.from_user.full_name}! Ты зарегистрирован в системе."
    )

async def command_track_handler(message: types.Message, state: FSMContext):
    await state.set_state(Tracking.waiting_for_mood)
    await message.answer(
        "Как твое настроение от 1 до 10? (1 - очень плохо, 10 - отлично)"
    )

async def command_report_handler(message: types.Message):
    await message.answer('...')

async def process_mood(message: types.Message, state: FSMContext):
    try:
        mood_score = int(message.text)
        if not 1 <= mood_score <= 10:
            await message.answer("Пожалуйста, введи число от 1 до 10.")
            return
        await state.update_data(mood_score=mood_score)
        await state.set_state(Tracking.waiting_for_trigger)
        await message.answer("Что сейчас вызывает наибольшее напряжение или радость?")
    except ValueError:
        await message.answer("Пожалуйста, введи число от 1 до 10.")

async def process_trigger(message: types.Message, state: FSMContext):
    trigger_text = message.text
    if len(trigger_text.strip()) < 2:
        await message.answer("Пожалуйста, опиши причину подробнее.")
        return
    await state.update_data(trigger_text=trigger_text)
    await state.set_state(Tracking.waiting_for_thought)
    await message.answer(
        "Запиши одну мысль, которая крутилась в голове сегодня."
    )

async def process_thought(message: types.Message, state: FSMContext):
    thought_text = message.text
    user_data = await state.get_data()
    save_entry(user_id=message.from_user.id,mood_score=user_data["mood_score"],trigger_text=user_data["trigger_text"],thought_text=thought_text)
    await state.clear()

async def main():
    bot = Bot(TOKEN)
    dp = Dispatcher()

    dp.message.register(command_start_handler, CommandStart())
    dp.message.register(command_track_handler, Command("track"))
    dp.message.register(command_report_handler, Command("report"))

    dp.message.register(process_mood,StateFilter(Tracking.waiting_for_mood),F.text.regexp(r'^(10|[1-9])$'))
    dp.message.register(process_trigger,StateFilter(Tracking.waiting_for_trigger))
    dp.message.register(process_thought,StateFilter(Tracking.waiting_for_thought))

    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())