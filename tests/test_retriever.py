from agent.retriever import get_retriever


def test_retriever_returns_k_results():
    r = get_retriever()
    results = r.search("prompt injection defense", k=4)
    assert len(results) == 4


def test_retriever_top_result_is_relevant():
    r = get_retriever()
    results = r.search("What is the OWASP Top 10?", k=3)
    doc_ids = [res.doc_id for res in results]
    assert "owasp-top10-overview" in doc_ids


def test_retriever_scores_are_sorted_descending():
    r = get_retriever()
    results = r.search("zero trust architecture policy enforcement point", k=5)
    scores = [res.score for res in results]
    assert scores == sorted(scores, reverse=True)
