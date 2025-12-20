import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command, StateFilter

from config import TOKEN
import handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    bot_instance = Bot(TOKEN)
    dp_instance = Dispatcher()

    dp_instance.message.register(handlers.command_start_handler, CommandStart())
    dp_instance.message.register(handlers.command_track_handler, Command("track"))
    dp_instance.message.register(handlers.help_handler, Command("help"))
    dp_instance.message.register(handlers.send_invoice_handler, Command("donate"))

    dp_instance.message.register(handlers.apply_password, handlers.Reg.wait_for_pass)

    dp_instance.message.register(handlers.process_mood, handlers.Tracking.waiting_for_mood)
    dp_instance.message.register(handlers.process_trigger, handlers.Tracking.waiting_for_trigger)
    dp_instance.message.register(handlers.process_thought, handlers.Tracking.waiting_for_thought)

    dp_instance.pre_checkout_query.register(handlers.pre_checkout_handler)
    dp_instance.message.register(handlers.success_payment_handler, F.successful_payment)

    dp_instance.callback_query.register(handlers.callback_query_handler)

    dp_instance.message.register(handlers.command_report_handler, Command("report"))
    dp_instance.message.register(handlers.check_balance, Command("ai_advice"))

    await dp_instance.start_polling(bot_instance)
