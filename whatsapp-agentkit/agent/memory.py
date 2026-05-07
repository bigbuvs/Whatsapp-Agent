import aiosqlite
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "agentkit.db"
MAX_HISTORY = 20


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                event_date TEXT NOT NULL,
                event_time TEXT,
                created_at TEXT NOT NULL
            )
        """)
        await db.commit()


async def save_message(phone: str, role: str, content: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (phone, role, content, created_at) VALUES (?, ?, ?, ?)",
            (phone, role, content, datetime.now().isoformat())
        )
        await db.commit()


async def get_history(phone: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """SELECT role, content FROM messages
               WHERE phone = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (phone, MAX_HISTORY)
        ) as cursor:
            rows = await cursor.fetchall()

    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


async def clear_history(phone: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM messages WHERE phone = ?", (phone,))
        await db.commit()
