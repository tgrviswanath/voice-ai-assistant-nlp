# AWS Deployment Guide — Project 18 Voice AI Assistant

---

## AWS Services for Voice AI Assistant

### 1. Ready-to-Use AI (No Model Needed)

| Service                    | What it does                                                                 | When to use                                        |
|----------------------------|------------------------------------------------------------------------------|----------------------------------------------------|
| **Amazon Transcribe**      | Speech-to-text — replace OpenAI Whisper                                     | Replace your Whisper STT pipeline                  |
| **Amazon Bedrock**         | Claude/Titan for LLM reasoning — replace Ollama llama3.2                    | Replace your local Ollama LLM                      |
| **Amazon Polly**           | Text-to-speech — replace Coqui TTS                                          | Replace your Coqui TTS pipeline                    |
| **Amazon Lex**             | Conversational AI with built-in session memory and intent detection          | Replace your LangGraph agent                       |

> **Amazon Transcribe + Bedrock + Polly** replace your Whisper + LangGraph + Ollama + Coqui TTS pipeline with fully managed services.

### 2. Host Your Own Model (Keep Current Stack)

| Service                    | What it does                                                        | When to use                                           |
|----------------------------|---------------------------------------------------------------------|-------------------------------------------------------|
| **AWS App Runner**         | Run backend container — simplest, no VPC or cluster needed          | Quickest path to production                           |
| **Amazon ECS Fargate**     | Run backend + nlp-service containers in a private VPC               | Best match for your current microservice architecture |
| **Amazon ECR**             | Store your Docker images                                            | Used with App Runner, ECS, or EKS                     |

### 3. Supporting Services

| Service                  | Purpose                                                                   |
|--------------------------|---------------------------------------------------------------------------|
| **Amazon S3**            | Store audio files and knowledge base documents                            |
| **Amazon DynamoDB**      | Persistent conversation memory per session                                |
| **AWS Secrets Manager**  | Store API keys and connection strings instead of .env files               |
| **Amazon CloudWatch**    | Track STT/TTS latency, session counts, request volume                     |

---

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  S3 + CloudFront — React Chat Frontend                      │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────────────────────┐
│  AWS App Runner / ECS Fargate — Backend (FastAPI :8000)     │
└──────────────────────┬──────────────────────────────────────┘
                       │ Internal
        ┌──────────────┴──────────────┐
        │ Option A                    │ Option B
        ▼                             ▼
┌───────────────────┐    ┌────────────────────────────────────┐
│ ECS Fargate       │    │ Amazon Transcribe + Bedrock        │
│ NLP Service :8001 │    │ + Amazon Polly (TTS)               │
│ Whisper+LangGraph │    │ No model download needed           │
│ +Ollama+CoquiTTS  │    │                                    │
└───────────────────┘    └────────────────────────────────────┘
```

---

## Prerequisites

```bash
aws configure
AWS_REGION=eu-west-2
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
```

---

## Step 1 — Create ECR and Push Images

```bash
aws ecr create-repository --repository-name voiceai/nlp-service --region $AWS_REGION
aws ecr create-repository --repository-name voiceai/backend --region $AWS_REGION
ECR=$AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR
docker build -f docker/Dockerfile.nlp-service -t $ECR/voiceai/nlp-service:latest ./nlp-service
docker push $ECR/voiceai/nlp-service:latest
docker build -f docker/Dockerfile.backend -t $ECR/voiceai/backend:latest ./backend
docker push $ECR/voiceai/backend:latest
```

---

## Step 2 — Deploy with App Runner

```bash
aws apprunner create-service \
  --service-name voiceai-backend \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "'$ECR'/voiceai/backend:latest",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "8000",
        "RuntimeEnvironmentVariables": {
          "NLP_SERVICE_URL": "http://nlp-service:8001"
        }
      }
    }
  }' \
  --instance-configuration '{"Cpu": "2 vCPU", "Memory": "4 GB"}' \
  --region $AWS_REGION
```

---

## Option B — Use Amazon Transcribe + Bedrock + Polly

```python
import boto3, json, io

transcribe = boto3.client("transcribe", region_name="eu-west-2")
bedrock = boto3.client("bedrock-runtime", region_name="eu-west-2")
polly = boto3.client("polly", region_name="eu-west-2")

def transcribe_audio(s3_uri: str, job_name: str) -> str:
    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": s3_uri},
        MediaFormat="wav",
        LanguageCode="en-US"
    )
    import time
    while True:
        status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        if status["TranscriptionJob"]["TranscriptionJobStatus"] in ["COMPLETED", "FAILED"]:
            break
        time.sleep(3)
    import urllib.request
    with urllib.request.urlopen(status["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]) as f:
        return json.loads(f.read())["results"]["transcripts"][0]["transcript"]

def generate_answer(question: str, context: str) -> str:
    response = bedrock.invoke_model(
        modelId="anthropic.claude-v2",
        body=json.dumps({"prompt": f"Context: {context}\n\nQuestion: {question}\nAnswer:", "max_tokens_to_sample": 300}),
        contentType="application/json"
    )
    return json.loads(response["body"].read())["completion"].strip()

def text_to_speech(text: str) -> bytes:
    response = polly.synthesize_speech(Text=text, OutputFormat="mp3", VoiceId="Joanna")
    return response["AudioStream"].read()
```

---

## Estimated Monthly Cost

| Service                    | Tier              | Est. Cost          |
|----------------------------|-------------------|--------------------|
| App Runner (backend)       | 2 vCPU / 4 GB     | ~$30–40/month      |
| App Runner (nlp-service)   | 2 vCPU / 4 GB     | ~$30–40/month      |
| ECR + S3 + CloudFront      | Standard          | ~$3–7/month        |
| Amazon Transcribe          | Pay per minute    | ~$2–5/month        |
| Amazon Bedrock (Claude)    | Pay per token     | ~$5–15/month       |
| Amazon Polly               | Pay per character | ~$1–3/month        |
| **Total (Option A)**       |                   | **~$63–87/month**  |
| **Total (Option B)**       |                   | **~$41–70/month**  |

For exact estimates → https://calculator.aws

---

## Teardown

```bash
aws ecr delete-repository --repository-name voiceai/backend --force
aws ecr delete-repository --repository-name voiceai/nlp-service --force
```
