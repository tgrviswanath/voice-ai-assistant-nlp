from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "Voice AI Assistant NLP Service"
    SERVICE_VERSION: str = "1.0.0"
    SERVICE_PORT: int = 8001
    WHISPER_MODEL: str = "base"
    TTS_MODEL: str = "tts_models/en/ljspeech/tacotron2-DDC"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    TOP_K: int = 3

    class Config:
        env_file = ".env"


settings = Settings()
