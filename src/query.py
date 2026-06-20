"""Semantic retrieval and grounded answer generation through Ollama."""

from __future__ import annotations

from typing import Any

import chromadb
from google import genai

from .config import (
    COLLECTION_NAME,
    DB_DIR,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    TOP_K,
)
from .ingest import embed_texts


def _citation(metadata: dict[str, Any]) -> str:
    location = (
        f"Page {metadata['page']}"
        if "page" in metadata
        else f"Section {metadata.get('section', 'unknown')}"
    )
    return f"{metadata.get('source', 'unknown')}, {location}"


def retrieve(question: str, top_k: int = TOP_K) -> list[dict[str, Any]]:
    if not DB_DIR.exists():
        raise RuntimeError("The index does not exist. Run `python -m src.ingest` first.")
    client = chromadb.PersistentClient(path=str(DB_DIR))
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception as exc:
        raise RuntimeError("The index is missing. Run `python -m src.ingest` first.") from exc

    count = collection.count()
    if count == 0:
        return []
    result = collection.query(
        query_embeddings=embed_texts([question]),
        n_results=min(top_k, count),
        include=["documents", "metadatas", "distances"],
    )
    return [
        {
            "text": text,
            "metadata": metadata,
            "distance": distance,
            "citation": _citation(metadata),
        }
        for text, metadata, distance in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0]
        )
    ]


def generate_answer(
    question: str,
    chunks: list[dict[str, Any]],
    api_key: str | None = None,
) -> str:
    if not chunks:
        return "I cannot find the answer in the provided documents."
    context = "\n\n---\n\n".join(
        f"[Source: {chunk['citation']}]\n{chunk['text']}" for chunk in chunks
    )
    prompt = f"""You are a precise document Q&A assistant.
Use ONLY the supplied context. Cite factual claims inline as (filename, Page N) or
(filename, Section N). If the context does not answer the question, reply exactly:
I cannot find the answer in the provided documents.
Do not use outside knowledge or invent details.

CONTEXT:
{context}

QUESTION: {question}

GROUNDED ANSWER:"""
    resolved_key = (api_key or GEMINI_API_KEY).strip()
    if not resolved_key:
        raise RuntimeError(
            "Gemini API key is missing. Enter it in the Streamlit sidebar or set "
            "GEMINI_API_KEY in the .env file."
        )
    try:
        client = genai.Client(api_key=resolved_key)
        response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    except Exception as exc:
        raise RuntimeError(f"Gemini request failed: {exc}") from exc
    if not response.text:
        raise RuntimeError("Gemini returned an empty response.")
    return response.text.strip()


def answer_question(
    question: str,
    top_k: int = TOP_K,
    api_key: str | None = None,
) -> dict[str, Any]:
    chunks = retrieve(question, top_k)
    return {
        "answer": generate_answer(question, chunks, api_key=api_key),
        "chunks": chunks,
    }
