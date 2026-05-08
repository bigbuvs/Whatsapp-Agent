import aiosqlite
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

DB_PATH = Path(__file__).parent.parent / "agentkit.db"
TIMEZONE = "America/Santiago"


async def generate_ics(phone: str) -> str:
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Atlas Personal Agent//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Atlas",
        "X-WR-TIMEZONE:America/Santiago",
        "X-WR-CALDESC:Calendario gestionado por Atlas",
    ]

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, title, description, event_date, event_time FROM events WHERE phone = ? ORDER BY event_date, event_time",
            (phone,)
        ) as cursor:
            rows = await cursor.fetchall()

    for row in rows:
        event_id, title, description, event_date, event_time = row

        uid = f"atlas-{event_id}@whatsapp-agent"
        dtstart, dtend = _build_dt(event_date, event_time, tz)

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now}",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{_escape(title)}",
        ]

        if description:
            lines.append(f"DESCRIPTION:{_escape(description)}")

        if event_time:
            lines += [
                "BEGIN:VALARM",
                "TRIGGER:-PT60M",
                "ACTION:DISPLAY",
                f"DESCRIPTION:Recordatorio: {_escape(title)}",
                "END:VALARM",
            ]

        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def _build_dt(event_date: str, event_time: str, tz) -> tuple[str, str]:
    if event_time:
        try:
            dt = datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M")
            dt = dt.replace(tzinfo=tz)
            dtstart = dt.strftime("%Y%m%dT%H%M%S")
            dtend = dt.replace(hour=dt.hour + 1).strftime("%Y%m%dT%H%M%S")
            return f"{dtstart}", f"{dtend}"
        except Exception:
            pass
    # All-day event
    d = datetime.strptime(event_date, "%Y-%m-%d").date()
    next_d = date(d.year, d.month, d.day + 1) if d.day < 28 else date(d.year, d.month + 1 if d.month < 12 else 1, 1)
    return f"{d.strftime('%Y%m%d')}", f"{next_d.strftime('%Y%m%d')}"


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
