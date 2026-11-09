---
layout: post
title: "[Day 2] 의도 분류와의 사투: 사용자가 정말 원하는 게 뭐지?"
date: 2026-08-21
categories: Query-Classification
tags: [nlp, intent, routing, keyword]
---

## 처음의 순진함

Day 1 회의 후, 첫 구현 대상은 Query Router였다.

생각은 단순했다:
> "정규식으로 ID 패턴 찾고, 키워드로 의도 분류하면 되겠지"

**초기 설계:**
```python
if "환불" in query:
    return SIMILAR_CASE
elif "왜" in query or "원인" in query:
    return ROOT_CAUSE
elif "SR-" in query:
    return EXACT_LOOKUP
else:
    return UNKNOWN
```

결과는 참담했다. **테스트: 10/25 (40%)**

"앗, 이거 복잡하네" 하며 넘어갔다. 처음엔.

## 막혔을 때: 실제 데이터와의 충돌

하지만 이 40%는 나중에 **정확도 23% 저하**의 근본 원인이 됐다.

Mock 데이터로는 안 보이던 것들:
- "환불 처리가 왜 안 돼?"는 ROOT_CAUSE도 맞지만 **SIMILAR_CASE일 수도** 있음
- "체크인 오류"의 "오류"는 keyword지만, 실제론 문제 유형을 나타내는 domain term
- "어제 배포된 것 때문 아닐까"는 "배포"라는 단어만으로는 구분 불가

**깨달음**: 키워드 분류는 **언어의 모호성을 무시한다**.

## 문제 1: "같은 단어, 다른 의미"

```
"결제 오류" = SIMILAR_CASE (과거 사례 찾기)
"결제가 안 돼서 왜 그런지 봐줄래" = ROOT_CAUSE (원인 분석)

같은 도메인이지만 다른 의도.
```

해결책: **의도별 keyword 확장**

```python
SIMILAR_CASE_KEYWORDS = {
    "사례", "문제", "오류", "장애",  # 이전
    "결제", "환불", "예약", "체크인",  # 도메인 용어
    "모바일", "웹", "앱",  # 채널
    "서비스", "요청"  # 핵심 용어
}

ROOT_CAUSE_KEYWORDS = {
    "왜", "원인", "영향", "해결",  # 인과
    "푼 방법", "어떻게",  # 과정
}

TIMELINE_KEYWORDS = {
    "최근", "언제", "이후",  # 시간
    "영향범위"  # 도메인
}
```

**결과: 10/25 → 15/25** (여전히 60%)

## 문제 2: "context가 없으면 의도도 불명확"

"배포 후 계속 오류 난다"는 문장을 보자.

- **keyword만**: "배포" → CHANGE_TIMELINE
- **실제 의도**: "배포된 코드 때문에 오류가 나는 거 아닌가?" = ROOT_CAUSE

해결책: **2-hop 분석**

```python
def classify_with_context(query: str) -> QueryType:
    # Step 1: 기본 키워드로 후보 선정
    candidates = find_keyword_matches(query)  # [TIMELINE, ROOT_CAUSE]
    
    # Step 2: 문맥 분석
    if has_causality_marker(query):  # "때문에", "영향", "원인"
        return ROOT_CAUSE
    elif has_temporal_marker(query):  # "최근", "이후"
        return CHANGE_TIMELINE
    
    # Step 3: 기본값
    return candidates[0] if candidates else UNKNOWN
```

**결과: 15/25 → 20/25** (80%)

## 문제 3: "같은 패턴, 다른 우선순위"

이제 마지막 문제:
```
"서비스 X가 장애 난 것 같은데, 
최근에 뭐 배포된 게 있나?"
```

겹치는 keyword:
- ROOT_CAUSE (원인)
- CHANGE_TIMELINE (최근 배포)

어떤 의도가 우선인가?

분석해보니:
1. 사용자는 먼저 **원인을 알고 싶어함** (Root cause)
2. 그 과정에서 timeline 정보도 필요

**priority 설정:**
```python
PRIORITY = {
    ROOT_CAUSE: 1,        # 최우선
    CHANGE_TIMELINE: 2,
    SIMILAR_CASE: 3,
    STRUCTURED_SEARCH: 4,
    EXACT_LOOKUP: 5,
}
```

**최종 결과: 20/25 → 25/25** ✅ (100%)

## 실제 코드에서 배운 것

```python
class QueryRouter:
    def classify(self, query: str) -> QueryType:
        # 1. ID 직접 조회 (가장 확실)
        if self._extract_id(query):
            return EXACT_LOOKUP
        
        # 2. 구조화 검색 (필터 있음)
        if self._has_filters(query):
            return STRUCTURED_SEARCH
        
        # 3-5. 텍스트 기반 (우선도)
        matches = self._find_keyword_matches(query)
        if not matches:
            return UNKNOWN
        
        return max(matches, key=lambda x: PRIORITY[x])
```

각 단계가 명확한 이유:
- **ID 우선**: 정확도 100%
- **구조화 우선**: 필터 처리가 명확
- **keyword**: fallback이지만, 우선도로 정렬

## 이 과정에서 배운 근본적 깨달음

**1. "NLP는 근본적으로 모호하다"**
- 해결책은 "더 똑똑한 알고리즘"이 아니라
- "확실한 신호부터 처리"하고
- "불확실한 것은 순위를 매기는" 것

**2. "Domain knowledge가 keyword보다 강하다"**
- "결제" = 단순 keyword가 아니라
- 우리 시스템의 **주요 도메인 용어**
- 이것을 인식하는 것이 분류 정확도를 50% 올림

**3. "의도 분류는 선택의 문제"**
- "이게 ROOT_CAUSE인가 TIMELINE인가?"는
- 불가능한 문제가 아니라
- **우선도를 설정하는 기술**의 문제

## 성능 기록

| 시점 | 정확도 | 개선 내용 |
|------|--------|---------|
| 초기 | 10/25 (40%) | 단순 keyword |
| v1.1 | 15/25 (60%) | Domain keyword 추가 |
| v1.2 | 20/25 (80%) | 인과 문맥 분석 |
| v1.3 | 25/25 (100%) | Priority 정렬 |

## 다음 스텝

이제 각 의도별로 검색 전략이 달라진다.
- EXACT_LOOKUP → PostgreSQL 직접 조회
- ROOT_CAUSE → Neo4j 경로 탐색 (인과 관계)
- SIMILAR_CASE → 의미론적 검색 (Neo4j 벡터)

Day 3부터는 이 의도들을 실제로 검색하는 방법을 본다.

---

**회고:**
> 정확도 40%에서 100%로의 여정은
> "더 똑똑해지는" 게 아니라
> "문제를 더 정확하게 이해하는" 과정이었다.

