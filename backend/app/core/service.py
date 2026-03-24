import httpx
import json as _json
from app.core.config import settings

NLP_URL = settings.NLP_SERVICE_URL


async def transcribe_audio(filename: str, content: bytes, content_type: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{NLP_URL}/api/v1/nlp/transcribe",
            files={"file": (filename, content, content_type)},
            timeout=120.0,
        )
        r.raise_for_status()
        return r.json()


async def ask_text(text: str, history: list) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{NLP_URL}/api/v1/nlp/ask",
            json={"text": text, "history": history},
            timeout=60.0,
        )
        r.raise_for_status()
        return r.json()


async def voice_ask(filename: str, content: bytes, content_type: str, history: list) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{NLP_URL}/api/v1/nlp/voice-ask",
            files={"file": (filename, content, content_type)},
            data={"history": _json.dumps(history)},
            timeout=180.0,
        )
        r.raise_for_status()
        return r.json()


async def speak(text: str) -> bytes:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{NLP_URL}/api/v1/nlp/speak",
            json={"text": text},
            timeout=60.0,
        )
        r.raise_for_status()
        return r.content
