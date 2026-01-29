from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def task_kb(task_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Поставил(а) реакцию", callback_data=f"done:{task_id}")
    kb.button(text="↩️ Отменить", callback_data=f"undo:{task_id}")

    kb.button(text="📊 Мой прогресс (неделя)", callback_data="me")
    kb.button(text="🏆 Топ недели", callback_data="top")
    kb.button(text="🏅 Топ месяца", callback_data="month_top")

    kb.button(text="ℹ️ Правила", callback_data="rules")

    kb.adjust(2, 2, 1, 1)
    return kb.as_markup()


def simple_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Мой прогресс (неделя)", callback_data="me")
    kb.button(text="🏆 Топ недели", callback_data="top")
    kb.button(text="🏅 Топ месяца", callback_data="month_top")
    kb.button(text="ℹ️ Правила", callback_data="rules")
    kb.adjust(2, 2)
    return kb.as_markup()