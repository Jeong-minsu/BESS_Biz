# GKS BESS — D+1 (2026-08-01, 토요일) Optimal Revenue Stack

**Issued**: 2026-07-31 07:30 CT (bess-optimizer)
**DAM bid cutoff**: 10:00 CT 2026-08-01
**Asset**: GKS_BESS_RN — 100 MW / 200 MWh / RTE 85%
**SoC Init**: 30 MWh (Rule 7 Override 1 — 7/31 terminal SoC = 0 MWh per recommendation; partial residual)
**Day type**: WEPEAK Saturday — 폭염 5일차

---

## DATA_STATUS

| Source | Status | Impact |
|---|---|---|
| Yes Energy Bidclose (2026-08-01) | **FAILED** — rate-limited | 절대 가격 수치 없음 |
| Smartbidder Energy/AS/DA-RT | **FAILED** — AADSTS7000222 7일+ 연속 (7/26~) | P(DA>RT), AS spread 전무 |
| Enverus / AG2 WSI | 미수집 | 기상·풍력 교차검증 불가 |
| Tenaska PTP (SoC) | FAILED — IP whitelist + endpoint cache | 전일 실적·SoC 실데이터 없음 |
| AS Playbook | 미생성 — recommend_as_position.py 미구현 | Prior 없이 자체 판단 |
| **유일한 기준**: 7/31 YE PROD (목요일) + 토요일 구조적 추론 | | |

> **경고**: 이 산출물의 모든 가격 수치는 전일(7/31 목요일) PROD 데이터와 토요일 구조적 특성에서 추론한 **방향성 전용** 추정값이다. 절대 수치의 신뢰도는 매우 낮다. DEGRADED 이중 실패(YE + Smartbidder). 수치를 정산·PnL 귀속에 사용 금지.

---

## Step 1-2: 입력 정합

### 수급 구조 (추론 — 실데이터 없음)

| 항목 | 목 7/31 PROD (기준) | 토 8/1 추론 | 비고 |
|---|---|---|---|
| Load 24h avg | 75,205 MW | 66,000-69,500 MW | -8-12% 요일 효과 + 폭염 하방 지지 |
| Duck Curve (HE10 부근) | 23,784 MW | **18,000-22,000 MW** | 총수요 감소 > 재생에너지 감소 → 더 깊어짐 |
| 저녁 NL 피크 | 70,709 MW (HE21) | 58,000-65,000 MW (HE19-21) | 총수요 낮아 절대값 완화 |
| Solar Cliff (HE19→HE20) | +11,549 MW/1h | **+8,000-10,000 MW/1h** | 동일 메커니즘, 충격 완화 |
| Solar 피크 | 30,472 MW (HE13) | 28,000-31,000 MW | 8월 초 일사각도 유사 |
| Wind 24h avg | 13,768 MW | 11,000-15,000 MW | 열돔 5일차 주간 억압 지속 |
| GR_WEST 주간 저점 | 2,947 MW (HE16) | 2,000-4,000 MW | 패턴 지속 추론 |
| 정비 outage | 7,114 MW avg | 7,500-9,500 MW | 주말 정비 상향 패턴 |

### 가격 뷰 (추론 — DEGRADED)

| 구간 | HE | DA 방향성 추론 | 신뢰도 |
|---|---|---|---|
| 야간 저점 | HE01-06 | $22-40/MWh | 낮음 |
| 태양광 상승 | HE07-09 | $8-22/MWh | 낮음 |
| **Duck Curve 최저** | **HE09-12** | **$0-12/MWh (RT 음수 High)** | 방향 MEDIUM-HIGH; 수치 LOW |
| Solar 고원 | HE12-15 | $12-30/MWh | 낮음 |
| 오후 ramp | HE15-17 | $30-55/MWh | 낮음 |
| Solar Cliff 진입 | HE18-19 | $35-60/MWh | 낮음 |
| Solar Cliff 피크 | HE20-21 | $45-75/MWh | 낮음 (Medium-Low spike) |
| 야간 복귀 | HE22-24 | $25-45/MWh | 낮음 |

### 혼잡 요약 (Stage 0 — Zero-data cycle)

| 신호 | 방향 | 활용 방침 |
|---|---|---|
| GKS MCC HE09-11 | -$3.0 to -$6.0+/MWh (방향: MEDIUM-HIGH) | 충전 창구 확인 신호로 활용; 수치는 입찰에 미사용 |
| SOUTH_HOUSTON_IMPORT HE19-22 | P(binding) 18-30% (LOW-MEDIUM) | Rule 6 HIGH 임계(35%) 미달 → DA 우선, RT 투기 금지 |
| GKS MCC HE19-22 | +$0.5 to +$2.5 uncond. (LOW conviction) | 방전 미미한 upside |

---

## Step 3: Top / Bottom Hours

**Bottom 2 (충전 최우선)**:
- **HE09** — NL est. 18,000-22,000 MW (이번 주 최저); RT 음수 리스크 HIGH; GKS MCC -$3 to -$6/MWh (방향 HIGH). BEST 충전 기회.
- **HE10** — Duck Curve 지속; Solar + Wind 동시 최대; GKS MCC 지속 할인. 2차 충전 (SoC = 200 MWh 완충).

**Top 2 (방전 최우선)**:
- **HE17** — 주거 냉방 피크 (Saturday HE14-16 이후 ramp 지속); Solar 여전히 감소 중; 풍력 주간 저점 통과 후; 가장 신뢰도 높은 방전 창구.
- **HE18** — Solar Cliff 진입; 가스 발전 급등 시작; 저녁 오후 최대 가격 기대 구간. 2차 방전.

**RT Spike 유보**: HE20-21
- SOUTH_HOUSTON_IMPORT P=18-30% (Saturday weekend discount) — Rule 6 HIGH 임계 35% 미달
- 토요일 총수요 낮아 spike 완화 → DA 우선 전략 유지
- 조건부 대안(Stack C)에서만 HE20-21 RT 고려

---

## Step 4: DA-RT Spread 전략

> 부호 규칙: spread = DA − RT. Positive = DA expensive = DA 매도 우위. Negative = RT > DA = RT 잔류 우위.

| 창구 | HE | 방향 추론 | 전략 |
|---|---|---|---|
| Duck Curve 충전 | HE09-10 | **Positive spread 가능성 HIGH** (DA > RT, RT 음수 리스크) | DA 충전 — 저단가 고정. RT 음수 실현 시 추가 이익 |
| 오전-오후 hold | HE11-16 | Positive spread 지속 가능 (Solar 고원) | NS/ECRS 오버레이; 에너지 미개입 |
| 저녁 방전 | HE17-18 | Spread 혼재 (Saturday는 RT spike 제한적) | **DA 방전 우선** — 정량 신호 없을 때 DA 확정 수익 선택 |
| Solar Cliff 피크 | HE19-21 | Negative spread 가능하지만 Saturday discount로 완화 | **RT 미개입** (P(binding)=18-30%; Rule 6 HIGH 미충족) |

**AS Spread (DEGRADED 완전 blind)**:
- 토요일 RRS / ECRS / NS DA 가격: 평일 대비 구조적 낮음 (weekend AS 수요 감소)
- Smartbidder 7일+ FAILED → AS 가격 정량화 불가
- 전략: NS 소량 DA (방향성 보조), ECRS Rule 1 최소 적용

---

## Step 5: Revenue Stack 시나리오

### Stack B (Primary — Energy Arbitrage, DA 중심)

HE09-10 DA 충전 + HE17-18 DA 방전. 토요일 Duck Curve 최심 + 일찍당겨진 저녁 peak 포착.

| 시나리오 | 충전 avg (HE09-10) | 방전 avg (HE17-18) | Gross margin | ×0.80 | MCC adj | Net Energy | AS P50 | Total |
|---|---|---|---|---|---|---|---|---|
| P10 (Bear) | $10/MWh | $35/MWh | ($35-$10)×200=$5,000 | $4,000 | +$400 | $4,400 | $400 | **$4,800** |
| P50 (Base) | $5/MWh | $48/MWh | ($48-$5)×200=$8,600 | $6,880 | +$600 | $7,480 | $800 | **$8,280** |
| P90 (Bull) | $2/MWh | $62/MWh | ($62-$2)×200=$12,000 | $9,600 | +$800 | $10,400 | $1,400 | **$11,800** |

> MCC adj: HE09-10 충전 할인 (-$2/MWh est. × 200 MWh = $400) + HE17-18 방전 미미한 uplift (+$1/MWh × 200 MWh = $200) = +$600 P50 (VERY LOW conviction). Rule 2 haircut 0.80× 적용. DEGRADED 불확실도 ±60%+.

### Stack A (AS-Heavy — 토요일 비추천)

- AS 가격 구조적 낮음 + Smartbidder FAILED → AS 최적화 불가
- NS DA 80 MW × 6h × $2/MW-h (토요일 추정) = $960; ECRS = $0-50
- 에너지 arbitrage 없을 때 total ≈ $1,000-2,000 → Stack B 대비 현저 열세
- **토요일 DEGRADED 조건에서 AS-Heavy는 비추천**

### Stack C (RT Spike Capture — 조건부)

- Stack B 충전 동일 (HE09-10)
- HE17-19: Hold + NS 50 MW
- HE20-21: RT primary dispatch 100 MW each
- 발동 조건 (아래 참조)
- EV: SOUTH_HOUSTON_IMPORT P=18-30% 기준; P50 spike 기대 낮음 → Stack B P50 $8,280 > Stack C P50 추산 $5,500
- **Stack C는 발동 조건 충족 시에만 전환**

---

## Recommendation (Primary) — Stack B: Energy Arbitrage

**전략 근거**: 토요일 구조적 특성 2가지가 Stack B를 우선:
1. SOUTH_HOUSTON_IMPORT P=18-30% (Saturday discount) → Rule 6 HIGH (35%) 미충족 → RT 투기 불적합
2. AS 가격 주말 구조적 저하 + Smartbidder FAILED → AS 최적화 불가 → 에너지 확정 수익 선택

**충전 창구**: HE09-10 (Duck Curve 최심, 이번 주 최저 단가 기회)
**방전 창구**: HE17-18 (Saturday 오후 피크 1-2h 조기 + Solar Cliff 진입)
**AS 오버레이**: NS 소량 hold 시간 + Rule 1 ECRS 최소 (토요일 기대 수익 낮음, 의무 적용)

### 시간별 스케줄

| HE | CT Window | Mode | Energy MW | NS MW | ECRS MW | RRS | RegUp | RegDown | SoC End MWh | DA Price Direction |
|----|-----------|------|----------:|------:|--------:|:---:|:-----:|:-------:|------------:|-------------------:|
| 01 | 00-01 | Idle+NS | 0 | 20 | 0 | 0 | 0 | 0 | 30 | $22-40 (ref) |
| 02 | 01-02 | Idle+NS | 0 | 20 | 0 | 0 | 0 | 0 | 30 | — |
| 03 | 02-03 | Idle+NS | 0 | 20 | 0 | 0 | 0 | 0 | 30 | — |
| 04 | 03-04 | Idle+NS | 0 | 20 | 0 | 0 | 0 | 0 | 30 | — |
| 05 | 04-05 | Idle+NS | 0 | 20 | 0 | 0 | 0 | 0 | 30 | — |
| 06 | 05-06 | Idle+NS | 0 | 20 | 0 | 0 | 0 | 0 | 30 | — |
| 07 | 06-07 | Idle | 0 | 0 | 0 | 0 | 0 | 0 | 30 | Solar ramp 시작 |
| 08 | 07-08 | Idle | 0 | 0 | 0 | 0 | 0 | 0 | 30 | $8-22 declining |
| **09** | **08-09** | **DA Charge** | **-100** | 0 | 0 | 0 | 0 | 0 | **115** | **$0-12 (RT -가능)** |
| **10** | **09-10** | **DA Charge** | **-100** | 0 | 0 | 0 | 0 | 0 | **200** | **$0-12 (Duck)** |
| 11 | 10-11 | Hold+NS | 0 | 50 | 0 | 0 | 0 | 0 | 200 | $5-18 |
| 12 | 11-12 | Hold+NS | 0 | 50 | 0 | 0 | 0 | 0 | 200 | $8-22 |
| 13 | 12-13 | Hold+NS | 0 | 50 | 0 | 0 | 0 | 0 | 200 | $12-30 |
| 14 | 13-14 | Hold+NS | 0 | 50 | 0 | 0 | 0 | 0 | 200 | $15-35 |
| 15 | 14-15 | Hold+NS+ECRS | 0 | 50 | 10 | 0 | 0 | 0 | 200 | $25-50 |
| 16 | 15-16 | Hold+NS+ECRS | 0 | 50 | 10 | 0 | 0 | 0 | 200 | $30-55 |
| **17** | **16-17** | **DA Discharge** | **+100** | 0 | 0 | 0 | 0 | 0 | **100** | **$30-55** |
| **18** | **17-18** | **DA Discharge** | **+100** | 0 | 0 | 0 | 0 | 0 | **0** | **$35-60** |
| 19 | 18-19 | Idle | 0 | 0 | 0 | 0 | 0 | 0 | 0 | SoC=0 |
| 20 | 19-20 | Idle | 0 | 0 | 0 | 0 | 0 | 0 | 0 | SoC=0 |
| 21 | 20-21 | Idle | 0 | 0 | 0 | 0 | 0 | 0 | 0 | SoC=0 |
| 22 | 21-22 | Idle | 0 | 0 | 0 | 0 | 0 | 0 | 0 | SoC=0 |
| 23 | 22-23 | Idle | 0 | 0 | 0 | 0 | 0 | 0 | 0 | SoC=0 |
| 24 | 23-00 | Idle | 0 | 0 | 0 | 0 | 0 | 0 | 0 | SoC=0 |

> **HE07-08 NS 제외 근거**: SoC 30 MWh → NS 30분 응답 기준 60 MW 최대. 그러나 HE09 이전 NS call로 충전 전 SoC가 감소할 경우 HE09-10 충전 목표(200 MWh) 달성 불가 리스크 존재. DEGRADED 조건에서 충전 창구 보존 우선.
>
> **HE19-24 NS 제외 근거**: SoC = 0 MWh → 방전 capacity 없음 → NS 제공 불가.

---

## SoC Balance Verification

| Checkpoint | SoC MWh | 계산 |
|---|---|---|
| HE01 시작 | 30 | Rule 7 Override 1 |
| HE01-08 (NS/Idle) | ~30 | NS call 드물어 SoC 변화 없음 (conservative) |
| **HE09 충전** | 30 + (100 × 0.85) = **115** | 그리드 100 MWh → 저장 85 MWh |
| **HE10 충전** | 115 + 85 = **200** | SoC FULL |
| HE11-16 (Hold) | **200** | 에너지 미개입 |
| **HE17 방전** | 200 − 100 = **100** | 100 MWh 방전 |
| **HE18 방전** | 100 − 100 = **0** | 100 MWh 방전. Terminal SoC = 0 |
| HE19-24 (Idle) | **0** | SoC = 0, 방전 불가 |

SoC 범위: 0 ≤ SoC ≤ 200 MWh. 경계 이탈 없음. FEASIBLE.

---

## HSL Constraint Verification (Hard Limit = 100 MW)

| HE | Energy MW | NS MW | ECRS MW | 합계 | HSL |
|----|----------:|------:|--------:|-----:|:---:|
| 01-06 | 0 | 20 | 0 | 20 | PASS |
| 07-08 | 0 | 0 | 0 | 0 | PASS |
| 09 | 100 (charge) | 0 | 0 | 100 | PASS |
| 10 | 100 (charge) | 0 | 0 | 100 | PASS |
| 11-14 | 0 | 50 | 0 | 50 | PASS |
| 15-16 | 0 | 50 | 10 | 60 | PASS |
| 17 | 100 (DA discharge) | 0 | 0 | 100 | PASS |
| 18 | 100 (DA discharge) | 0 | 0 | 100 | PASS |
| 19-24 | 0 | 0 | 0 | 0 | PASS (SoC=0) |

전 24시간 HSL 100 MW 준수. NS+Energy 동시 초과 없음 (Jul 23 critical failure 재발 방지).

---

## DA 입찰 파라미터

| HE | 방향 | MW | 입찰 가격 | 근거 |
|----|------|----|----------|------|
| HE09 | Buy (DA charge) | 100 | Max buy ≤ **$10/MWh** | Duck Curve $0-12 범위 상단 − 여유. 음전기 구간에서 DA 충전 확보 목표 |
| HE10 | Buy (DA charge) | 100 | Max buy ≤ **$12/MWh** | SoC 완충 최우선; $12는 Duck Curve 추론 상단 |
| HE17 | Sell (DA discharge) | 100 | Min offer ≥ **$35/MWh** | $30-55 추론 범위 하단; 최소 수익 보호 |
| HE18 | Sell (DA discharge) | 100 | Min offer ≥ **$40/MWh** | Solar Cliff onset; $35-60 범위 mid-low; floor 소폭 상향 |

> **신뢰도 매우 낮음 (DEGRADED)**: 위 가격은 방향성 추론 기반. 실제 DA 청산가 수준이 다를 경우 충전 미실행(HE09-10 가격 $10-12 초과) 또는 방전 미실행(HE17-18 가격 $35-40 미달) 가능. Smartbidder PROD 복구 후 즉시 재조정 필요.

---

## Top / Bottom Hours 요약

- **충전 최우선**: HE09, HE10 (Duck Curve — 이번 주 가장 낮은 가격 추론, RT 음수 High)
- **방전 최우선**: HE17, HE18 (Saturday 오후 peak 1-2h 조기 + Solar Cliff 진입)
- **RT spike 유보**: HE20-21 (P=18-30% LOW-MEDIUM; Rule 6 HIGH 미충족; Stack C 조건부만)
- **절대 방전 금지**: HE09-12 (Duck Curve RT 음전기 고위험; BESS 방전 중 RT 음수 = 수익 손실)

---

## DA-RT Spread 전략 요약

- **에너지**: DA 우선 (HE09-10 DA 충전 lock-in; HE17-18 DA 방전 확정 수익 선택)
  - RT spike 포기 근거: SOUTH_HOUSTON_IMPORT P=18-30% (Saturday discount) < Rule 6 HIGH 임계 35%
- **RRS**: 제외 (Rule 4 RegUp 배제 패턴 지속; 토요일 RRS 낮음 추론)
- **ECRS**: HE15-16 최소 10 MW DA (Rule 1 Summer 의무; 기대 수익 $20-40, 청산 불확실)
- **NS**: HE01-06 20 MW, HE11-16 50 MW (DA 제출; 토요일 낮은 AS 가격 반영하여 수량 축소)

---

## Expected Revenue

| 구분 | P10 | P50 | P90 |
|---|---|---|---|
| Energy Arbitrage (net, Rule 2 + MCC) | $4,400 | $7,480 | $10,400 |
| Non-Spin (DA) | $200 | $600 | $1,100 |
| ECRS (Rule 1, 낮은 확률) | $10 | $30 | $80 |
| **Total** | **$4,600** | **$8,110** | **$11,580** |

- **vs Smartbidder benchmark**: 계산 불가 (DEGRADED 7일 연속)
- **vs 7-day moving avg**: 계산 불가 (연속 DEGRADED)
- **WDPEAK 대비 토요일 할인**: 7/31 추천 P50 $18,300 대비 이번 P50 $8,110 (−56%)
  - 토요일 가격 30-40% 낮음 + SOUTH_HOUSTON_IMPORT 미결합 가정 반영

> **불확실도 경고**: DEGRADED 이중 실패 하에서 P10-P90 밴드는 실제 불확실도의 일부만 반영. 실제 결과는 이 범위를 벗어날 수 있음. 상기 수치를 의사결정의 절대 기준으로 사용 금지.

---

## Risks

| 리스크 | 방향 | 확률 추론 | Revenue 영향 | 대응 |
|---|---|---|---|---|
| Duck Curve RT 음전기 HE09-12 실현 | 충전 단가 추가 하락 → upside | HIGH (방향 확실) | 충전 cost 절감 +$200-600 추가 | DA 충전 입찰 유지; RT 음전기는 DA 충전 비용 감소 효과 |
| HE09-10 DA 가격 $12 초과 (bid ceiling 초과) | 충전 미실행 | LOW-MEDIUM | SoC 30 MWh 유지 → HE17-18 방전 절반만 가능 | HE10-11로 충전 shift; max buy $15로 상향 검토 |
| HE17-18 DA 가격 $35 미달 (방전 미실행) | 방전 미청산 | MEDIUM | 에너지 수익 $0 → NS만 남음 (~$800) | 방전 시간 HE18-19로 1h 후방 shift; min offer 하향 $30 검토 |
| SOUTH_HOUSTON_IMPORT 불시 결합 (HE20-21) | RT spike — SoC 이미 0 → 기회 손실 | LOW (18-30%) | Stack B 미포착; Stack C 대비 기회비용 $2,000-5,000 | 수용 가능; 토요일 EV 기준 Stack B가 우위 |
| 주말 outage 저녁 복귀 지연 | HE17-19 가격 상방 | MEDIUM (정비 7,500-9,500 MW) | 방전 수익 +$500-1,500 upside | Stack B 포착 (DA 방전 실행 중) |
| 폭염 예상치 못한 약화 | 주거 냉방 부하 하락, 저녁 가격 하방 | LOW | P10 시나리오 방향 |  수용 |
| RT 비자발적 dispatch (Rule 8) | Smartbidder 자율 실행 divergence | ACTIVE — 구조적 | 실제 dispatch ≠ 이 추천 | 실행 divergence는 Tenaska/Smartbidder에서 독립 운영. 이 산출물은 STRATEGIC BENCHMARK |

---

## Alternative: Stack C — RT Spike Capture (조건부)

**발동 트리거 (둘 중 하나)**:
1. Smartbidder 10:00 CT DAM cutoff 전 복구 + P(DA>RT) at HE20 < 0.50 (RT>DA 신호)
2. 인트라데이 NL ramp HE18→HE21 예측이 +12,000 MW 초과 (총수요 기대보다 강한 경우)

**Stack C 스케줄 변경**:
- HE09-10: 동일 (DA 충전)
- HE11-19: Hold + NS 50 MW (에너지 미개입)
- **HE20**: RT dispatch +100 MW (RT floor ≥ $50/MWh)
- **HE21**: DA discharge +100 MW (min offer ≥ $50/MWh)
- HE22-24: Idle (SoC = 0)

**Stack C EV 근거**:
- SOUTH_HOUSTON_IMPORT P=18-30%: P50 EV at HE20-21 ≈ 200 MWh × $58 × 0.80 × 0.30 (binding fraction) + 200 MWh × $40 × 0.80 × 0.70 (non-binding) ≈ **$2,792 + $4,480 = $7,272** (조도 기준값)
- Stack B P50: $8,110
- **Stack C는 현재 EV 기준 열세**. 위 트리거 조건 충족 시에만 전환.

---

## 기술 제약 요약

| 항목 | 설정 | 검증 |
|---|---|---|
| 100 MW HSL | 전 시간 준수 | PASS (표 참조) |
| 200 MWh SoC 상한 | 최대 200 MWh (HE10 말) | PASS |
| 0 MWh SoC 하한 | 최소 0 MWh (HE18 이후) | PASS |
| NS SoC 지속성 | HE01-06: 30 MWh → NS 20 MW (30분 기준 60 MW 최대) PASS | |
| 충전 중 AS 제외 | HE09-10 AS = 0 | PASS |
| 방전 중 AS 제외 | HE17-18 AS = 0 | PASS |
| Rule 1 ECRS Summer | HE15-16 10 MW ECRS | APPLIED (최소 적용) |
| Rule 2 (0.80× haircut) | 에너지 gross margin에 적용 | APPLIED |
| Rule 4 RegUp 제외 | RegUp = 0 전 시간 | APPLIED |
| Rule 6 HOUSTON_IMPORT | P=18-30% < 35% → Rule 6 HIGH 미충족 → DA primary | APPLIED |
| Rule 7 SoC init | 30 MWh (Override 1) | APPLIED |
| Rule 8 RT dispatch | ACTIVE — 실행 divergence 구조적 | ACTIVE |

---

## Downstream Handoffs

**dart-virtual-trader**:
- HE09-12 GKS 노드 MCC 음수 방향 신호: GKS 노드 HB_SOUTH 대비 weak (congestion-analyst). BESS 충전 중 노드 concentration 고려.
- HE17-18 방전: GKS 노드 MCC ~$0 (NEGLIGIBLE). Virtual position 필요성 낮음.
- SOUTH_HOUSTON_IMPORT: P=18-30% (낮음). HB_HOUSTON virtual 규모 신중하게.

**congestion-analyst**:
- 8/1 Saturday 결합 여부 (T+2 ~8/3 정산) — Stage 0 Saturday calibration 데이터.
- GKS MCC HE09-11 실현값: Duck Curve calibration 핵심 포인트.

**pnl-manager**:
- T+2 Tenaska 8/1 정산 예상: ~2026-08-03.
- 8/1 실데이터 수신 시 self-review 즉시 작성: `memory/bess-optimizer/learnings/2026-08-01.md`

**reporter**:
- Primary Stack B: DA charge HE09-10 / DA discharge HE17-18. P10/P50/P90: $4,600/$8,110/$11,580.
- DATA_STATUS: FULL DEGRADED — 절대 수치 신뢰도 매우 낮음. 방향성 전용.
- 토요일 WEPEAK 구조 + 폭염 5일차 Duck Curve 최심 주의.

---

## 데이터 복구 액션 (우선순위)

1. **[P0 URGENT]** Smartbidder client_secret 갱신 — Ascend rep 즉시 연락 (7일+ 연속 FAILED; 이번 주 전체 blind spot). DAM cutoff 전 복구 시 Stack C 전환 검토 가능.
2. **[P1]** Yes Energy rate-limit 해소 — `shared/scripts/fetch_market_data.py` sleep 간격 조정. 8/1 데이터 DAM cutoff 전 재시도.
3. **[P1]** Tenaska endpoint cache `TENASKA_EP_*` 4개 env var 설정 — 비대화형 실행 차단 해제.
4. **[P2]** Enverus/AG2 재개 — Duck Curve 깊이, GR_WEST 교차검증.

---

*bess-optimizer | reports/daily/2026-08-01-bess-stack.md | Issued 2026-07-31 07:30 CT*
*Primary: Stack B — Energy Arbitrage (DA charge HE09-10 / DA discharge HE17-18)*
*Expected Revenue: P10 $4,600 / P50 $8,110 / P90 $11,580 (FULL DEGRADED — 방향성 전용)*
*DATA_STATUS: YES_ENERGY=FAILED | SMARTBIDDER=FAILED (7일+) | TENASKA=FAILED | AS_PLAYBOOK=ABSENT*
*Rule 6 NOT triggered (P=18-30% < 35%). DA primary strategy.*
*T+2 Tenaska 정산 예상: 2026-08-03. Self-review: memory/bess-optimizer/learnings/2026-08-01.md*
*EXECUTION DIVERGENCE ACTIVE (Rule 8): Smartbidder operates independently. This output is STRATEGIC BENCHMARK only.*
