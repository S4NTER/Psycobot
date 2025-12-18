from aiogram.types import InlineKeyboardButton, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

def get_main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📝 Записать настроение", callback_data="track"))
    builder.row(
        InlineKeyboardButton(text="📊 Отчёт за неделю", callback_data="report"),
        InlineKeyboardButton(text="🤖 Совет AI", callback_data="ai_advice")
    )
    builder.row(InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help"))
    return builder.as_markup()

def get_mood_keyboard():
    builder = ReplyKeyboardBuilder()
    for i in range(1, 11):
        builder.add(KeyboardButton(text=str(i)))
    builder.adjust(5, 5)
    return builder.as_markup(resize_keyboard=True)