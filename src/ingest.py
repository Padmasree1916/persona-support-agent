"""Document extraction, chunking, embedding, and persistent indexing."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import chromadb
from docx import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from sklearn.feature_extraction.text import HashingVectorizer

from .config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    DATA_DIR,
    DB_DIR,
    EMBEDDING_DIMENSIONS,
)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def _clean_text(text: str) -> str:
    """Remove page-number lines and normalize whitespace without joining paragraphs."""
    text = re.sub(r"(?m)^\s*(?:page\s+)?\d+\s*$", "", text)
    paragraphs = [re.sub(r"[ \t]+", " ", part).strip() for part in text.split("\n\n")]
    return "\n\n".join(part for part in paragraphs if part)


def extract_document(path: Path) -> list[dict[str, Any]]:
    """Extract text units while retaining human-readable location metadata."""
    suffix = path.suffix.lower()
    units: list[dict[str, Any]] = []

    if suffix == ".pdf":
        for page_number, page in enumerate(PdfReader(str(path)).pages, start=1):
            text = _clean_text(page.extract_text() or "")
            if text:
                units.append({"text": text, "source": path.name, "page": page_number})
    elif suffix == ".docx":
        document = Document(str(path))
        for section, paragraph in enumerate(document.paragraphs, start=1):
            text = _clean_text(paragraph.text)
            if text:
                units.append({"text": text, "source": path.name, "section": section})
    elif suffix in {".txt", ".md"}:
        text = _clean_text(path.read_text(encoding="utf-8", errors="ignore"))
        if text:
            units.append({"text": text, "source": path.name, "section": 1})

    return units


def load_documents(data_dir: Path = DATA_DIR) -> list[dict[str, Any]]:
    if not data_dir.exists():
        return []
    units: list[dict[str, Any]] = []
    for path in sorted(data_dir.iterdir()):
        if (
            path.is_file()
            and path.name.lower() != "readme.md"
            and path.suffix.lower() in SUPPORTED_EXTENSIONS
        ):
            units.extend(extract_document(path))
    return units


def chunk_documents(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks: list[dict[str, Any]] = []
    for unit in units:
        for chunk_number, text in enumerate(splitter.split_text(unit["text"]), start=1):
            metadata = {key: value for key, value in unit.items() if key != "text"}
            metadata["chunk"] = chunk_number
            digest = hashlib.sha256(
                f"{metadata}|{text}".encode("utf-8")
            ).hexdigest()[:24]
            chunks.append({"id": digest, "text": text, "metadata": metadata})
    return chunks


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Create a stable batch of local word/character n-gram embeddings."""
    vectorizer = HashingVectorizer(
        n_features=EMBEDDING_DIMENSIONS,
        alternate_sign=False,
        norm="l2",
        stop_words="english",
        ngram_range=(1, 2),
    )
    return vectorizer.transform(texts).toarray().astype(float).tolist()


def index_documents(force_rebuild: bool = False) -> int:
    """Batch-index all supported files. Existing indexes remain unless rebuilt."""
    units = load_documents()
    if not units:
        raise RuntimeError(f"No supported documents found in {DATA_DIR}")
    chunks = chunk_documents(units)

    DB_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(DB_DIR))
    if force_rebuild:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    existing = set(collection.get(include=[])["ids"])
    pending = [chunk for chunk in chunks if chunk["id"] not in existing]
    if pending:
        # One collection call lets the embedding function process the texts in batches.
        collection.add(
            ids=[chunk["id"] for chunk in pending],
            documents=[chunk["text"] for chunk in pending],
            metadatas=[chunk["metadata"] for chunk in pending],
            embeddings=embed_texts([chunk["text"] for chunk in pending]),
        )

    print(
        f"Loaded {len(units)} document units; created {len(chunks)} chunks; "
        f"indexed {len(pending)} new chunks in {DB_DIR}."
    )
    return len(chunks)


if __name__ == "__main__":
    index_documents(force_rebuild=True)
