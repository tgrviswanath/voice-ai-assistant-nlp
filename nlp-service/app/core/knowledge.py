"""
FAISS-based knowledge base.
Loads plain-text documents from nlp-service/data/knowledge/
and builds a searchable vector index.
"""
import os
import glob
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from app.core.config import settings

_embedder = None
_index = None
_chunks: list[str] = []

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "knowledge")

# Built-in sample knowledge so the assistant works out of the box
_SAMPLE_DOCS = [
    "Python is a high-level, interpreted programming language known for its simplicity and readability.",
    "FastAPI is a modern, fast web framework for building APIs with Python based on standard type hints.",
    "LangGraph is a library for building stateful, multi-actor applications with LLMs using a graph-based workflow.",
    "Whisper is an automatic speech recognition system developed by OpenAI, trained on 680,000 hours of multilingual data.",
    "Coqui TTS is an open-source text-to-speech library that supports many languages and voice models.",
    "FAISS (Facebook AI Similarity Search) is a library for efficient similarity search and clustering of dense vectors.",
    "Ollama allows you to run large language models locally on your machine without internet access.",
    "Sentence Transformers provide pre-trained models to compute dense vector representations of sentences.",
    "spaCy is an industrial-strength natural language processing library for Python.",
    "The all-MiniLM-L6-v2 model is a lightweight sentence transformer that maps sentences to a 384-dimensional vector space.",
]


def _get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _embedder


def _load_knowledge_files() -> list[str]:
    docs = list(_SAMPLE_DOCS)
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    for path in glob.glob(os.path.join(KNOWLEDGE_DIR, "*.txt")):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            # Split into paragraphs
            for para in content.split("\n\n"):
                para = para.strip()
                if len(para) > 20:
                    docs.append(para)
    return docs


def build_index():
    global _index, _chunks
    embedder = _get_embedder()
    _chunks = _load_knowledge_files()
    embeddings = embedder.encode(_chunks, convert_to_numpy=True, normalize_embeddings=True)
    dim = embeddings.shape[1]
    _index = faiss.IndexFlatIP(dim)
    _index.add(embeddings.astype(np.float32))


def search(query: str, top_k: int = None) -> list[dict]:
    global _index, _chunks
    if _index is None:
        build_index()
    k = top_k or settings.TOP_K
    embedder = _get_embedder()
    q_vec = embedder.encode([query], convert_to_numpy=True, normalize_embeddings=True)
    scores, indices = _index.search(q_vec.astype(np.float32), min(k, len(_chunks)))
    return [
        {"chunk": _chunks[idx], "score": round(float(score), 4)}
        for score, idx in zip(scores[0], indices[0])
        if idx >= 0
    ]
