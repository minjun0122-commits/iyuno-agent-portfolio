# Corpus sources & licensing

The 20 documents in `data/raw/` are **original explanatory write-ups authored
for this coursework project** (by the repository author, with drafting help
from Claude), not verbatim copies of any single publication. Each summarizes
a well-known, publicly documented technical or security topic/standard so
retrieval and citation are meaningful and checkable. Frontmatter in every
file records the topic it summarizes and the date it was written/retrieved.

| doc_id | Topic summarized | Public standard / body it refers to |
|---|---|---|
| owasp-top10-overview | Web app security risks | OWASP Top 10 |
| owasp-llm-top10 | LLM application security risks | OWASP Top 10 for LLM Applications |
| nist-csf-summary | Cybersecurity risk management | NIST Cybersecurity Framework 2.0 |
| zero-trust-architecture | Zero trust networking | NIST SP 800-207 |
| api-rate-limiting | Rate limiting algorithms | Industry-standard patterns (token/leaky bucket, sliding window) |
| retrieval-augmented-generation | RAG system design | General ML/IR literature |
| tool-calling-agents | LLM tool/function calling | General LLM agent literature |
| agent-evaluation-metrics | Agent evaluation | General ML/IR evaluation literature |
| prompt-injection-defense | Prompt injection mitigation | OWASP LLM Top 10, general security literature |
| vector-databases-overview | ANN search / vector DBs | HNSW, IVF, PQ (general IR literature) |
| cwe-common-weaknesses | Software weakness taxonomy | MITRE CWE |
| secure-coding-input-validation | Input validation & injection defense | OWASP secure coding practices |
| incident-response-lifecycle | IR process | NIST SP 800-61 style lifecycle |
| api-authentication-patterns | AuthN/AuthZ patterns | OAuth 2.0 / OpenID Connect / JWT specs |
| data-licensing-basics | Data/corpus licensing | Creative Commons, GPL/copyleft general practice |
| latency-cost-tradeoffs | LLM serving trade-offs | General MLOps literature |
| logging-and-observability | Observability | General SRE/observability literature |
| ci-cd-testing-pyramid | Testing strategy | Classic "testing pyramid" (Mike Cohn) |
| hallucination-and-grounding | Generative model grounding | General LLM/NLP literature |
| least-privilege-agent-permissions | Least privilege for agents | Classic least-privilege access control principle |

**Why not scrape the primary sources verbatim?** Reproducing copyrighted
prose from external sites is avoided; instead each topic is explained in the
author's own words so the corpus can be published in this public repository
without licensing ambiguity. `scripts/generate_corpus.py` regenerates
`data/raw/*.md` deterministically and documents this decision inline.

Generated/retrieved: 2026-09-08 (Asia/Seoul).
