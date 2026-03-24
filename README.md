# Project 18 - Voice AI Assistant

Microservice NLP system that listens to voice input, understands it with Whisper, reasons with a LangGraph agent backed by Ollama LLM and a FAISS knowledge base, then speaks the answer back using Coqui TTS.

## Architecture

```
Frontend :3000  →  Backend :8000  →  NLP Service :8001
  React/MUI        FastAPI/httpx      Whisper + LangGraph + Ollama + FAISS + Coqui TTS
```

## What's Different from Previous Projects

| Project | Input | NLP Stack | Output |
|---------|-------|-----------|--------|
| 15 | Audio | Whisper + BART | Summary + Tasks |
| 17 | Image/PDF | Tesseract + FAISS + Ollama | Entities + Q&A |
| **18** | **Voice / Text** | **Whisper + LangGraph + Ollama + FAISS + Coqui TTS** | **Spoken answer + chat history** |

## NLP Service — 5 modules

| File | Role |
|------|------|
| `stt.py` | Whisper converts audio → text |
| `knowledge.py` | sentence-transformers + FAISS index over built-in + custom docs |
| `agent.py` | LangGraph graph: retrieve → generate → respond, with short-term memory |
| `tts.py` | Coqui TTS converts answer text → WAV audio bytes |
| `routes.py` | `/transcribe`, `/ask`, `/speak`, `/voice-ask` (full pipeline) |

## API Endpoints

| Endpoint | Input | Output |
|----------|-------|--------|
| `POST /api/v1/transcribe` | audio file | `{text, language}` |
| `POST /api/v1/ask` | `{text, history}` | `{answer, context, history}` |
| `POST /api/v1/speak` | `{text}` | WAV audio bytes |
| `POST /api/v1/voice-ask` | audio file + history | `{question, answer, context, history, audio_base64}` |

## Local Run

```bash
# Prerequisites
# 1. Install Ollama: https://ollama.ai  →  ollama pull llama3.2
# 2. Coqui TTS model downloads automatically on first run (~100MB)

# Terminal 1 - NLP Service
cd nlp-service && python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001

# Terminal 2 - Backend
cd backend && python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 3 - Frontend
cd frontend && npm install && npm start
```

- NLP Service: http://localhost:8001/docs
- Backend API: http://localhost:8000/docs
- Frontend UI: http://localhost:3000

## UI Features

- 🎙 **Voice input** — press mic button, speak, press stop → auto-transcribed and answered
- ⌨️ **Text input** — type question, press Enter or Send
- 🔊 **TTS playback** — click speaker icon on any assistant reply to hear it
- 💬 **Chat history** — full conversation with user/assistant bubbles
- 🗑 **Clear chat** — reset conversation memory

## Add Custom Knowledge

Drop `.txt` files into `nlp-service/data/knowledge/` — they are indexed automatically on startup.
