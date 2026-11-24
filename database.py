import sqlite3
from datetime import date, datetime, timedelta

DB_NAME = "database.db"

WORK_START = "10:00"
WORK_END = "20:00"
SLOT_STEP_MINUTES = 30

WEEKDAYS_RU = {0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Вс"}


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price INTEGER NOT NULL,
            duration_minutes INTEGER NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_name TEXT,
            user_phone TEXT,
            service_id INTEGER,
            service_name TEXT NOT NULL,
            service_price INTEGER,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    cur.execute("SELECT COUNT(*) AS c FROM services")
    if cur.fetchone()["c"] == 0:
        default_services = [
            ("Маникюр без покрытия", "Классический или аппаратный маникюр без покрытия ногтей", 1500, 60),
            ("Маникюр с гель-лаком", "Маникюр с покрытием гель-лаком в один цвет", 2500, 90),
            ("Наращивание ногтей", "Наращивание ногтей гелем или акригелем", 3500, 120),
            ("Снятие покрытия", "Снятие гель-лака или искусственных ногтей", 1000, 30),
            ("Дизайн ногтей", "Декоративный дизайн (окончательная цена зависит от сложности)", 500, 30),
        ]
        cur.executemany(
            "INSERT INTO services (name, description, price, duration_minutes) VALUES (?, ?, ?, ?)",
            default_services,
        )
        conn.commit()
    conn.close()


def get_services():
    conn = get_connection()
    cur = conn.execute("SELECT * FROM services ORDER BY id")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_service(service_id: int):
    conn = get_connection()
    cur = conn.execute("SELECT * FROM services WHERE id = ?", (service_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def format_date(iso_str: str) -> str:
    d = date.fromisoformat(iso_str)
    return d.strftime("%d.%m.%Y") + f" ({WEEKDAYS_RU[d.weekday()]})"


def generate_time_slots():
    slots = []
    t = datetime.strptime(WORK_START, "%H:%M")
    end = datetime.strptime(WORK_END, "%H:%M")
    while t < end:
        slots.append(t.strftime("%H:%M"))
        t += timedelta(minutes=SLOT_STEP_MINUTES)
    return slots


def get_bookings_by_date(date_str: str):
    conn = get_connection()
    cur = conn.execute(
        """
        SELECT b.time, s.duration_minutes
        FROM bookings b
        JOIN services s ON b.service_id = s.id
        WHERE b.date = ? AND b.status = 'active'
        """,
        (date_str,),
    )
    rows = [(r["time"], r["duration_minutes"]) for r in cur.fetchall()]
    conn.close()
    return rows


def get_free_slots(date_str: str, service_duration: int):
    booked = get_bookings_by_date(date_str)
    free = []
    for slot in generate_time_slots():
        slot_start = datetime.strptime(slot, "%H:%M")
        slot_end = slot_start + timedelta(minutes=service_duration)
        overlap = False
        for b_start, b_duration in booked:
            b_start_dt = datetime.strptime(b_start, "%H:%M")
            b_end = b_start_dt + timedelta(minutes=b_duration)
            if slot_start < b_end and b_start_dt < slot_end:
                overlap = True
                break
        if not overlap:
            free.append(slot)
    return free


def add_booking(user_id, user_name, user_phone, service_id, service_name, date_str, time_str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT price FROM services WHERE id = ?", (service_id,))
    row = cur.fetchone()
    price = row["price"] if row else None
    cur.execute(
        """
        INSERT INTO bookings
            (user_id, user_name, user_phone, service_id, service_name,
             service_price, date, time, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
        """,
        (
            user_id,
            user_name,
            user_phone,
            service_id,
            service_name,
            price,
            date_str,
            time_str,
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    booking_id = cur.lastrowid
    conn.close()
    return booking_id


def get_active_bookings_by_user(user_id: int):
    conn = get_connection()
    cur = conn.execute(
        """
        SELECT * FROM bookings
        WHERE user_id = ? AND status = 'active'
        ORDER BY date, time
        """,
        (user_id,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def cancel_booking(booking_id: int, user_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE bookings
        SET status = 'cancelled'
        WHERE id = ? AND user_id = ? AND status = 'active'
        """,
        (booking_id, user_id),
    )
    conn.commit()
    changed = cur.rowcount
    conn.close()
    return changed > 0


def get_booking(booking_id: int):
    conn = get_connection()
    cur = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None