"""Streamlit interface for the document Q&A bot."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.config import DATA_DIR, DB_DIR, GEMINI_API_KEY, GEMINI_MODEL, TOP_K
from src.ingest import SUPPORTED_EXTENSIONS, index_documents
from src.query import answer_question


def _document_count() -> int:
    return sum(
        1
        for path in DATA_DIR.iterdir()
        if path.is_file()
        and path.name.lower() != "readme.md"
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def _render_sources(chunks: list[dict[str, Any]]) -> None:
    if not chunks:
        return
    st.markdown("**Retrieved sources**")
    for number, chunk in enumerate(chunks, start=1):
        label = f"{number}. {chunk['citation']}"
        with st.expander(label):
            st.caption(f"Cosine distance: {chunk['distance']:.4f} — lower is better")
            st.write(chunk["text"])


st.set_page_config(
    page_title="Document Q&A Bot",
    page_icon="📚",
    layout="wide",
)

st.title("📚 Document Q&A Bot")
st.caption(
    "Ask questions about the indexed PDF, DOCX, and TXT files. "
    "Answers are grounded in retrieved passages and include citations."
)

with st.sidebar:
    st.header("Knowledge base")
    st.metric("Source documents", _document_count())
    st.write(f"Index: `{'ready' if DB_DIR.exists() else 'not built'}`")
    st.write(f"Answer model: `{GEMINI_MODEL}`")
    gemini_api_key = st.text_input(
        "Gemini API key",
        value=GEMINI_API_KEY,
        type="password",
        help="Used only for Gemini requests. Prefer setting GEMINI_API_KEY in .env.",
    )
    top_k = st.slider("Retrieved chunks", min_value=1, max_value=10, value=TOP_K)

    if st.button("Rebuild document index", type="primary", use_container_width=True):
        try:
            with st.spinner("Reading, chunking, and indexing documents..."):
                chunk_count = index_documents(force_rebuild=True)
            st.success(f"Indexed {chunk_count} chunks.")
        except Exception as exc:
            st.error(f"Indexing failed: {exc}")

    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption("Create a Gemini API key in Google AI Studio. Never commit it.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            _render_sources(message.get("chunks", []))

if question := st.chat_input("Ask a question about the documents"):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Retrieving evidence and generating an answer..."):
                result = answer_question(
                    question, top_k=top_k, api_key=gemini_api_key
                )
            st.markdown(result["answer"])
            _render_sources(result["chunks"])
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": result["answer"],
                    "chunks": result["chunks"],
                }
            )
        except RuntimeError as exc:
            message = f"Unable to answer: {exc}"
            st.error(message)
            st.session_state.messages.append(
                {"role": "assistant", "content": message, "chunks": []}
            )
