# `.claude/agents/` — Claude Code Sub-Agents

8개 sub-agent 정의. Claude Code의 **Task 도구**로 호출되어 격리된 컨텍스트에서 실행됨. 각 .md는 YAML frontmatter (name / description / tools / model) + Markdown 본문 (R&R, 프로세스, 산출물 형식, memory 규칙).

| Agent | Office | Daily / Weekly | 핵심 R&R |
|---|---|---|---|
| [`market-analyst`](./market-analyst.md) | Middle | Daily | D+1 ERCOT 시황 브리핑 (5-6 bullet 자연어) |
| [`congestion-analyst`](./congestion-analyst.md) | Middle | Daily | Constraint binding probability + λ + 노드 MCC |
| [`bess-optimizer`](./bess-optimizer.md) | Front | Daily | GKS BESS DA/RT Energy + AS revenue stack |
| [`dart-virtual-trader`](./dart-virtual-trader.md) | Front | Daily | DART virtual short/long 포지션 추천 |
| [`crr-trader`](./crr-trader.md) | Front | Auction cycle | CRR 트레이딩 기회 3개 발굴 |
| [`pnl-manager`](./pnl-manager.md) | Back | Daily + Weekly | GKS 실적 + Smartbidder benchmark + 全 BESS 랭킹 |
| [`evaluator`](./evaluator.md) | Back | Weekly | 7개 에이전트 점검 + 개선 plan 등록 |
| [`reporter`](./reporter.md) | Back | Daily + Weekly | Daily/Weekly Report 생성 (취합·요약) |

---

## YAML Frontmatter 구조

각 에이전트의 `.md` 파일은 다음 frontmatter로 시작:

```yaml
---
name: agent-name                        # kebab-case, 본 폴더 내 unique
description: 어떤 상황에 어떤 일을 하는지, 무엇을 안 하는지를 명확히 기술
tools: Read, Write, Edit, Bash, ...     # 사용 가능 도구 명시
model: inherit                          # 또는 sonnet, opus, haiku
---
```

---

## 필수 섹션 (모든 에이전트 공통)

각 에이전트 정의 파일의 본문은 다음 섹션을 포함:

1. **Role (R&R)** — Responsible / NOT in scope 명확히
2. **Inputs** — 어디서 어떤 데이터/산출물을 받는지
3. **Process** — 단계별 실행 절차
4. **산출물 형식** — 출력 템플릿 (마크다운/JSON/HTML 등)
5. **Memory & Learning** — history / learnings / plans 작성 의무
6. **충돌 회피 규칙** — 다른 에이전트 영역 침범 금지 명시

---

## 새 에이전트 추가 시

1. 본 폴더에 `<new-agent>.md` 작성 (위 형식 준수)
2. 이 README 표에 추가
3. `../ORGANIZATION.md`의 R&R 매트릭스 업데이트 (R&R 충돌 검사)
4. `../memory/<new-agent>/` 폴더 생성 (history / learnings / plans)
5. `../orchestration/daily-0730-workflow.md` 또는 weekly에 시퀀스 편입
6. `../README.md`의 조직도 업데이트
