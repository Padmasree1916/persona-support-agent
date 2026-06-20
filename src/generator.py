from .models import ChatTurn, RetrievedChunk


PERSONA_INSTRUCTIONS = {
    "Technical Expert": "Give a technical root-cause explanation and precise numbered troubleshooting steps. Preserve exact settings and endpoints from context.",
    "Frustrated User": "Acknowledge the inconvenience briefly. Use simple, reassuring, action-oriented steps and avoid jargon.",
    "Business Executive": "Be concise and outcome-focused. State operational impact, policy timelines found in context, and the next action with minimal jargon.",
}


class ResponseGenerator:
    def __init__(self, api_key: str = "", model: str = "gemini-2.5-flash") -> None:
        self.api_key = api_key
        self.model = model

    def generate(self, query: str, persona: str, chunks: list[RetrievedChunk], history: list[ChatTurn]) -> str:
        if not chunks:
            return "I couldn’t find a grounded answer in the support knowledge base, so I’m escalating this to a human specialist."
        if self.api_key:
            try:
                return self._with_gemini(query, persona, chunks, history)
            except Exception:
                pass
        return self._grounded_fallback(persona, chunks)

    def _with_gemini(self, query: str, persona: str, chunks: list[RetrievedChunk], history: list[ChatTurn]) -> str:
        from google import genai
        from google.genai import types

        context = "\n\n".join(f"[{chunk.citation()}]\n{chunk.text}" for chunk in chunks)
        recent = "\n".join(f"{turn.role}: {turn.content}" for turn in history[-6:])
        instruction = f"""You are a customer support agent.
Style: {PERSONA_INSTRUCTIONS[persona]}
Use only facts in KNOWLEDGE BASE. If a fact is absent, say so; never invent a timeline, setting, or policy.
Add compact inline source references using the supplied source labels.

KNOWLEDGE BASE:
{context}

RECENT CONVERSATION:
{recent}"""
        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.model,
            contents=query,
            config=types.GenerateContentConfig(system_instruction=instruction, temperature=0.2),
        )
        return response.text

    @staticmethod
    def _grounded_fallback(persona: str, chunks: list[RetrievedChunk]) -> str:
        facts = []
        for chunk in chunks[:2]:
            sentences = [part.strip() for part in chunk.text.replace("\n", " ").split(".") if len(part.strip()) > 25]
            facts.extend(sentences[:2])
        body = "\n".join(f"- {fact}." for fact in facts[:4])
        citation = "; ".join(dict.fromkeys(chunk.citation() for chunk in chunks[:2]))
        if persona == "Frustrated User":
            lead = "I understand this has been frustrating. Here are the clearest steps from our support guide:"
        elif persona == "Technical Expert":
            lead = "Based on the retrieved support documentation, use this diagnostic path:"
        else:
            lead = "Here’s the documented impact and recommended next action:"
        return f"{lead}\n\n{body}\n\nSources: {citation}"

