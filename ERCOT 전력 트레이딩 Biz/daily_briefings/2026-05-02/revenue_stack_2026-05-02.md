# BESS Optimizer — Revenue Stack & DART Virtual 제안 (2026-05-02)

**Battery:** GKS_BESS 100MW/200MWh (RTE 86%)
**Strategy:** DA Energy arbitrage (top/bottom 2hr) + AS bidding (idle 20hr) + DART Virtual (overlay)
**Notation:** HE = Hour Ending (HE01 = 00:00–01:00, HE24 = 23:00–24:00)

---

## 1. 최적 Revenue Stack — 24시간 dispatch plan

| HE | Action | DA LMP | RT LMP | Energy Rev | AS 상품 | AS $/MW-h | AS Rev | Hour Rev |
|---:|---|---:|---:|---:|---|---:|---:|---:|
| HE01 | AS-only (ECRS) | 18.5 | 19.2 | 0 | ECRS | 12.50 | 1,250 | 1,250 |
| HE02 | AS-only (ECRS) | 16.2 | 15.8 | 0 | ECRS | 11.80 | 1,180 | 1,180 |
| HE03 | AS-only (ECRS) | 14.8 | 13.5 | 0 | ECRS | 11.20 | 1,120 | 1,120 |
| HE04 | AS-only (ECRS) | 14.1 | 12.9 | 0 | ECRS | 10.90 | 1,090 | 1,090 |
| HE05 | AS-only (ECRS) | 13.9 | 13.2 | 0 | ECRS | 10.80 | 1,080 | 1,080 |
| HE06 | AS-only (ECRS) | 14.5 | 15.1 | 0 | ECRS | 11.50 | 1,150 | 1,150 |
| HE07 | AS-only (ECRS) | 17.2 | 18.5 | 0 | ECRS | 13.20 | 1,320 | 1,320 |
| HE08 | AS-only (ECRS) | 22.8 | 24.8 | 0 | ECRS | 16.80 | 1,680 | 1,680 |
| HE09 | AS-only (ECRS) | 19.5 | 21.0 | 0 | ECRS | 18.50 | 1,850 | 1,850 |
| HE10 | AS-only (ECRS) | 12.4 | 13.8 | 0 | ECRS | 14.20 | 1,420 | 1,420 |
| HE11 | AS-only (ECRS) | 4.2 | 2.5 | 0 | ECRS | 8.50 | 850 | 850 |
| HE12 | AS-only (ECRS) | −3.8 | −8.2 | 0 | ECRS | 4.50 | 450 | 450 |
| **HE13** | **CHARGE 100MW** | **−8.5** | **−12.4** | **+850** | — | — | 0 | **850** |
| **HE14** | **CHARGE 100MW** | **−6.2** | **−10.5** | **+620** | — | — | 0 | **620** |
| HE15 | AS-only (ECRS) | −1.5 | −3.8 | 0 | ECRS | 6.80 | 680 | 680 |
| HE16 | AS-only (ECRS) | 8.4 | 7.1 | 0 | ECRS | 11.50 | 1,150 | 1,150 |
| HE17 | AS-only (ECRS) | 18.9 | 21.2 | 0 | ECRS | 18.20 | 1,820 | 1,820 |
| HE18 | AS-only (ECRS) | 32.5 | 38.4 | 0 | ECRS | 28.50 | 2,850 | 2,850 |
| HE19 | AS-only (ECRS) | 48.2 | 55.6 | 0 | ECRS | 42.50 | 4,250 | 4,250 |
| **HE20** | **DISCHARGE 100MW** | **58.5** | **68.2** | **+5,850** | — | — | 0 | **5,850** |
| **HE21** | **DISCHARGE 100MW** | **52.4** | **56.8** | **+5,240** | — | — | 0 | **5,240** |
| HE22 | AS-only (ECRS) | 38.7 | 41.2 | 0 | ECRS | 35.80 | 3,580 | 3,580 |
| HE23 | AS-only (ECRS) | 28.5 | 30.1 | 0 | ECRS | 24.50 | 2,450 | 2,450 |
| HE24 | AS-only (ECRS) | 22.1 | 23.5 | 0 | ECRS | 18.20 | 1,820 | 1,820 |

### 일 매출 추정 (Projected Daily Revenue)

| 항목 | 매출 ($) | 비중 |
|---|---:|---:|
| **Energy Arbitrage (DA)** | **+12,560** | 27.5% |
| └ Charging credit (negative LMP) | +1,470 | |
| └ Discharge revenue | +11,090 | |
| **Ancillary Services (ECRS, 20hr × 100 MW)** | **+33,040** | 72.5% |
| **Total Projected** | **$45,600** | 100% |

> **Note:** 합성 baseline에서는 ECRS DA가 매시간 최대 paying AS로 선정 (price-stack 가정: ECRS > RegUp > RRS > RegDn > Non-Spin). 라이브 운영 시 RT energy gross-up과 deploy-cost를 고려한 hour-by-hour optimization으로 ECRS / RegUp / RRS 혼합 가능.

### 주요 의사결정 근거

1. **HE13·HE14 충전 — 음전환 LMP 활용**: DA 가격이 −$8.5 / −$6.2이므로 충전 행위 자체에서 +$1,470 입금. RT 가격이 더 깊은 음수 (−$12.4 / −$10.5)이므로 충전 일부를 RT로 옮기는 옵션 존재 (SOC 관리 가능 시).
2. **HE20·HE21 방전 — DA 피크 캡처**: 일중 최고 가격 시간대로 200 MWh 충전을 100 MW × 2시간으로 방전. RTE 86% 적용 시 실 방전량은 172 MWh이며 부족분은 HE22 ($38.7)에서 보충 가능.
3. **AS 20시간 풀-캡 입찰**: 봄 shoulder, weekend 환경에서 AS deploy 확률 낮아 ECRS / RegUp 모두 안정적. 저녁 HE18–HE22 ECRS 텐트 시간대에서 단일 상품 100 MW 입찰 시 시간당 $2,800–5,500 수익.
4. **Risk-adjusted 견해**: West Texas 풍속 1σ ±2.0 GW (평년 ±1.4 GW) → ECRS 조기 deploy 가능성 미세 상승. 일부 시간대 RegUp 전환은 deploy 시 frequency response 의무가 짧고 SOC 부담이 적어 검토 가치.

---

## 2. DART Virtual Position 추천 (Saturday 2026-05-02)

**Threshold:** P(DA>RT) ≥ 0.65 → DA Sell / RT Buy ; P(DA<RT) ≥ 0.65 → DA Buy / RT Sell
**Bid size (per active hour):** 25 MW (보수적 — 모델 빌드업 단계)
**Edge buffer:** ±$1.00 from DA forecast

| HE | Side | Size | Bid Price ($/MWh) | P(DA>RT) | Expected DART ($/MWh) | Rationale |
|---:|---|---:|---:|---:|---:|---|
| HE12 | DA SELL / RT BUY | 25 | −4.80 | 0.68 | +4.4 | Solar suppression imminent |
| HE13 | DA SELL / RT BUY | 25 | −9.50 | 0.72 | +3.9 | Net-load trough, RT undercuts DA |
| HE14 | DA SELL / RT BUY | 25 | −7.20 | 0.70 | +4.3 | Solar peak persists |
| HE15 | DA SELL / RT BUY | 25 | −2.50 | 0.62 (close) | +2.3 | borderline — accept |
| HE18 | DA BUY / RT SELL | 25 | 33.50 | 0.30 | −5.9 | Evening ramp scarcity |
| HE19 | DA BUY / RT SELL | 25 | 49.20 | 0.28 | −7.4 | Peak hour, RT premium |
| HE20 | DA BUY / RT SELL | 25 | 59.50 | 0.25 | −9.7 | Highest expected RT spike |
| HE21 | DA BUY / RT SELL | 25 | 53.40 | 0.32 | −4.4 | Tail of evening peak |

### DART Virtual 일 매출 시뮬레이션
- **DA Sell / RT Buy** 4시간 × 25 MW × 평균 +$3.7/MWh ≈ **+$370**
- **DA Buy / RT Sell** 4시간 × 25 MW × 평균 +$6.85/MWh (기대값 절대) ≈ **+$685**
- **합산 기대수익:** **+$1,055** (확률가중 기대값)
- **VaR 95% (down):** −$520 (예측 실패·한 방향 풀 노출 가정)

### 입찰 사유 & 리스크
- **Long DART (DA Buy / RT Sell, 저녁 피크):** HE18–HE21에서 RT가 DA 대비 +$9–11 더 튀는 패턴. 데이터센터 load + 솔라 ramp-down 동시 발생 시 RT가 빠르게 위쪽으로 발산. 토요일 평년 패턴 + outage stack 결합이 근거.
- **Short DART (DA Sell / RT Buy, 미드데이):** 음전환 LMP 시간대에 DA가 RT보다 덜 음수일 확률 70%+. 솔라 over-forecast 또는 풍력 추가 발현 시 RT가 추가 마이너스로 갈 가능성.
- **Risk #1:** 풍력 under-perform 시 미드데이 음전환 안 옴 → Short DART 손실. Hedge: West WIND_STWPF 실시간 모니터링.
- **Risk #2:** 데이터센터 demand response 발현 시 저녁 피크 RT 안 튐. Hedge: HE18 시점 ERCOT 60-min ahead price preview 모니터.
- **Risk #3:** AS deploy frequency 상승 시 BESS energy capacity loss → 방전 불가. Hedge: SOC ≥ 130 MWh 유지 by HE20.

---

## 3. 운용 체크리스트 (07:30 CT 제출 전)

- [ ] DAM Energy bid: HE13·HE14 charge bid −$15/MWh (deep buy), HE20·HE21 discharge bid +$45/MWh (firm sell)
- [ ] AS bid 20시간: ECRS 100 MW @ price-taker (자가 floor 옵션 −$0.10)
- [ ] DART Virtual: 8시간 × 25 MW positions (위 표대로)
- [ ] Tenaska COP submission: SOC 시퀀스 검증
- [ ] CRR 보유 포지션 확인 (NORTH↔HOUSTON 보유분 평가)
- [ ] Risk monitor 알림 셋업: West wind STWPF, RT 5-min, ERCOT outage 변동
