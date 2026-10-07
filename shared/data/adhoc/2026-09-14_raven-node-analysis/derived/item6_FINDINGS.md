# ITEM 6 — DART virtual at RVN_RN: is there a regime- or congestion-*conditional* edge?

**Question**: item3a's unconditional edge is thin (7 morning LONG hours, ≈ $1.23/MWh). Does conditioning on market regime or on congestion state make DART virtual at Raven materially better — *ex-ante*, out-of-sample, after multiple-testing correction?

**Short answer: No.** 4,394 hypotheses were tested. Nothing that is strictly usable at the 10:00 CT D-1 bid cutoff beats the unconditional hour-of-day rule on out-of-sample EV/MWh. Two things look real but are small: (1) constraint bind state is strongly persistent day to day, so congestion *is* forecastable, and a strict-ex-ante "short HE14–18 when STPWAP39_1 bound in DA two days ago" rule earns +1.07 $/MWh on the 3-year test window (t 2.7) with a higher hit rate and half the drawdown of the static afternoon short — but the static afternoon short earns +1.32 on the same hours, so the condition improves risk, not EV. (2) Two-thirds of item3a's "follow yesterday's sign" edge was look-ahead leakage: with the strictly-known D-2 sign it drops from +2.76 to +0.90 $/MWh (3-yr) and from +1.77 to −0.10 on the real 2026 window.

**Data**: real only. RVN_RN own DA/RT 2026-06-04..09-13 (102 days, 2,448 h); item2 NNLS proxy 2023-12-02..2026-06-03 (SOUTH-zone member ⇒ pre-2026 *basis* conclusions are indicative only, flagged where relevant). Congestion at the Raven location from `item2_congestion_hourly_panel.parquet` (−SF×λ, proxy SFs pre-2026). System load / wind / solar actuals fetched from the datalake (`raw/item6_fundamentals.parquet`, 24,429 h, ≤7 missing). `spread = DA − RT`; short PnL = +spread. PnL is spread × 1 MW per traded hour, no clearing model or fees (same as item3a).

**Splits**: REAL — train 2026-06-04..07-31 (58 d), test 08-01..09-13 (44 d). FULL — train 2023-12-02..2025-08-31, test 2025-09-01..2026-09-13 (378 d, contains the real window). All thresholds / hour sets fitted on train only.

**Availability classes** (relative to the 10:00 CT D-1 cutoff), used throughout:
- `ex_ante_lag2` — built from D-2: **strictly known**.
- `ex_ante_lag1` — built from the full D-1 day (item3a convention). At 10:00 on D-1, HE11–24 of D-1 have not happened. **Mildly leaky; upper bound.**
- `needs_fc` — same-day DA price level/shape, load, wind, solar. DA clears ~13:30 D-1, after the cutoff; only usable via a forecast. **Upper bound.**
- `ex_post` — same-day RT. Diagnostic only.

Scripts: `scripts/item6_fetch_fundamentals.py` → `item6_build_panel.py` → `item6_regime.py`, `item6_congestion.py`, `item6_rules.py` → `item6_dashboard_payload.py`. Dashboard JSON: `derived/item6_dashboard.json`.

---

## 1. Regime-conditioned hourly edge (Deliverable 1)

13 daily regime variables (terciles on train) × 24 HE, plus 5 HE-blocks, plus season (3-yr proxy). Two test families per window: **separation** (Kruskal-Wallis across terciles: does the regime move the hourly spread at all?) and **within-regime edge** (one-sample t of the conditional mean). BH at FDR 10% within each family.

### 1a. Which variables actually separate the hourly spread?

| feature | class | FULL (3-yr): HEs with BH-sig separation /24 | REAL (2026): /24 |
|---|---|---|---|
| same-day RT level / RT max | ex_post | 24 / 24 | 11 / 5 |
| **spread_mean_lag1** (yesterday's mean spread) | ex_ante_lag1 (leaky) | **24** | 3 |
| **spread_mean_lag2** (D-2 mean spread) | **ex_ante_lag2 (strict)** | **1** | **0** |
| season | known | 17 | — |
| same-day RT vol | ex_post | 16 | 3 |
| DA shape (peak − offpeak) | needs_fc | 14 | 2 |
| net-load max / DA level / wind / load / solar | needs_fc | 10–13 | 0–6 |
| rt_max_lag2 / rt_vol_lag2 | ex_ante_lag2 | 6 / 2 | 0 / 0 |
| rt_max_lag1 / rt_vol_lag1 / mcc_abs_lag1 | ex_ante_lag1 | 3–5 | 0–3 |

Read: **the strictly-ex-ante regime variables carry almost no hour-level information.** Everything that separates well is either not known at bid time (same-day RT, same-day DA level) or is the leaky D-1 spread. The collapse of `spread_mean_lag1` (24/24) → `spread_mean_lag2` (1/24) is the key result of this section: the day-to-day persistence item3a found is dominated by D-1 hours that are *after* the cutoff.

Tally, regime families: separation 1,015 tests (BH survivors 384; of the strict-lag2 ones, FULL has 9 HE-level + 7 block-level, REAL has 0 HE-level + 10 block-level); within-regime edge 3,074 tests (BH 641). Full table: `item6_regime_separation.csv`, `item6_regime_hourly.csv`.

### 1b. The cells that looked best on the real window, and why they are not an edge

The strongest REAL cells were all the same story: **after a volatile / spiky day (rt_vol or rt_max D-1 or D-2 in the top tercile), the morning long (HE7–11) is bigger** — block mean −1.74 (t −4.96, n 255 h) for `rt_vol_lag2 high`, vs −0.94 unconditional. Similar cells: `rt_max_lag1 high` HE10 (t −4.24), `wind_mean low` HE9–11 (needs_fc, t −3.2 to −4.0).

Three checks kill it:
1. **Permutation null.** Re-assigning the regime labels across days at random (300 permutations, hour structure preserved) and taking the largest |t| across all 936 regime×HE cells gives a median max-|t| of **4.15** (p90 5.0). The observed maximum is **4.35 → family-wise p = 0.35**. The REAL-window regime search is indistinguishable from selection on noise. (`item6_permutation_null.json`)
2. **Out-of-sample it does not beat the static rule.** REAL test window: `R_long_HE7-11_if_rt_vol_lag2_high` EV +1.52 $/MWh on 160 h; the unconditional `B_long_HE7-11_static` EV **+1.75** on 220 h. Same for rt_max_lag2 (+1.44) and rt_vol_lag1 (+1.71). Train→test shrinkage of the regime rules averaged 17% (2.50 → 2.08) — modest, but the filter simply drops hours without raising EV per hour beyond noise.
3. **The sign flips by season.** On the 3-yr proxy the *same* condition (rt_vol_lag2 high, HE7–11) has EV of the LONG side of **−53 (DJF 2024), −7 (DJF 2025), −44 (DJF 2026)**, +0.9/+0.4/+3.5 in JJA. A volatile day in winter precedes a DA *premium* (short wins); in summer 2026 it preceded a DA discount. So the summer-2026 finding is a summer-2026 regime feature, not a Raven rule.

Season itself is the only "known-in-advance" regime that separates (17/24 HE) — already documented in item3a §4 (DJF short 23/24 hours). Nothing here changes that.

### 1c. Leakage in the persistence rule (item3a §3 correction)

| rule | REAL 2026 EV $/MWh (all 102 d) | FULL 3-yr EV | FULL test (378 d) EV / Sharpe·day |
|---|---|---|---|
| follow yesterday's sign per HE, **lag1 (leaky)** | +1.77 | +2.76 | +3.01 / 0.12 |
| follow yesterday's sign per HE, **lag2 (strict)** | **−0.10** | **+0.90** | +0.63 / 0.04 |
| same, HE9–20 only, lag1 / lag2 | +2.57 / +0.16 | +3.00 / +1.17 | +2.54 / +1.28 (Sharpe 0.21 / 0.08) |

**67% of the lag-1 edge on the 3-yr panel and 100% of it on the 2026 window came from D-1 hours not known at the cutoff.** The strict version is still positive on the 3-yr panel (+0.9; positive in 10 of 14 year-seasons, negatives SON-2024 −0.29, MAM-2025 −0.06, DJF-2025 −0.34, JJA-2026 −0.48) but with Sharpe 0.04/day and a −$5.9k/MW max drawdown it is a tilt, not a strategy. item3a's "+$42/day" should be read as "+$14/day at best, ≈0 in 2026" if implemented honestly (or implemented with a D-1 HE1–9 partial-day signal, not tested here).

---

## 2. Congestion-conditioned edge (Deliverable 2)

24 constraints tracked: item2 top-10 (3-yr) + the real-window top-12 + next-in-rank (WESTEX, ARROZ_EL_CAM1_1, 421__A, FORTMA_YELWJC1_1). Bind = DA λ > 0 at that hour (RT: λ > 0 in any SCED interval). Panel-hour alignment verified empirically: hour-ending gives corr(MCC_DA, DA basis vs BUSAVG) = 0.80 on the real window vs 0.69 for hour-beginning.

### 2a. Basis share under binding (the item2 hypothesis)

Unconditional basis share of RVN spread variance on the real window: **3.3%** vs HB_BUSAVG (item3a said 5%; same order). On days when a given constraint binds in DA (`item6_congestion_basis_share.csv`):

| constraint (REAL) | bind days | basis-vs-system var share, bind days | other days |
|---|---|---|---|
| STPWAP39_1 | 91 | 5.9% | 1.3% |
| 35055__A | 79 | 6.6% | 1.7% |
| 587__A | 19 | **49%** | 4.0% |
| 107__B | 21 | 35% | 4.7% |
| WESTEX | 49 | 35% | 3.4% |
| THWZEN98_A | 52 | 26% | 3.4% |
| 421__A | 46 | 26% | 3.5% |
| 630__B | 11 | 23% | 5.3% |

So yes — on days when the *rarer* North/Houston 138–345 kV constraints bind (587__A, 107__B, WESTEX, THWZEN98_A, 421__A), Raven's basis becomes a quarter to a half of its spread variance. On the two workhorses (STPWAP39_1, 35055__A, binding 78–89% of summer days) it stays ≤ 7%. The basis is *there* on the right days; the question is whether its sign is predictable.

### 2b. Ex-post: when X binds, what is the spread? (diagnostic — not tradeable)

`item6_congestion_expost.csv`; 85 tests, 49 BH-significant. Excess = spread minus the same-HE unconditional mean (removes hour-of-day). Real window highlights:

| constraint | market | n h | MCC at Raven | excess spread | t | basis vs HOU / SYS |
|---|---|---|---|---|---|---|
| STPWAP39_1 | RT bind | 525 | +2.19 | **+1.62** | 6.2 | +0.61 / −0.30 |
| THWZEN98_A | RT | 182 | +1.22 | +2.00 | 6.1 | +0.61 / −1.01 |
| WESTEX | RT | 249 | +1.65 | +1.55 | 4.7 | +0.27 / −0.92 |
| 107__B | DA | 233 | +2.93 | +2.03 | 3.9 | +0.03 / −0.55 |
| HARGRO_TWINBU1_1 | RT | 32 | −1.26 | **−6.78** | −4.2 | ≈0 |
| BLESSI_PAVLOV1_1 | RT | 29 | +4.95 | −7.93 | −2.7 | −8.35 / −8.13 |
| 35055__A (largest real-window negative) | DA | 482 | −4.87 | +0.22 | 0.6 | −0.70 / +0.35 |
| E_PASP | DA | 723 | −1.02 | −0.39 | −0.3 | ≈0 |

Two structural points. (i) The excess when a Houston-import constraint binds in **RT** is positive (short wins) but its **basis-vs-system component is negative** — the effect is coming through the *system* spread (RT binding of these constraints coincides with soft-RT afternoons), not through Raven's MCC. (ii) For the two constraints that dominate the real-node MCC ledger (35055__A −3.1k, E_PASP −0.8k over 100 days), DA binding produces **no excess spread at all** — the DA-only MCC depresses DA *and* the market anticipates it, so DA−RT is unchanged. item2's "DA net positive, RT net negative ⇒ short lean" is a statement about MCC totals, and it does not translate into a spread lean at the affected hours.

On the FULL window the largest ex-post effects are winter tail episodes (STPELM27_1 RT bind: excess +84, n 147 h; 50__A RT: +122, n 85 h; ARROZ RT: +58) — cold-morning DA premia around January events. Real, but 2–3 episodes, not a tradeable rule.

### 2c. Persistence of bind state — the ex-ante gate (**this part is positive**)

`item6_congestion_persistence.csv`; Fisher exact on P(bind D | bind D-lag) vs P(bind D | no bind), 96 tests, 72 BH-significant.

| constraint | window | P(bind day) | P(bind | bound D-1) | lift | P(bind | bound D-2) | lift | same-HE P(bind h | bound h D-1) vs base |
|---|---|---|---|---|---|---|---|
| STPWAP39_1 | FULL | 0.30 | 0.80 | 2.7 | 0.74 | 2.5 | 0.75 vs 0.09 |
| 35055__A | FULL | 0.22 | 0.79 | 3.5 | 0.75 | 3.4 | 0.72 vs 0.06 |
| E_PASP | FULL | 0.69 | 0.86 | 1.2 | 0.83 | 1.2 | 0.56 vs 0.23 |
| 1710__A | FULL | 0.11 | 0.81 | 7.5 | 0.77 | 7.1 | 0.64 vs 0.02 |
| STPELM27_1 / 50__A (winter episodic) | FULL | 0.07 | 0.71 / 0.61 | 10 / 8.6 | 0.65 / 0.51 | 9 / 7 | 0.47 / 0.27 |
| 587__A | REAL | 0.19 | 0.58 | 3.1 | 0.37 | 2.0 | 0.43 vs 0.06 |
| 107__B | REAL | 0.21 | 0.86 | 4.2 | 0.76 | 3.7 | 0.67 vs 0.10 |
| 378T387_1 | REAL | 0.28 | 0.93 | 3.3 | 0.93 | 3.3 | 0.82 vs 0.07 |

**Bind state is highly predictable from two days earlier** (lifts 2–13× on the 3-yr panel, decaying only slightly from lag1 to lag2; same-hour persistence 0.5–0.8 vs base rates of 0.02–0.25). So "condition on which constraints bind" *is* ex-ante feasible. The failure below is not a forecastability failure — it is that knowing the constraint will bind tells you little about DA−RT.

### 2d. Ex-ante constraint rules

Rule per constraint: signal = bound in DA on D-1 (lag1, leaky) or D-2 (lag2, strict); hours = the constraint's typical DA-binding HEs (top HEs covering 60% of *train* bind-hours); side = short if its MCC at Raven is positive (raises DA), long if negative. 74 rule-tests (`item6_congestion_exante.csv`), BH-adjusted on whole-window EV and separately on test-window EV.

Rules passing both (positive EV, BH on full and on test, correct pre-declared sign):

| window | constraint | lag | side / hours | signal days | EV $/MWh | t | hit | EV same hours, signal OFF | p vs OFF | sys part / basis part | train → test EV (t_test) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FULL | **STPWAP39_1** | **2 (strict)** | short HE14–18 | 301 | **+3.17** | 8.0 | 0.69 | +1.59 | **0.023** | 1.97 / **1.20** | 4.60 → **+1.07** (2.7) |
| FULL | STPWAP39_1 | 1 | short HE14–18 | 302 | +4.09 | 10.6 | 0.69 | +1.20 | 0.00003 | 2.93 / 1.15 | 6.34 → +0.81 (2.1) |
| FULL | 1710__C (RETIRED 2025-10) | 2 | short HE13–19 | 290 | +3.33 | 6.1 | 0.69 | +1.79 | 0.03 | 2.29 / 1.05 | 3.66 → +1.84 | 
| FULL | SEA_AAT1 | 2 | short HE14–19 | 253 | +2.03 | 4.5 | 0.65 | +2.61 | 0.41 | 1.27 / 0.76 | 3.95 → +1.37 |
| FULL | TREADW_YELWJC1_1 | 2 | short HE10–18 | 532 | +1.52 | 6.3 | 0.62 | +1.82 | 0.57 | 0.92 / 0.60 | 2.05 → +0.96 |
| FULL | 421__A | 2 | short HE10–16 | 178 | +0.78 | 2.8 | 0.59 | +1.49 | 0.12 | 0.04 / 0.74 | −0.61 → +0.93 |
| REAL | 1715__B | 1 (leaky) | short HE11,16–19 | 31 | +3.29 | 4.3 | 0.69 | −0.30 | 0.0003 | 2.07 / 1.22 | 1.83 → +3.80 (3.8) |
| REAL | FORTMA_YELWJC1_1 | 1 / 2 | long HE4–11 | 86 | +1.29 / +0.68 | 6.0 / 3.8 | 0.53 | +0.27 / +3.39 | — | 1.20 / 0.09 | = the morning long; binds 85% of days, basis part 0.09 → **not a congestion edge** |

Only **STPWAP39_1** clears the bar that matters — conditional EV significantly above the same hours with the signal off (p 0.02) *and* a meaningful basis component (1.2 of 3.2 $/MWh, i.e. part of it is genuinely Raven-local congestion, consistent with item2's "most forward-relevant positive for Raven"). But note the decay: JJA EV +10.3 (2024, n 165 h) → +3.3 (2025, n 385) → **+0.17 (2026, n 415)**; it is positive in 10 of 12 year-seasons (both negatives are n ≤ 25 h). On the real 2026 window the rule is nearly vacuous: STPWAP bound on 89% of days so the signal is on almost always, and the conditional EV (+0.84 test) equals the static afternoon short (+0.83).

Negative results worth recording: the MCC-sign rule is *wrong* for the negative-MCC constraints — long HE17–22 when E_PASP bound: EV **−3.9** (FULL), long HE10–13 when 35055__A bound: −0.8, long HE1–8 when HARGRO bound: −1.7, long on 50__A / STPELM27 / ARROZ: −10 to −18. In every case the system spread (evening/winter DA premium) overwhelms the node MCC; the basis part is −0.1 to −0.8. **"DA congestion negative at Raven ⇒ go long DA" loses money because the constraint binds precisely in the hours when the system-wide DA premium is largest.** `1715__B` on REAL (31 signal days, lag2 version: train EV −0.99) is a small-n artefact; `1710__C` is retired.

---

## 3. Combined rule backtest vs the item3a baseline (Deliverable 3)

25 pre-declared rules × 2 windows, chronological train/test (`item6_rules_backtest.csv`, `item6_rules_by_year.csv`). REAL test window = 2026-08-01..09-13 (44 days), the window item2 also used for proxy OOS.

**REAL test window (real RVN_RN prices), 1 MW per traded hour:**

| rule | class | n h | EV $/MWh | $/day | hit (h / d) | Sharpe·day (ann.) | max DD | worst h | t |
|---|---|---|---|---|---|---|---|---|---|
| **B0 item3a: long HE3,5,7–11** (baseline) | static | 308 | **+1.56** | 10.9 | 0.61 / 0.64 | **0.42** (8.0) | −76 | −7.7 | 5.5 |
| B: long HE7–11 static | static | 220 | +1.75 | 8.8 | 0.61 / 0.61 | 0.43 (8.2) | −54 | −6.8 | 4.9 |
| R: long HE7–11 if rt_vol_lag2 high | strict | 160 | +1.52 | 7.6 | 0.58 / 0.59 | 0.42 | −43 | −6.8 | 4.2 |
| R: long HE7–11 if rt_max_lag2 high | strict | 175 | +1.44 | 7.2 | 0.59 / 0.60 | 0.41 | −43 | −6.8 | 4.3 |
| R: long HE7–11 if wind low | needs_fc | 70 | +3.66 | 18.3 | 0.71 / 0.71 | 0.63 | −16 | −6.8 | 4.0 |
| C: short HE14–18 if STPWAP39_1 bound D-2 | strict | 200 | +0.84 | 4.2 | 0.58 / 0.65 | 0.13 | −203 | −36.6 | 1.2 |
| B: short HE14–18 static | static | 220 | +0.83 | 4.2 | 0.59 / 0.66 | 0.12 | −203 | −36.6 | 1.2 |
| C: short HE11,16–19 if 1715__B bound D-1 | leaky, n=23 d | 115 | +3.80 | 19.0 | 0.68 / 0.78 | 0.50 | −128 | −29.4 | 3.8 |
| X: B0 long + STPWAP D-2 short HE14–18 | strict | 508 | +1.27 | 14.7 | 0.60 / 0.68 | 0.42 | −179 | −36.6 | 4.0 |
| P: follow yesterday's sign per HE, lag1 (leaky) | leaky | 1,056 | +1.26 | 30.2 | 0.60 / 0.64 | 0.13 | −1,878 | −427 | 1.5 |
| P: same, **lag2 (strict)** | strict | 1,056 | **−1.03** | −24.7 | 0.51 / 0.55 | −0.12 | −2,224 | −427 | −1.2 |
| B0refit: best side per HE fitted on train | static | 220 | −2.64 | −13.2 | 0.59 / 0.52 | −0.11 | −1,120 | −308 | −1.0 |

- **Baseline holds OOS**: item3a's hour set (fitted on all 102 days, so partly in-sample) earns +1.56 on the 44 held-out days (train-period EV was +0.99); every one of the 7 hours is positive on the test window (HE3 +0.89 … HE8 +2.80).
- **No strict-ex-ante conditional rule beats +1.56 / Sharpe 0.42.** The regime filters land at +1.44–1.52 on fewer hours. Adding the STPWAP afternoon short raises $/day (10.9 → 14.7) at the same Sharpe but triples the drawdown and brings a −$37 worst hour into a book whose worst hour was −$8.
- The only rules that beat it need information you do not have: perfect same-day wind (+3.66, 14 days), or D-1 afternoon/evening prices (1715__B lag1, +3.80 on 23 days; lag2 version train EV −0.99 — not robust).
- Fitting "best side per HE" on the first 58 days and trading it on the next 44 loses −2.64 $/MWh. Static sign rules do not carry across even two summer months at this node (item3a's expanding-window result, confirmed).

**FULL test window (2025-09-01..2026-09-13, 378 days; proxy ⇒ real from 2026-06-04):**

| rule | class | n h | EV | $/day | hit h | Sharpe·day | max DD | worst h |
|---|---|---|---|---|---|---|---|---|
| B0 item3a long HE3,5,7–11 | static | 2,646 | **−2.29** | −16.0 | 0.44 | −0.05 | −8,379 | −1,300 |
| B0refit (train-fitted best side per HE: **short** most hours) | static | 3,780 | +1.99 | 19.9 | 0.57 | 0.09 | −1,026 | −616 |
| B: short HE14–18 static | static | 1,890 | +1.32 | 6.6 | 0.58 | 0.10 | −612 | −149 |
| **C: short HE14–18 if STPWAP39_1 bound D-2** | **strict** | 610 | **+1.07** | 5.4 | **0.63** | **0.14** | **−283** | −51 |
| C: short HE14–18 if any Houston-import (STPWAP/1710__A/SEA_AAT1) bound D-2 | strict | 1,170 | +0.69 | 3.5 | 0.59 | 0.07 | −900 | −149 |
| P: follow yesterday's sign, lag1 (leaky) / lag2 (strict) | — | 9,070 | +3.01 / +0.63 | 72 / 15 | 0.58 / 0.53 | 0.12 / 0.04 | −2,781 / −5,890 | −616 / −1,460 |
| P: same HE9–20, lag1 / lag2 | — | 4,536 | +2.54 / +1.28 | 30 / 15 | 0.59 / 0.52 | 0.21 / 0.08 | −740 / −1,010 | −444 / −238 |
| R: long HE7–11 if rt_vol_lag2 high | strict | 565 | −6.00 | −30 | 0.40 | −0.08 | −4,667 | −1,300 |
| X: B0 long + STPWAP short | strict | 3,256 | −1.66 | −14 | 0.48 | −0.05 | −8,321 | −1,300 |

The summer-2026 baseline is a **summer** rule: on a window containing a winter it loses −2.29 $/MWh (DJF EV of the long side −10.6 / −4.0 / −15.6 in 2024/25/26; JJA +0.8 / +0.1 / +1.0). The STPWAP rule is the only strict-ex-ante conditional rule with positive OOS EV, hit rate ≥ 60% and a drawdown under $300/MW — but the unconditioned afternoon short earns more per MWh on the same window (1.32 vs 1.07; the condition mainly removes 2/3 of the hours and the worst of the tail: worst hour −51 vs −149, DD −283 vs −612).

---

## 4. Honest negative result and overfitting accounting (Deliverable 4)

**Hypotheses tested: 4,394** (regime separation 1,015; within-regime edge 3,074; ex-post constraint excess 85; ex-ante constraint rules 74; bind persistence 96; pre-declared rule backtests 50). BH q=0.10 rejections: 1,181 — but almost all of them are in the ex-post / needs-forecast / leaky-lag1 classes or restate the unconditional hour-of-day and season effects. Restricting to what is *strictly ex-ante and conditional*:

| family | strict-ex-ante tests | BH survivors | survivors that beat the unconditional same-hour rule OOS |
|---|---|---|---|
| regime separation, HE grain (REAL / FULL) | 72 / 72 | 0 / 9 | 0 — and family-wise permutation p = 0.35 on REAL |
| regime within-cell edge, block grain (REAL) | 45 | 12 | 0 (rt_vol/rt_max lag2 morning long: OOS +1.44–1.52 vs +1.75 static) |
| constraint bind persistence, lag2 | 48 | 33 | n/a (bind state *is* predictable — this is the one clean positive) |
| ex-ante constraint rules, lag2 (REAL / FULL) | 18 / 19 | 5 / 14 (positive-EV: 4 / 6) | **1** (STPWAP39_1 on FULL: p vs signal-off 0.02; still below static on EV, above on Sharpe/DD) |
| pre-declared rules, strict ex-ante (REAL test) | 11 | — | 0 beat B0 on EV and Sharpe simultaneously |

How much of the apparent conditional edge was overfitting / leakage?
- **Persistence rule**: 67% of the 3-yr edge and 100% of the 2026 edge came from D-1 hours after the cutoff (2.76 → 0.90; 1.77 → −0.10).
- **Regime × HE search on the real window**: the best in-sample |t| (4.35) is at the *median* of the pure-noise selection distribution (4.15; p 0.35) — i.e., effectively all of the apparent hourly regime edge is selection. The block-level morning-long-after-volatile-day cells were real in summer 2026 (train 2.1 → test 1.5, 28% shrinkage) but flip sign in winter and do not beat the unconditional morning long.
- **Ex-ante constraint rules (FULL)**: train → test shrinkage 53–84% for the four positive Houston-import rules (STPWAP 4.60 → 1.07; TREADW 2.05 → 0.96; SEA_AAT1 3.95 → 1.37; any-import 4.46 → 0.69). The direction survives; roughly two-thirds to three-quarters of the in-sample magnitude does not.
- **Best-side-per-HE refit** (the simplest "conditional" rule — condition on the hour): +2.75 train → **−2.64 test** on the real window.

**Conclusion.** DART virtual at RVN_RN cannot be materially improved over the item3a baseline by conditioning on regime or congestion with information available at the DAM cutoff. The reasons are structural, not statistical power: (1) Raven's spread is 97.5% the system spread, and the strictly-known lagged system state (D-2) carries almost no hour-level information about D; (2) congestion at Raven *is* forecastable (bind persistence 2–13×) but the market prices DA-only congestion into DA, so a binding constraint moves the LMP without moving DA−RT — the one exception, STPWAP39_1 summer afternoons, has a genuine ~$1.2/MWh basis component whose total effect has decayed from +10 (2024) to ≈0 (2026); (3) the summer-2026 conditional patterns (volatile-day → morning long) reverse in winter.

**What to carry into the FY2027 outlook / dart-virtual-trader**
- Budget DART at Raven as the *system* trade item3a sized: ≈ $1.2–1.6/MWh on the 7 morning long hours in summer, with the item3a §4 seasonal picture (winter is short) — **no conditional uplift**.
- Use constraint bind persistence (STPWAP39_1, 35055__A, 1710__A, SEA_AAT1: P(bind | bound D-2) 0.74–0.77) as a **risk filter on the afternoon short**, not as an alpha source: when STPWAP39_1 was bound two days earlier, the HE14–18 short's worst hour was −$51 vs −$149 unconditioned and drawdown halved, at a cost of ~0.25 $/MWh EV. That is the only ex-ante-usable congestion result.
- Retire the "follow yesterday's sign" tilt unless it is implemented with a D-1 HE1–9 partial-day signal and re-validated; the lag-1 numbers in item3a are not achievable.
- Any regime overlay should be seasonal, not lagged-volatility based.

## Limitations
- 102 real days; the 3-yr panel is a proxy whose SOUTH-zone member (41%) makes pre-2026 *basis* magnitudes indicative (the STPWAP basis component is the least affected: RVN SF −0.023 vs proxy −0.031; WHARTN rules are proxy artefacts and were excluded from conclusions).
- Regime terciles are coarse; no interaction models were fitted (deliberately — 102 days cannot support them).
- Same-day wind/load/solar were tested as *actuals* (upper bound on a forecast-based rule). A forecast-vintage test (D-1 10:00 STWPF/STPPF) was not run; given the actuals-based rule fails to beat the static rule on the 3-yr window (long HE7–11 if wind low: −8.8 OOS), a forecast version cannot do better on average.
- No clearing model, DAM fees, or credit — all PnL is spread × MW assuming the virtual clears.
