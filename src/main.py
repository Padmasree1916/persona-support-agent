"""Command-line interface for indexing and querying documents."""

from __future__ import annotations

import argparse

from .config import TOP_K
from .ingest import index_documents
from .query import answer_question


def _show_result(question: str, top_k: int) -> None:
    result = answer_question(question, top_k)
    print(f"\nAnswer:\n{result['answer']}")
    print("\nRetrieved source chunks:")
    for number, chunk in enumerate(result["chunks"], start=1):
        preview = chunk["text"].replace("\n", " ")[:300]
        print(f"\n{number}. {chunk['citation']} (distance: {chunk['distance']:.4f})")
        print(preview + ("..." if len(chunk["text"]) > 300 else ""))


def interactive(top_k: int = TOP_K) -> None:
    print("Document Q&A Bot — enter a question, or type 'quit' to exit.")
    while True:
        question = input("\nQuestion: ").strip()
        if question.lower() in {"quit", "exit"}:
            break
        if question:
            try:
                _show_result(question, top_k)
            except RuntimeError as exc:
                print(f"Error: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Grounded document Q&A bot")
    subparsers = parser.add_subparsers(dest="command")
    index_parser = subparsers.add_parser("index", help="build the persistent index")
    index_parser.add_argument("--rebuild", action="store_true")
    ask_parser = subparsers.add_parser("ask", help="ask one question")
    ask_parser.add_argument("question")
    ask_parser.add_argument("--top-k", type=int, default=TOP_K)
    chat_parser = subparsers.add_parser("chat", help="start the interactive loop")
    chat_parser.add_argument("--top-k", type=int, default=TOP_K)
    args = parser.parse_args()

    if args.command == "index":
        index_documents(force_rebuild=args.rebuild)
    elif args.command == "ask":
        _show_result(args.question, args.top_k)
    else:
        interactive(getattr(args, "top_k", TOP_K))


if __name__ == "__main__":
    main()
