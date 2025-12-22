import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command

from config import TOKEN
import handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    bot_instance = Bot(TOKEN)
    dp = Dispatcher()

    dp.message.register(handlers.command_start_handler, CommandStart())
    dp.message.register(handlers.command_track_handler, Command("track"))
    dp.message.register(handlers.help_handler, Command("help"))
    dp.message.register(handlers.send_invoice_handler, Command("donate"))

    dp.message.register(handlers.apply_password, handlers.Reg.wait_for_pass)

    dp.message.register(handlers.process_mood, handlers.Tracking.waiting_for_mood)
    dp.message.register(handlers.process_trigger, handlers.Tracking.waiting_for_trigger)
    dp.message.register(handlers.process_thought, handlers.Tracking.waiting_for_thought)

    dp.pre_checkout_query.register(handlers.pre_checkout_handler)
    dp.message.register(handlers.success_payment_handler, F.successful_payment)

    dp.callback_query.register(handlers.callback_query_handler)

    dp.message.register(handlers.command_report_handler, Command("report"))
    dp.message.register(handlers.check_balance, Command("ai_advice"))

    await dp.start_polling(bot_instance)
