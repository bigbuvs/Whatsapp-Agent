import os
import re
import json
import anthropic
from agent.memory import get_history, save_message, clear_history
from agent.calendar import add_event, get_events, delete_event
from agent.knowledge import load_knowledge
from config.prompts import get_system_prompt

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-sonnet-4-6"

INTENT_PROMPT = """Analiza el siguiente mensaje y determina qué acción realizar.
Responde SOLO con un objeto JSON válido, sin texto adicional.

Opciones:
1. Crear evento: {"action": "add_event", "title": "...", "date": "YYYY-MM-DD", "time": "HH:MM o null"}
2. Ver agenda hoy: {"action": "get_events", "period": "today"}
3. Ver agenda mañana: {"action": "get_events", "period": "tomorrow"}
4. Ver agenda semana: {"action": "get_events", "period": "week"}
5. Eliminar evento: {"action": "delete_event", "keyword": "..."}
6. Borrar historial: {"action": "clear_history"}
7. Respuesta normal: {"action": "chat"}

Fecha actual: {date}

Mensaje: "{message}"

Responde SOLO con el JSON:"""


async def process_message(phone: str, text: str) -> str:
    text = text.strip()
    if not text:
        return "No recibí ningún mensaje."

    from datetime import datetime
    today = datetime.now().strftime("%A %d de %B de %Y")

    # Ask Claude to detect intent
    try:
        intent_resp = client.messages.create(
            model=MODEL,
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": INTENT_PROMPT.format(date=today, message=text)
            }]
        )
        raw = intent_resp.content[0].text.strip()
        # Extract JSON if wrapped in markdown
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        intent = json.loads(json_match.group() if json_match else raw)
    except Exception:
        intent = {"action": "chat"}

    action = intent.get("action", "chat")

    if action == "clear_history":
        await clear_history(phone)
        return "Historial borrado. Comenzamos desde cero."

    if action == "get_events":
        period = intent.get("period", "today")
        return await get_events(phone, period)

    if action == "delete_event":
        keyword = intent.get("keyword", text)
        return await delete_event(phone, keyword)

    if action == "add_event":
        title = intent.get("title") or "Evento"
        date = intent.get("date") or datetime.now().strftime("%Y-%m-%d")
        time = intent.get("time") or None
        if time == "null":
            time = None
        result = await add_event(phone, title, date, time)
        await save_message(phone, "user", text)
        await save_message(phone, "assistant", result)
        return result

    # Default: chat with Claude
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
