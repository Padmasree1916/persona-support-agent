import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / ".env.local", override=True)


def _gemini_api_key() -> str:
    value = os.getenv("GEMINI_API_KEY", "").strip()
    return "" if value.startswith("replace_with_") else value


@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", "data")))
    chroma_dir: Path = field(default_factory=lambda: Path(os.getenv("CHROMA_DIR", "chroma_db")))
    gemini_api_key: str = field(default_factory=_gemini_api_key)
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    top_k: int = field(default_factory=lambda: int(os.getenv("TOP_K", "3")))
    retrieval_threshold: float = field(default_factory=lambda: float(os.getenv("RETRIEVAL_THRESHOLD", "0.12")))
    frustration_turn_limit: int = field(default_factory=lambda: int(os.getenv("FRUSTRATION_TURN_LIMIT", "2")))
    chunk_size: int = 700
    chunk_overlap: int = 100
    collection_name: str = "adsparkx_support_kb"
    sensitive_terms: tuple[str, ...] = (
        "refund", "duplicate charge", "charged twice", "legal", "lawsuit",
        "account ownership", "delete my account", "bank details", "chargeback",
    )
