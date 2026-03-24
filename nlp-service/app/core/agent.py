"""
LangGraph agent: routes user query through tools and generates a response.

Graph nodes:
  retrieve  → search FAISS knowledge base
  generate  → call Ollama LLM with context + memory
  respond   → return final answer

Memory: last N turns stored in state (short-term, in-process).
"""
from typing import TypedDict, Annotated
import operator
import ollama
from langgraph.graph import StateGraph, END
from app.core.knowledge import search
from app.core.config import settings

# ── State ──────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    question: str
    context: list[dict]
    history: Annotated[list[dict], operator.add]
    answer: str


# ── Nodes ──────────────────────────────────────────────────────────────────

def retrieve_node(state: AgentState) -> dict:
    chunks = search(state["question"], top_k=settings.TOP_K)
    return {"context": chunks}


def generate_node(state: AgentState) -> dict:
    context_text = "\n".join(c["chunk"] for c in state["context"])
    history_text = ""
    for turn in state["history"][-6:]:  # last 3 exchanges
        history_text += f"User: {turn['user']}\nAssistant: {turn['assistant']}\n"

    prompt = f"""You are a helpful voice assistant. Answer concisely in 1-3 sentences.
Use the context below if relevant. If not relevant, answer from your knowledge.

Context:
{context_text}

{f"Conversation history:{chr(10)}{history_text}" if history_text else ""}
User: {state["question"]}
Assistant:"""

    try:
        response = ollama.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = response["message"]["content"].strip()
    except Exception:
        # Fallback: return best context chunk
        answer = state["context"][0]["chunk"] if state["context"] else "I'm sorry, I couldn't process that."

    return {
        "answer": answer,
        "history": [{"user": state["question"], "assistant": answer}],
    }


# ── Graph ──────────────────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = build_graph()
    return _agent


def run_agent(question: str, history: list[dict] = None) -> dict:
    agent = get_agent()
    result = agent.invoke({
        "question": question,
        "context": [],
        "history": history or [],
        "answer": "",
    })
    return {
        "answer": result["answer"],
        "context": result["context"],
        "history": result["history"],
    }
