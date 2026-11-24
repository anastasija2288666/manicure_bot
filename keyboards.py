from datetime import date, timedelta

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from database import WEEKDAYS_RU, format_date, get_services


def get_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню с постоянными кнопками под полем ввода."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💅 Прайс-лист"),
                KeyboardButton(text="📅 Записаться"),
            ],
            [
                KeyboardButton(text="🖼 Портфолио и адрес"),
                KeyboardButton(text="📋 Мои записи"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите пункт меню",
    )


def get_services_keyboard(services) -> InlineKeyboardMarkup:
    """Кнопки выбора услуги для начала записи."""
    buttons = [
        [InlineKeyboardButton(text=f"{s['name']} — {s['price']} ₽", callback_data=f"service:{s['id']}")]
        for s in services
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ В главное меню", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_dates_keyboard() -> InlineKeyboardMarkup:
    """Кнопки выбора даты: ближайшие 5 дней inclusive сегодня."""
    buttons = []
    for i in range(5):
        d = date.today() + timedelta(days=i)
        buttons.append(
            [InlineKeyboardButton(text=f"{d.day:02d}.{d.month:02d} ({WEEKDAYS_RU[d.weekday()]})", callback_data=f"date:{d.isoformat()}")]
        )
    buttons.append([InlineKeyboardButton(text="⬅️ Назад к услугам", callback_data="booking:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_times_keyboard(free_slots) -> InlineKeyboardMarkup:
    """Кнопки выбора свободного времени (по 3 в ряд)."""
    buttons = []
    row = []
    for slot in free_slots:
        row.append(InlineKeyboardButton(text=slot, callback_data=f"time:{slot}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="⬅️ Назад к датам", callback_data="booking:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение или отмена оформления записи."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить запись", callback_data="booking:confirm"),
                InlineKeyboardButton(text="❌ Отменить", callback_data="booking:cancel"),
            ],
        ]
    )


def get_cancel_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    """Кнопка отмены конкретной записи из раздела «Мои записи»."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"cancel:{booking_id}")]
        ]
    )