import json
import re

from .models import PERSONAS, PersonaResult


class PersonaClassifier:
    def __init__(self, api_key: str = "", model: str = "gemini-2.5-flash") -> None:
        self.api_key = api_key
        self.model = model

    def classify(self, message: str) -> PersonaResult:
        if self.api_key:
            try:
                return self._classify_with_gemini(message)
            except Exception:
                pass
        return self._classify_with_rules(message)

    def _classify_with_gemini(self, message: str) -> PersonaResult:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)
        schema = {
            "type": "OBJECT",
            "properties": {
                "persona": {"type": "STRING", "enum": list(PERSONAS)},
                "confidence": {"type": "NUMBER"},
                "reasoning": {"type": "STRING"},
            },
            "required": ["persona", "confidence", "reasoning"],
        }
        response = client.models.generate_content(
            model=self.model,
            contents=message,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "Classify this customer support message as exactly Technical Expert, "
                    "Frustrated User, or Business Executive. Technical experts use APIs, logs, "
                    "code, and configuration language. Frustrated users show urgency or emotion. "
                    "Executives focus on impact, risk, operations, and timelines. Return JSON only."
                ),
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.0,
            ),
        )
        parsed = json.loads(response.text)
        return PersonaResult(parsed["persona"], float(parsed["confidence"]), parsed["reasoning"])

    @staticmethod
    def _classify_with_rules(message: str) -> PersonaResult:
        text = message.lower()
        technical = ("api", "http", "401", "403", "500", "token", "oauth", "webhook", "logs", "sdk", "database", "config", "header", "json", "latency")
        frustrated = ("urgent", "nothing works", "again", "ridiculous", "angry", "immediately", "fed up", "hours", "terrible", "demand")
        executive = ("business impact", "operations", "revenue", "sla", "timeline", "risk", "roi", "customers affected", "downtime", "executive")
        scores = {
            "Technical Expert": sum(term in text for term in technical),
            "Frustrated User": sum(term in text for term in frustrated) + min(message.count("!"), 2),
            "Business Executive": sum(term in text for term in executive),
        }
        persona = max(scores, key=scores.get)
        if not scores[persona]:
            persona = "Frustrated User" if re.search(r"\b(help|problem|issue|can't|cannot)\b", text) else "Business Executive"
        confidence = min(0.95, 0.58 + 0.09 * scores.get(persona, 1))
        return PersonaResult(persona, confidence, "Local vocabulary and tone classifier (Gemini is used when configured).")

