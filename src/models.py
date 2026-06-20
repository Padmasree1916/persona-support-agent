from dataclasses import dataclass, field
from typing import Any


PERSONAS = ("Technical Expert", "Frustrated User", "Business Executive")


@dataclass(slots=True)
class PersonaResult:
    persona: str
    confidence: float
    reasoning: str


@dataclass(slots=True)
class RetrievedChunk:
    text: str
    source: str
    section: str
    page: int | None
    score: float

    def citation(self) -> str:
        location = f"page {self.page}" if self.page else self.section
        return f"{self.source} — {location}"


@dataclass(slots=True)
class ChatTurn:
    role: str
    content: str
    persona: str | None = None


@dataclass(slots=True)
class AgentResult:
    persona: PersonaResult
    response: str
    sources: list[RetrievedChunk]
    escalated: bool
    escalation_reasons: list[str] = field(default_factory=list)
    handoff: dict[str, Any] | None = None

