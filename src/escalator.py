import re
from collections import Counter
from datetime import datetime, timezone

from .config import Settings
from .models import ChatTurn, PersonaResult, RetrievedChunk


class Escalator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate(self, message: str, persona: PersonaResult, chunks: list[RetrievedChunk], history: list[ChatTurn]) -> list[str]:
        reasons = []
        lowered = message.lower()
        if any(term in lowered for term in self.settings.sensitive_terms):
            reasons.append("Sensitive billing, legal, or account request")
        if not chunks:
            reasons.append("No relevant knowledge-base content found")
        elif chunks[0].score < self.settings.retrieval_threshold:
            reasons.append(f"Low retrieval confidence ({chunks[0].score:.2f})")
        frustrated_turns = sum(
            turn.role == "user" and bool(re.search(r"urgent|again|still|nothing works|ridiculous|fed up|!", turn.content.lower()))
            for turn in history[-6:]
        )
        if persona.persona == "Frustrated User" and frustrated_turns >= self.settings.frustration_turn_limit:
            reasons.append("Repeated unresolved frustration")
        return reasons

    @staticmethod
    def handoff(message: str, persona: PersonaResult, chunks: list[RetrievedChunk], history: list[ChatTurn], reasons: list[str]) -> dict:
        user_messages = [turn.content for turn in history if turn.role == "user"]
        attempted = []
        for turn in user_messages:
            attempted.extend(re.findall(r"(?:tried|attempted|already)\s+([^.!?]+)", turn, flags=re.I))
        sources = list(dict.fromkeys(chunk.citation() for chunk in chunks))
        return {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "persona": persona.persona,
            "issue": message,
            "conversation_history": [{"role": turn.role, "content": turn.content} for turn in history[-8:]],
            "retrieved_documents": sources,
            "retrieval_confidence": round(chunks[0].score, 3) if chunks else 0.0,
            "actions_already_attempted": attempted or ["No explicit attempted steps detected"],
            "escalation_reasons": reasons,
            "recommended_next_steps": "Human agent should verify identity if needed, review account-level evidence, and contact the customer with a documented resolution plan.",
        }

