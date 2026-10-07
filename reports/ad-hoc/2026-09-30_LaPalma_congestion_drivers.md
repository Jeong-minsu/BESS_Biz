# La Palma congestion — 트리거·발생조건 분석 (2026-09-30)

**데이터**: Yes Energy Datalake 실데이터 (mock 없음) — DA/RT constraint (2024-07-03 ~ 2026-09-30), market shift factor, 송전 outage 스냅샷(HE13/HE18), WZ_Southern load, GR_SOUTH/COASTAL wind, SouthEast solar, Brownsville(KBRO) 기온, 60-day SMNE 발전기 출력(~2026-08-01).
**코드/산출물**: `shared/data/adhoc/2026-09-30_lapalma-congestion/{scripts,raw,derived}`

---

## 0. 결론 요약

1. **"최근 강하게 발생하는 La Palma congestion" = `LA_PALMA_XF1A / XF1B` (La Palma 345/138kV 변압기 뱅크)**. 기존 단골이던 HAINE__LA_PAL1_1(138 line)과는 **다른 constraint**다. 2026-08 이전에는 사실상 binding 이력이 없었다.
   - 9월 한 달 GKS 영향(−SF×λ 누적): **DA +$4.8k/MW, RT +$13.7k/MW**. RT는 **9/22 ($5,251 base-case cap)**와 **9/28 ($4,500 contingency cap)** 두 날이 대부분이다.
   - GKS SF = **−0.31 ~ −0.37**. 이 constraint가 걸리면 GKS LMP가 오르므로 **방전에 유리**하다. HAINE의 |SF| 0.03보다 10배 이상 크다.
2. **트리거는 날씨가 아니라 계통 토폴로지(outage/신규 선로) 변화다.**
   - 8월은 9월보다 더 더웠고(HE16-20 load 6.8GW, 93°F) 풍력도 비슷했다. 그런데 binding은 8%에 그쳤다.
   - **9/17 이후에는 HE10–21 binding 확률이 77–100%**다. 이 구간 안에서는 load·기온·풍력·일사 구간과 무관하게 binding이 ~95–100%다. 즉 regime switch다.
3. **Regime을 만든 요소** (시점이 일치함; ERCOT network model이 없어 인과는 추정):
   - 구조적 배경:
     - ① **Silas Ray CC1(Brownsville, SF −0.44)이 2025-09 이후 출력 0**이다. Cameron County 로컬 발전이 사라졌다.
     - ② **신규 Kingfisher 345 루프**가 2026-06-27~30에 가압됐다. 이때부터 `MKNGSTE5`(Kingfisher–Stewart Road 345 N-1) contingency가 **7/30 처음 등장**했고, 이것이 XF의 지배 contingency다.
     - ③ **La Palma 345 bus 작업과 La Palma–Kingfisher 345 outage**(2/4부터, 종료 예정 **12/10**)로 La Palma 345측 구성이 축소돼 있다.
   - 9/17 점화: **Ajo–Reforzar 345 복선이 복귀**했다(2025-12-06부터 강제정지, 9/16 마지막). 복귀 다음 날부터 XF가 매일 binding한다.
   - 9/21 이후 증폭:
     - **La Palma–Kelvin 138 + La Palma 138 breaker 7340/7510이 계획정지** 중이다(9/21~**10/09**).
     - **Cruce–Reforzar 345 복선이 계획정지** 중이다(9/23~**11/10**).
     - **Stewart Road ST1 변압기가 강제정지**됐다(9/22~25). 9/22에는 XF1A가 **base case**로 전환되며 limit이 625에서 210–540MW로 깎였고 $5,251 cap을 찍었다.
4. **언제 걸리나**
   - DA는 **HE10–21**(peak HE16–19)에 걸린다.
   - RT 스파이크는 **HE16–20**, 해가 지며 로컬 solar가 빠지는데 Valley 부하는 6.5GW로 유지되는 시간대다.
   - RT binding 7일은 **전부 평일**이었고 주말 4일은 0건이었다(표본 작음).
   - 전망:
     - La Palma–Kelvin 138이 복귀하는 **10/9까지는 매일 binding이 기본값**이다.
     - 이후에도 La Palma 345 작업(~12/10), Cruce–Reforzar(~11/10), Delsol–Frontera(~10/20)가 남아 있어 **risk가 이어진다**. 다만 10월 냉각으로 Valley load가 내려가면 빈도와 강도는 줄 것으로 예상한다.

---

## 1. La Palma 계열 constraint 식별

| Constraint | 설비 | 지배 contingency | 활성 시기 | GKS SF | 성격 |
|---|---|---|---|---|---|
| **LA_PALMA_XF1A / XF1B** | La Palma 345/138 autotransformer (limit RT 625 / 676 MW) | **MKNGSTE5** (Kingfisher–Stewart 345), 9/22는 BASE CASE | **2026-08 ~ 현재 (9/17부터 급증)** | **−0.31 / −0.36** | 345 → 138 **import** 병목 (Valley 138 load pocket 공급) |
| HAINE__LA_PAL1_1 | La Palma–Haine Dr 138 line | MHARNED5 (Harlingen–N.Edinburg 345), SRAYRI38 | 2024-07 ~ (겨울·봄 강함) | −0.02 ~ −0.03 | 로컬 재생에너지 주입이 138에 과부하 |
| LA_PAL_VCAVAZ1_1 | La Palma–Villa Cavazos 138 | SSTILOM8 | 2025-09 ~ (Silas Ray 이탈 후) | ≈0 | Brownsville 쪽 load serving |

**XF 방향성 (all-node SF)**:
- Valley 전 노드의 SF가 음수다 = 주입하면 완화된다.
  - 1군 −0.43~−0.54: Laureles BESS, Los Fresnos ESR, Vancourt, Nebula, Mesquite, E Harris, W Harlingen ESR, Harlingen, **Silas Ray**, Olmito.
  - 2군 −0.21~−0.31: **GKS**, Frontera, Duke/Hidalgo, NEDIN, Falcon, **Railroad DC tie**.
- 북쪽 Kenedy/Willacy 풍력(Baffin, Peñascal, El Sauz, Las Majadas 등)만 +0.02~0.10으로 소폭 악화 방향이다.
- 따라서 이 constraint는 **Valley 순수요 − 로컬 공급 = 345에서 끌어오는 import** 병목이다.

## 2. 월별 binding 이력 (DA hrs / RT hrs)

| 월 | XF1A+XF1B DA | XF RT | HAINE DA | HAINE RT | VCAVAZ DA |
|---|---|---|---|---|---|
| 2026-05 | 14 | 0 | 27 | 10 | 145 |
| 2026-06 | 8 | 0 | 100 | 22 | 117 |
| 2026-07 | 1 | 0 | 62 | 9 | 214 |
| 2026-08 | 52 | 0 | 64 | 44 | 164 |
| **2026-09** | **215 ($12.9k λ합)** | **39 ($35k)** | 124 | 35 | 52 |

- XF1A/B는 2025-05 이후 연간 1–14시간 수준이었다. **2026-08에 신규 등장했고 9월에 폭증**했다.

## 3. 트리거 분석

### 3-1. 날씨·부하 lens — 트리거 아님 (regime 내 판별력 없음)
HE12-21 기준 P(binding):

| 구간 | 8/1–9/16 | 9/17–9/30 |
|---|---|---|
| South load 6.6–6.9 GW | 14% | 100% |
| KBRO 기온 >93°F | 20% | 98% |
| GR_SOUTH wind <800 MW | **38%** | 99% |
| GR_SOUTH wind >2.5 GW | **0%** | 86% |
| HE16-20 평균 load / 기온 | 8월 6.8GW / 93°F → **8%** | 6.6GW / 91°F → **98%** |

- **9/17 이전**의 산발 binding(6%)은 **HE12–15 + 남부 풍력 약할 때**(<800MW)에 집중됐다.
- **9/17 이후**에는 날씨와 무관하게 매일 걸린다. 오히려 8월이 더 덥고 부하가 높았다.

### 3-2. 송전 outage lens — 핵심 트리거
일별 XF binding과 Valley 주요 설비 상태 대조 (`derived/key_outage_timeline.csv`):

| 시점 | 이벤트 | XF 반응 |
|---|---|---|
| 2025-09 | Silas Ray CC1 출력 0 (SMNE) | VCAVAZ binding 시작. 이후 Cameron County 로컬 발전 공백 |
| 2026-02-04 ~ 12/10 | La Palma 345 bus 장비 (T011N*, PS23/24) outage | 345측 구성 축소 (배경) |
| 2026-06-27~30 | Kingfisher–Stewart / NEDIN–Kingfisher 345 가압 (outage 해제) | 7/30 `MKNGSTE5` 첫 등장 → 8/1 XF DA 첫 binding |
| 2026-06-28 ~ 12/10 | **La Palma–Kingfisher 345 강제정지 지속** | 신규 루프가 La Palma에 직결되지 않은 상태 |
| **2026-09-17** | **Ajo–Reforzar 345 복선 복귀** (2025-12부터 정지) | **다음 날부터 매일 DA 8–21 hr binding** |
| 2026-09-21 ~ 10/09 | **La Palma–Kelvin 138 + La Palma 138 breaker 계획정지** | 9/21 XF1B RT 첫 binding, DA λ 상승 |
| 2026-09-22 ~ 25 | **Stewart Road ST1 XFMR + Progreso–Stewart 69 강제정지** | **9/22 XF1A BASE CASE, limit 210–540MW, $5,251 cap (HE16–20)** |
| 2026-09-23 ~ 11/10 | Cruce–Reforzar 345 복선 계획정지 | 9/24 DA 급등 (GKS DA +$1,989/MW-day) |

- 해석: Ajo–Reforzar 복귀로 북쪽 345 import 경로가 열렸다. 그러면 SCED는 Valley 로컬 가스(Frontera/Duke/NEDIN, 2군 relief) 대신 import를 늘린다. Silas Ray가 빠진 Cameron 138 pocket은 그 전력을 **La Palma 345/138 변압기로 받는다**. 이 상태에서 Kingfisher–Stewart 345(N-1)가 끊기면 XF가 과부하되는 구조다.
- 한계: ERCOT CRR network model(contingency membership)이 없다. 따라서 위 인과는 **시점 일치 + SF 방향**에 근거한 추정이다.

### 3-3. 발전소 outage lens
- **Silas Ray CC1**: 2024년 월평균 9–15MW에서 **2025-09 이후 0**(SILAS_10만 0–10MW)으로 떨어졌다. XF·VCAVAZ의 구조적 배경이다.
- **Frontera**: Delsol–Frontera 345와 Frontera 변압기가 2026-05-08부터 강제정지(~10/20)다. 그래도 출력은 유지됐다(8월 452MW, 138 경유 추정).
- Duke/Hidalgo와 NEDIN CC는 정상 가동이다(8월 474/291MW).
- 한계: 60-day 공시라 **8/1 이후 unit 출력은 미확인**이다. 9월 regime의 발전기 측면은 검증하지 못했다.

### 3-4. RT 스파이크(강도) 조건 — regime 안에서
- RT binding 7일(9/17, 21, 22, 23, 25, 28, 29)은 **전부 평일**이다. 주말 4일(9/19, 20, 26, 27)은 풍력이 낮고 순수요가 높았는데도 RT 0건이었다.
- Cap 2일:
  - 9/22는 추가 로컬 outage(Stewart ST1)로 base-case limit 축소가 원인이다.
  - 9/28(월)은 contingency limit 625MW에서 HE16–19 동안 지속됐다.
- 일별 지역 날씨와 RT λ의 상관은 약하다(n=13). 강도는 **추가 138/69 outage와 평일 load 형태**가 좌우하는 것으로 보인다.

## 4. 시간대 패턴 (9/17 이후, XF 합산)

| HE | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P(binding) | .77 | .92 | .92 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | .92 | .85 | .69 |
| GKS DA MCC $/MWh | 1 | 3 | 5 | 9 | 18 | 28 | 41 | 53 | 56 | 54 | 39 | 28 | 10 |
| GKS RT MCC $/MWh | 0 | 0 | 0 | 1 | 6 | 10 | 53 | **163** | **276** | **255** | **174** | 60 | 1 |

## 5. GKS 시사점 (신호만 — 입찰·포지션 결정은 bess-optimizer / dart-virtual-trader 영역)

- **LMP 레벨**: XF가 걸리면 GKS LMP가 **+SF×λ(λ×0.31~0.37)**만큼 오른다. HE16–20 방전 가치를 크게 올리는 요인이다. λ $4,500이면 GKS에 +$1,400~1,650/MWh가 더해진다.
- **DART 성향**:
  - 평소 날에는 **DA에만 congestion이 반영되고 RT는 안 걸린다** → DA>RT, short-lean (예: 9/24 DA +$1,989/MW-day, RT 0).
  - 평일 RT cap이 터지는 날은 **극단적 RT>DA** → long tail.
  - 즉 E_PASP·HAINE과 같은 "만성 DA binding은 short, 드문 RT scarcity는 long" 패턴이다. RT 누적 $의 90% 이상이 cap 2일에서 나왔다.
- **HAINE**(겨울·봄 오후, 풍력·태양광 많을 때)과 **VCAVAZ**(여름 폭염, 저풍력 한낮)는 GKS |SF|가 작다(≤0.03). GKS 가격 영향은 미미하다.

## 6. 발생 가능성 전망 (Watch list)

| 기간 | XF binding 가능성 | 근거 |
|---|---|---|
| ~10/09 | **매우 높음 (DA 매일 HE10–21), 평일 HE16–20 RT spike risk** | La Palma–Kelvin 138 + La Palma 138 breaker 정지 지속, Ajo–Reforzar in-service |
| 10/10 ~ 11/10 | 높음→중간 | Cruce–Reforzar 정지(~11/10), Delsol–Frontera(~10/20), La Palma 345 작업(~12/10). 10월 냉각으로 Valley load 하락 |
| ~12/10 이후 | La Palma–Kingfisher 345 복귀 효과 **방향 미정** | 345 infeed가 추가돼 XF 분담이 늘 수도, loop 강화로 완화될 수도 있음. 복귀 직후 재평가 필요 |
| 11월~3월 | HAINE regime 복귀 | 과거 2년 겨울·봄 HE12–19 binding 60–100%. 풍력 ≥2.5GW에서 51% |

**Daily 체크 트리거 (당일 ERCOT outage file)**:
- (a) La Palma / Kelvin / Stewart / Reforzar / Kingfisher 관련 138·345 신규 outage
- (b) Valley 138 변압기 강제정지 (Stewart ST1 사례처럼 base-case 전환과 cap을 유발)
- (c) 평일 + HE16–20 + GR_SOUTH wind 저조

## 7. 한계
- Contingency → 요소 매핑(ERCOT CRR NMMS)이 없어 "Ajo–Reforzar 복귀 → XF 폭증" 인과는 확정하지 못했다.
- 새 regime 표본은 14일뿐이다. 요일 효과는 가설 수준이다.
- 8/1 이후 unit 출력과 Valley BESS(ESR) 동작은 60-day 공시 지연으로 미반영이다.
- 9/30 outage는 부분 스냅샷이다.
