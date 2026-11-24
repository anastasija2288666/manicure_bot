import logging
from datetime import date, timedelta

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config import ADMIN_ID
from database import (
    add_blocked_slot,
    add_or_update_user,
    delete_booking,
    get_all_active_bookings,
    get_all_blocked_slots,
    get_all_users,
    get_blocked_slots,
    get_free_slots,
    get_booking,
    get_service,
    get_services,
    update_service_price,
)
from keyboards import (
    get_admin_bookings_keyboard,
    get_admin_menu,
    get_admin_services_keyboard,
    get_block_dates_keyboard,
    get_block_times_keyboard,
    get_cancel_keyboard,
    get_main_menu,
)

router = Router()
log = logging.getLogger(__name__)


class AdminStates(StatesGroup):
    waiting_for_price = State()
    waiting_for_broadcast = State()


def _is_admin(user_id: int) -> bool:
    return ADMIN_ID is not None and user_id == ADMIN_ID


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к админ-панели.")
        return
    await state.clear()
    await message.answer("🔐 Админ-панель студии маникюра:", reply_markup=get_admin_menu())


@router.callback_query(F.data == "admin:exit")
async def cb_admin_exit(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Вы вышли из админ-режима.", reply_markup=None)
    await callback.message.answer("Главное меню:", reply_markup=get_main_menu())
    await callback.answer()


@router.callback_query(F.data == "admin:back")
async def cb_admin_back(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await callback.message.edit_text("🔐 Админ-панель студии маникюра:", reply_markup=get_admin_menu())
    await callback.answer()


# ---------- 📋 Все записи ----------

@router.callback_query(F.data == "admin:bookings")
async def cb_admin_bookings(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    bookings = get_all_active_bookings()
    if not bookings:
        await callback.message.edit_text(
            "Активных записей нет.", reply_markup=get_admin_menu()
        )
    else:
        await callback.message.edit_text(
            "📋 <b>Все активные записи:</b>", reply_markup=get_admin_bookings_keyboard(bookings)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:cancel:"))
async def cb_admin_cancel_booking(callback: CallbackQuery, bot: Bot):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    booking_id = int(callback.data.split(":")[2])

    booking = get_booking(booking_id)
    if not booking:
        await callback.answer("Запись не найдена", show_alert=True)
        return

    success = delete_booking(booking_id)
    if success:
        try:
            await bot.send_message(
                booking["user_id"],
                (
                    "⛔ <b>Ваша запись отменена мастером</b>\n\n"
                    f"Услуга: {booking['service_name']}\n"
                    f"Дата: {booking['date']}\n"
                    f"Время: {booking['time']}\n\n"
                    "Приносим извинения за неудобства. "
                    "Вы можете записаться на другое время через бота."
                ),
            )
        except Exception as exc:
            log.exception("Не удалось уведомить клиента об отмене: %s", exc)

        await callback.answer("Запись удалена и клиент уведомлён", show_alert=True)
        bookings = get_all_active_bookings()
        if not bookings:
            await callback.message.edit_text(
                "Активных записей нет.", reply_markup=get_admin_menu()
            )
        else:
            await callback.message.edit_text(
                "📋 <b>Все активные записи:</b>",
                reply_markup=get_admin_bookings_keyboard(bookings),
            )
    else:
        await callback.answer("Не удалось удалить запись", show_alert=True)


# ---------- 🚫 Закрыть день/окно ----------

@router.callback_query(F.data == "admin:block_menu")
async def cb_admin_block_menu(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(
        "🚫 Выберите дату для блокировки времени:",
        reply_markup=get_block_dates_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("block:date:"))
async def cb_admin_block_date(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    date_str = callback.data.split(":")[2]
    await state.update_data(block_date=date_str)

    blocked_rows = get_blocked_slots(date_str)
    blocked_times = {r[0] for r in blocked_rows}

    await callback.message.edit_text(
        f"📅 Дата: {date_str}\n"
        "Выберите время для блокировки (⛔ — уже заблокировано):",
        reply_markup=get_block_times_keyboard(date_str, blocked_times),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("block:time:"))
async def cb_admin_block_time(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    parts = callback.data.split(":")
    date_str = parts[2]
    time_str = parts[3]

    data = await state.get_data()
    blocked_times = set(data.get("blocked_times_toggle", []))

    if time_str in blocked_times:
        blocked_times.discard(time_str)
    else:
        blocked_times.add(time_str)
    await state.update_data(blocked_times_toggle=list(blocked_times))

    await callback.message.edit_reply_markup(
        reply_markup=get_block_times_keyboard(date_str, blocked_times)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("block:done:"))
async def cb_admin_block_done(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    date_str = callback.data.split(":")[2]
    data = await state.get_data()
    selected_times = set(data.get("blocked_times_toggle", []))

    if not selected_times:
        await callback.answer("Вы не выбрали время для блокировки", show_alert=True)
        return

    blocked_count = 0
    for time_str in selected_times:
        if add_blocked_slot(date_str, time_str, reason="Админ-панель"):
            blocked_count += 1

    await state.update_data(blocked_times_toggle=[])
    await callback.message.edit_text(
        f"✅ Заблокировано {blocked_count} времен(а/ов) на {date_str}.",
        reply_markup=get_admin_menu(),
    )
    await callback.answer()


# ---------- 💅 Изменить прайс ----------

@router.callback_query(F.data == "admin:price_menu")
async def cb_admin_price_menu(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    services = get_services()
    await callback.message.edit_text(
        "💅 Выберите услугу для изменения цены:",
        reply_markup=get_admin_services_keyboard(services),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:price:set:"))
async def cb_admin_price_set(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    service_id = int(callback.data.split(":")[3])
    service = get_service(service_id)
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    await state.update_data(price_service_id=service_id)
    await state.set_state(AdminStates.waiting_for_price)
    await callback.message.edit_text(
        f"Услуга: <b>{service['name']}</b>\n"
        f"Текущая цена: {service['price']} ₽\n\n"
        "Введите новую цену числом (например, 2500):"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_price, F.text)
async def process_admin_price(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    try:
        new_price = int(message.text.strip())
        if new_price < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное целое число (например, 2500).")
        return

    data = await state.get_data()
    service_id = data["price_service_id"]
    service = get_service(service_id)
    success = update_service_price(service_id, new_price)
    await state.clear()

    if success:
        await message.answer(
            f"✅ Цена на услугу «{service['name']}» обновлена: {new_price} ₽",
            reply_markup=get_admin_menu(),
        )
    else:
        await message.answer("❌ Не удалось обновить цену.", reply_markup=get_admin_menu())


# ---------- 📢 Рассылка клиентам ----------

@router.callback_query(F.data == "admin:broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.message.edit_text(
        "📢 Введите текст рассылки, который будет отправлен всем клиентам:"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_broadcast, F.text)
async def process_admin_broadcast(message: Message, state: FSMContext, bot: Bot):
    if not _is_admin(message.from_user.id):
        return
    text = message.text.strip()
    if not text:
        await message.answer("❌ Текст не может быть пустым.")
        return

    users = get_all_users()
    await state.clear()

    sent = 0
    failed = 0
    for user_id, _username, _first_name, _last_name, _phone in users:
        try:
            await bot.send_message(user_id, f"📢 <b>Сообщение от студии:</b>\n\n{text}")
            sent += 1
        except Exception as exc:
            log.exception("Не удалось отправить сообщение пользователю %s: %s", user_id, exc)
            failed += 1

    await message.answer(
        f"📊 Рассылка завершена:\n"
        f"• Отправлено: {sent}\n"
        f"• Не доставлено: {failed}",
        reply_markup=get_admin_menu(),
    )
