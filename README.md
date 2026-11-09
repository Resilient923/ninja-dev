# GraphRAG 개발 일지 - GitHub Pages

2주 블로그 시리즈: Retriever 프로젝트의 성장 스토리

## 📋 14일 포스트 목록

| Day | 주제 | 발행일 |
|-----|------|--------|
| 1 | GraphRAG 아키텍처 설계 | 2026-08-20 |
| 2 | Query Router - 의도 분류 | 2026-08-21 |
| 3 | PostgreSQL 스키마 통합 | 2026-08-22 |
| 4 | Neo4j 벡터 인덱스 | 2026-08-23 |
| 5 | RRF - 다중 엔진 통합 | 2026-08-24 |
| 6 | 그래프 경로 탐색 1부 | 2026-08-25 |
| 7 | 그래프 경로 탐색 2부 | 2026-08-26 |
| 8 | Context 렌더링 | 2026-08-27 |
| 9 | LangGraph 워크플로우 | 2026-08-28 |
| 10 | 답변 생성과 Citation | 2026-08-29 |
| 11 | 채널별 렌더링 | 2026-08-30 |
| 12 | 선제추천 (Recommend) | 2026-08-31 |
| 13 | 보안과 접근제어 | 2026-09-01 |
| 14 | 모니터링과 운영 | 2026-09-02 |

## 🚀 자동 발행 설정

### Step 1: GitHub 저장소 생성

```bash
# 로컬 저장소 초기화
cd /Users/shinkyuchul/Desktop/agentai/hack/retriever/blog
git init
git add .
git commit -m "Initial blog setup with 14 posts"
```

### Step 2: GitHub에 푸시

```bash
git remote add origin https://github.com/YOUR_USERNAME/retriever-blog.git
git branch -M main
git push -u origin main
```

### Step 3: GitHub Pages 활성화

Settings → Pages → Source: `Deploy from a branch` → `main` 선택
→ `docs` 폴더 선택 → Save

### Step 4: 자동 발행 확인

GitHub Actions 탭에서 `publish` 워크플로우 활성화
→ 매일 09:00 UTC에 자동 발행됨

## 📊 발행 일정

- **매일 09:00 UTC** (17:00 KST)
- 자동으로 해당 날짜의 포스트 발행
- GitHub Pages에 자동 배포

## 🎯 포스트 스타일

- 실제 개발 경험 기반
- 문제 → 고민 → 해결 → 배움 구조
- 기술적 깊이와 성장 스토리 결합

---

**생성 완료**: 2026-08-20
**예상 발행 완료**: 2026-09-02

