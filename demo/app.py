"""Streamlit demo for iyuno-agent-portfolio.

Run with:  streamlit run demo/app.py
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import streamlit as st

from agent.router import answer_query, answer_query_llm
from agent.tools import CALL_LOG

st.set_page_config(page_title="iyuno-agent-portfolio", page_icon="🔎")
st.title("🔎 iyuno-agent-portfolio")
st.caption(
    "공개 기술·보안 문서 20개를 검색해 출처와 함께 답하는 RAG + tool calling 에이전트. "
    "Iyuno AI Agent Engineer 채용 공고 과제로 만들었습니다."
)

with st.sidebar:
    st.header("실행 모드")
    use_llm = st.toggle("Claude API 사용 (ANTHROPIC_API_KEY 필요)", value=False)
    st.markdown("---")
    st.markdown(
        "**예시 질문** (문서가 영어라 질문도 영어로 해주세요)\n"
        "- What is prompt injection?\n"
        "- 17*24\n"
        "- What is zero trust architecture?\n"
        "- Can you book me a flight?"
    )

query = st.text_input("질문", placeholder="예: What is the OWASP Top 10?")

if st.button("질문하기") and query.strip():
    with st.spinner("답변 생성 중..."):
        resp = answer_query_llm(query) if use_llm else answer_query(query)

    st.markdown("### 답변")
    st.write(resp.answer)

    if resp.citations:
        st.markdown("**출처:** " + ", ".join(f"`{c}`" for c in resp.citations))

    col1, col2, col3 = st.columns(3)
    col1.metric("응답 시간 (ms)", f"{resp.latency_ms:.1f}")
    col2.metric("모드", resp.mode)
    col3.metric("도구 호출 수", len(resp.tool_calls))

    with st.expander("도구 호출 기록"):
        st.json(resp.tool_calls)

st.markdown("---")
with st.expander("최근 도구 호출 로그 (이번 세션)"):
    st.json(CALL_LOG[-20:])
