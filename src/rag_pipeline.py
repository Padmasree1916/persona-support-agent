import hashlib
import math
import re
import sys
from pathlib import Path

from .config import Settings
from .models import RetrievedChunk


class LocalEmbeddingFunction:
    """Deterministic local feature-hashing embeddings; no model download required."""

    dimension = 768
    stopwords = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
        "i", "if", "in", "is", "it", "my", "of", "on", "or", "should", "the",
        "this", "to", "use", "what", "when", "where", "with", "your",
    }
    aliases = {
        "charged": "charge", "charges": "charge", "charging": "charge",
        "demands": "demand", "demanded": "demand", "twice": "duplicate",
        "refunded": "refund", "refunds": "refund",
    }

    def name(self) -> str:
        return "adsparkx-local-hashing-v1"

    def __call__(self, input: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in input]

    def embed(self, text: str) -> list[float]:
        tokens = [
            self.aliases.get(token, token)
            for token in re.findall(r"[a-z0-9]+", text.lower())
            if token not in self.stopwords
        ]
        features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        vector = [0.0] * self.dimension
        for token in features:
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            value = int.from_bytes(digest, "little")
            vector[value % self.dimension] += 1.0 if (value >> 8) & 1 else -1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class RAGPipeline:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.embedding = LocalEmbeddingFunction()
        self._fallback: list[dict] = []
        self.collection = None
        self.client = None
        # Chroma's native Windows extension does not yet run safely on Python 3.14.
        # Keep the application usable with its in-memory cosine fallback there.
        if sys.version_info >= (3, 14):
            return
        try:
            import chromadb
            self.client = chromadb.PersistentClient(path=str(settings.chroma_dir))
            self.collection = self.client.get_or_create_collection(
                name=settings.collection_name,
                embedding_function=self.embedding,
                metadata={"hnsw:space": "cosine"},
            )
        except (ImportError, ValueError, TypeError):
            self.client = None

    def ingest(self, rebuild: bool = False) -> int:
        documents = self._load_documents()
        records = []
        for source, page, text in documents:
            for index, (section, chunk) in enumerate(self._chunk(text)):
                chunk_id = hashlib.sha1(f"{source}:{page}:{index}:{chunk}".encode()).hexdigest()
                records.append({
                    "id": chunk_id, "document": chunk,
                    "metadata": {"source": source, "page": page or 0, "section": section},
                })
        self._fallback = records
        if self.collection is not None:
            if rebuild:
                self.client.delete_collection(self.settings.collection_name)
                self.collection = self.client.create_collection(
                    name=self.settings.collection_name,
                    embedding_function=self.embedding,
                    metadata={"hnsw:space": "cosine"},
                )
            for start in range(0, len(records), 100):
                batch = records[start:start + 100]
                if batch:
                    self.collection.upsert(
                        ids=[item["id"] for item in batch],
                        documents=[item["document"] for item in batch],
                        metadatas=[item["metadata"] for item in batch],
                    )
        return len(records)

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        limit = top_k or self.settings.top_k
        if self.collection is not None and self.collection.count():
            result = self.collection.query(query_texts=[query], n_results=min(limit, self.collection.count()))
            return [
                RetrievedChunk(
                    text=document,
                    source=metadata["source"],
                    section=metadata.get("section", "Document"),
                    page=metadata.get("page") or None,
                    score=max(0.0, 1.0 - float(distance)),
                )
                for document, metadata, distance in zip(
                    result["documents"][0], result["metadatas"][0], result["distances"][0]
                )
            ]
        return self._fallback_retrieve(query, limit)

    def _fallback_retrieve(self, query: str, limit: int) -> list[RetrievedChunk]:
        query_vector = self.embedding.embed(query)
        ranked = []
        for record in self._fallback:
            vector = self.embedding.embed(record["document"])
            score = sum(a * b for a, b in zip(query_vector, vector))
            ranked.append((score, record))
        return [RetrievedChunk(
            text=item["document"], source=item["metadata"]["source"],
            section=item["metadata"]["section"], page=item["metadata"]["page"] or None,
            score=max(0.0, score),
        ) for score, item in sorted(ranked, reverse=True, key=lambda pair: pair[0])[:limit]]

    def _load_documents(self) -> list[tuple[str, int | None, str]]:
        loaded = []
        for path in sorted(self.settings.data_dir.glob("*")):
            if path.suffix.lower() in {".md", ".txt"}:
                loaded.append((path.name, None, path.read_text(encoding="utf-8")))
            elif path.suffix.lower() == ".pdf":
                try:
                    from pypdf import PdfReader
                    for page_number, page in enumerate(PdfReader(path).pages, 1):
                        loaded.append((path.name, page_number, page.extract_text() or ""))
                except ImportError:
                    continue
        return loaded

    def _chunk(self, text: str) -> list[tuple[str, str]]:
        section = "Overview"
        pieces: list[tuple[str, str]] = []
        buffer = ""
        for block in re.split(r"\n\s*\n", text):
            block = block.strip()
            if not block:
                continue
            if block.startswith("#"):
                section = block.lstrip("# ").strip()
            if len(buffer) + len(block) + 2 <= self.settings.chunk_size:
                buffer = f"{buffer}\n\n{block}".strip()
            else:
                if buffer:
                    pieces.append((section, buffer))
                buffer = (buffer[-self.settings.chunk_overlap:] + "\n" + block).strip()
        if buffer:
            pieces.append((section, buffer))
        return pieces
