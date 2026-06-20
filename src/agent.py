from .classifier import PersonaClassifier
from .config import Settings
from .escalator import Escalator
from .generator import ResponseGenerator
from .models import AgentResult, ChatTurn
from .rag_pipeline import RAGPipeline


class SupportAgent:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.classifier = PersonaClassifier(self.settings.gemini_api_key, self.settings.gemini_model)
        self.rag = RAGPipeline(self.settings)
        self.generator = ResponseGenerator(self.settings.gemini_api_key, self.settings.gemini_model)
        self.escalator = Escalator(self.settings)
        self.history: list[ChatTurn] = []

    def initialize(self, rebuild: bool = False) -> int:
        return self.rag.ingest(rebuild=rebuild)

    def respond(self, message: str) -> AgentResult:
        persona = self.classifier.classify(message)
        chunks = self.rag.retrieve(message)
        reasons = self.escalator.evaluate(message, persona, chunks, self.history)
        self.history.append(ChatTurn("user", message, persona.persona))
        response = self.generator.generate(message, persona.persona, chunks, self.history)
        if reasons:
            response += "\n\nThis request has been flagged for a human support specialist."
        handoff = self.escalator.handoff(message, persona, chunks, self.history, reasons) if reasons else None
        self.history.append(ChatTurn("assistant", response))
        return AgentResult(persona, response, chunks, bool(reasons), reasons, handoff)

    def reset(self) -> None:
        self.history.clear()

