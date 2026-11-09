---
layout: post
title: "[Day 3] PostgreSQL과의 싸움: ITSM 스키마는 왜 이렇게 복잡한가?"
date: 2026-08-22
categories: Development
tags: ['postgresql', 'database', 'schema', 'itsm']
excerpt: "[Day 3] PostgreSQL과의 싸움: ITSM 스키마는 왜 이렇게 복잡한가?"
---

## ITSM 팀과의 첫 만남

PostgreSQL에 접근하는 날, ITSM 팀에게 받은 문서:
- 70개 테이블
- 250+ 컬럼
- 정규화 수준: NF2 (정규형 2차)

생각: "뭐 이렇게 복잡해? 그냥 simple query로 가져오면 되지"

초기 쿼리:
```sql
SELECT * FROM sr_table 
WHERE sr_id = ?
```

현실: 컬럼 수가 너무 많고, NULL 값이 너무 많고, 
뭔가 조인되어야 할 데이터들이 흩어져 있음.

## 문제 1: "SR_ID를 어떻게 찾지?"

"SR-001을 조회해줄래"라는 요청이 들어왔다.

시도:
```sql
SELECT * FROM sr WHERE sr_id = 'SR-001';
```

결과: 0 rows

"뭐? 데이터가 없다고?"

실제 컬럼명: sr.request_id (sr_id가 아님)
실제 스키마: sr_flat 뷰를 통해서만 접근 가능

**해결**: ITSM 팀과 schema mapping 문서 작성
```python
# adapters/itsm_schema_preflight.py
MAPPING = {
    "sr_id": "sr_flat.request_id",
    "title": "sr_flat.short_description",
    "status": "sr_flat.state",
}
```

## 문제 2: "이건 정말 같은 데이터인가?"

두 번째 문제: 같은 SR인데 여러 곳에 있음

```
sr_table (원본)
sr_flat (뷰)
sr_history (변경 이력)
sr_attachment (첨부)
```

어느 것을 쿼리해야 정확한가?

삽질 끝에 깨달음:
- **sr_flat**: 현재 상태 (정규화된 최신 데이터)
- **sr_history**: 감사용 (모든 변경 기록)
- **sr_table**: 원본 (최적화 전)

**결론**: sr_flat 뷰만 사용 (성능 + 정확성)

## 문제 3: "왜 이 데이터가 NULL인가?"

25개 필드 중 평균 5개만 채워져 있음.

분석 결과:
- 필수 필드: request_id, short_description, state
- 선택 필드: 대부분 NULL (나중에 채워짐)
- 데이터 품질 편차: 부서별로 다름

**대응**: Defensive programming
```python
def get_sr(sr_id: str) -> dict:
    sr = db.query(f"SELECT * FROM sr_flat WHERE request_id = '{sr_id}'")
    if not sr:
        return None
    
    # NULL 처리
    return {
        "id": sr["request_id"],
        "title": sr["short_description"] or "(제목 없음)",
        "status": sr["state"] or "UNKNOWN",
        "description": sr["description"] or "",
    }
```

## Live 테스트: 1/1 통과 ✅

첫 실제 조회:
```
Query: SR-2607000101
Response: 200 OK
```

데이터가 정확했다!

## 배운 것

**1. Schema는 문서가 아니라 생물**
- 정규화 규칙은 이상적
- 실제 데이터는 현실적
- 갭을 채우는 것이 engineering

**2. ITSM 도메인을 이해하는 것이 절반**
- "왜 이 필드가 NULL일까?"는
- 데이터 품질 문제가 아니라
- 비즈니스 프로세스의 반영

**3. Mapping 계층이 얼마나 중요한가**
- sr.request_id vs sr_id
- 이 한 줄의 차이가
- 삽질을 3일 줄임

---

**깨달음:**
> 데이터베이스는 자료의 집합이 아니라
> 비즈니스 프로세스의 기록이다.


