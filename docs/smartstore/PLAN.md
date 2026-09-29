# 네이버 스마트스토어 위탁판매(드롭쉬핑) 자동판매 계획

> 대상: 커머스API센터 애플리케이션(client_id/secret)을 이미 보유한 1인/소규모 위탁판매 셀러
> 코드: `smartstore/` 패키지 (이 문서의 4~6단계를 구현한 MVP)

## 목표

"주문 확인 → 공급사 발주 → 송장 등록 → 재고·가격 동기화 → CS 답변"까지의 반복 업무를
**사람 개입 없이 돌리되, 예외(품절·발주 실패·마진 미달)만 사람이 처리**하는 구조를 만든다.

---

## 1. 단계별 로드맵

| 단계 | 기간(예시) | 할 일 | 완료 기준 |
|---|---|---|---|
| 0. 준비 | 1주 | 사업자등록, 통신판매업 신고, 스마트스토어 개설, 커머스API센터 앱 등록(**API 호출 IP 등록** 포함) | 토큰 발급 성공 |
| 1. 공급사 선정 | 1주 | 도매꾹/도매매, 오너클랜 등 위탁 허용 도매처 2곳 이상 확보. 상세이미지 사용 허락, 대량(엑셀) 발주·송장 다운로드 지원 여부 확인 | 공급사별 발주/송장 방식 정리 |
| 2. 소싱 | 상시 | 아래 **소싱 기준** 통과 상품만 등록. 판매자상품코드(sellerManagementCode) = 공급사 SKU 로 통일 | `product_map.csv` 작성 |
| 3. 상품 등록 | 2주 | 초기 30~50개 수동/반자동 등록 → 반응 보고 확장. 상품명 키워드는 네이버 쇼핑 검색 가이드 준수 | 등록 상품 전부 SKU 매핑 |
| 4. 주문·배송 자동화 | 1주 | `sync-orders`, `sync-tracking` dry-run 1주 → `--apply` 전환 | 발주 성공률 ≥ 98% |
| 5. 재고·가격 동기화 | 1주 | `sync-inventory` 로 공급사 품절 → 즉시 재고 0, 원가 변동 → 가격 재계산 | 품절취소율 < 1% |
| 6. CS 자동화 | 1주 | `draft-cs` 로 Q&A 초안 생성 → 사람이 검토 후 `--post` | 평균 응답시간 < 12h |
| 7. 개선 루프 | 매주 | KPI 리뷰, 저마진·고CS 상품 정리, 잘 팔리는 카테고리 확장 | 주간 리포트 |

## 2. 소싱 기준 (체크리스트)

- 마진: 아래 가격 공식으로 계산한 판매가가 **경쟁 최저가 대비 +10% 이내**일 것
- 공급사 출고: 주문 후 2영업일 내 출고, 재고 수량 API/엑셀 제공
- 피해야 할 카테고리: 인증 필요 품목(전기용품 KC, 어린이제품, 식품·건기식, 화장품 책임판매업), 브랜드/상표권 이슈 상품, 부피·파손 위험 큰 상품
- 옵션이 많은 상품은 MVP 이후(현재 코드는 단일 SKU 상품만 재고 동기화)

## 3. 가격 공식

```
판매가 = (공급가 + 배송비) ÷ (1 − 수수료율 − 목표마진율)   → 100원 단위 올림
마진율 = (판매가 × (1 − 수수료율) − 공급가 − 배송비) ÷ 판매가
```

- 수수료율 기본값 5.63% = 네이버페이 주문관리 수수료(최대 3.63%) + 네이버쇼핑 매출연동 수수료(2%).
  **판매자센터에서 실제 요율 확인 후 `SMARTSTORE_FEE_RATE` 로 조정.**
- 목표마진 15%, 최소마진 5% (미달 시 재고 0 → 사실상 판매중지)
- 예: 공급가 8,000 + 배송비 3,000 → 11,000 ÷ 0.7937 = 13,859 → **13,900원**

## 4. 자동화 파이프라인

```
[cron 10분] sync-orders
  네이버: 변경주문(PAYED) 조회 ─→ 상세 조회 ─→ 공급사 재고 확인
     ├ 재고 부족 → FAILED (발주확인 안 함, 사람이 취소/대체 처리)
     └ 재고 OK  → 네이버 발주확인 → 공급사 발주 → ORDERED

[cron 30분] sync-tracking
  공급사 송장 조회 ─→ 네이버 발송처리(dispatch) → SHIPPED

[cron 1시간] sync-inventory
  공급사 재고·원가 ─→ 가격 공식 ─→ 네이버 원상품 가격/재고 수정

[cron 1일 2회] draft-cs
  미답변 Q&A ─→ Claude 초안(키 없으면 템플릿) ─→ 검토 후 --post
```

### 주문 상태 머신 (SQLite `orders` 테이블)

`NEW → CONFIRMED → ORDERED → SHIPPED`, 어느 단계든 실패 시 `FAILED`(사람 처리).
- 재실행해도 같은 주문을 두 번 발주하지 않음(멱등). 발주확인 후 공급사 발주 전에 죽으면 다음 실행에서 이어서 발주.
- 송장 등록 실패 시 `ORDERED` 유지 + 사유 기록 → 다음 실행에서 재시도.

### 공급사 연동 방식

`smartstore/suppliers/base.py` 의 `Supplier` 인터페이스(`get_item` / `place_order` / `get_tracking`)만 구현하면 된다.
- 기본 제공 `CSVSupplier`: 공급사 재고표 CSV 읽기 → 발주서 CSV 생성(공급사 대량발주 페이지에 업로드) → 공급사에서 받은 송장 CSV 읽기.
  대부분의 도매 사이트가 엑셀 대량발주를 지원하므로 API 없이도 바로 시작 가능.
- 공급사가 OpenAPI 를 제공하면(예: 도매꾹) 같은 인터페이스로 어댑터를 추가해 완전 자동화.

## 5. 리스크 & 정책

| 리스크 | 대응 |
|---|---|
| 품절 주문 | 발주확인 전에 공급사 재고 확인. FAILED 주문은 **24시간 내** 구매자 연락 후 취소(판매자 귀책 품절취소는 페널티 대상) |
| 발송 지연 페널티 | 발송기한 D-1 까지 SHIPPED 안 된 주문을 매일 확인(운영 루틴), 공급사 출고 SLA 2영업일 계약 |
| 가격 역마진 | 원가 변동 시 매시간 재계산, 최소마진 미달이면 재고 0 |
| 상품명 어뷰징/중복등록 | 같은 공급사 상품 중복 등록 금지, 키워드 반복 금지 |
| 개인정보 | 수취인 정보는 DB에 저장하지 않음. 발주서 CSV 는 업로드 후 삭제. `data/smartstore/` 는 gitignore |
| API 키 유출 | 환경변수로만 주입, 레포에 커밋 금지. 커머스API 호출 IP 제한 사용 |
| API 호출 한도 | 429/5xx 지수 백오프 재시도(최대 3회), 조회는 300건 단위 배치 |
| 잘못된 자동 실행 | 모든 쓰기 작업은 기본 dry-run, `--apply` 명시 시에만 실행. CS 답변 게시는 `--post` 추가 필요 |

## 6. KPI (주간 리뷰)

| 지표 | 목표 | 산출 |
|---|---|---|
| 일 주문수 | 성장 추세 | orders 테이블 |
| 발주 성공률 | ≥ 98% | ORDERED+SHIPPED / 전체 |
| 평균 발송 소요시간 | ≤ 2영업일 | 결제 → SHIPPED |
| 품절취소율 | < 1% | FAILED(out of stock) / 전체 |
| 평균 마진율 | ≥ 12% | 가격 공식 기준 |
| CS 응답시간 | < 12h | cs_drafts |

## 7. 실행 방법

```bash
pip install -r requirements.txt

export NAVER_COMMERCE_CLIENT_ID=...        # 커머스API센터 애플리케이션 ID
export NAVER_COMMERCE_CLIENT_SECRET=...    # 애플리케이션 시크릿($2a$04$... 형태)
export ANTHROPIC_API_KEY=...               # 선택: CS 초안에 Claude 사용

# 공급사/상품 매핑 파일 준비 (examples/smartstore/*.csv 참고)
mkdir -p data/smartstore && cp examples/smartstore/*.csv data/smartstore/

# 1) 키 없이 전체 흐름 확인
python -m smartstore.jobs all --mock

# 2) 실제 API, 조회만 (dry-run 기본)
python -m smartstore.jobs sync-orders

# 3) 결과 확인 후 쓰기 모드
python -m smartstore.jobs sync-orders --apply
```

cron 예시(서버, KST):
```
*/10 * * * *  cd /srv/store && python -m smartstore.jobs sync-orders --apply    >> logs/orders.log 2>&1
*/30 * * * *  cd /srv/store && python -m smartstore.jobs sync-tracking --apply  >> logs/tracking.log 2>&1
7 * * * *     cd /srv/store && python -m smartstore.jobs sync-inventory --apply >> logs/inventory.log 2>&1
0 9,17 * * *  cd /srv/store && python -m smartstore.jobs draft-cs --apply       >> logs/cs.log 2>&1
```
종료코드 2 = 실패 주문 존재 → 알림(메일/슬랙) 연결 권장.
GitHub Actions cron 도 가능하지만 커머스API **IP 화이트리스트** 때문에 고정 IP 서버가 더 적합하다.

## 8. 구현 전 확인 필요 사항

- 사용 엔드포인트 경로·필드명은 커머스API 문서 기준으로 작성했으나, 실제 적용 전 [커머스API 문서](https://apicenter.commerce.naver.com/)에서
  주문(`last-changed-statuses`, `query`, `confirm`, `dispatch`), 상품(`v2/products/origin-products`), 문의(`contents/qnas`) 스펙을 한 번 더 대조할 것.
- 택배사 코드(`deliveryCompanyCode`, 예: CJGLS)는 문서의 코드표 사용.
- 첫 실제 실행은 반드시 dry-run 으로 응답 형태를 확인.
