import asyncio
import json
import base64
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel
from app.core.stt import transcribe
from app.core.tts import synthesize
from app.core.agent import run_agent

MAX_AUDIO_SIZE = 100 * 1024 * 1024  # 100 MB
AUDIO_EXTS = {"wav", "mp3", "m4a", "ogg", "flac", "webm"}

router = APIRouter(prefix="/api/v1/nlp", tags=["voice-assistant"])


class TextInput(BaseModel):
    text: str
    history: list[dict] = []


class VoiceResponse(BaseModel):
    question: str
    answer: str
    context: list[dict]
    history: list[dict]
    language: str = "en"


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in AUDIO_EXTS:
        raise HTTPException(status_code=400, detail=f"Unsupported audio format: .{ext}")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty audio file")
    if len(content) > MAX_AUDIO_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max 100MB")
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, transcribe, content, file.filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask", response_model=VoiceResponse)
async def ask_text(body: TextInput):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text cannot be empty")
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, run_agent, body.text, body.history)
        return VoiceResponse(
            question=body.text,
            answer=result["answer"],
            context=result["context"],
            history=result["history"],
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/speak")
async def speak(body: TextInput):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text cannot be empty")
    loop = asyncio.get_running_loop()
    audio = await loop.run_in_executor(None, synthesize, body.text)
    if not audio:
        raise HTTPException(status_code=503, detail="TTS unavailable")
    return Response(content=audio, media_type="audio/wav")


@router.post("/voice-ask")
async def voice_ask(file: UploadFile = File(...), history: str = "[]"):
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in AUDIO_EXTS:
        raise HTTPException(status_code=400, detail=f"Unsupported audio format: .{ext}")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty audio file")
    if len(content) > MAX_AUDIO_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max 100MB")
    try:
        hist = json.loads(history)
    except Exception:
        hist = []
    try:
        loop = asyncio.get_running_loop()
        stt_result = await loop.run_in_executor(None, transcribe, content, file.filename)
        question = stt_result["text"]
        if not question:
            raise HTTPException(status_code=422, detail="Could not transcribe audio")
        agent_result = await loop.run_in_executor(None, run_agent, question, hist)
        audio_bytes = await loop.run_in_executor(None, synthesize, agent_result["answer"])
        return {
            "question": question,
            "answer": agent_result["answer"],
            "context": agent_result["context"],
            "history": agent_result["history"],
            "language": stt_result.get("language", "en"),
            "audio_base64": base64.b64encode(audio_bytes).decode() if audio_bytes else "",
        }
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
