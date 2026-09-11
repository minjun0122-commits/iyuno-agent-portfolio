"""Streamlit demo for agentic-knowledge-triage.

Run with:  streamlit run demo/app.py
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import streamlit as st

from agent.router import answer_query, answer_query_llm
from agent.tools import CALL_LOG

st.set_page_config(page_title="agentic-knowledge-triage", page_icon="🔎")
st.title("🔎 agentic-knowledge-triage")
st.caption(
    "RAG + tool calling agent over a 20-document public tech/security corpus. "
    "Built for the Iyuno AI Agent Engineer job-posting coursework assignment."
)

with st.sidebar:
    st.header("Mode")
    use_llm = st.toggle("Use Claude API (needs ANTHROPIC_API_KEY)", value=False)
    st.markdown("---")
    st.markdown(
        "**Try:**\n"
        "- What is prompt injection?\n"
        "- 17*24\n"
        "- What is zero trust architecture?\n"
        "- Can you book me a flight?"
    )

query = st.text_input("Ask a question", placeholder="e.g. What is the OWASP Top 10?")

if st.button("Ask") and query.strip():
    with st.spinner("Thinking..."):
        resp = answer_query_llm(query) if use_llm else answer_query(query)

    st.markdown("### Answer")
    st.write(resp.answer)

    if resp.citations:
        st.markdown("**Sources:** " + ", ".join(f"`{c}`" for c in resp.citations))

    col1, col2, col3 = st.columns(3)
    col1.metric("Latency (ms)", f"{resp.latency_ms:.1f}")
    col2.metric("Mode", resp.mode)
    col3.metric("Tool calls", len(resp.tool_calls))

    with st.expander("Tool call trace"):
        st.json(resp.tool_calls)

st.markdown("---")
with st.expander("Recent tool call log (session)"):
    st.json(CALL_LOG[-20:])
