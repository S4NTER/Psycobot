import logging
import os
from datetime import timedelta, datetime
from aiogram.fsm.state import State, StatesGroup
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, ReplyKeyboardRemove
from aiogram.types import LabeledPrice
from aiogram import Bot
from aiogram.types import PreCheckoutQuery

import db
import texts
import keyboards
from visualization import generate_mood_chart
from AI import ask_gpt

logger = logging.getLogger(__name__)
db.initialize_db()


async def delete_previous_bot_message(bot: Bot, chat_id: int, state: FSMContext):
    data = await state.get_data()
    bot_message_id = data.get('bot_message_id')

    if bot_message_id:
        try:
            await bot.delete_message(chat_id=chat_id,message_id=bot_message_id)
            await state.update_data(bot_message_id=None)
        except Exception as e:
            logger.error(f"Не удалось удалить старое сообщение бота (ID: {bot_message_id}): {e}")


async def send_and_store_message(message: types.Message, state: FSMContext, text: str, reply_markup=None,delete_user_msg: bool = True):
    if delete_user_msg:
        try:
            await message.delete()
        except Exception as e:
            logger.error(f"Не удалось удалить сообщение пользователя: {e}")

    await delete_previous_bot_message(message.bot, message.chat.id, state)

    msg = await message.answer(
        text=text,
        reply_markup=reply_markup
    )
    await state.update_data(bot_message_id=msg.message_id)
    return msg


class Tracking(StatesGroup):
    waiting_for_mood = State()
    waiting_for_trigger = State()
    waiting_for_thought = State()


class Reg(StatesGroup):
    wait_for_pass = State()


async def command_start_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    chat_id = message.chat.id
    username = message.from_user.username
    db.register_user(user_id, chat_id, username)

    await state.set_state(Reg.wait_for_pass)
    await send_and_store_message(
        message=message,
        state=state,
        text=texts.SET_PASS_TEXT,
        reply_markup=ReplyKeyboardRemove()
    )


async def command_track_handler(message: types.Message, state: FSMContext):
    await state.set_state(Tracking.waiting_for_mood)
    await send_and_store_message(
        message=message,
        state=state,
        text=texts.MOOD_QUESTION,
        reply_markup=keyboards.get_mood_keyboard()
    )


async def process_mood(message: types.Message, state: FSMContext):
    try:
        await message.delete()
    except Exception as e:
        logger.error(f"Не удалось удалить сообщение пользователя: {e}")

    try:
        mood_score = int(message.text)

        if not 1 <= mood_score <= 10:
            data = await state.get_data()
            error_message_id = data.get('error_message_id')
            if error_message_id:
                try:
                    await message.bot.delete_message(
                        chat_id=message.chat.id,
                        message_id=error_message_id
                    )
                except Exception as e:
                    logger.error(f"Не удалось удалить предыдущее сообщение об ошибке: {e}")

            error_msg = await message.answer(
                "❌ Пожалуйста, выберите цифру от 1 до 10.",
                reply_markup=keyboards.get_mood_keyboard()
            )
            await state.update_data(error_message_id=error_msg.message_id)
            return

        await delete_previous_bot_message(message.bot, message.chat.id, state)

        data = await state.get_data()
        error_message_id = data.get('error_message_id')
        if error_message_id:
            try:
                await message.bot.delete_message(
                    chat_id=message.chat.id,
                    message_id=error_message_id
                )
            except Exception as e:
                logger.error(f"Не удалось удалить сообщение об ошибке: {e}")

        await state.update_data(mood_score=mood_score)

        msg = await message.answer(
            texts.TRIGGER_QUESTION,
            reply_markup=ReplyKeyboardRemove()
        )

        await state.update_data(bot_message_id=msg.message_id)
        await state.update_data(error_message_id=None)
        await state.set_state(Tracking.waiting_for_trigger)

    except ValueError:
        data = await state.get_data()
        error_message_id = data.get('error_message_id')
        if error_message_id:
            try:
                await message.bot.delete_message(
                    chat_id=message.chat.id,
                    message_id=error_message_id
                )
            except Exception as e:
                logger.error(f"Не удалось удалить предыдущее сообщение об ошибке: {e}")

        error_msg = await message.answer(
            "❌ Пожалуйста, введите число от 1 до 10.",
            reply_markup=keyboards.get_mood_keyboard()
        )
        await state.update_data(error_message_id=error_msg.message_id)


async def process_trigger(message: types.Message, state: FSMContext):
    logger.info(f"process_trigger вызван! Текст: {message.text}")

    try:
        await message.delete()
    except Exception as e:
        logger.error(f"Failed to delete trigger message: {e}")

    await state.update_data(trigger_text=message.text)

    await delete_previous_bot_message(message.bot, message.chat.id, state)

    msg = await message.answer(
        texts.THOUGHT_QUESTION,
        reply_markup=ReplyKeyboardRemove()
    )

    await state.update_data(bot_message_id=msg.message_id)

    logger.info(f"Новое сообщение отправлено с ID: {msg.message_id}")
    await state.set_state(Tracking.waiting_for_thought)


async def process_thought(message: types.Message, state: FSMContext):
    try:
        await message.delete()
    except Exception as e:
        logger.error(f"Failed to delete thought message: {e}")

    user_data = await state.get_data()
    thought_text = message.text

    db.save_entry(
        user_id=message.from_user.id,
        mood_score=user_data["mood_score"],
        trigger_text=user_data["trigger_text"],
        thought_text=thought_text
    )

    await delete_previous_bot_message(message.bot, message.chat.id, state)

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
        await message.answer(texts.NO_WEEKLY_DATA, reply_markup=keyboards.get_report_keyboard())
        return

    chart_path = f"/tmp/mood_chart_{user_id}.png"

    if not generate_mood_chart(data, chart_path):
        await message.answer(texts.ERRORS["chart_error"], reply_markup=keyboards.get_report_keyboard())
        return

    try:
        photo = FSInputFile(chart_path)
        await message.answer_photo(
            photo,
            caption=texts.CHART_CAPTION,
            reply_markup=keyboards.get_report_keyboard()
        )

        if os.path.exists(chart_path):
            os.remove(chart_path)
    except Exception as e:
        logger.error(f"Error sending chart: {e}")
        await message.answer(texts.ERRORS["send_chart_error"], reply_markup=keyboards.get_report_keyboard())


async def help_handler(message: types.Message):
    await message.answer(texts.HELP_TEXT, reply_markup=keyboards.get_help_keyboard())


async def callback_query_handler(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data

    if action == "ai_advice":
        await callback.answer("Анализирую записи и готовлю совет")
        try:
            await callback.message.delete()
        except Exception as e:
            logger.error(f"Failed to delete callback message: {e}")
        await check_balance(callback.message, callback.from_user.id, state)  # Передаем state!

    elif action == "pay_ai":
        await callback.answer("Принимаю оплату")
        await state.update_data(payment_request_message_id=callback.message.message_id)
        try:
            await callback.message.delete()
        except Exception as e:
            logger.error(f"Failed to delete callback message: {e}")
        await send_invoice_handler(callback.message, state)

    elif action == "payment":
        await callback.answer("Открываю оплату")
        try:
            await callback.message.delete()
        except Exception as e:
            logger.error(f"Failed to delete callback message: {e}")
        await send_invoice_handler(callback.message, state)

    elif action == "back_from_invoice":
        await callback.answer("Возвращаюсь назад")
        data = await state.get_data()

        messages_to_try_delete = [
            data.get('invoice_message_id'),
            data.get('back_message_id'),
            data.get('payment_request_message_id'),
        ]

        for msg_id in messages_to_try_delete:
            if msg_id:
                try:
                    await callback.message.bot.delete_message(
                        chat_id=callback.message.chat.id,
                        message_id=msg_id
                    )
                    logger.info(f"Удалили сообщение {msg_id}")
                except Exception as e:
                    logger.debug(f"Сообщение {msg_id} уже удалено или не существует: {e}")

        await state.update_data(
            invoice_message_id=None,
            back_message_id=None,
            payment_request_message_id=None
        )

        await callback.message.answer(
            text=texts.MAIN_MENU_TEXT,
            parse_mode="Markdown",
            reply_markup=keyboards.get_main_menu_keyboard()
        )
        return


    elif action == "track":
        await callback.answer("Начинаю запись настроения")
        try:
            await callback.message.delete()
        except Exception as e:
            logger.error(f"Failed to delete callback message: {e}")
        await command_track_handler(callback.message, state)

    elif action == "report":
        await callback.answer("Формирую отчёт")
        try:
            await callback.message.delete()
        except Exception as e:
            logger.error(f"Failed to delete callback message: {e}")
        await command_report_handler(callback.message, callback.from_user.id)

    elif action == "back_to_menu":
        await callback.answer("Возвращаюсь в меню")
        try:
            await callback.message.delete()
        except Exception as e:
            logger.error(f"Failed to delete callback message: {e}")
        await callback.message.answer(
            text=texts.MAIN_MENU_TEXT,
            parse_mode="Markdown",
            reply_markup=keyboards.get_main_menu_keyboard()
        )

    elif action == "help":
        await callback.answer("Открываю справку")
        try:
            await callback.message.delete()
        except Exception as e:
            logger.error(f"Failed to delete callback message: {e}")
        await help_handler(callback.message)
    else:
        await callback.answer(texts.ERRORS["unknown_command"])

async def track_from_button_handler(message: types.Message, state: FSMContext):
    await send_and_store_message(message=message,state=state,text=texts.MOOD_QUESTION,reply_markup=keyboards.get_mood_keyboard())
    await state.set_state(Tracking.waiting_for_mood)


async def safe_delete_message(bot, chat_id, message_id, description=""):
    if not message_id:
        return False

    try:
        await bot.delete_message(
            chat_id=chat_id,
            message_id=message_id
        )
        logger.info(f"Успешно удалили сообщение {message_id} ({description})")
        return True
    except Exception as e:
        logger.debug(f"Не удалось удалить сообщение {message_id} ({description}): {e}")
        return False

async def send_invoice_handler(message: types.Message, state: FSMContext):
    prices = [LabeledPrice(label='XTR', amount=1)]

    try:
        await message.delete()
    except Exception as e:
        logger.debug(f"Сообщение уже удалено: {e}")

    try:
        msg = await message.answer_invoice(
            title="Оплата за совет AI-ассистента",
            description="Поддержать канал на 1 звезду!",
            prices=prices,
            provider_token="",
            payload=f"channel_support_{message.from_user.id}_{datetime.now().timestamp()}",
            currency="XTR",
        )

        back_keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="◀️ Назад", callback_data="back_from_invoice")]
            ]
        )

        back_msg = await message.answer(
            "Чтобы вернуться в меню, нажмите кнопку ниже:",
            reply_markup=back_keyboard
        )

        await state.update_data(
            invoice_message_id=msg.message_id,
            back_message_id=back_msg.message_id
        )

    except Exception as e:
        logger.error(f"Error in send_invoice_handler: {e}")
        await message.answer("❌ Не удалось создать счет для оплаты. Попробуйте позже.")


async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


async def success_payment_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await safe_delete_message(
        message.bot, message.chat.id,
        data.get('invoice_message_id'), "инвойс"
    )
    await safe_delete_message(
        message.bot, message.chat.id,
        data.get('back_message_id'), "сообщение с кнопкой Назад"
    )
    await safe_delete_message(
        message.bot, message.chat.id,
        data.get('payment_request_message_id'), "сообщение с предложением оплаты"
    )

    try:
        await message.delete()
    except:
        pass

    user_id = message.from_user.id
    curr_balance = db.get_balance(user_id)
    curr_balance += 1
    db.set_balance(user_id, curr_balance)

    await message.answer(
        "✅ Оплата прошла успешно! Теперь у вас есть доступ к AI-советам.",
        reply_markup=keyboards.get_ai_access_keyboard()
    )

    await state.update_data(
        invoice_message_id=None,
        back_message_id=None,
        payment_request_message_id=None
    )


async def check_balance(message: types.Message, user_id: int, state: FSMContext = None):
    print(f"check_balance вызван для user_id: {user_id}")
    curr_balance = db.get_balance(user_id)
    print(f"Текущий баланс: {curr_balance}")

    if curr_balance >= 1:
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
        advice_message = texts.AI_ADVICE_TEMPLATE.format(
            time=datetime.now().strftime("%d.%m.%Y %H:%M"),
            mood=latest_entry['mood_score'],
            trigger=latest_entry['trigger_text'],
            thought=latest_entry['thought_text'],
            advice=advice
        )

        await message.answer(advice_message, reply_markup=keyboards.get_ai_keyboard())

        curr_balance -= 1
        db.set_balance(user_id, curr_balance)
        print(f"Новый баланс после списания: {db.get_balance(user_id)}")
        return
    else:
        payment_msg = await message.answer(
            "Недостаточно оплаченных запросов AI, пополните счет",
            reply_markup=keyboards.get_payment_keyboard()
        )
        if state:
            await state.update_data(payment_request_message_id=payment_msg.message_id)
        return

async def show_payment_message(message: types.Message):
    await message.answer(
        texts.PAYMENT_REQUEST_TEXT,
        parse_mode="Markdown",
        reply_markup=keyboards.get_payment_keyboard()
    )


async def command_ai_advice_command_handler(message: types.Message):
    await show_payment_message(message)


async def apply_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    try:
        await message.delete()
    except Exception as e:
        logger.error(f"Failed to delete password message: {e}")

    data = await state.get_data()
    bot_message_id = data.get('bot_message_id')

    if len(password) < 6:
        if bot_message_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=bot_message_id,
                    text="❌ Пароль должен содержать минимум 6 символов. Попробуйте еще раз:\n\n" + texts.SET_PASS_TEXT,
                    reply_markup=ReplyKeyboardRemove()
                )
            except Exception as e:
                logger.error(f"Failed to edit message: {e}")
        return

    user_id = message.from_user.id
    db.set_password(user_id, password)

    if bot_message_id:
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=bot_message_id
            )
        except Exception as e:
            logger.error(f"Failed to delete bot message: {e}")

    await state.clear()

    name = message.from_user.first_name
    if message.from_user.last_name:
        name = f"{name} {message.from_user.last_name}"

    welcome_message = texts.WELCOME_TEXT.format(name=name)
    await message.answer(welcome_message, reply_markup=keyboards.get_main_menu_keyboard())