import json

import streamlit as st

from src import SupportAgent


st.set_page_config(page_title="Adsparkx Persona Support", page_icon="✨", layout="wide")
st.title("Persona-Adaptive Customer Support")
st.caption("Grounded answers, audience-aware tone, and safe human escalation")


@st.cache_resource
def load_agent() -> SupportAgent:
    agent = SupportAgent()
    agent.initialize()
    return agent


agent = load_agent()
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.subheader("System")
    st.write("LLM mode:", "Gemini" if agent.settings.gemini_api_key else "Offline demo fallback")
    st.write("Retrieval threshold:", agent.settings.retrieval_threshold)
    if st.button("Rebuild knowledge index"):
        count = agent.initialize(rebuild=True)
        st.success(f"Indexed {count} chunks")
    if st.button("Clear conversation"):
        st.session_state.messages = []
        agent.reset()
        st.rerun()

for item in st.session_state.messages:
    with st.chat_message(item["role"]):
        st.markdown(item["content"])
        if item.get("details"):
            with st.expander("Agent details"):
                st.json(item["details"])

if prompt := st.chat_input("Describe your support issue"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Searching the support knowledge base…"):
            result = agent.respond(prompt)
        st.markdown(result.response)
        cols = st.columns(3)
        cols[0].metric("Persona", result.persona.persona)
        cols[1].metric("Retrieval confidence", f"{result.sources[0].score:.2f}" if result.sources else "0.00")
        cols[2].metric("Escalation", "Yes" if result.escalated else "No")
        with st.expander("Retrieved sources"):
            for source in result.sources:
                st.write(f"**{source.citation()}** · score {source.score:.2f}")
                st.caption(source.text[:500])
        if result.handoff:
            with st.expander("Human handoff summary", expanded=True):
                st.json(result.handoff)
                st.download_button("Download handoff JSON", json.dumps(result.handoff, indent=2), "handoff.json", "application/json")
    details = {
        "persona": result.persona.persona,
        "persona_confidence": result.persona.confidence,
        "sources": [source.citation() for source in result.sources],
        "escalated": result.escalated,
        "escalation_reasons": result.escalation_reasons,
        "handoff": result.handoff,
    }
    st.session_state.messages.append({"role": "assistant", "content": result.response, "details": details})

