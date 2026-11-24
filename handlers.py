import logging
from datetime import date

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config import ADMIN_ID
from database import (
    add_booking,
    add_or_update_user,
    cancel_booking,
    format_date,
    get_active_bookings_by_user,
    get_free_slots,
    get_service,
    get_services,
    update_user_phone,
)
from keyboards import (
    get_cancel_keyboard,
    get_confirm_keyboard,
    get_dates_keyboard,
    get_main_menu,
    get_services_keyboard,
    get_times_keyboard,
)

router = Router()
log = logging.getLogger(__name__)


class BookingStates(StatesGroup):
    service = State()
    date = State()
    time = State()
    name = State()
    phone = State()
    confirm = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    add_or_update_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    await state.clear()
    await message.answer(
        "👋 Добро пожаловать в студию маникюра!\n\n"
        "Выберите действие в меню ниже:",
        reply_markup=get_main_menu(),
    )


@router.message(F.text == "💅 Прайс-лист")
async def price_list(message: Message):
    services = get_services()
    lines = ["💅 <b>Прайс-лист услуг</b>\n"]
    for s in services:
        lines.append(
            f"• <b>{s['name']}</b> — {s['price']} ₽\n"
            f"  {s['description']} (примерно {s['duration_minutes']} мин)"
        )
    lines.append("\nЗаписаться можно через кнопку «📅 Записаться».")
    await message.answer("\n".join(lines), reply_markup=get_main_menu())


@router.message(F.text == "🖼 Портфолио и адрес")
async def portfolio(message: Message):
    await message.answer(
        "📍 <b>Адрес студии:</b> г. Москва, ул. Примерная, д. 10\n"
        "🚇 Станция метро: «Примерная» (5 мин пешком)\n"
        "🕒 Работаем ежедневно с 10:00 до 20:00\n\n"
        "🖼 <b>Портфолио работ:</b> https://instagram.com/manicure_studio_example\n\n"
        "Записаться онлайн — через кнопку «📅 Записаться».",
        reply_markup=get_main_menu(),
    )


@router.message(F.text == "📅 Записаться")
async def start_booking(message: Message, state: FSMContext):
    await state.clear()
    services = get_services()
    await state.set_state(BookingStates.service)
    await message.answer("💅 Выберите услугу:", reply_markup=get_services_keyboard(services))


@router.message(F.text == "📋 Мои записи")
async def my_bookings(message: Message):
    bookings = get_active_bookings_by_user(message.from_user.id)
    if not bookings:
        await message.answer(
            "У вас нет активных записей.",
            reply_markup=get_main_menu(),
        )
        return
    for b in bookings:
        await message.answer(
            f"💅 <b>{b['service_name']}</b> — {b['service_price']} ₽\n"
            f"📅 {format_date(b['date'])} | 🕒 {b['time']}\n"
            f"📞 {b['user_phone']}",
            reply_markup=get_cancel_keyboard(b["id"]),
        )
    await message.answer(
        "Чтобы отменить запись, нажмите «❌ Отменить запись» под нужной записью.",
        reply_markup=get_main_menu(),
    )


@router.callback_query(F.data == "back_to_menu")
async def cb_back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Главное меню:", reply_markup=None)
    await callback.message.answer("Выберите пункт меню:", reply_markup=get_main_menu())
    await callback.answer()


@router.callback_query(BookingStates.service, F.data.startswith("service:"))
async def cb_service(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split(":")[1])
    service = get_service(service_id)
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    await state.update_data(
        service_id=service["id"],
        service_name=service["name"],
        service_price=service["price"],
        service_duration=service["duration_minutes"],
    )
    await state.set_state(BookingStates.date)
    await callback.message.edit_text(
        f"Выбрано: <b>{service['name']}</b> — {service['price']} ₽\n\n"
        "📅 Выберите дату (ближайшие 5 дней):",
        reply_markup=get_dates_keyboard(),
    )
    await callback.answer()


@router.callback_query(BookingStates.date, F.data.startswith("date:"))
async def cb_date(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.split(":")[1]
    data = await state.get_data()
    duration = data["service_duration"]
    await state.update_data(booking_date=date_str)
    await state.set_state(BookingStates.time)
    free_slots = get_free_slots(date_str, duration)
    if not free_slots:
        await callback.message.edit_text(
            f"На {format_date(date_str)} свободного времени нет. Выберите другую дату:",
            reply_markup=get_dates_keyboard(),
        )
    else:
        await callback.message.edit_text(
            f"📅 Дата: {format_date(date_str)}\n"
            "🕒 Выберите свободное время:",
            reply_markup=get_times_keyboard(free_slots),
        )
    await callback.answer()


@router.callback_query(BookingStates.time, F.data.startswith("time:"))
async def cb_time(callback: CallbackQuery, state: FSMContext):
    time_str = callback.data.split(":")[1]
    data = await state.get_data()
    await state.update_data(booking_time=time_str)
    await state.set_state(BookingStates.name)
    await callback.message.edit_text(
        f"📅 {format_date(data['booking_date'])} | 🕒 {time_str}\n\n"
        "Введите, пожалуйста, ваше имя:",
    )
    await callback.answer()


@router.callback_query(BookingStates.service, F.data == "booking:back")
@router.callback_query(BookingStates.date, F.data == "booking:back")
@router.callback_query(BookingStates.time, F.data == "booking:back")
async def cb_booking_back(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BookingStates.service)
    await callback.message.edit_text(
        "💅 Выберите услугу:", reply_markup=get_services_keyboard(get_services())
    )
    await callback.answer()


@router.message(BookingStates.name, F.text)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(client_name=message.text.strip())
    await state.set_state(BookingStates.phone)
    await message.answer("Введите ваш номер телефона:")


@router.message(BookingStates.phone, F.text)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(client_phone=message.text.strip())
    update_user_phone(message.from_user.id, message.text.strip())
    await state.set_state(BookingStates.confirm)
    data = await state.get_data()
    text = (
        "📋 <b>Проверьте данные перед подтверждением записи:</b>\n\n"
        f"• Услуга: {data['service_name']} — {data['service_price']} ₽\n"
        f"• Дата: {format_date(data['booking_date'])}\n"
        f"• Время: {data['booking_time']}\n"
        f"• Имя: {data['client_name']}\n"
        f"• Телефон: {data['client_phone']}\n\n"
        "Подтверждаете запись?"
    )
    await message.answer(text, reply_markup=get_confirm_keyboard())


@router.callback_query(BookingStates.confirm, F.data == "booking:confirm")
async def cb_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    booking_id = add_booking(
        user_id=callback.from_user.id,
        user_name=callback.from_user.full_name,
        user_phone=data["client_phone"],
        service_id=data["service_id"],
        service_name=data["service_name"],
        date_str=data["booking_date"],
        time_str=data["booking_time"],
    )
    await state.clear()
    await callback.message.edit_text(
        "✅ <b>Запись подтверждена!</b>\n\n"
        f"💅 {data['service_name']} — {data['service_price']} ₽\n"
        f"📅 {format_date(data['booking_date'])} | 🕒 {data['booking_time']}\n"
        f"📞 {data['client_phone']}\n\n"
        "Ждём вас в студии!",
        reply_markup=None,
    )
    await callback.message.answer("Главное меню:", reply_markup=get_main_menu())

    # Уведомление мастера о новой записи
    if ADMIN_ID:
        try:
            await callback.bot.send_message(
                ADMIN_ID,
                "🔔 <b>Новая запись!</b>\n\n"
                f"Клиент: {callback.from_user.full_name} (ID {callback.from_user.id})\n"
                f"Телефон: {data['client_phone']}\n"
                f"Услуга: {data['service_name']} — {data['service_price']} ₽\n"
                f"Дата: {format_date(data['booking_date'])}\n"
                f"Время: {data['booking_time']}",
            )
        except Exception as exc:
            log.exception("Не удалось отправить уведомление мастеру: %s", exc)
    await callback.answer()


@router.callback_query(BookingStates.confirm, F.data == "booking:cancel")
async def cb_cancel_booking_flow(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Запись отменена.", reply_markup=None)
    await callback.message.answer("Главное меню:", reply_markup=get_main_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("cancel:"))
async def cb_cancel_existing(callback: CallbackQuery):
    booking_id = int(callback.data.split(":")[1])
    success = cancel_booking(booking_id, callback.from_user.id)
    if success:
        await callback.message.edit_text("❌ Ваша запись отменена.", reply_markup=None)
        await callback.message.answer("Главное меню:", reply_markup=get_main_menu())
    else:
        await callback.answer("Не удалось отменить запись (возможно, она уже отменена)", show_alert=True)
        return
    await callback.answer()