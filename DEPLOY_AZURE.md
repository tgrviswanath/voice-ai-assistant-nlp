# Azure Deployment Guide — Project 18 Voice AI Assistant

---

## Azure Services for Voice AI Assistant

### 1. Ready-to-Use AI (No Model Needed)

| Service                              | What it does                                                                 | When to use                                        |
|--------------------------------------|------------------------------------------------------------------------------|----------------------------------------------------|
| **Azure AI Speech — STT**            | Speech-to-text with speaker diarization — replace OpenAI Whisper             | Replace your Whisper STT pipeline                  |
| **Azure OpenAI Service**             | GPT-4 for LLM reasoning — replace Ollama llama3.2                           | Replace your local Ollama LLM                      |
| **Azure AI Speech — TTS**            | Neural text-to-speech — replace Coqui TTS                                   | Replace your Coqui TTS pipeline                    |
| **Azure AI Search**                  | Vector knowledge base — replace your in-memory FAISS KB                     | Replace your FAISS knowledge base                  |

> **Azure AI Speech + Azure OpenAI + Azure AI Search** replace your Whisper + LangGraph + Ollama + FAISS + Coqui TTS pipeline with fully managed services.

### 2. Host Your Own Model (Keep Current Stack)

| Service                        | What it does                                                        | When to use                                           |
|--------------------------------|---------------------------------------------------------------------|-------------------------------------------------------|
| **Azure Container Apps**       | Run your 3 Docker containers (frontend, backend, nlp-service)       | Best match for your current microservice architecture |
| **Azure Container Registry**   | Store your Docker images                                            | Used with Container Apps or AKS                       |

### 3. Supporting Services

| Service                       | Purpose                                                                  |
|-------------------------------|--------------------------------------------------------------------------|
| **Azure Blob Storage**        | Store audio files and knowledge base documents                           |
| **Azure Cosmos DB**           | Persistent conversation memory per session                               |
| **Azure Key Vault**           | Store API keys and connection strings instead of .env files              |
| **Azure Monitor + App Insights** | Track STT/TTS latency, session counts, request volume                |

---

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Azure Static Web Apps — React Chat Frontend                │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────────────────────┐
│  Azure Container Apps — Backend (FastAPI :8000)             │
└──────────────────────┬──────────────────────────────────────┘
                       │ Internal
        ┌──────────────┴──────────────┐
        │ Option A                    │ Option B
        ▼                             ▼
┌───────────────────┐    ┌────────────────────────────────────┐
│ Container Apps    │    │ Azure AI Speech (STT + TTS)        │
│ NLP Service :8001 │    │ + Azure OpenAI + Azure AI Search   │
│ Whisper+LangGraph │    │ No model download needed           │
│ +Ollama+CoquiTTS  │    │                                    │
└───────────────────┘    └────────────────────────────────────┘
```

---

## Prerequisites

```bash
az login
az group create --name rg-voice-ai --location uksouth
az extension add --name containerapp --upgrade
```

---

## Step 1 — Create Container Registry and Push Images

```bash
az acr create --resource-group rg-voice-ai --name voiceaiacr --sku Basic --admin-enabled true
az acr login --name voiceaiacr
ACR=voiceaiacr.azurecr.io
docker build -f docker/Dockerfile.nlp-service -t $ACR/nlp-service:latest ./nlp-service
docker push $ACR/nlp-service:latest
docker build -f docker/Dockerfile.backend -t $ACR/backend:latest ./backend
docker push $ACR/backend:latest
```

---

## Step 2 — Deploy Container Apps

```bash
az containerapp env create --name voiceai-env --resource-group rg-voice-ai --location uksouth

az containerapp create \
  --name nlp-service --resource-group rg-voice-ai \
  --environment voiceai-env --image $ACR/nlp-service:latest \
  --registry-server $ACR --target-port 8001 --ingress internal \
  --min-replicas 1 --max-replicas 3 --cpu 2 --memory 4.0Gi

az containerapp create \
  --name backend --resource-group rg-voice-ai \
  --environment voiceai-env --image $ACR/backend:latest \
  --registry-server $ACR --target-port 8000 --ingress external \
  --min-replicas 1 --max-replicas 5 --cpu 0.5 --memory 1.0Gi \
  --env-vars NLP_SERVICE_URL=http://nlp-service:8001
```

---

## Option B — Use Azure AI Speech + Azure OpenAI

```python
import azure.cognitiveservices.speech as speechsdk
from openai import AzureOpenAI
import io

speech_config = speechsdk.SpeechConfig(
    subscription=os.getenv("AZURE_SPEECH_KEY"),
    region=os.getenv("AZURE_SPEECH_REGION")
)
openai_client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-02-01"
)

def transcribe_audio(audio_path: str) -> str:
    audio_config = speechsdk.AudioConfig(filename=audio_path)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    return recognizer.recognize_once().text

def generate_answer(question: str, context: str) -> str:
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": f"Answer using this context: {context}"},
            {"role": "user", "content": question}
        ]
    )
    return response.choices[0].message.content

def text_to_speech(text: str) -> bytes:
    speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    result = synthesizer.speak_text_async(text).get()
    return result.audio_data
```

---

## Estimated Monthly Cost

| Service                  | Tier      | Est. Cost          |
|--------------------------|-----------|--------------------|
| Container Apps (backend) | 0.5 vCPU  | ~$10–15/month      |
| Container Apps (nlp-svc) | 2 vCPU    | ~$25–35/month      |
| Container Registry       | Basic     | ~$5/month          |
| Static Web Apps          | Free      | $0                 |
| Azure AI Speech (STT+TTS)| Pay per hour | ~$3–8/month     |
| Azure OpenAI (GPT-4)     | Pay per token | ~$10–25/month  |
| **Total (Option A)**     |           | **~$40–55/month**  |
| **Total (Option B)**     |           | **~$28–53/month**  |

For exact estimates → https://calculator.azure.com

---

## Teardown

```bash
az group delete --name rg-voice-ai --yes --no-wait
```
