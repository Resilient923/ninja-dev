---
title: W3 - Retriever P0를 실제 Neo4j 그래프 계약에 맞추기
date: 2026-08-09 23:40:00 +0900
categories: [GraphRAG, 개발일지, W3]
tags: [Retriever, Neo4j, Cypher, P0, ExactLookup, ACL, ContextBuilder]
author_profile: true
toc: true
toc_sticky: true
excerpt: 문서 프로젝트의 실측 그래프와 Retriever 코드를 대조하고, 조용히 0건을 반환하던 P0 스키마 불일치를 고쳤다.
---

## 오늘 한 일

오늘은 `document` 프로젝트의 Neo4j 실측 결과와 `retriever` 구현을 직접 대조했다.
설계상 이름과 실제 그래프 속성명이 달라도 Cypher는 오류 없이 0건을 반환한다.
그래서 테스트 통과보다 먼저 **실제 그래프 계약과 코드가 같은지**를 확인하는 데 집중했다.

주요 결과는 두 저장소에 나눠 기록했다.

- Retriever 코드: `207da8e feat: align retriever with document graph schema`
- document 설계·상태 문서: `d75751e [계약] retriever P0 구현과 그래프 계약 반영`

로컬 검증은 `161 passed, 4 skipped`, Ruff 통과였다. Neo4j/Azure/PostgreSQL 실환경 검증은
터널과 운영 환경변수가 필요해 아직 대기 상태다.

## 1. 실제 그래프 키로 Cypher를 교체했다

기존 코드가 사용하던 이름은 실제 적재 그래프와 달랐다.

| 대상 | 잘못 사용하던 속성 | 실제 속성 |
|---|---|---|
| 변경 | `change_id` | `chg_id` |
| 릴리즈 | `release_id` | `rel_id` |
| 장애 | `incident_id`, `title` | `inc_id`, `summary` |
| 답변 | `answer_id`, `title` | `note_id`, `body` |
| 담당자 | `employee_id` | `user_id` |

이름이 틀려도 Neo4j는 예외를 내지 않는다. 결과가 비어 있을 뿐이다. 따라서
`root_cause_*`, `change_timeline`, `similar_case`, `default_enrichment` 템플릿을
실제 키에 맞춰 바꿨다.

그래프 출처에는 전 라벨에 존재하지 않는 `source_version`을 필수로 요구하지 않고,
실행 출처가 `neo4j-live`임을 표시하는 fallback을 사용했다.

## 2. Neo4j 드라이버 timeout 계약을 고쳤다

기존 호출은 다음과 같았다.

```python
driver.execute_query(..., timeout_=seconds)
```

설치된 Neo4j 드라이버에서는 이 인자가 거부될 수 있다. 그래프 확장 쿼리는
`neo4j.Query(cypher, timeout=seconds)`로 감싸도록 바꿨다. 테스트 더블과의 호환 fallback은
남겼지만, 실제 드라이버가 사용하는 계약을 우선한다.

## 3. 시스템·서비스 필터를 관계 기반으로 바꿨다

실제 그래프에는 `node.systems`, `node.services` 같은 평면 배열이 없다.
SR과 분류 노드 사이의 관계를 타야 한다.

```cypher
(sr:SR)-[:대상시스템]->(system:시스템)
(sr:SR)-[:대상서비스]->(service:서비스)
```

Neo4j 벡터 검색도 이 관계를 `OPTIONAL MATCH`해 필터링하도록 변경했다.
또한 질의에서 추출한 시스템·서비스를 인증 범위에 단순히 추가하지 않고 교집합으로 좁혔다.
검색 품질 수정이면서 동시에 권한 범위 확장 취약점 수정이기도 하다.

## 4. Exact Lookup을 엔터티별로 분리했다

이전에는 CHG·REL·INC도 SR PostgreSQL Repository에 전달됐다.
이제 SR은 원장 Repository를 사용하고, 변경·릴리즈·장애는 Neo4j의 실제 키로 조회한다.
없는 비-SR ID는 예외가 아니라 정상 `EMPTY`로 끝나도록 구성했다.

추가로 실데이터에 존재하는 다음 식별자도 파싱한다.

- SRM 계열 SR
- `REL####-##` 릴리즈
- `RPL` 및 `WN-` 답변
- `AGT-{한글이름}` 담당자

답변·담당자는 파싱할 수 있지만 그래프 탐색 앵커로 자동 사용하지 않는다.
인식과 탐색 허용을 분리해야 숫자나 답변 ID가 SR 조회로 잘못 들어가지 않는다.

## 5. 그래프 Context에 사실을 넣었다

관계명만 이어 붙인 컨텍스트는 LLM이 읽을 수 없다.

```text
[PATH:...] 원인 → 편성 → 파생
```

이를 노드 유형·ID·라벨·핵심 시각과 방향이 포함된 구조로 바꿨다.

```text
INCIDENT:INC... (결제 장애, occurred_at=...)
  -[원인]-> RELEASE:REL... (정기배포, deployed_at=...)
  -[편성]-> CHANGE:CHG... (설정 변경, created_at=...)
```

이제 경로가 단순한 관계 목록이 아니라 답변 생성과 citation 검증에 사용할 수 있는
근거 블록이 된다.

## 6. 검색 인덱스 연결 현황

문서 프로젝트의 실제 벡터 인덱스는 다음 7종이다.

```text
sr_vec · chunk_vec · doc_vec · note_vec · chg_vec · inc_vec · rel_vec
```

이번 코드에는 우선 `sr_vec`, `doc_vec`, `chunk_vec`를 연결했다. 추천 경로는 SR 검색만
사용하도록 별도 Provider 목록을 두었다. 문서·청크가 추천 카드에 섞여 SR 결과를 밀어내지
않게 하기 위한 조치다.

다만 `note_vec`, `chg_vec`, `inc_vec`, `rel_vec`까지 모두 연결한 것은 아니다.
또 청크에서 문서로 돌아갈 때 `chunk.doc_id`를 사용하면 안 되고,
`(문서)-[:본문청크]->(청크)`를 타야 한다. 이 두 항목은 다음 P0 작업으로 남겼다.

## 다음 작업

다음 순서는 아래와 같다.

1. 7개 벡터 인덱스 전부를 타입별 검색 Provider로 연결
2. 청크 검색 결과를 `:본문청크` 관계로 문서에 복귀
3. Neo4j 시간 비교용 UTC-naive 정규화 함수와 회귀 테스트 추가
4. 개념 탐색에서 `(:개념)-[:연관]-(:개념)` 무방향 매치 추가
5. 실시간 ITSM 변경을 실제 Neo4j에서 확인하는 E2E 시나리오 작성

오늘의 교훈은 간단하다.

> GraphRAG의 첫 번째 품질 게이트는 모델이 아니라 그래프 계약이다.
> 키 하나, 방향 하나, 시간 타입 하나가 틀리면 시스템은 실패하지 않고 조용히 틀린다.
