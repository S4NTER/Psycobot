from aiogram.types import InlineKeyboardButton, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def get_main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📝 Записать настроение", callback_data="track"))
    builder.row(
        InlineKeyboardButton(text="📊 Отчёт за неделю", callback_data="report"),
        InlineKeyboardButton(text="🤖 Совет AI", callback_data="request_ai_advice")
    )
    builder.row(InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help"))
    return builder.as_markup()


def get_mood_keyboard():
    builder = ReplyKeyboardBuilder()
    for i in range(1, 11):
        builder.add(KeyboardButton(text=str(i)))
    builder.adjust(5, 5)
    return builder.as_markup(resize_keyboard=True)


def get_payment_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Оплатить 1 ⭐", callback_data="payment"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment"))
    return builder.as_markup()


def get_ai_access_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🤖 Получить AI-совет", callback_data="get_ai_advice"))
    builder.row(InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu"))
    return builder.as_markup()
