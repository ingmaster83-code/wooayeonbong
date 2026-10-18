# 우아연봉 생성 스크립트

데이터(국민연금공단 가입 사업장 내역 15083277) → 회사별 집계 → 정적 사이트.

1. `python scripts/fetch_nps.py --from YYYYMM` — 월별 CSV 다운로드(`data/raw/`, gitignore). 파일명 YYYYMM 의 자료는 전월 기준. 12개월치가 있어야 입사·퇴사율이 계산된다.
2. `python scripts/build_data.py 20` — `_data/companies.json.gz` 생성(법인, 가입자 20명 이상, 커밋 대상).
3. `python scripts/build_site.py 30` — `_site/` 생성(가입자 30명 이상 회사 페이지). 배포는 GitHub Actions(`deploy.yml`)가 `_data` 만으로 빌드한다.

- `salary.py` 실수령액 계산(2026 요율), `assets/js/calc.js` 가 같은 식(`test_calc.js`+`test_calc.py` 로 대조).
- 월 갱신(매월 26일 전후 새 파일): 1→2 실행 후 커밋·푸시. 요율·상한이 바뀌면 `salary.py`·`calc.js`·`build_site.py` 의 상수 수정(국민연금 요율은 매년 0.5%p↑, 기준소득월액 상한은 매년 7월).
- 점검: `check_site.py`(링크·중복·JSON-LD), `peek.py <경로>`(본문 텍스트 확인).
