import pytest
from unittest.mock import patch, MagicMock
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
    assert r.json()["status"] == "ok"


@patch("app.core.agent.run_agent", return_value={
    "answer": "Python is a high-level programming language.",
    "context": [{"chunk": "Python is a high-level language.", "score": 0.95}],
    "history": [{"user": "What is Python?", "assistant": "Python is a high-level programming language."}],
})
def test_ask_text(mock_agent):
    r = client.post("/api/v1/nlp/ask", json={"text": "What is Python?", "history": []})
    assert r.status_code == 200
    data = r.json()
    assert "answer" in data
    assert "history" in data
    assert len(data["history"]) == 1


def test_ask_empty_text():
    r = client.post("/api/v1/nlp/ask", json={"text": "  ", "history": []})
    assert r.status_code == 400


def test_transcribe_unsupported():
    r = client.post(
        "/api/v1/nlp/transcribe",
        files={"file": ("audio.csv", b"a,b,c", "text/csv")},
    )
    assert r.status_code == 400


def test_transcribe_empty():
    r = client.post(
        "/api/v1/nlp/transcribe",
        files={"file": ("audio.wav", b"", "audio/wav")},
    )
    assert r.status_code == 400


def test_knowledge_search():
    from app.core.knowledge import search, build_index
    build_index()
    results = search("What is Python?", top_k=3)
    assert isinstance(results, list)
    assert len(results) > 0
    assert "chunk" in results[0]
    assert "score" in results[0]


@patch("app.core.agent.run_agent", return_value={
    "answer": "FastAPI is a web framework.",
    "context": [],
    "history": [{"user": "What is FastAPI?", "assistant": "FastAPI is a web framework."}],
})
def test_agent_with_history(mock_agent):
    history = [{"user": "Hello", "assistant": "Hi there!"}]
    r = client.post("/api/v1/nlp/ask", json={"text": "What is FastAPI?", "history": history})
    assert r.status_code == 200
    assert r.json()["answer"] == "FastAPI is a web framework."
