from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel
from app.core.service import transcribe_audio, ask_text, voice_ask, speak
import httpx

router = APIRouter(prefix="/api/v1", tags=["voice-assistant"])


class TextInput(BaseModel):
    text: str
    history: list[dict] = []


def _handle(e: Exception):
    if isinstance(e, httpx.ConnectError):
        raise HTTPException(status_code=503, detail="NLP service unavailable")
    if isinstance(e, httpx.HTTPStatusError):
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    raise HTTPException(status_code=500, detail=str(e))


@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    try:
        content = await file.read()
        return await transcribe_audio(file.filename, content, file.content_type or "audio/wav")
    except Exception as e:
        _handle(e)


@router.post("/ask")
async def ask(body: TextInput):
    try:
        return await ask_text(body.text, body.history)
    except Exception as e:
        _handle(e)


@router.post("/voice-ask")
async def voice_ask_endpoint(file: UploadFile = File(...), history: str = "[]"):
    try:
        content = await file.read()
        import json
        hist = json.loads(history)
        return await voice_ask(file.filename, content, file.content_type or "audio/wav", hist)
    except Exception as e:
        _handle(e)


@router.post("/speak")
async def speak_endpoint(body: TextInput):
    try:
        audio = await speak(body.text)
        return Response(content=audio, media_type="audio/wav")
    except Exception as e:
        _handle(e)
