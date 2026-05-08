import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Form, Request, Response, HTTPException
from fastapi.responses import PlainTextResponse
from twilio.request_validator import RequestValidator
from twilio.rest import Client as TwilioClient
from agent.atlas import process_message
from agent.memory import init_db
from agent.ics import generate_ics

AUTHORIZED_NUMBERS = {"whatsapp:+56944657212", "whatsapp:+56984392287"}
TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN  = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_PHONE_NUMBER = os.environ["TWILIO_PHONE_NUMBER"]

twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
validator = RequestValidator(TWILIO_AUTH_TOKEN)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Atlas — Agente Personal", lifespan=lifespan)


@app.get("/")
async def root():
    return {"status": "Atlas online"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/calendar.ics")
async def calendar_ics(phone: str = "+56944657212"):
    ics = await generate_ics(phone)
    return PlainTextResponse(
        content=ics,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=atlas.ics"}
    )


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    NumMedia: str = Form(default="0"),
):
    forwarded_proto = request.headers.get("x-forwarded-proto", "https")
    host = request.headers.get("host", request.url.hostname)
    url = f"{forwarded_proto}://{host}{request.url.path}"

    form_data = dict(await request.form())
    signature = request.headers.get("X-Twilio-Signature", "")

    if not validator.validate(url, form_data, signature):
        raise HTTPException(status_code=403, detail="Firma inválida")

    if From not in AUTHORIZED_NUMBERS:
        return Response(content="", media_type="text/plain", status_code=200)

    if not Body or not Body.strip():
        return Response(content="", media_type="text/plain", status_code=200)

    phone = From.replace("whatsapp:", "")
    reply = await process_message(phone, Body)

    twilio_client.messages.create(
        body=reply,
        from_=f"whatsapp:{TWILIO_PHONE_NUMBER}",
        to=From
    )

    return Response(content="", media_type="text/plain", status_code=200)

