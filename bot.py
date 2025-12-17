import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def command_start_handler(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.full_name}! Я твой Карманный Психолог. Нажми /track, чтобы начать запись."
    )

async def command_track_handler(message: types.Message):
    await message.answer(
        "Как твое настроение от 1 до 10? (1 - очень плохо, 10 - отлично)"
    )

async def command_report_handler(message: types.Message):
    await message.answer('...')

async def main():
    if TOKEN == "BOT_TOKEN":
        logger.error("Токен не установлен")
        return

    bot = Bot(TOKEN)
    dp = Dispatcher()

    dp.message.register(command_start_handler, CommandStart())
    dp.message.register(command_track_handler, Command("track"))
    dp.message.register(command_report_handler, Command("report"))

    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())