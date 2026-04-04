# GCP Deployment Guide — Project 18 Voice AI Assistant

---

## GCP Services for Voice AI Assistant

### 1. Ready-to-Use AI (No Model Needed)

| Service                              | What it does                                                                 | When to use                                        |
|--------------------------------------|------------------------------------------------------------------------------|----------------------------------------------------|
| **Speech-to-Text API**               | Speech recognition with speaker diarization — replace OpenAI Whisper         | Replace your Whisper STT pipeline                  |
| **Vertex AI Gemini**                 | Gemini Pro for LLM reasoning — replace Ollama llama3.2                      | Replace your local Ollama LLM                      |
| **Text-to-Speech API**               | Neural text-to-speech — replace Coqui TTS                                   | Replace your Coqui TTS pipeline                    |
| **Vertex AI Matching Engine**        | Vector knowledge base — replace your in-memory FAISS KB                     | Replace your FAISS knowledge base                  |

> **Speech-to-Text + Vertex AI Gemini + Text-to-Speech** replace your Whisper + LangGraph + Ollama + FAISS + Coqui TTS pipeline with fully managed services.

### 2. Host Your Own Model (Keep Current Stack)

| Service                    | What it does                                                        | When to use                                           |
|----------------------------|---------------------------------------------------------------------|-------------------------------------------------------|
| **Cloud Run**              | Run backend + nlp-service containers — serverless, scales to zero   | Best match for your current microservice architecture |
| **Artifact Registry**      | Store your Docker images                                            | Used with Cloud Run or GKE                            |

### 3. Supporting Services

| Service                        | Purpose                                                                   |
|--------------------------------|---------------------------------------------------------------------------|
| **Cloud Storage**              | Store audio files and knowledge base documents                            |
| **Firestore**                  | Persistent conversation memory per session                                |
| **Secret Manager**             | Store API keys and connection strings instead of .env files               |
| **Cloud Monitoring + Logging** | Track STT/TTS latency, session counts, request volume                     |

---

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Firebase Hosting — React Chat Frontend                     │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────────────────────┐
│  Cloud Run — Backend (FastAPI :8000)                        │
└──────────────────────┬──────────────────────────────────────┘
                       │ Internal HTTPS
        ┌──────────────┴──────────────┐
        │ Option A                    │ Option B
        ▼                             ▼
┌───────────────────┐    ┌────────────────────────────────────┐
│ Cloud Run         │    │ Speech-to-Text API                 │
│ NLP Service :8001 │    │ + Vertex AI Gemini                 │
│ Whisper+LangGraph │    │ + Text-to-Speech API               │
│ +Ollama+CoquiTTS  │    │ No model download needed           │
└───────────────────┘    └────────────────────────────────────┘
```

---

## Prerequisites

```bash
gcloud auth login
gcloud projects create voiceai-project --name="Voice AI Assistant"
gcloud config set project voiceai-project
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com speech.googleapis.com \
  texttospeech.googleapis.com aiplatform.googleapis.com \
  firestore.googleapis.com storage.googleapis.com cloudbuild.googleapis.com
```

---

## Step 1 — Create Artifact Registry and Push Images

```bash
GCP_REGION=europe-west2
gcloud artifacts repositories create voiceai-repo \
  --repository-format=docker --location=$GCP_REGION
gcloud auth configure-docker $GCP_REGION-docker.pkg.dev
AR=$GCP_REGION-docker.pkg.dev/voiceai-project/voiceai-repo
docker build -f docker/Dockerfile.nlp-service -t $AR/nlp-service:latest ./nlp-service
docker push $AR/nlp-service:latest
docker build -f docker/Dockerfile.backend -t $AR/backend:latest ./backend
docker push $AR/backend:latest
```

---

## Step 2 — Deploy to Cloud Run

```bash
gcloud run deploy nlp-service \
  --image $AR/nlp-service:latest --region $GCP_REGION \
  --port 8001 --no-allow-unauthenticated \
  --min-instances 1 --max-instances 3 --memory 4Gi --cpu 2

NLP_URL=$(gcloud run services describe nlp-service --region $GCP_REGION --format "value(status.url)")

gcloud run deploy backend \
  --image $AR/backend:latest --region $GCP_REGION \
  --port 8000 --allow-unauthenticated \
  --min-instances 1 --max-instances 5 --memory 1Gi --cpu 1 \
  --set-env-vars NLP_SERVICE_URL=$NLP_URL
```

---

## Option B — Use Speech-to-Text + Gemini + Text-to-Speech

```python
from google.cloud import speech_v1, texttospeech_v1
import vertexai
from vertexai.generative_models import GenerativeModel

speech_client = speech_v1.SpeechClient()
tts_client = texttospeech_v1.TextToSpeechClient()
vertexai.init(project="voiceai-project", location="europe-west2")
gemini = GenerativeModel("gemini-pro")

def transcribe_audio(audio_bytes: bytes) -> str:
    audio = speech_v1.RecognitionAudio(content=audio_bytes)
    config = speech_v1.RecognitionConfig(encoding=speech_v1.RecognitionConfig.AudioEncoding.WEBM_OPUS, language_code="en-US")
    result = speech_client.recognize(config=config, audio=audio)
    return " ".join([r.alternatives[0].transcript for r in result.results])

def generate_answer(question: str, context: str) -> str:
    return gemini.generate_content(f"Context: {context}\n\nQuestion: {question}\nAnswer:").text

def text_to_speech(text: str) -> bytes:
    synthesis_input = texttospeech_v1.SynthesisInput(text=text)
    voice = texttospeech_v1.VoiceSelectionParams(language_code="en-US", name="en-US-Neural2-F")
    audio_config = texttospeech_v1.AudioConfig(audio_encoding=texttospeech_v1.AudioEncoding.MP3)
    response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    return response.audio_content
```

---

## Estimated Monthly Cost

| Service                    | Tier                  | Est. Cost          |
|----------------------------|-----------------------|--------------------|
| Cloud Run (backend)        | 1 vCPU / 1 GB         | ~$10–15/month      |
| Cloud Run (nlp-service)    | 2 vCPU / 4 GB         | ~$20–30/month      |
| Artifact Registry          | Storage               | ~$1–2/month        |
| Firebase Hosting           | Free tier             | $0                 |
| Speech-to-Text API         | Pay per minute        | ~$2–5/month        |
| Text-to-Speech API         | Pay per character     | ~$1–3/month        |
| Vertex AI Gemini           | Pay per token         | ~$5–15/month       |
| **Total (Option A)**       |                       | **~$32–48/month**  |
| **Total (Option B)**       |                       | **~$19–40/month**  |

For exact estimates → https://cloud.google.com/products/calculator

---

## Teardown

```bash
gcloud run services delete backend --region $GCP_REGION --quiet
gcloud run services delete nlp-service --region $GCP_REGION --quiet
gcloud artifacts repositories delete voiceai-repo --location=$GCP_REGION --quiet
gcloud projects delete voiceai-project
```
