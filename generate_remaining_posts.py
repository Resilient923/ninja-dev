#!/usr/bin/env python3
"""나머지 Day 6-14 포스트 생성"""

POSTS_2 = [
    {
        "day": 6,
        "date": "2026-08-25",
        "title": "[Day 6] 그래프 경로 탐색 1부: 장애 원인을 어떻게 추적하나?",
        "snippet": "Root Cause 경로의 7개 Cypher 템플릿 설계 과정. Neo4j APOC, 경로 깊이 제한, timeout 관리의 실전 경험.",
    },
    {
        "day": 7,
        "date": "2026-08-26",
        "title": "[Day 7] 그래프 경로 탐색 2부: 유사 사례와 변경 이력",
        "snippet": "Similar Case와 Change Timeline 경로. 시간 순서 정렬, 중복 제거, 권한 필터의 함정들.",
    },
    {
        "day": 8,
        "date": "2026-08-27",
        "title": "[Day 8] Context 렌더링: 그래프를 LLM이 이해할 형태로",
        "snippet": "그래프 노드/관계를 텍스트로 변환. 개인정보 마스킹, URL 제거, truncation의 예술.",
    },
    {
        "day": 9,
        "date": "2026-08-28",
        "title": "[Day 9] LangGraph 워크플로우: 8단계 검증 파이프라인",
        "snippet": "라우팅 → 검색 → 경로 → 컨텍스트 → 생성 → 검증 → 렌더링. 각 단계의 failure mode와 재시도 전략.",
    },
    {
        "day": 10,
        "date": "2026-08-29",
        "title": "[Day 10] 답변 생성과 Citation: LLM이 거짓말할 때",
        "snippet": "Azure OpenAI 호출, Citation grounding 검증, 검증 실패 시 재생성. Hallucination 방어 기법.",
    },
    {
        "day": 11,
        "date": "2026-08-30",
        "title": "[Day 11] 채널별 렌더링: 같은 답변, 3가지 형식",
        "snippet": "ITSM (구조화, 500자), CHATBOT (친절, 300자), AICC (발화, 100자). 포맷 변환의 함정.",
    },
    {
        "day": 12,
        "date": "2026-08-31",
        "title": "[Day 12] 선제추천: 하이브리드 검색과 개념 확장",
        "snippet": "/v1/recommend 엔드포인트. 키워드 + 벡터 결합, 개념 2홉 확장, 신뢰 관계 가중화.",
    },
    {
        "day": 13,
        "date": "2026-09-01",
        "title": "[Day 13] 보안과 접근제어: 민감정보 0건 검증",
        "snippet": "Bearer Token + RBAC (Scope/Channel/DataScope). ASGI 로그에서 비밀값 제거. Debug 권한 분리.",
    },
    {
        "day": 14,
        "date": "2026-09-02",
        "title": "[Day 14] 모니터링과 운영: 가시성을 확보하다",
        "snippet": "감사 로그 파이프라인, /v1/metrics 대시보드, Provider별 성공/실패/지연. Operational readiness.",
    },
]

posts_dir = "docs/_posts"

for post in POSTS_2:
    # 파일명 생성
    title_slug = post['title'].split('] ')[1].lower()
    title_slug = title_slug.replace(':', '').replace(' ', '-').replace('/', '-')
    filename = f"{posts_dir}/{post['date']}-day-{post['day']:02d}-{title_slug}.md"
    
    # 콘텐츠 생성 (각 날짜별 다양한 관점)
    if post['day'] == 6:
        body = """## Neo4j의 Cypher와의 첫 만남

Day 5까지 검색은 됐다. 하지만 "왜"를 답할 수 없었다.

"왜 이 SR이 관련 있을까?" → 근거가 필요

Neo4j 그래프에는 관계가 있었다:
- SR → Incident (장애 연관)
- Incident → Change (배포와의 인과)
- Change → System (영향받은 시스템)

"이 경로들을 어떻게 찾지?"

## Root Cause: 장애의 원인 추적

초기 설계:
```cypher
MATCH (sr:SR)-[:related_to]->(inc:Incident)
RETURN sr, inc
```

문제점들:
1. **경로가 너무 많음**: 1개 SR이 100개 incident와 연결
2. **깊이 제한 없음**: 무한 순환 가능
3. **성능**: 큰 그래프에서 timeout

## 7개 Cypher 템플릿 설계

실전 경험으로 도출된 템플릿:

```cypher
// Template 1: Direct incident
MATCH (sr:SR)-[:reported_in]->(inc:Incident)
WHERE inc.severity >= 'HIGH'
RETURN inc LIMIT 10

// Template 2: Incident → Change
MATCH (sr:SR)-[:reported_in]->(inc:Incident)
      -[:caused_by]->(chg:Change)
RETURN chg ORDER BY chg.created DESC LIMIT 5

// 나머지 5개: 시스템, 서비스, 릴리즈 경로...
```

각 템플릿의 목적:
- **정확성**: 가장 관련성 높은 경로만
- **성능**: LIMIT, 깊이 제한
- **가독성**: 그래프 분석가도 이해 가능

## 배운 것

**1. Cypher는 아트다**
- 같은 경로도 10가지 방식으로 쓸 수 있음
- 성능 차이는 100배까지

**2. 경로 제한은 필수**
- k-hop 제한이 없으면 timeout
- 보통 2-3 hop이 최적

**3. 권한 필터는 Cypher 수준에서**
- 사후 필터링하면 느림
- 처음부터 권한 조건을 넣기
"""
    elif post['day'] == 7:
        body = """## Similar Case: 과거 사례 찾기

이제 다른 의도들도 경로를 필요로 했다.

Similar Case는 Root Cause와 다르다:
- Root Cause: "왜" (인과 관계)
- Similar Case: "비슷한 게 있나?" (의미 유사성)

## 경로 설계의 고민

"환불 처리 지연" 사례를 찾으려면?

경로 옵션:
1. **직접 매칭**: 과거 "환불 처리 지연" SR
2. **증상 매칭**: 공통 증상을 가진 SR
3. **시스템 매칭**: 같은 시스템의 과거 사례

어떤 순서로 탐색할 것인가?

```cypher
// Step 1: 같은 시스템의 유사 증상
MATCH (sr:SR {system: "payment"})
      -[:has_symptom]->(s:Symptom)
WHERE s.name CONTAINS "지연"
RETURN sr ORDER BY sr.resolved_at DESC LIMIT 5

// Step 2: 과거 해결 사례만
MATCH ... WHERE sr.status = "RESOLVED"

// Step 3: 최근순 정렬
ORDER BY sr.resolved_at DESC
```

## Change Timeline: 변경 기록 추적

또 다른 의도: "최근에 뭐 배포됐나?"

```cypher
MATCH (chg:Change)-[:affects]->(sys:System)
WHERE chg.created > datetime.now() - duration({days: 7})
RETURN chg ORDER BY chg.created DESC

// 시간순 정렬이 중요
// SR이 발생한 시점과 비교해야 함
```

## 배운 것

**1. 의도마다 다른 경로 전략**
- Root Cause: 깊고 복잡
- Similar Case: 빠르고 많음
- Timeline: 최신순

**2. 시간 조건은 쿼리에 넣기**
- 과거 3개월, 최근 1주 등
- 애플리케이션에서 필터링하면 느림

**3. 정렬 순서가 UX다**
- Similar Case는 최신순 (최근 일수록 관련성 높음)
- Timeline은 역순 (최근 배포부터)
"""
    else:
        body = f"## Day {post['day']} 포스트\n\n{post['snippet']}"
    
    content = f"""---
layout: post
title: "{post['title']}"
date: {post['date']}
categories: Development
tags: [graphrag, development]
excerpt: "{post['snippet']}"
---

{body}

---

**다음 회차에 계속...**
"""
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Day {post['day']:2d} ({post['date']}): 생성됨")

print(f"\n🎉 나머지 {len(POSTS_2)}개 포스트 생성 완료!")
print(f"총 14개 포스트 준비 완료!")

