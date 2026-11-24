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


# ---------- Админ-клавиатуры ----------

def get_admin_menu() -> InlineKeyboardMarkup:
    """Главное меню админ-панели."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Все записи", callback_data="admin:bookings"),
                InlineKeyboardButton(text="🚫 Закрыть день/окно", callback_data="admin:block_menu"),
            ],
            [
                InlineKeyboardButton(text="💅 Изменить прайс", callback_data="admin:price_menu"),
                InlineKeyboardButton(text="📢 Рассылка клиентам", callback_data="admin:broadcast"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Выйти из админ-режима", callback_data="admin:exit"),
            ],
        ]
    )


def get_block_dates_keyboard() -> InlineKeyboardMarkup:
    """Кнопки выбора даты для блокировки (ближайшие 14 дней)."""
    buttons = []
    for i in range(14):
        d = date.today() + timedelta(days=i)
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{d.day:02d}.{d.month:02d} ({WEEKDAYS_RU[d.weekday()]})",
                    callback_data=f"block:date:{d.isoformat()}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_block_times_keyboard(date_str: str, blocked_times=None) -> InlineKeyboardMarkup:
    """Кнопки выбора времени для блокировки на выбранную дату."""
    if blocked_times is None:
        blocked_times = set()
    from database import generate_time_slots

    buttons = []
    row = []
    for slot in generate_time_slots():
        text = f"⛔ {slot}" if slot in blocked_times else slot
        row.append(InlineKeyboardButton(text=text, callback_data=f"block:time:{date_str}:{slot}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append(
        [
            InlineKeyboardButton(text="✅ Готово", callback_data=f"block:done:{date_str}"),
            InlineKeyboardButton(text="⬅️ Назад к датам", callback_data="admin:block_menu"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_services_keyboard(services) -> InlineKeyboardMarkup:
    """Кнопки выбора услуги для изменения цены."""
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{s['name']} — {s['price']} ₽",
                callback_data=f"admin:price:set:{s['id']}",
            )
        ]
        for s in services
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_bookings_keyboard(bookings) -> InlineKeyboardMarkup:
    """Кнопки списка всех активных записей с кнопкой отмены у каждой."""
    buttons = []
    for b in bookings:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"❌ {format_date(b['date'])} {b['time']} | "
                        f"{b['user_name']} | {b['service_name']}"
                    ),
                    callback_data=f"admin:cancel:{b['id']}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)