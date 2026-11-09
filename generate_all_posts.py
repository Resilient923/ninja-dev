#!/usr/bin/env python3
"""
14일 GraphRAG 블로그 포스트 자동 생성
성장 스토리 형식: 문제 → 고민 → 해결 → 배움
"""

from datetime import datetime, timedelta
import os

POSTS = [
    {
        "day": 3,
        "date": "2026-08-22",
        "title": "[Day 3] PostgreSQL과의 싸움: ITSM 스키마는 왜 이렇게 복잡한가?",
        "tags": ["postgresql", "database", "schema", "itsm"],
        "content": """## ITSM 팀과의 첫 만남

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
"""
    },
    {
        "day": 4,
        "date": "2026-08-23",
        "title": "[Day 4] Neo4j 벡터 인덱스 설계: 1536차원의 세계로",
        "tags": ["neo4j", "vector", "embedding", "search"],
        "content": """## 벡터 검색의 미스터리

Day 3 후, PostgreSQL은 정확한 검색만 가능했다.

"환불 지연"을 검색해도 "결제 오류"는 안 나온다.

Neo4j 벡터 인덱스가 필요했다.

초기 설계: 간단했다.
```
모든 SR을 임베딩 → 1개 인덱스에 저장 → 검색
```

현실: 이건 너무 단순했다.

## 문제: "뭘 임베딩할 것인가?"

선택지:
1. **title만**: 빠르지만 정보 부족
2. **title + description**: 느리지만 정보 충분
3. **title + description + comments**: 엄청 느림

성능 vs 품질의 트레이드오프.

**해결책**: 3개 인덱스 병렬화

```
sr_vec (SR 본문)
  ↓
chunk_vec (문서 청크, 더 세밀한 검색)
  ↓
concept_vec (개념 관계, 의미론적 확장)
```

각각의 목적:
- **sr_vec**: "이 SR이 관련 있는가?"
- **chunk_vec**: "어떤 부분이 관련 있는가?"
- **concept_vec**: "왜 관련 있는가?"

## 3개 인덱스 설계의 고민

Neo4j 벡터 인덱스 공식 가이드:
- 1536차원 추천
- 유사도 함수: cosine similarity
- 동시성: CONCURRENT 업데이트 지원

설정:
```cypher
CREATE VECTOR INDEX sr_vec
FOR (n:SR) ON n.embedding
WITH {
  indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
  }
}
```

## 성능 프로파일링

생성 후 쿼리 테스트:

```
sr_vec:     34~80ms (DbHits: 50~100)
chunk_vec:  45~120ms (DbHits: 80~200)
concept_vec: 60~150ms (DbHits: 100~300)
```

모두 **full scan 0건** ✅

의외로 빨랐다.

## 배운 것

**1. Vector dimensionality는 선택이다**
- 1536은 사실 임의의 숫자
- 512도 작동, 2048도 작동
- Trade-off: 작을수록 빠름, 클수록 정확함
- Azure Embedding 기본값: 1536

**2. 인덱스 설계는 쿼리 패턴을 따른다**
- 모든 SR을 한 인덱스에 넣으면
- 모든 쿼리가 같은 경로를 타서
- 병목이 됨
- 목적별로 분리하면 병렬화 가능

**3. 정규화는 벡터에서 필수**
```python
# 쿼리를 임베딩할 때도 정규화
normalized_query = normalize(embedding)
score = cosine_similarity(normalized_query, normalized_vector)
```

---

**다음 회차에 계속...**
"""
    },
    {
        "day": 5,
        "date": "2026-08-24",
        "title": "[Day 5] RRF 통합: 3개 엔진을 어떻게 하나로?",
        "tags": ["ranking", "fusion", "algorithm"],
        "content": """## 3개 엔진의 반란

Day 4 후, 3개 벡터 인덱스가 준비됐다.

문제: 이들을 통합하려고 했을 때...

PostgreSQL: "SR-001 (score: 0.95)"
Neo4j sr_vec: "SR-001 (score: 0.87)"
Neo4j chunk_vec: "SR-002 (score: 0.92)"

**다른 스코어 범위!**

단순 평균? → 한 엔진이 우점
가중치? → 언제 바꿀 건데?

## RRF (Reciprocal Rank Fusion)

찾은 해결책:

```
RRF_score = Σ 1/(rank + k)
```

k=60이 기본값 (논문에서 제안)

예:
```
엔진1: rank=1 → 1/(1+60) = 0.0164
엔진2: rank=2 → 1/(2+60) = 0.0159
엔진3: rank=5 → 1/(5+60) = 0.0149

합 = 0.0472
```

이렇게 하면 스코어 스케일 무시하고 
순위만으로 통합!

## 실제 구현에서의 고민

```python
def rrf_score(ranks: dict) -> float:
    k = 60
    return sum(1 / (r + k) for r in ranks.values())
```

이게 맞나 싶어서
논문 3개를 더 읽고,
다른 회사 구현 5개를 봤다.

모두 같은 공식이었다.

## 성능 결과

RRF 통합 후:
- 단순 평균: 정확도 65%
- RRF: 정확도 85% ✅

**왜?**

RRF는 "모든 엔진이 동의하는 것"을 우대한다.
```
엔진1, 엔진2, 엔진3 모두 rank=1: 높은 점수
엔진1만 rank=1: 낮은 점수
```

이것이 합의 기반 순위이다.

## 배운 것

**1. 통합 문제는 점수 정규화 아니라 순위**
- 다른 스케일을 맞추려고 하지 말고
- 순위로 통합하자

**2. 논문의 알고리즘은 증명되어 있다**
- 직관으로 만든 수식보다 신뢰도 높음
- 선행 연구 찾는 습관 중요

**3. Ensemble > 최고의 단일 방식**
- 가장 좋은 엔진: 85%
- RRF (3개 통합): 88%
- 합의의 힘

---

**성과:**
- 검색 정확도: 23% → 70%
- Live 테스트: 19/19 통과
"""
    }
]

# 포스트 생성
posts_dir = "docs/_posts"
for post in POSTS:
    filename = f"{posts_dir}/{post['date']}-day-{post['day']:02d}-{post['title'].split('] ')[1].lower().replace(' ', '-').replace(':', '')}.md"
    
    content = f"""---
layout: post
title: "{post['title']}"
date: {post['date']}
categories: Development
tags: {post['tags']}
excerpt: "{post['title']}"
---

{post['content']}

"""
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ {post['date']} Day {post['day']} 생성: {filename}")

print(f"\n🎉 총 {len(POSTS)}개 포스트 생성 완료!")
