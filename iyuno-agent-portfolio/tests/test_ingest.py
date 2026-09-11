from agent.ingest import ingest


def test_ingest_produces_chunks():
    chunks = ingest()
    assert len(chunks) > 0


def test_ingest_covers_all_20_documents():
    chunks = ingest()
    doc_ids = {c.doc_id for c in chunks}
    assert len(doc_ids) >= 20, f"expected at least 20 source documents, got {len(doc_ids)}"


def test_chunks_have_required_metadata():
    chunks = ingest()
    for c in chunks[:5]:
        assert c.title
        assert c.retrieved_date != ""
        assert c.chunk_id.count("::chunk") == 1
