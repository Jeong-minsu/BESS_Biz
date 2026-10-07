"""Season-wise threshold optimisation + generalisation tests.

Seasons: 겨울 Jan-Feb / 봄 Mar-May / 여름 Jun-Aug / (Sep 1-7 = holdout)
Tests:  (a) in-sample optimum per season
        (b) split-half within season (optimise 1st half -> apply 2nd half)
        (c) cross-season transfer matrix
        (d) leave-one-month-out within season
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")

A = Path(__file__).resolve().parents[1]
m = pd.read_parquet(A / "derived" / "joined.parquet").sort_values("ft_utc").reset_index(drop=True)
m["ds"] = m.date.astype(str); m["mo"] = m.ds.str[:7]
pd.set_option("display.width", 240, "display.max_columns", 40)

SEASON = {"2026-01":"겨울","2026-02":"겨울","2026-03":"봄","2026-04":"봄","2026-05":"봄",
          "2026-06":"여름","2026-07":"여름","2026-08":"여름","2026-09":"9월holdout"}
m["season"] = m.mo.map(SEASON)
G = np.round(np.arange(0.0, 1.001, 0.02), 2)


def mdd(c):
    p = np.maximum.accumulate(np.concatenate([[0.0], c])); return float((p - np.concatenate([[0.0], c])).max())


def apply(d, s_hi, l_hi):
    sp, dw, rw = d.spread.to_numpy(), d.da_win_probability.to_numpy(), d.rt_win_probability.to_numpy()
    ms = dw >= s_hi; ml = (rw >= l_hi) & ~ms
    pnl = np.where(ms, sp, 0.0) + np.where(ml, -sp, 0.0)
    t = pnl[ms | ml]
    w, l = t[t > 0], t[t < 0]
    return dict(cum=float(t.sum()), n=int(t.size), ev=float(t.mean()) if t.size else np.nan,
                win=float((t > 0).mean()) if t.size else np.nan,
                pl=float(w.mean()/abs(l.mean())) if w.size and l.size else np.nan,
                mdd=mdd(np.cumsum(pnl)), n_sh=int(ms.sum()), n_lg=int(ml.sum()))


def best(d):
    out = None
    for s in G:
        for l in G:
            r = apply(d, s, l)
            if out is None or r["cum"] > out[2]["cum"]:
                out = (s, l, r)
    return out


print("="*104)
print("### (a) 시즌별 in-sample 최적 (전수 탐색 51x51)")
print("="*104)
seasons = ["겨울","봄","여름","9월holdout"]
opt = {}
rows = []
for s in seasons:
    d = m[m.season == s]
    sh, lh, r = best(d)
    opt[s] = (sh, lh)
    sp = d.spread.to_numpy()
    rows.append(dict(season=s, days=d.date.nunique(), hours=len(d), S_hi=sh, L_hi=lh,
                     cum=r["cum"], ev=r["ev"], win=r["win"], pl=r["pl"], mdd=r["mdd"],
                     sh_h=r["n_sh"], lg_h=r["n_lg"],
                     base_long=-sp.sum(), base_short=sp.sum(),
                     uplift=r["cum"] - max(-sp.sum(), sp.sum())))
print(pd.DataFrame(rows).round(2).to_string(index=False))
print("\n  base_long/base_short = 신호 미사용 baseline. uplift = 최적 − 더 좋은 baseline")

print("\n"+"="*104)
print("### (b) 시즌 내 split-half : 전반부로 최적화 → 후반부에 그대로 적용")
print("="*104)
for s in ["겨울","봄","여름"]:
    d = m[m.season == s]
    dates = sorted(d.date.unique()); cut = dates[len(dates)//2]
    d1, d2 = d[d.date < cut], d[d.date >= cut]
    sh, lh, r1 = best(d1)
    r2 = apply(d2, sh, lh)
    sp2 = d2.spread.to_numpy()
    print(f"{s:>4}: 전반 최적 S={sh:.2f} L={lh:.2f} → 전반 cum={r1['cum']:+9,.0f} ev={r1['ev']:+6.2f} win={r1['win']:.3f}")
    print(f"       후반 적용        → 후반 cum={r2['cum']:+9,.0f} ev={r2['ev']:+6.2f} win={r2['win']:.3f} "
          f"| 후반 baseline(long) {-sp2.sum():+,.0f}  best-of-baseline {max(-sp2.sum(),sp2.sum()):+,.0f}")
    sh2, lh2, r2b = best(d2)
    print(f"       (후반 자체 최적 S={sh2:.2f} L={lh2:.2f} cum={r2b['cum']:+,.0f}) "
          f"→ 전반 파라미터가 후반 최적의 {100*r2['cum']/r2b['cum'] if r2b['cum'] else float('nan'):.0f}% 달성\n")

print("="*104)
print("### (c) 교차 시즌 전이 : 행=최적화한 시즌, 열=적용한 시즌 (누적 $/MW)")
print("="*104)
mat = pd.DataFrame(index=seasons, columns=seasons, dtype=float)
for a in seasons:
    sh, lh = opt[a]
    for b in seasons:
        mat.loc[a, b] = apply(m[m.season == b], sh, lh)["cum"]
base = pd.Series({b: max(-m[m.season==b].spread.sum(), m[m.season==b].spread.sum()) for b in seasons})
mat.loc["신호미사용 최선"] = base
print(mat.round(0).to_string())

print("\n"+"="*104)
print("### (d) leave-one-month-out : 시즌 내 나머지 달로 최적화 → 뺀 달에 적용")
print("="*104)
for s in ["겨울","봄","여름"]:
    mos = sorted(m[m.season == s].mo.unique())
    for mo in mos:
        tr, te = m[(m.season == s) & (m.mo != mo)], m[m.mo == mo]
        sh, lh, _ = best(tr)
        r = apply(te, sh, lh)
        spt = te.spread.to_numpy()
        print(f"{s:>4} {mo}: 학습 S={sh:.2f} L={lh:.2f} → 적용 cum={r['cum']:+9,.0f} "
              f"win={r['win']:.3f} | baseline(long){-spt.sum():+8,.0f} best-base {max(-spt.sum(),spt.sum()):+8,.0f}")
    print()

print("="*104)
print("### (e) 임계값 없이: 시즌별 원천 통계 (방향성이 계절을 타는가)")
print("="*104)
t = m.groupby("season").apply(lambda x: pd.Series({
    "days": x.date.nunique(), "hours": len(x),
    "mean_spread": x.spread.mean(), "median_spread": x.spread.median(),
    "P(DA>RT)": (x.spread > 0).mean(),
    "mean_da_win": x.da_win_probability.mean(),
    "corr(da_win, spread)": x.da_win_probability.corr(x.spread),
    "corr(da_win, sign)": x.da_win_probability.corr((x.spread > 0).astype(float)),
}), include_groups=False)
print(t.round(3).to_string())
print("\n월별:")
t2 = m.groupby("mo").apply(lambda x: pd.Series({
    "mean_spread": x.spread.mean(), "P(DA>RT)": (x.spread > 0).mean(),
    "corr_sign": x.da_win_probability.corr((x.spread > 0).astype(float)),
}), include_groups=False)
print(t2.round(3).to_string())
