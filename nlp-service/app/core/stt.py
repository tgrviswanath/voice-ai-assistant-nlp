"""
Whisper-based speech-to-text transcriber.
Accepts audio bytes (wav, mp3, m4a, ogg, flac, webm).
"""
import os
import tempfile
import whisper
from app.core.config import settings

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = whisper.load_model(settings.WHISPER_MODEL)
    return _model


def transcribe(audio_bytes: bytes, filename: str = "audio.wav") -> dict:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "wav"
    model = _get_model()

    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        result = model.transcribe(tmp_path, fp16=False)
        return {
            "text": result["text"].strip(),
            "language": result.get("language", "en"),
        }
    finally:
        os.unlink(tmp_path)
