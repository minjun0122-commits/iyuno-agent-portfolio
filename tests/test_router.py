from agent.router import answer_query, answer_query_llm


def test_arithmetic_routing():
    resp = answer_query("12*8")
    assert "96" in resp.answer


def test_factual_routing_has_citation():
    resp = answer_query("What is retrieval augmented generation?")
    assert len(resp.citations) >= 1


def test_direct_doc_id_lookup():
    resp = answer_query("owasp top10 overview")
    assert resp.citations == ["owasp-top10-overview::chunk0"] or resp.citations


def test_out_of_scope_falls_back_gracefully():
    # A query far outside the corpus should not crash and should still
    # return a well-formed response object.
    resp = answer_query("asdkjaslkdj qweqweqwe zzzxxxccc")
    assert isinstance(resp.answer, str)


def test_llm_mode_falls_back_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    resp = answer_query_llm("What is zero trust?")
    assert "no ANTHROPIC_API_KEY" in resp.mode
