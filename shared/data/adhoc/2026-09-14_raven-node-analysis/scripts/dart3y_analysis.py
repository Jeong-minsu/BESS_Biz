"""Raven DART virtual — 3-year hourly analysis on the proxy node, split by season/month and by
EX-ANTE (forecast) system tightness, with a strict train/test check.

Conventions (as requested):
  spread = DA - RT
  SHORT  = sell DA, buy back RT  -> PnL = +spread   (wins when DA > RT)
  LONG   = buy DA, sell back RT  -> PnL = -spread   (wins when RT > DA)

Price: item2 NNLS proxy for RVN_RN (homogeneous 3-yr series; real RVN tracks it with 98% hourly sign agreement).
Tightness: ERCOT day-ahead forecasts for day D published on D-1 by 13:59 GMT (before the 10:00 CT bid close):
  fc_peak_nl = max over hours of (MTLF load - STWPF wind - STPPF solar)
  tight_rank = percentile of fc_peak_nl vs the previous 60 days' fc_peak_nl (season-adjusted, uses past only)
  tercile    : LOOSE (<1/3) / NORMAL / TIGHT (>2/3)
Train 2023-12..2025-12, test 2026-01..2026-09 (out-of-sample). Real data only.
"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd

BASE = Path(__file__).resolve().parents[1]; D = BASE / "derived"; RAW = BASE / "raw"
N = {"CBEC_ALL": 10001765766, "RBN_BESS1": 10017290064, "TAV_RN": 10016969364, "RVN": 10019925379}
W, B0 = {"CBEC_ALL": 0.4148, "RBN_BESS1": 0.5407, "TAV_RN": 0.0445}, -0.065
SEASON = {12: "겨울", 1: "겨울", 2: "겨울", 3: "봄", 4: "봄", 5: "봄", 6: "여름", 7: "여름", 8: "여름", 9: "가을", 10: "가을", 11: "가을"}
SEAS_ORDER = ["겨울", "봄", "여름", "가을"]
TIGHT_ORDER = ["여유", "보통", "타이트"]

# ------------------------------------------------------------------ hourly proxy spread
parts = []
for f in sorted(glob.glob(str(RAW / "price_panel/*.parquet"))):
    if Path(f).stem < "202312":
        continue
    d = pd.read_parquet(f)
    parts.append(d[d.OBJECTID.isin(N.values())])
px = pd.concat(parts, ignore_index=True)
inv = {v: k for k, v in N.items()}
px["node"] = px.OBJECTID.map(inv)
px["dt"] = pd.to_datetime(px.DATETIME)
da = px.pivot_table(index="dt", columns="node", values="DALMP")
rt = px.pivot_table(index="dt", columns="node", values="RTLMP")
ix = da.index.intersection(rt.index)
da, rt = da.loc[ix], rt.loc[ix]
proxy_da = B0 + sum(W[k] * da[k] for k in W)
proxy_rt = B0 + sum(W[k] * rt[k] for k in W)
h = pd.DataFrame({"spread": proxy_da - proxy_rt, "real_spread": da["RVN"] - rt["RVN"]}).dropna(subset=["spread"])
h["he"] = h.index.hour.where(h.index.hour != 0, 24)
h["day"] = (h.index - pd.Timedelta(hours=1)).normalize()       # HE24 (00:00 next day) belongs to D
h = h[(h.day >= "2023-12-01") & (h.day <= "2026-09-13")]
h["year"] = h.day.dt.year
h["month"] = h.day.dt.month
h["season"] = h.month.map(SEASON)
h["season_year"] = np.where(h.month == 12, h.year + 1, h.year)   # Dec belongs to next winter

# ------------------------------------------------------------------ ex-ante tightness
fc = pd.read_parquet(RAW / "dart3y_forecasts.parquet")
fc["nl"] = fc.load_fc - fc.wind_fc - fc.solar_fc
fcd = fc.groupby("day").agg(fc_peak_nl=("nl", "max"), fc_load_peak=("load_fc", "max")).sort_index() / 1000
fcd["fc_evening_nl"] = fc.assign(he=fc.dt.dt.hour.where(fc.dt.dt.hour != 0, 24)).query("he>=18 and he<=22").groupby("day").nl.max() / 1000
roll = fcd.fc_peak_nl.shift(1).rolling(60, min_periods=30)
fcd["tight_rank"] = [
    (np.nan if pd.isna(x) else (w < x).mean())
    for x, w in zip(fcd.fc_peak_nl, [fcd.fc_peak_nl.shift(1).iloc[max(0, i - 60):i].dropna().values for i in range(len(fcd))])
]
fcd.loc[fcd.fc_peak_nl.shift(1).rolling(60, min_periods=30).count() < 30, "tight_rank"] = np.nan
fcd["tight"] = pd.cut(fcd.tight_rank, [-0.01, 1 / 3, 2 / 3, 1.01], labels=TIGHT_ORDER)
h = h.merge(fcd[["fc_peak_nl", "tight_rank", "tight"]], left_on="day", right_index=True, how="left")
print(f"hours: {len(h):,}  days: {h.day.nunique()}  with tightness label: {h.tight.notna().mean():.1%}")


# ------------------------------------------------------------------ helpers
def side_stats(x):
    """x = hourly spreads for one cell. Returns stats for SHORT (+spread) and LONG (-spread) and best side."""
    x = x.dropna()
    n = len(x)
    if n < 20:
        return None
    mu, sd = x.mean(), x.std()
    t = mu / (sd / np.sqrt(n)) if sd > 0 else 0.0
    out = {"n": int(n), "mean_spread": float(mu), "median_spread": float(x.median()), "t": float(t)}
    for side, pnl in (("short", x), ("long", -x)):
        win, loss = pnl[pnl > 0], -pnl[pnl < 0]
        out[side] = {
            "p_win": float((pnl > 0).mean()),
            "avg_win": float(win.mean()) if len(win) else 0.0,
            "avg_loss": float(loss.mean()) if len(loss) else 0.0,
            "pl_ratio": float(win.mean() / loss.mean()) if len(win) and len(loss) and loss.mean() > 0 else np.nan,
            "ev": float(pnl.mean()),
            "worst1pct_loss": float(-np.percentile(pnl, 1)),
        }
    best = "short" if mu > 0 else "long"
    out["best"] = best
    out["ev_best"] = abs(float(mu))
    # robust: winsorised mean (1/99 pct) — are we just harvesting a few spikes?
    lo, hi = np.percentile(x, [1, 99])
    out["mean_wins"] = float(x.clip(lo, hi).mean())
    return out


def year_signs(sub, key="year", years=(2024, 2025, 2026)):
    s = {}
    for y in years:
        v = sub[sub[key] == y].spread
        s[y] = float(v.mean()) if len(v) >= 15 else None
    return s


def consistent(signs, need=None):
    vals = [v for v in signs.values() if v is not None]
    if len(vals) < 2:
        return 0, len(vals)
    pos = sum(v > 0 for v in vals); neg = sum(v < 0 for v in vals)
    return max(pos, neg), len(vals)


results = {}

# ================================================================== A. 3-year hourly base table
print("\n=== A. 3년 시간대별 기본 분석 (proxy, 2023-12 ~ 2026-09) ===")
print(f"{'HE':>3} {'mean':>7} {'t':>6} {'best':>6} {'P(win)':>7} {'P/L':>5} {'EV':>6} {'worst1%':>8} {'wins-mean':>9} | 2024 2025 2026 | 일관")
rowsA = []
for he in range(1, 25):
    sub = h[h.he == he]
    st = side_stats(sub.spread)
    ys = year_signs(sub)
    c, k = consistent(ys)
    bs = st[st["best"]]
    rowsA.append({"he": he, **{k2: v for k2, v in st.items() if k2 not in ("short", "long")},
                  "short": st["short"], "long": st["long"], "years": ys, "consistent_years": f"{c}/{k}"})
    ysf = " ".join(("  +  " if (v or 0) > 0 else "  −  ") if v is not None else "  .  " for v in ys.values())
    print(f"{he:>3} {st['mean_spread']:>+7.2f} {st['t']:>+6.2f} {st['best']:>6} {bs['p_win']:>7.1%} "
          f"{bs['pl_ratio']:>5.2f} {st['ev_best']:>6.2f} {bs['worst1pct_loss']:>8.1f} {st['mean_wins']:>+9.2f} |{ysf}| {c}/{k}")
results["A_hourly_3y"] = rowsA

# ================================================================== B. season x HE and month x HE
print("\n=== B. 계절 × 시간대: 평균 가격차 (+ = SHORT 유리) · t · 연도 일관성 ===")
rowsB = []
for s in SEAS_ORDER:
    line = f"{s:>3} "
    for he in range(1, 25):
        sub = h[(h.season == s) & (h.he == he)]
        st = side_stats(sub.spread)
        ys = year_signs(sub, key="season_year")
        c, k = consistent(ys)
        rowsB.append({"season": s, "he": he, "mean": st["mean_spread"], "t": st["t"], "mean_wins": st["mean_wins"],
                      "n": st["n"], "years": ys, "consistent": c, "n_years": k, "best": st["best"],
                      "p_win_best": st[st["best"]]["p_win"], "worst1pct_best": st[st["best"]]["worst1pct_loss"],
                      "pl_best": st[st["best"]]["pl_ratio"]})
        mark = "*" if abs(st["t"]) >= 2 and c == k and k >= 2 else " "
        line += f"{st['mean_spread']:+5.1f}{mark}"
    print(line)
print("  (* = |t|≥2 이고 모든 연도에서 같은 방향)")
results["B_season_he"] = rowsB

month_he = h.pivot_table(index="month", columns="he", values="spread", aggfunc="mean")
month_he_wins = h.groupby(["month", "he"]).spread.apply(lambda x: x.clip(*np.percentile(x, [1, 99])).mean()).unstack()
results["B_month_he_mean"] = {int(m): {int(k): float(v) for k, v in r.items()} for m, r in month_he.iterrows()}
results["B_month_he_wins"] = {int(m): {int(k): float(v) for k, v in r.items()} for m, r in month_he_wins.iterrows()}

# ================================================================== C. forecast tightness x HE
print("\n=== C. 예측 기준 계통 타이트함 × 시간대: 평균 가격차 ===")
rowsC = []
for tg in TIGHT_ORDER:
    line = f"{tg:>3} "
    for he in range(1, 25):
        sub = h[(h.tight == tg) & (h.he == he)]
        st = side_stats(sub.spread)
        ys = year_signs(sub)
        c, k = consistent(ys)
        rowsC.append({"tight": tg, "he": he, "mean": st["mean_spread"], "t": st["t"], "mean_wins": st["mean_wins"],
                      "n": st["n"], "years": ys, "consistent": c, "n_years": k, "best": st["best"],
                      "p_win_best": st[st["best"]]["p_win"], "worst1pct_best": st[st["best"]]["worst1pct_loss"],
                      "pl_best": st[st["best"]]["pl_ratio"]})
        mark = "*" if abs(st["t"]) >= 2 and c == k and k >= 2 else " "
        line += f"{st['mean_spread']:+5.1f}{mark}"
    print(line)
results["C_tight_he"] = rowsC

# ================================================================== D. season x tightness x HE-block
BLOCKS = {"새벽 1–6시": range(1, 7), "아침 7–11시": range(7, 12), "낮 12–16시": range(12, 17),
          "저녁 17–21시": range(17, 22), "밤 22–24시": range(22, 25)}
h["block"] = h.he.map({hh: b for b, rr in BLOCKS.items() for hh in rr})
print("\n=== D. 계절 × 타이트함 × 시간 구간: 평균 가격차 (t) ===")
rowsD = []
for s in SEAS_ORDER:
    for tg in TIGHT_ORDER:
        line = f"{s} {tg:>3} "
        for b in BLOCKS:
            sub = h[(h.season == s) & (h.tight == tg) & (h.block == b)]
            st = side_stats(sub.spread)
            if st is None:
                line += "   n/a       "; continue
            ys = year_signs(sub, key="season_year")
            c, k = consistent(ys)
            rowsD.append({"season": s, "tight": tg, "block": b, "mean": st["mean_spread"], "t": st["t"],
                          "mean_wins": st["mean_wins"], "n": st["n"], "consistent": c, "n_years": k,
                          "best": st["best"], "p_win_best": st[st["best"]]["p_win"],
                          "worst1pct_best": st[st["best"]]["worst1pct_loss"], "pl_best": st[st["best"]]["pl_ratio"]})
            line += f"{st['mean_spread']:+6.1f}({st['t']:+.1f}) "
        print(line)
results["D_season_tight_block"] = rowsD

# ================================================================== E. out-of-sample test
train = h[h.day < "2026-01-01"]
test = h[h.day >= "2026-01-01"]
from math import erf, sqrt
def pval(t):
    return 2 * (1 - 0.5 * (1 + erf(abs(t) / sqrt(2))))

def select(df, keys, years=(2024, 2025), ykey="year"):
    """Cells chosen on TRAIN: |t|>=2, same sign in 2024 and 2025, winsorised mean same sign (not spike-driven)."""
    chosen, tested = [], 0
    for grp, sub in df.groupby(keys, observed=True):
        st = side_stats(sub.spread)
        if st is None:
            continue
        tested += 1
        ys = {y: sub[sub[ykey] == y].spread.mean() for y in years}
        if any(pd.isna(v) for v in ys.values()):
            continue
        same = all(np.sign(v) == np.sign(st["mean_spread"]) for v in ys.values())
        robust = np.sign(st["mean_wins"]) == np.sign(st["mean_spread"])
        if abs(st["t"]) >= 2 and same and robust:
            chosen.append({"cell": grp if isinstance(grp, tuple) else (grp,), "side": st["best"],
                           "train_ev": st["ev_best"], "t": st["t"], "p": pval(st["t"])})
    # Benjamini-Hochberg at q=0.10 over all tested cells
    ps = sorted(c["p"] for c in chosen)
    m = tested; thr = 0
    for i, p in enumerate(ps, 1):
        if p <= 0.10 * i / m:
            thr = p
    for c in chosen:
        c["bh_pass"] = c["p"] <= thr
    return chosen, tested

def evaluate(df, keys, chosen, only_bh=False):
    pnl = []
    for c in chosen:
        if only_bh and not c["bh_pass"]:
            continue
        mask = np.ones(len(df), bool)
        for k, v in zip(keys, c["cell"]):
            mask &= (df[k] == v).values
        x = df.loc[mask, "spread"]
        pnl.append(x if c["side"] == "short" else -x)
    if not pnl:
        return {"hours": 0}
    p = pd.concat(pnl)
    daily = p.groupby(df.loc[p.index, "day"]).sum()
    return {"hours": int(len(p)), "ev_per_mwh": float(p.mean()), "hit_rate": float((p > 0).mean()),
            "total_usd_per_mw": float(p.sum()), "worst_hour": float(p.min()), "worst_day": float(daily.min()),
            "days_positive": float((daily > 0).mean()), "median_pnl": float(p.median())}

FAMILIES = {
    "① 시간대만 (24칸)": ["he"],
    "② 계절 × 시간대 (96칸)": ["season", "he"],
    "③ 타이트함 × 시간대 (72칸)": ["tight", "he"],
    "④ 계절 × 타이트함 × 구간 (60칸)": ["season", "tight", "block"],
}
print("\n=== E. 학습(2023-12~2025) → 검증(2026.1~9, 사전 선택 규칙 그대로 적용) ===")
print(f"{'규칙군':30s} {'검정':>4} {'선택':>4} {'BH통과':>5} | {'학습EV':>6} | {'검증 시간':>7} {'EV/MWh':>7} {'적중':>6} {'$/MW':>8} {'최악일':>8} {'흑자일':>6}")
rowsE = {}
for name, keys in FAMILIES.items():
    tr = train.dropna(subset=[k for k in keys if k in ("tight",)]) if "tight" in keys else train
    te = test.dropna(subset=["tight"]) if "tight" in keys else test
    chosen, tested = select(tr, keys)
    tr_ev = evaluate(tr, keys, chosen)
    te_all = evaluate(te, keys, chosen)
    te_bh = evaluate(te, keys, chosen, only_bh=True)
    nbh = sum(c["bh_pass"] for c in chosen)
    rowsE[name] = {"tested": tested, "selected": len(chosen), "bh_pass": nbh, "train": tr_ev, "test": te_all,
                   "test_bh_only": te_bh,
                   "cells": [{"cell": list(map(str, c["cell"])), "side": c["side"], "train_ev": c["train_ev"],
                              "t": c["t"], "bh_pass": bool(c["bh_pass"])} for c in chosen]}
    def fmt(r):
        if r.get("hours", 0) == 0:
            return f"{0:>7} {'—':>7} {'—':>6} {'—':>8} {'—':>8} {'—':>6}"
        return (f"{r['hours']:>7} {r['ev_per_mwh']:>+7.2f} {r['hit_rate']:>6.1%} {r['total_usd_per_mw']:>+8.0f} "
                f"{r['worst_day']:>+8.0f} {r['days_positive']:>6.1%}")
    tre = f"{tr_ev['ev_per_mwh']:+.2f}" if tr_ev.get("hours") else "—"
    print(f"{name:30s} {tested:>4} {len(chosen):>4} {nbh:>5} | {tre:>6} | {fmt(te_all)}")
    if nbh and nbh < len(chosen):
        print(f"{'   └ BH 통과 칸만':30s} {'':>4} {'':>4} {'':>5} | {'':>6} | {fmt(te_bh)}")
results["E_oos"] = rowsE

# naive comparison: trade every hour on the 3-yr overall best side (hindsight-free = train side)
json.dump(results, open(D / "dart3y_results.json", "w"), indent=1, default=lambda o: None if (isinstance(o, float) and np.isnan(o)) else str(o))
h[["spread", "real_spread", "he", "day", "year", "month", "season", "tight", "tight_rank", "fc_peak_nl"]].to_parquet(D / "dart3y_hourly_panel.parquet")
print("\nwrote dart3y_results.json, dart3y_hourly_panel.parquet")
