from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel
from app.core.stt import transcribe
from app.core.tts import synthesize
from app.core.agent import run_agent

router = APIRouter(prefix="/api/v1/nlp", tags=["voice-assistant"])

AUDIO_EXTS = {"wav", "mp3", "m4a", "ogg", "flac", "webm"}


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
    return transcribe(content, file.filename)


@router.post("/ask", response_model=VoiceResponse)
def ask_text(body: TextInput):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text cannot be empty")
    result = run_agent(body.text, body.history)
    return VoiceResponse(
        question=body.text,
        answer=result["answer"],
        context=result["context"],
        history=result["history"],
    )


@router.post("/speak")
def speak(body: TextInput):
    """Returns WAV audio bytes for the given text."""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text cannot be empty")
    audio = synthesize(body.text)
    if not audio:
        raise HTTPException(status_code=503, detail="TTS unavailable")
    return Response(content=audio, media_type="audio/wav")


@router.post("/voice-ask")
async def voice_ask(file: UploadFile = File(...), history: str = "[]"):
    """Full pipeline: audio → STT → agent → TTS. Returns JSON with answer + audio base64."""
    import json, base64
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in AUDIO_EXTS:
        raise HTTPException(status_code=400, detail=f"Unsupported audio format: .{ext}")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty audio file")

    stt_result = transcribe(content, file.filename)
    question = stt_result["text"]
    if not question:
        raise HTTPException(status_code=422, detail="Could not transcribe audio")

    try:
        hist = json.loads(history)
    except Exception:
        hist = []

    agent_result = run_agent(question, hist)
    audio_bytes = synthesize(agent_result["answer"])

    return {
        "question": question,
        "answer": agent_result["answer"],
        "context": agent_result["context"],
        "history": agent_result["history"],
        "language": stt_result.get("language", "en"),
        "audio_base64": base64.b64encode(audio_bytes).decode() if audio_bytes else "",
    }
