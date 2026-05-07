import os
import re
import anthropic
from agent.memory import get_history, save_message
from agent.calendar import (
    add_event, get_events, delete_event, parse_date_from_text
)
from agent.knowledge import load_knowledge
from config.prompts import get_system_prompt

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-sonnet-4-6"


async def process_message(phone: str, text: str) -> str:
    text = text.strip()

    # Calendar intent detection
    lower = text.lower()

    if _matches(lower, ["borra", "elimina", "cancela", "quita"]) and \
       _matches(lower, ["evento", "reunión", "cita", "agenda"]):
        keyword = _extract_quoted_or_last_words(text)
        return await delete_event(phone, keyword)

    # Primero verificar si quiere AGREGAR un evento (tiene verbo + objeto)
    if _matches(lower, ["agenda", "añade", "agrega", "crea", "programa", "agéndame", "añádeme"]) and \
       _matches(lower, ["reunión", "evento", "cita", "clase", "recordatorio", "llamada", "para", "el", "mañana", "hoy", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]):
        return await _handle_calendar_add(phone, text)

    # Luego verificar si quiere CONSULTAR la agenda
    if _matches(lower, ["qué tengo", "que tengo", "mi agenda", "mis eventos", "mis reuniones", "ver agenda"]):
        if "mañana" in lower:
            return await get_events(phone, "tomorrow")
        if "semana" in lower:
            return await get_events(phone, "week")
        return await get_events(phone, "today")

    if lower in ["borrar historial", "limpiar historial", "nueva conversación"]:
        from agent.memory import clear_history
        await clear_history(phone)
        return "Historial borrado. Comenzamos desde cero."

    # Standard AI response
    return await _ask_claude(phone, text)


async def _ask_claude(phone: str, user_text: str) -> str:
    history = await get_history(phone)
    knowledge = load_knowledge()
    system = get_system_prompt(knowledge)

    messages = history + [{"role": "user", "content": user_text}]

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=messages
    )

    reply = response.content[0].text

    await save_message(phone, "user", user_text)
    await save_message(phone, "assistant", reply)

    return reply


async def _handle_calendar_add(phone: str, text: str) -> str:
    # Extract event title — ask Claude to parse it
    parse_prompt = f"""Del siguiente mensaje, extrae:
1. Título del evento (conciso, 1-6 palabras)
2. Fecha en formato YYYY-MM-DD (si no se especifica, usa hoy)
3. Hora en formato HH:MM (si no se especifica, escribe "none")

Mensaje: "{text}"

Responde SOLO en este formato exacto:
TITULO: <título>
FECHA: <YYYY-MM-DD>
HORA: <HH:MM o none>"""

    resp = client.messages.create(
        model=MODEL,
        max_tokens=100,
        messages=[{"role": "user", "content": parse_prompt}]
    )
    parsed = resp.content[0].text.strip()

    title = _extract_field(parsed, "TITULO") or "Evento"
    date = _extract_field(parsed, "FECHA") or _parse_date_simple(text)
    time = _extract_field(parsed, "HORA")
    if time and time.lower() == "none":
        time = None

    result = await add_event(phone, title, date, time)
    await save_message(phone, "user", text)
    await save_message(phone, "assistant", result)
    return result


def _matches(text: str, keywords: list[str]) -> bool:
    return any(k in text for k in keywords)


def _extract_quoted_or_last_words(text: str) -> str:
    quoted = re.findall(r'"([^"]+)"', text)
    if quoted:
        return quoted[0]
    words = text.split()
    return " ".join(words[-3:]) if len(words) >= 3 else text


def _extract_field(text: str, field: str) -> str:
    match = re.search(rf"{field}:\s*(.+)", text)
    return match.group(1).strip() if match else ""


def _parse_date_simple(text: str) -> str:
    from datetime import datetime
    date, _ = parse_date_from_text(text)
    return date or datetime.now().strftime("%Y-%m-%d")
