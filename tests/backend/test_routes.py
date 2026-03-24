import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

MOCK_ASK = {
    "question": "What is Python?",
    "answer": "Python is a high-level programming language.",
    "context": [{"chunk": "Python is a high-level language.", "score": 0.95}],
    "history": [{"user": "What is Python?", "assistant": "Python is a high-level programming language."}],
    "language": "en",
}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200


@patch("app.core.service.ask_text", new_callable=AsyncMock, return_value=MOCK_ASK)
def test_ask_endpoint(mock_ask):
    r = client.post("/api/v1/ask", json={"text": "What is Python?", "history": []})
    assert r.status_code == 200
    assert r.json()["answer"] == "Python is a high-level programming language."


@patch("app.core.service.ask_text", new_callable=AsyncMock, return_value=MOCK_ASK)
def test_ask_with_history(mock_ask):
    history = [{"user": "Hello", "assistant": "Hi!"}]
    r = client.post("/api/v1/ask", json={"text": "What is Python?", "history": history})
    assert r.status_code == 200


@patch("app.core.service.speak", new_callable=AsyncMock, return_value=b"RIFF....WAV")
def test_speak_endpoint(mock_speak):
    r = client.post("/api/v1/speak", json={"text": "Hello world", "history": []})
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
