import json

from src import SupportAgent


def main() -> None:
    agent = SupportAgent()
    print(f"Indexed {agent.initialize()} support chunks. Type 'quit' to exit.")
    while True:
        message = input("\nYou: ").strip()
        if message.lower() in {"quit", "exit"}:
            break
        result = agent.respond(message)
        print(f"Persona: {result.persona.persona} ({result.persona.confidence:.2f})")
        print("Sources:", ", ".join(source.citation() for source in result.sources) or "None")
        print("Agent:", result.response)
        print("Escalated:", result.escalated)
        if result.handoff:
            print(json.dumps(result.handoff, indent=2))


if __name__ == "__main__":
    main()

