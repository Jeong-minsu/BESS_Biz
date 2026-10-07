# ITEM 3a — DART virtual at RVN_RN: win probability, P/L ratio, short vs long

**Window (real RVN_RN data)**: 2026-06-04 .. 2026-09-13, 102 flowdays, 2,448 hours (identical hours for all nodes).
**Convention**: `spread = DA − RT` ($/MWh). Virtual SHORT PnL = +spread, virtual LONG PnL = −spread. HE 1..24, period-ending, America/Chicago.
**System reference**: `HB_BUSAVG` (OBJECTID 10000698380, ERCOT bus-average hub) as the congestion-free "ERCOT lambda" proxy. `HB_HOUSTON` (10000697077) used as Raven's zonal hub for congestion-basis conditioning. `HB_HUBAVG` also exists but was not used.
**Data**: real Yes Energy datalake hourly DA/RT via `raw/price_panel/*.parquet`. No mock. Prices only — this is a price-based edge analysis, not fleet execution.
**Scripts**: `scripts/item3a_build_panel.py` → `scripts/item3a_dart_analysis.py` → `scripts/item3a_proxy_extension.py`.
**Data**: `derived/item3a_dart_stats.json` (dashboard: per-node hourly tables + summary + patterns + sizing), `derived/item3a_hourly_{RVN_RN,GKS_BESS_RN,HB_BUSAVG,HB_HOUSTON}.csv`, `derived/item3a_proxy_seasonal.json`, `derived/item3a_proxy_hourly_by_season.csv`, `derived/item3a_node_panel.parquet`.

"Tradeable hour" rule used throughout: |t-stat of mean spread| ≥ 1.5, EV > 0 on the best side, Kelly f > 0, and best-side loss p99 ≤ 20 × EV (a high win rate with a catastrophic tail fails this).

---

## 1. Headline — RVN_RN hourly (summer 2026, real data)

| | Short DA | Long DA |
|---|---|---|
| P(win), all hours | **56.0%** | 44.0% |
| Mean spread (EV of short) | **−0.61 $/MWh** | +0.61 $/MWh |
| Hours where side has +EV | 5 (HE16–20) | 19 |
| Typical P/L ratio | 0.4–0.7 | 1.4–2.5 |
| Loss p99 by hour | 13–45 (HE1–18), **136–303 (HE20–23)** | 5–11 (HE1–11), 13–27 (HE12–18), 39–77 (HE19–23) |

Short wins more often; long makes the money. The RVN_RN DART spread is a small positive drift punctuated by rare RT spikes — classic negatively-skewed short. The top 1% of hours carry 19% of total |PnL|; all 12 largest-|spread| hours are RT spikes (short losses), e.g. 2026-08-26 HE23 −427, 2026-09-02 HE21 −308, 2026-08-23 HE22 −276 $/MWh, and every one is a system-wide event (`sys_spread` within a few $ of the node spread).

**Hours that pass the tradeable rule: 7, all LONG — HE 3, 5, 7, 8, 9, 10, 11** (morning; DA over-prices RT, most likely the solar ramp):

| HE | P(long win) | mean win | mean loss | P/L | EV $/MWh | loss p95 / p99 | t | Kelly f |
|---|---|---|---|---|---|---|---|---|
| 3 | 0.471 | 4.16 | 2.10 | 1.98 | +0.85 | 6.4 / 8.7 | −1.50 | 0.20 |
| 5 | 0.520 | 4.27 | 2.52 | 1.70 | +1.01 | 6.5 / 9.5 | −1.57 | 0.24 |
| 7 | 0.500 | 5.43 | 2.48 | 2.19 | +1.47 | 7.1 / 10.0 | −2.15 | 0.27 |
| 8 | 0.461 | 5.22 | 2.11 | 2.47 | +1.27 | 5.0 / 5.8 | −1.97 | 0.24 |
| 9 | 0.588 | 3.26 | 1.56 | 2.09 | +1.27 | 3.7 / 4.7 | −3.21 | 0.39 |
| **10** | **0.657** | 3.38 | 2.15 | 1.57 | **+1.48** | 4.2 / 5.6 | **−3.91** | **0.44** |
| 11 | 0.569 | 4.27 | 2.69 | 1.59 | +1.27 | 6.8 / 7.2 | −2.87 | 0.30 |

(all columns from `item3a_hourly_RVN_RN.csv`.) Benign tails (p99 ≤ $10/MWh) but a small edge: the seven hours together are worth ≈ **$1.23/MWh, i.e. $8.8k over the 102-day window at 10 MW**; worst single hour at 10 MW was −$108.

**Evening peak short (HE16–20)** — P(short win) 64–72%, but P/L 0.58–0.73 and loss p99 $36–136/MWh. HE19 is the archetype: 71.6% win, EV +2.78, Kelly 0.31, yet p99 loss $57 and p99/EV = 20× → fails the tail rule. HE20–23 short: trimmed-1% mean is +2.2 to +2.8 (short "wins" 63–66% of hours) but the untrimmed mean is −1.5 to −3.4 with p99 loss $118–303. **Never short HE20–23 without an explicit spike model.**

Sanity: no hour is near 100% win; the highest is 71.6% (HE19 short). No implausible EVs — everything is within ±3.4 $/MWh.

## 2. Is DART at RVN_RN *easier* than at GKS or the system? — **No. RVN_RN is the system trade.**

Decomposition: `node spread = HB_BUSAVG spread + basis spread`. At RVN_RN in summer 2026: var(spread) 394, var(system) 438, var(basis) **22** (5%), corr(node, system) = **0.975**. Mean DA basis vs HB_HOUSTON −1.21, RT −1.11 $/MWh (Raven sits slightly *below* the Houston hub; vs BUSAVG +0.85/+0.95). Raven's congestion contributes essentially nothing to its DART spread in this window.

"Easier" defined as: (a) more tradeable hours by the rule above, (b) mean |EV| of the best side, (c) edge-to-vol |mean|/std, (d) sign stability of the best side across a first-half/second-half split, (e) in-sample best-side daily Sharpe (1 MW/HE).

| Node | tradeable hrs | mean \|EV\| best side | edge/vol | half-split stability | in-sample Sharpe | composite rank |
|---|---|---|---|---|---|---|
| HB_BUSAVG (system) | 7 | 1.18 | 0.024 | 0.750 | 0.210 | 1.8 |
| **RVN_RN** | 7 | 1.16 | 0.031 | 0.667 | 0.221 | 2.0 |
| GKS_BESS_RN | 5 | 1.18 | 0.063 | 0.667 | 0.201 | 2.2 |
| (HB_HOUSTON, ref) | 7 | 1.26 | 0.025 | 0.708 | 0.239 | — |

Ranking, easiest first: **HB_BUSAVG ≈ RVN_RN ≈ GKS_BESS_RN** — the differences are inside sampling noise (composite scores 1.8/2.0/2.2, Sharpe 0.20–0.22 for all three, the same 7 morning long hours are tradeable at RVN and the hub, 5 of the 7 at GKS). The structural difference is *what* you are trading, not how easy it is: GKS's spread is only 0.725 correlated with the system spread and its SOUTH-zone basis carries var 210 (76% of its spread variance, vs 5% at Raven) — GKS DART is substantially a congestion trade, Raven DART is a pure system trade. GKS's better edge/vol (mean −1.05 vs −0.61, std 16.7 vs 19.8) comes from that basis adding a long tilt, not from more tradeable hours. Operational conclusion for the FY2027 outlook: **do not budget a node-specific DART edge for Raven**; whatever DART is worth at Raven is what it is worth at the Houston hub. The RVN–GKS spread correlation is 0.745, so the two positions partially diversify — because of GKS's basis, not Raven's.

## 3. Short or long favoured, and is there a pattern?

**Hour-of-day (survives)**: morning LONG (HE7–11, block mean −0.94, t −4.8; HE1–6 −0.77, t −3.1) and evening-peak SHORT (HE15–20, block mean +1.06, t +1.6, P(short win) 65%) — but the evening short only "survives" if you accept the tail; by the tail rule it does not. HE21–24 block mean −2.19 is entirely spike-driven (trimmed mean positive).

**Day-of-week / weekend (does NOT survive)**: raw numbers show Wed −4.27 (t −2.1), Thu/Fri +1.5/+1.8 (t 2.4/2.8), Sun −2.58, weekend −1.73 (t −2.4). Removing the 4 largest-|spread| days (08-26 Wed, 08-23 Sun, 06-06 Sat, 09-02 Wed = 4% of days) flips Wed to +1.31, weekend to +0.36 and Sun to −0.35. Pure spike artefact; no DOW rule.

**Monthly drift (sign flips — no stable bias)**: Jun −2.00 (t −4.5, long), **Jul +2.14 (t +5.6, short)**, Aug −2.00 (t −1.9), Sep −0.92. Excluding the 4 spike days: Jun −0.99, Jul +2.14, Aug +0.89, Sep +0.81 — i.e. ex-spikes the node drifts *short* in Jul–Sep and *long* in June. Half-split best-side stability is only 16/24 hours, and a fixed "best side per HE" rule fitted on an expanding window is **negative** out-of-sample (−$13.7/day per 1 MW/HE after day 21; same at GKS −8.1 and hub −9.8). A static hourly sign rule is not tradeable within this window. **The window is summer only (Jun–mid-Sep); none of this extrapolates to winter/shoulder — see §4.**

**Congestion sign (NOT the strongest conditioner at Raven — the node is nearly congestion-free)**:
- Same-hour RT basis vs HB_HOUSTON > +0.5 (n=231): mean −4.35, P(long win) 63.6%, t −2.6 — when Raven's RT is pushed above the Houston hub, long wins, but this is only known after the fact and coincides with spike hours.
- Same-hour DA basis: no signal (< −0.5: +0.45, t 1.4; > +0.5: +0.74, t 0.2).
- Previous-day mean DA basis > +0.5 (tradeable ex-ante): mean −9.73, P(long win) 73%, t −4.7 — **but n = 96 hours = 4 days**, all containing spike evenings. Not usable; previous-day RT basis sign shows nothing (−0.36, t −0.3).
- Basis share of spread variance: 2.4% JJA, 2.7% MAM, 4.5% SON, **15% DJF** (proxy, §4). Congestion becomes relevant in winter, not summer.

**System tightness**: hub DA price bucket (forecastable at bid time): <p50 ($27) mean −0.52 (t −3.5, long); p50–90 −1.01 (t −2.6, long); p90–99 +0.79 with P(short win) **73%** but t 0.2 (tail); >p99 −1.46. Hub RT bucket (post-hoc): >p99 −116, p90–99 −7.8 — the spike states. Read: on ordinary and mid-priced DA days the morning long has a small consistent edge; on high-DA days short wins ~3 in 4 hours but a single spike evening erases weeks.

**Persistence / autocorrelation (survives, and is the only thing that does)**: daily-mean spread sign repeats **64.7%** of days vs 51.9% expected iid; daily acf(1) 0.14, acf(7) 0.16; per-HE acf(1) is 0.18–0.29 for HE9–20 and ≈0 for HE1–8/22–24. Rule backtests, 1 MW per HE, summer 2026:

| Rule | RVN_RN $/day | Sharpe | days won | worst day | GKS $/day | HB_BUSAVG $/day |
|---|---|---|---|---|---|---|
| always short | −14.5 | −0.07 | 60% | −1,292 | −25.1 | −12.1 |
| always long | +14.5 | +0.07 | 40% | −352 | +25.1 | +12.1 |
| **follow yesterday's sign per HE** | **+42.4** | **0.244** | 68% | −1,054 | +25.9 | +41.8 |
| in-sample best side per HE | +27.9 | 0.221 | 49% | −118 | +28.2 | +28.4 |
| expanding best side (OOS, after 21 d) | −13.7 | −0.09 | 43% | −973 | −8.1 | −9.8 |

Yesterday's sign predicts today's (weakly, and identically at GKS and the hub — it is a system regime effect, not a Raven effect). Caveats: 1 MW/HE with no bid-price/clearing model (a virtual bid only clears if the offer crosses DA), no DAM fees, and the worst day (−$1,054 per MW) shows the rule still eats spikes.

## 4. Multi-year seasonal extension via item2 proxy — **completed**

Proxy from `derived/item2_proxy_definition.json` (`nominated_nnls`): `LMP = −0.065 + 0.4148·CBEC_ALL + 0.5407·RBN_BESS1 + 0.0445·TAV_RN`, same weights on DA and RT. History is bounded by RBN_BESS1 (DA from 2023-12) → **proxy window 2023-12-02 .. 2026-09-13, 1,017 days, 24,405 hours** (three winters: 2023-24, 24-25, 25-26). Caveat: 41% of the blend is CBEC_ALL (SOUTH zone) — the proxy's congestion footprint is not Raven's, so the seasonal picture is reliable for the system-driven spread, indicative only for node basis.

**Validation on the real window** (proxy vs RVN_RN actual, 2026-06-04..09-13): best-side agreement **21/24 hours** (misses HE12/14/15 where the actual mean is ≈0), corr of hourly mean spreads **0.98**, MAE 0.18 $/MWh, MAE of P(short win) 0.006, long-side loss p99 matches to within $1–2 in every hour. Proxy is fit for this purpose.

**Seasonal picture (proxy, 3 years)**:

| Season | days | mean spread | std | P(short win) | hrs \|t\|≥1.5 | short-favoured hrs | Σ best-side EV/day (1 MW/HE) | basis var share |
|---|---|---|---|---|---|---|---|---|
| **DJF** | 270 | **+4.57** | 60.9 | 60.1% | 10 | **23/24** | 112 | **15%** |
| MAM | 276 | +1.38 | 49.0 | 61.6% | 6 | 15 | 53 | 3% |
| JJA | 276 | +1.24 | 41.7 | 58.8% | 11 | 11 | 44 | 2% |
| SON | 195 | −0.18 | 31.6 | 56.7% | 1 | 13 | 27 | 5% |

- **Winter is a SHORT market**: DJF short-favoured in 23/24 hours; the big edge is the morning DA premium, HE7–9 mean +11.3 / +15.7 / +14.3 $/MWh, P(short win) 64–72%, P/L 1.3–1.7, t 1.7–2.2 — with short-side loss p99 of $378 / $211 / $135 (RT spikes on cold mornings). HE10–16 short is the cleaner winter trade: EV +3 to +5, t 2.1–3.8, p99 loss $28–75. January dominates (HE7–9 +29/+39/+36).
- **Spring**: short HE17–18 (EV +4.7/+5.6, t 3.7/3.0, p99 $103/$162), HE12 (t 3.2). HE20–21 short EV +8–10 but p99 loss $730/$744 — do not.
- **Summer, 3-year**: short HE14–19 (t 2.8–5.7, P(short win) 65–74%, EV +1.8 to +7.8, p99 loss $60–83) and long HE6–8/11 (t −1.9 to −3.2, EV +0.7–1.4, p99 $10–13). HE20–22 short EV positive but t < 1 and p99 loss $286–513.
- **Autumn**: nothing tradeable (1 hour |t| ≥ 1.5); HE16–17 and HE20–21 negative means are spike-driven (p99 $378–479).
- **Summer 2026 was atypical**: JJA mean spread −0.36 (2024 +1.54, 2025 +2.54); peak HE16–20 mean +1.41 vs +7.5 (2024) and +7.0 (2025). The long tilt found in §1 on real data is a 2026 feature (more RT spike evenings, weaker DA peak premium), not a Raven feature — the proxy reproduces it exactly. **Do not carry the summer-2026 "long" conclusion into FY2027; the 3-year base rate is short-favoured in every season except SON.**
- Multi-year always-short: +$45/day per 1 MW/HE (Sharpe 0.08, worst day −$3,592); always-long −$45. Follow-yesterday-sign, all HE: **+$66/day, Sharpe 0.14, positive in every year (2024 +84, 2025 +37, 2026 +86) and every season (DJF 90, MAM 61, JJA 77, SON 26)**, worst day −$2,481. Restricted to HE9–20: +$36/day, Sharpe 0.18, positive in all years/seasons, worst day −$2,479 (SON 2024), 2026 worst −$241. Full-history per-HE acf(1): 0.20–0.44 for HE1–12 and HE23–24, ≈0.02–0.08 for HE16–21 — persistence lives in overnight/morning hours across years (winter regimes), whereas evening spikes are unpredictable from yesterday.

## 5. Sizing implication — input for `dart-virtual-trader`, not bids

Basis: quarter-Kelly of a nominal 100 MW cap, then capped so the p99 hourly loss ≤ $5,000 (a placeholder risk budget for the trader to replace). Full table in `item3a_dart_stats.json → sizing_rvn`.

- **Summer, real data**: 5–11 MW **long** in HE3, 5, 7–11 (HE9–11 ≈ 7–11 MW, HE3/5/7/8 ≈ 5–7 MW). Tails are benign (p99 $5–10/MWh → $50–110 per hour at 10 MW), so the Kelly bound binds, not the loss budget. Expected value ≈ $1.2/MWh → ~$85/day at 10 MW across the 7 hours. That is the honest size of the summer edge at this node: small.
- **Evening short HE16–19**: 0 MW by the rule. If the trader wants exposure, ≤ 4–8 MW (quarter-Kelly 1.5–7.8 MW) with the explicit acceptance that p99 loss is $36–57/MWh and 2026 produced three evenings with −$120 to −$430/MWh hours. HE20–23 short: 0 MW under any static rule.
- **Winter (proxy, forward-looking for FY2027)**: the largest EV of the year is short HE7–16 in DJF (EV +3 to +16/MWh, P(short win) 60–72%), but the HE7–9 tail (p99 $135–378) means the loss budget binds: $5k / $378 ≈ 13 MW at HE7, 24 MW at HE8, 37 MW at HE9; HE10–16 allows 67–100 MW by budget but quarter-Kelly gives ~10–15 MW. Recommend the trader treat winter as a short-biased season with a spike filter (cold-load forecast / ORDC risk) rather than a static rule.
- **Persistence overlay**: following yesterday's per-HE sign has been positive every year and season on the proxy and at both nodes in 2026; at 10 MW/HE for HE9–20 that is ≈ +$360/day on the 3-year average with a −$25k worst day. Reasonable as a tilt on top of the daily forecast, not as the whole strategy.
- **Portfolio note**: the RVN spread is 0.975 correlated with the system spread and 0.745 with GKS. A Raven position is a system position — size it as such; GKS adds a partly independent (SOUTH congestion) leg. Do not size the two nodes independently as if they were uncorrelated.

## What was not done / limitations
- No fleet-execution cross-check (`skills/estimate-bess-dart-virtual/`) — the task is price-based; the 60-day disclosure lag also means RVN_RN's own virtual awards (from June) are only partly available.
- No net-load / ORDC conditioning beyond hub price percentile (not in the price panel; would need a datalake fetch).
- No bid-price clearing model, DAM fees, or credit costs in any backtest — all PnL is "spread × MW" assuming the position clears.
- The proxy's SOUTH-zone member means winter basis behaviour (15% variance share) is not Raven's; a Houston-only proxy (item2's `nominated_houston_only_ols`) could be swapped in if node-specific winter congestion becomes the question.
