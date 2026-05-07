import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Form, Request, Response, HTTPException
from twilio.request_validator import RequestValidator
from twilio.rest import Client as TwilioClient
from agent.atlas import process_message
from agent.memory import init_db

AUTHORIZED_NUMBER = "whatsapp:+56944657212"
TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
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


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    NumMedia: str = Form(default="0"),
):
    # Validate request comes from Twilio
    url = str(request.url)
    form_data = dict(await request.form())
    signature = request.headers.get("X-Twilio-Signature", "")

    if not validator.validate(url, form_data, signature):
        raise HTTPException(status_code=403, detail="Firma inválida")

    # Only respond to authorized number
    if From != AUTHORIZED_NUMBER:
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
