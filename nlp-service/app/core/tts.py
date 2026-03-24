"""
Coqui TTS: converts text response to speech audio (WAV bytes).
Falls back to empty bytes if TTS unavailable.
"""
import io
import tempfile
import os
from TTS.api import TTS as CoquiTTS
from app.core.config import settings

_tts = None


def _get_tts():
    global _tts
    if _tts is None:
        _tts = CoquiTTS(model_name=settings.TTS_MODEL, progress_bar=False)
    return _tts


def synthesize(text: str) -> bytes:
    """Returns WAV audio bytes for the given text."""
    if not text.strip():
        return b""
    try:
        tts = _get_tts()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        tts.tts_to_file(text=text[:500], file_path=tmp_path)
        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()
        os.unlink(tmp_path)
        return audio_bytes
    except Exception:
        return b""
