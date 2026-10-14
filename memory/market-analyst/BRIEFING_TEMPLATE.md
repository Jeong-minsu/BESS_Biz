# BRIEFING_TEMPLATE.md — market-analyst canonical format
# Created: 2026-09-28 (W39 session — 9th consecutive attempt, finally persisted)
# Purpose: Structural anchor for daily 5-6 bullet briefings; DEGRADED fallback language; format standards

---

## 1. Standard Briefing Header

```
# ERCOT D+1 (YYYY-MM-DD) Market Briefing
**Data quality**: [PRODUCTION | PARTIAL | DEGRADED]
**Tyba**: [OPERATIONAL | DEGRADED — fetch failed / empty file]
**Filed**: YYYY-MM-DD HH:MM CT
```

---

## 2. Canonical Section Structure (5-6 bullets)

### Section A — Headline
One-sentence view: weather driver + key generation theme + price regime.
Example: "Moderate load + strong GR_WEST wind → midday duck extreme, HE19-20 spike risk elevated; DA $55-65 range."

### Section B — Demand & Supply
- Load: WZ_ERCOT BIDCLOSE 24h avg N MW; peak HE N MW (vs prior day ±N MW)
- Net load: 24h avg N MW; ramp HE18→HE20 N→N MW (+N MW in 2h)
- Duck curve severity: NL trough HE N = N MW
  - SEVERE threshold: NL trough ≤ 25,000 MW
  - EXTREME threshold: NL trough ≤ 22,000 MW
  - Scarcity Cliff threshold: NL ≥ 60,000 MW (evening ramp into scarcity ORDC)
- Cap-out: ERCOT TOTAL_RESOURCE_CAP_OUT 24h avg N MW (MORA 2026 baseline: 6,911 MW)

### Section C — Renewable Supply
- Solar: ERCOT SOLAR_COPHSL_BIDCLOSE peak N MW (HE N); 24h avg N MW
- Wind: ERCOT WIND_COPHSL_BIDCLOSE 24h avg N MW
  - GR_WEST STWPF: N MW avg (SCI assessment: LOW / MEDIUM / HIGH binding probability)
  - GR_NORTH COPHSL: N MW avg
  - GR_COASTAL STWPF: N MW avg
  - GR_SOUTH STWPF: N MW avg

### Section D — Price View
- DA Energy: 24h avg $N/MWh; peak HE N ($N), HE N ($N); off-peak HE N ($N)
- RT outlook: RT_LMP P50 HE18-20 = $N, P(DA<RT) = N% (Tyba; direct RT spike probability not provided) or [DEGRADED — heuristic]
- Spread: DA − RT = +$N (DA premium) or −$N (RT premium expected HE N-N)
- AS: RRS DA $N; ECRS DA $N; Non-spin DA $N (or DEGRADED — heuristic only)

### Section E — AG2 / Enverus vs Yes Energy Gap
- AG2 WSI load vs Yes Energy BIDCLOSE: N MW gap (+/- direction)
- Enverus STPF load vs Yes Energy BIDCLOSE: N MW gap
- Which source was more accurate in last week's analog: [source]
- Implication: [upside/downside load risk for price]

### Section F — Risks / Watch Items
- (2-3 bullet items) specific to the day: outage returns, weather extremes, GR_WEST near-zero, special events

---

## 3. DEGRADED Fallback Language

When Tyba is unavailable (`shared/data/raw/tyba/{D+1}_GKS_forecast.csv` missing or empty — Tyba fetch failure), use this standard block in Section D:

```
**[DEGRADED — Tyba forecast fetch failed / file empty]**
DA/RT price forecasts, P(DA>RT), and DA AS prices from Tyba are UNAVAILABLE.
Price estimates below are heuristic-only, derived from Yes Energy BidClose + prior-day RT analog.
Accuracy: ±$20-30/MWh for peak hours; ±$5-10/MWh for off-peak. Do not use for DA bid sizing.
```

---

## 4. Data Source Priority (Spread Sign Convention)

**Spread convention**: `spread = DA − RT`.
- Positive spread (DA > RT) → DA expensive → signal: short DA / long RT
- Negative spread (DA < RT) → RT expensive → signal: long DA / short RT

**Source priority**:
1. Yes Energy BIDCLOSE — PRODUCTION if fetch succeeds
2. Enverus STPF — PRODUCTION if fetch succeeds (secondary)
3. AG2 WSI Trader — PRODUCTION if endpoint available
4. Tyba — PRODUCTION if fetch succeeds (replaced Smartbidder, 2026-10)
5. Heuristic/analog — DEGRADED, clearly labeled

---

## 5. Key Thresholds Reference

| Metric | Threshold | Significance |
|---|---|---|
| NL trough (duck curve) | ≤ 25,000 MW | SEVERE duck — midday price suppression likely |
| NL trough (duck curve) | ≤ 22,000 MW | EXTREME duck — curtailment / negative price risk |
| Evening net load | ≥ 60,000 MW | Scarcity Cliff — ORDC adder elevated |
| Cap-out vs MORA baseline | > 6,911 MW | Elevated forced outage — tight reserve margin |
| GR_WEST STWPF | < 2,000 MW | HIGH SCI probability — West Hub congestion |
| GR_WEST STWPF | 2,000–6,000 MW | MEDIUM SCI probability |
| GR_WEST STWPF | > 6,000 MW | LOW SCI probability |
| ERCOT wind 24h avg | < 8,000 MW | Low wind day — net load elevated; RT spike risk high |

---

## 6. Self-Review Anchor (Daily)

At session close, record in `memory/market-analyst/learnings/YYYY-MM-DD.md`:
1. My DA avg forecast vs actual (MAE)
2. My peak HE vs actual peak HE
3. Enverus / AG2 / Yes Energy — which was closest to actuals
4. Risk items flagged: occurred / did not occur
5. One structural note to carry forward
