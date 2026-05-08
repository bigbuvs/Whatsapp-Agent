import os
import aiosqlite
import re
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(os.environ.get("DB_PATH", str(Path(__file__).parent.parent / "agentkit.db")))


async def add_event(phone: str, title: str, event_date: str, event_time: str = None, description: str = None) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO events (phone, title, description, event_date, event_time, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (phone, title, description, event_date, event_time, datetime.now().isoformat())
        )
        await db.commit()

    time_str = f" a las {event_time}" if event_time else ""
    return f'Evento "{title}" agendado para el {event_date}{time_str}.'


async def get_events(phone: str, date_filter: str = "today") -> str:
    today = datetime.now().date()

    if date_filter == "today":
        start = today.isoformat()
        end = today.isoformat()
        label = "hoy"
    elif date_filter == "tomorrow":
        tomorrow = (today + timedelta(days=1))
        start = tomorrow.isoformat()
        end = tomorrow.isoformat()
        label = "mañana"
    elif date_filter == "week":
        start = today.isoformat()
        end = (today + timedelta(days=7)).isoformat()
        label = "esta semana"
    else:
        start = today.isoformat()
        end = (today + timedelta(days=30)).isoformat()
        label = "próximos 30 días"

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """SELECT title, description, event_date, event_time
               FROM events
               WHERE phone = ? AND event_date BETWEEN ? AND ?
               ORDER BY event_date, event_time""",
            (phone, start, end)
        ) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        return f"No tienes eventos agendados para {label}."

    lines = [f"Agenda para {label}:"]
    for title, desc, date, time in rows:
        time_str = f" — {time}" if time else ""
        desc_str = f"\n  {desc}" if desc else ""
        lines.append(f"• {date}{time_str}: {title}{desc_str}")

    return "\n".join(lines)


async def delete_event(phone: str, title_keyword: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, title FROM events WHERE phone = ? AND title LIKE ?",
            (phone, f"%{title_keyword}%")
        ) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            return f'No encontré ningún evento con "{title_keyword}".'

        if len(rows) == 1:
            await db.execute("DELETE FROM events WHERE id = ?", (rows[0][0],))
            await db.commit()
            return f'Evento "{rows[0][1]}" eliminado.'

        titles = "\n".join([f"• {r[1]}" for r in rows])
        return f"Encontré múltiples eventos. Sé más específico:\n{titles}"


def parse_date_from_text(text: str) -> tuple[str, str]:
    today = datetime.now()
    text_lower = text.lower()

    if "hoy" in text_lower:
        return today.strftime("%Y-%m-%d"), ""
    if "mañana" in text_lower:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d"), ""

    days = {"lunes": 0, "martes": 1, "miércoles": 2, "jueves": 3,
            "viernes": 4, "sábado": 5, "domingo": 6}
    for day_name, day_num in days.items():
        if day_name in text_lower:
            diff = (day_num - today.weekday()) % 7 or 7
            return (today + timedelta(days=diff)).strftime("%Y-%m-%d"), ""

    time_match = re.search(r'(\d{1,2})[:\.]?(\d{0,2})\s*(am|pm)?', text_lower)
    time_str = ""
    if time_match:
        hour = int(time_match.group(1))
        minutes = time_match.group(2) or "00"
        period = time_match.group(3)
        if period == "pm" and hour < 12:
            hour += 12
        time_str = f"{hour:02d}:{minutes.zfill(2)}"

    return today.strftime("%Y-%m-%d"), time_str
