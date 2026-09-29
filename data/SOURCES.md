# 문서 출처와 라이선스

`data/raw/`의 문서 20개는 이 과제를 위해 **직접 작성한 설명 문서**입니다(저장소 작성자가
Claude의 초안 도움을 받아 작성). 특정 출판물을 그대로 옮긴 것이 아니며, 각 문서는 널리
알려지고 공개된 기술·보안 주제나 표준을 요약합니다. 그래서 검색과 출처 표시를 의미 있게
확인할 수 있습니다. 모든 파일의 앞부분(frontmatter)에 요약한 주제와 작성·수집 날짜가
기록되어 있습니다.

| doc_id | 요약한 주제 | 참고한 공개 표준 / 기관 |
|---|---|---|
| owasp-top10-overview | 웹 애플리케이션 보안 위험 | OWASP Top 10 |
| owasp-llm-top10 | LLM 애플리케이션 보안 위험 | OWASP Top 10 for LLM Applications |
| nist-csf-summary | 사이버보안 위험 관리 | NIST Cybersecurity Framework 2.0 |
| zero-trust-architecture | 제로 트러스트 네트워크 | NIST SP 800-207 |
| api-rate-limiting | 요청 속도 제한 알고리즘 | 업계 표준 방식 (token/leaky bucket, sliding window) |
| retrieval-augmented-generation | RAG 시스템 설계 | 일반 ML/정보검색 문헌 |
| tool-calling-agents | LLM 도구 호출 | 일반 LLM 에이전트 문헌 |
| agent-evaluation-metrics | 에이전트 평가 | 일반 ML/정보검색 평가 문헌 |
| prompt-injection-defense | 프롬프트 인젝션 대응 | OWASP LLM Top 10, 일반 보안 문헌 |
| vector-databases-overview | 근사 최근접 이웃 검색 / 벡터 DB | HNSW, IVF, PQ (일반 정보검색 문헌) |
| cwe-common-weaknesses | 소프트웨어 약점 분류 | MITRE CWE |
| secure-coding-input-validation | 입력 검증과 인젝션 방어 | OWASP 시큐어 코딩 가이드 |
| incident-response-lifecycle | 사고 대응 절차 | NIST SP 800-61 방식의 대응 단계 |
| api-authentication-patterns | 인증·인가 방식 | OAuth 2.0 / OpenID Connect / JWT 명세 |
| data-licensing-basics | 데이터·말뭉치 라이선스 | Creative Commons, GPL/카피레프트 일반 관행 |
| latency-cost-tradeoffs | LLM 서빙의 속도·비용 균형 | 일반 MLOps 문헌 |
| logging-and-observability | 관측 가능성 | 일반 SRE/관측 가능성 문헌 |
| ci-cd-testing-pyramid | 테스트 전략 | 고전적인 "테스트 피라미드" (Mike Cohn) |
| hallucination-and-grounding | 생성 모델의 근거 기반 답변 | 일반 LLM/NLP 문헌 |
| least-privilege-agent-permissions | 에이전트의 최소 권한 | 고전적인 최소 권한 접근 제어 원칙 |

**원문을 그대로 수집하지 않은 이유:** 외부 사이트의 저작권 있는 글을 그대로 옮기지 않기
위해, 각 주제를 작성자의 말로 다시 설명했습니다. 덕분에 라이선스 문제 없이 공개 저장소에
올릴 수 있습니다. `scripts/generate_corpus.py`가 `data/raw/*.md`를 항상 같은 내용으로
다시 만들며, 이 결정을 코드 안에도 기록해 두었습니다.

작성·수집일: 2026-09-08 (Asia/Seoul)
