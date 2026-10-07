"""Quick check for the user's framing: at Raven, is DART driven by system-wide factors rather than node congestion?

Decomposes the Raven (proxy) hourly DA-RT spread into
  (a) ERCOT system spread (HB_BUSAVG) and Houston hub spread, vs node-specific residual
  (b) how much of the system spread is explained by ERCOT's own forecast errors
      (actual - D-1 forecast, for load / wind / solar / net load)   <- ex-post, NOT tradeable
  (c) what is known at bid time: forecast level (tightness) and forecast BIAS (average error sign)
Real data only. 2023-12 .. 2026-09.
"""
import glob
from pathlib import Path
import numpy as np, pandas as pd

BASE = Path(__file__).resolve().parents[1]; RAW = BASE / "raw"; D = BASE / "derived"
h = pd.read_parquet(D / "dart3y_hourly_panel.parquet")

HUBS = {"HB_BUSAVG": 10000698380, "HB_HOUSTON": 10000697077}
parts = []
for f in sorted(glob.glob(str(RAW / "price_panel/*.parquet"))):
    if Path(f).stem < "202312":
        continue
    d = pd.read_parquet(f)
    parts.append(d[d.OBJECTID.isin(HUBS.values())])
px = pd.concat(parts); px["dt"] = pd.to_datetime(px.DATETIME)
inv = {v: k for k, v in HUBS.items()}; px["hub"] = px.OBJECTID.map(inv)
sp = (px.pivot_table(index="dt", columns="hub", values="DALMP") - px.pivot_table(index="dt", columns="hub", values="RTLMP"))
h = h.join(sp.rename(columns={"HB_BUSAVG": "sys", "HB_HOUSTON": "hou"}), how="inner")

fc = pd.read_parquet(RAW / "dart3y_forecasts.parquet").set_index("dt")
act = pd.read_parquet(RAW / "item6_fundamentals.parquet"); act["dt"] = pd.to_datetime(act.hour_end); act = act.set_index("dt")
e = pd.DataFrame(index=fc.index)
e["err_load"] = (act.load_mw - fc.load_fc) / 1000          # + = more demand than forecast  -> RT tighter
e["err_wind"] = (act.wind_mw - fc.wind_fc) / 1000          # + = more wind than forecast    -> RT looser
e["err_solar"] = (act.solar_mw - fc.solar_fc) / 1000
e["err_netload"] = e.err_load - e.err_wind - e.err_solar     # + = RT tighter than DA expected
e["fc_netload"] = (fc.load_fc - fc.wind_fc - fc.solar_fc) / 1000
h = h.join(e, how="inner").dropna(subset=["spread", "sys", "err_netload"])

def r2(y, X):
    X = np.column_stack([np.ones(len(y))] + [np.asarray(x) for x in X])
    b, *_ = np.linalg.lstsq(X, np.asarray(y), rcond=None)
    res = np.asarray(y) - X @ b
    return 1 - res.var() / np.asarray(y).var(), b

# robust versions: clip at 1/99 pct so a few storm hours don't dominate R2
def clip(s):
    lo, hi = np.percentile(s, [1, 99]); return s.clip(lo, hi)

print("=== (a) Raven spread explained by system-wide spreads (hourly) ===")
for lab, cols in [("ERCOT 시스템(HB_BUSAVG)", ["sys"]), ("Houston 허브", ["hou"]), ("둘 다", ["sys", "hou"])]:
    raw, _ = r2(h.spread, [h[c] for c in cols])
    rob, _ = r2(clip(h.spread), [clip(h[c]) for c in cols])
    print(f"  {lab:22s} R2 raw {raw:.3f} | clipped {rob:.3f}")

print("\n=== (b) system spread explained by ERCOT forecast errors (EX-POST, not tradeable) ===")
y = clip(h.sys)
for lab, cols in [("순수요 예측오차", ["err_netload"]), ("수요 예측오차", ["err_load"]), ("풍력 예측오차", ["err_wind"]),
                  ("태양광 예측오차", ["err_solar"]), ("세 가지 모두", ["err_load", "err_wind", "err_solar"])]:
    v, b = r2(y, [clip(h[c]) for c in cols])
    print(f"  {lab:14s} R2 {v:.3f}   coef(GW) {np.round(b[1:], 2)}")
# daily level (DART is bid per day; daily avg spread vs daily avg error)
dd = h.groupby("day").agg(sys=("sys", "mean"), rav=("spread", "mean"), err=("err_netload", "mean"), errmax=("err_netload", "max"))
v, b = r2(clip(dd.sys), [clip(dd.err)])
print(f"  [일평균] 순수요 예측오차 → 시스템 가격차 R2 {v:.3f}, 1GW 오차당 {b[1]:+.2f} $/MWh")
print(f"  [일평균] Raven 가격차 vs 시스템 가격차 corr {dd.rav.corr(dd.sys):.3f}")

# sign logic: when RT turns out tighter than forecast (err>0), RT > DA -> spread < 0 (LONG wins)
h["err_bin"] = pd.cut(h.err_netload, [-99, -3, -1, 1, 3, 99], labels=["−3GW 이하(예보보다 여유)", "−3~−1", "±1GW", "+1~+3", "+3GW 이상(예보보다 타이트)"])
g = h.groupby("err_bin", observed=True).agg(hours=("sys", "size"), sys_mean=("sys", "mean"), sys_median=("sys", "median"),
                                             short_win=("sys", lambda x: (x > 0).mean()))
print("\n  순수요 예측오차 구간별 시스템 가격차 (DA−RT):")
print(g.round(2).to_string())

print("\n=== (c) what is known at bid time ===")
bias = h.groupby(h.index.year)[["err_load", "err_wind", "err_solar", "err_netload"]].mean()
print("  연도별 평균 예측오차 (GW, + = 실제가 예측보다 큼):"); print(bias.round(2).to_string())
hour_bias = h.groupby("he")[["err_netload"]].mean().T.round(2)
print("  시간대별 평균 순수요 예측오차 (GW):"); print(hour_bias.to_string())
h["tq"] = pd.qcut(h.fc_netload, 3, labels=["예측 순수요 하", "중", "상"])
print("  예측 순수요 수준별 시스템 가격차 평균:", h.groupby("tq", observed=True).sys.mean().round(2).to_dict())
