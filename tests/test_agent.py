from src.classifier import PersonaClassifier
from src.config import Settings
from src.escalator import Escalator
from src.models import ChatTurn, PersonaResult, RetrievedChunk
from src.rag_pipeline import RAGPipeline


def test_personas_are_detected():
    classifier = PersonaClassifier()
    assert classifier.classify("Show the API header and 401 logs").persona == "Technical Expert"
    assert classifier.classify("Nothing works again! This is urgent!").persona == "Frustrated User"
    assert classifier.classify("What is the business impact and recovery timeline?").persona == "Business Executive"


def test_sensitive_billing_escalates():
    settings = Settings()
    chunks = [RetrievedChunk("Billing information", "billing.txt", "Billing", None, 0.8)]
    reasons = Escalator(settings).evaluate(
        "I demand a refund for a duplicate charge", PersonaResult("Frustrated User", .9, "test"), chunks, []
    )
    assert any("Sensitive" in reason for reason in reasons)


def test_local_retrieval_finds_api_article():
    settings = Settings()
    rag = RAGPipeline.__new__(RAGPipeline)
    rag.settings = settings
    from src.rag_pipeline import LocalEmbeddingFunction
    rag.embedding = LocalEmbeddingFunction()
    rag.collection = None
    rag._fallback = []
    rag.ingest()
    result = rag.retrieve("API bearer authorization token", 1)
    assert result and result[0].source == "api_authentication.md"
