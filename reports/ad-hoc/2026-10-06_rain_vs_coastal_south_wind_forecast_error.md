# 비가 오면 Coastal/South 풍력 actual이 forecast 대비 줄어드는가 — 가설 검증

**작성**: 2026-10-06 | **기간**: 2024-01-01 ~ 2026-09-30 (1,004일, 시간별 24,085행/지역) | **데이터**: 전부 실데이터 (mock 없음)

## 결론

| 지역 | 가설 | 비 오는 시간 오차 | 마른 시간 오차 | 차이 (day-block bootstrap 95% CI) |
|---|---|---|---|---|
| **Coastal** | **지지** | −4.9% of cap (−164 MW, 2026) | −3.0% (−88 MW) | **−1.9pp [−3.6, −0.4]** 유의 |
| **South** | **기각** | −1.3% | −1.3% | −0.0pp [−2.1, +1.8] 무효과 |

- Coastal은 비가 오는 시간에 actual이 forecast보다 **추가로 약 75~80 MW(cap의 약 2pp) 더 모자라고**, 오차 분산도 커진다 (MAE 9.2 → 13.2% of cap). 일 단위(일 강수 ≥ 0.10 in)로 봐도 같은 방향·같은 크기 [−3.3, −0.3].
- 단, **Coastal은 비와 무관하게 STWPF가 구조적으로 과대예측**(마른 시간도 평균 −3.0%, 60%가 음수). 비는 이 기본 편향 위에 얹히는 추가 효과다.
- South는 비 유무로 평균 차이가 없다. 2026년엔 오히려 비 오는 시간이 +69 MW로 양(+).

## 메커니즘 — "비"가 아니라 "비 + 약한 바람" 조합

관측소 풍속(station wind speed) 사분위로 층화하면 Coastal 효과가 선명히 갈린다 (2025–26, MW 평균 오차):

| 관측 풍속 | 마른 시간 | 비 오는 시간 | bootstrap diff (전체 기간, pp) |
|---|---|---|---|
| q1 (약풍) | −9 | **−123** | −2.6 [−5.1, −0.6] |
| q2 | −36 | **−224** | −3.2 [−5.3, −1.3] |
| q3 | −62 | **−138** | −3.1 [−4.9, −1.1] |
| q4 (강풍) | −308 | −155 | **+3.0 [−0.1, +6.2]** (역전) |

- 약·중풍에 비가 오면 (해상 층운형 강수, 대류성 소나기 등 바람 없는 비) actual이 크게 빠진다.
- 강풍에 비가 오면 (전선 통과, 폭풍) 오히려 예측보다 덜 빠진다. 즉 "비 → 풍력 감소"는 **약풍 regime에서만** 성립.
- 강수 강도별로는 단조 증가가 아니다. **trace(<0.03 in/h)가 −5.3%로 가장 크고** 0.03–0.10 in은 −2.6%. 효과를 만드는 건 강수량이 아니라 "비가 오는 기상 상태"다.

## 계절·시간대·예측수준별 (Coastal, 비 − 마른 시간 차이)

| 층 | diff (pp) | 95% CI | 판정 |
|---|---|---|---|
| JJA | −3.9 | [−6.9, −1.2] | 유의 |
| SON | −3.9 | [−6.4, −1.1] | 유의 |
| DJF | −2.2 | [−5.5, +1.0] | 방향 같으나 미달 |
| MAM | +2.6 | [−1.0, +5.9] | **역전** (봄은 마른 날도 −7.3%로 이미 크게 과대예측) |
| fc 중위 tercile | −2.9 | [−5.2, −0.3] | 유의 |
| fc 상위 tercile | −2.1 | [−4.6, +0.2] | 경계 (상위는 마른 날도 −9.5%) |
| fc 하위 tercile | +1.5 | [−0.4, +3.6] | 무효과 (바닥 효과) |
| 시간대 | HE1–6 −2.4, HE7–12 −1.3, HE13–18 −0.9, HE19–24 −1.9 | 모두 CI가 0 포함 | 시간대 차이 없음 |
| 연도 | 2024 −2.3, 2025 −1.2, 2026 −2.2 | 각각 CI 0 포함 | 3년 모두 같은 방향 (합치면 유의) |

South는 모든 층에서 CI가 0을 포함하거나 양(+)이다 (MAM +4.6 [+0.7, +7.8], HE13–18 +2.4 [+0.4, +4.6]). 비 오는 시간의 평균 예측치 자체가 낮아(35.8% vs 46.3% of cap) 예측이 이미 비를 반영하고 있을 가능성이 있다.

## 트레이딩 함의

- **Coastal 풍력 forecast를 쓰는 D+1 view에서, 약·중풍 + 강수 예보 시간대는 STWPF에서 cap의 2~3%(약 80~120 MW)를 추가 차감**하는 것이 통계적으로 정당하다. 여름·가을에 가장 강하고, 봄엔 적용하지 않는다.
- 강풍 + 비(전선)는 차감하지 말 것. 오히려 과대예측이 덜하다.
- South는 비 조정을 하지 않는다.
- 효과 크기(80~120 MW)는 ERCOT 시스템 풍력 오차(MAE 약 1,000~1,800 MW) 대비 작다. **시스템 net load view를 바꿀 크기는 아니고, Coastal 지역 basis / Houston-South 혼잡 관점의 미세 조정**에 적합하다.

## 방법

- forecast: Yes Energy datalake `ercot/vintage/wind_stwpf/`, D−1 13:59 GMT 이하 최신 vintage (leakage-free, DAM 마감 이전). GR_COASTAL(10004189446), GR_SOUTH(10004189447).
- actual: datalake `ercot/gen/wind_rti/` 같은 OBJECTID.
- 정규화: `err_pct = (actual − forecast) / cap`, cap = 해당 지역 시간별 actual의 중심 60일 rolling max (fleet 성장 보정; Coastal 3.56→3.78 GW, South 2.82→3.34 GW).
- 강수: AG2 `GetHistoricalObservations` HISTORICAL_HOURLY_OBSERVED, precipitation + windSpeed. Coastal = KCRP·KVCT·KIAH, South = KBRO·KLRD (**KMFE는 구독에 없음**). AG2 시각은 local standard(CST 고정)·hour-beginning → CPT hour-ending으로 변환. 관측 풍속 vs actual 발전 상관으로 lag 스캔 결과 +1h가 최적 (0.764→0.757 수준, 차이 미미).
- rain_any = 지역 관측소 중 1곳 이상 ≥0.005 in/h. Coastal 전체 시간의 8.0%, South 4.3%. rainy_day = 일 강수 관측소 평균 ≥ 0.10 in (Coastal 18.5%, South 9.9%의 날).
- 통계: 일 단위 block bootstrap 1,000회 (층화 400회), 평균 차이의 2.5/50/97.5 percentile.

## 한계

- 공항 point 관측으로 풍력단지 강수를 대리. Coastal 단지(Kenedy·Willacy·Nueces·San Patricio)는 KCRP가 가깝지만 KIAH는 멀다. South 단지(Webb·Starr·Zapata)는 KLRD 한 곳에 사실상 의존.
- "비 때문에 actual이 줄었다"와 "비 오는 기상 상태를 STWPF가 과대예측한다"는 같은 데이터로 구분 불가. 트레이딩 용도로는 어느 쪽이든 동일.
- 강우 강도 bin 상위(>0.30 in/h)는 n=52로 노이즈.

## 산출물

- `shared/data/adhoc/2026-10-06_rain-wind-error/scripts/{fetch.py,analyze.py}`
- `raw/{wind_fc,wind_act,precip}.parquet`, `raw/ag2_raw/*.csv`
- `derived/panel.parquet` (시간별 merge 패널), `derived/results.json` (전체 통계)
