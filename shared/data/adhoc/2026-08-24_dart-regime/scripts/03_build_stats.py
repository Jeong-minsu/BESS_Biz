"""
DART regime analysis #03 — build hourly master + regime win-rate / P-L stats.

Regime classification (per market day, D-1 bid-close vintage forecasts only):
  normal          : forecast peak net load <= 68,000 MW
  scarcity_bearish: > 68,000 MW  AND  SOUTH wind STWPF @HE20 >= 2,000 MW
                                 AND  COASTAL wind STWPF @HE20 >= 2,000 MW
                    (v2 criterion, user-confirmed 2026-08-24: per-region HE20 snapshot.
                     v1 region-average >= 2.5 GW caught only 2/12 scarcity days;
                     v2 splits 6/6 with evening basis separation -34.8 vs -9.1 $/MWh)
  scarcity_lambda : > 68,000 MW  AND  wind below threshold (GKS RT follows ERCOT lambda)

Supplementary (ex-post) split of scarcity days by REALIZED evening basis
  basis = RTLMP_GKS - RTLMP_HB_BUSAVG, avg HE18-22; <= -15 $/MWh -> bearish_realized.

Market stat  (GKS DA-RT virtual): spread = DA - RT at GKS_BESS_RN.
  short win  = spread > 0.  P/L ratio = mean(spread|>0) / mean(-spread|<0).
Our actuals  (Tenaska award):
  short_MWh = max(DA_Sales_Qty - RT_Generation_Qty, 0)   per hour
  long_MWh  = max(DA_Purchases_Qty - RT_Consumption_Qty, 0)
  pnl_usd   = short*spread + long*(-spread)
  win = pnl > 0 among hours with position >= 1 MWh.

Outputs: derived/hourly_master.csv, derived/day_regimes.csv, derived/regime_stats.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[5]
ADHOC = Path(__file__).resolve().parents[1]
RAW = ADHOC / "raw"
DERIVED = ADHOC / "derived"
DERIVED.mkdir(parents=True, exist_ok=True)
PNL_DIR = PROJECT_ROOT / "shared" / "data" / "pnl" / "gks" / "hourly"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

START, END = "2026-07-01", "2026-08-23"
NETLOAD_THRESH = 68_000.0
WIND_THRESH = 2_000.0   # per-region, HE20 snapshot
WIND_HE = 20
EVENING_HE = list(range(18, 23))          # HE18-22 evening peak window
MIN_POS_MWH = 1.0

BLOCKS = {
    "HE1-6 overnight": range(1, 7),
    "HE7-14 solar": range(7, 15),
    "HE15-17 ramp": range(15, 18),
    "HE18-22 evening": range(18, 23),
    "HE23-24 late": range(23, 25),
}

# ---------- 1. Yes Energy master ----------
ye = pd.read_csv(RAW / "ye_lmp_fc.csv")
ye = ye.rename(columns={
    "GKS_BESS_RN (DALMP)": "da",
    "GKS_BESS_RN (RTLMP)": "rt",
    "ERCOT (NET_LOAD_FORECAST_BID_CLOSE)": "netload_fc",
    "GR_SOUTH (WIND_STWPF_BIDCLOSE)": "wind_south_fc",
    "GR_COASTAL (WIND_STWPF_BIDCLOSE)": "wind_coastal_fc",
})
ye["date"] = pd.to_datetime(ye["MARKETDAY"]).dt.date.astype(str)
ye["he"] = ye["HOURENDING"].astype(int)
ye = ye[(ye["date"] >= START) & (ye["date"] <= END)]
for c in ["da", "rt", "netload_fc", "wind_south_fc", "wind_coastal_fc"]:
    ye[c] = pd.to_numeric(ye[c], errors="coerce")
ye["spread"] = ye["da"] - ye["rt"]

hb = pd.read_csv(RAW / "ye_busavg.csv").rename(columns={"HB_BUSAVG (RTLMP)": "rt_hub"})
ye = ye.merge(hb[["MARKETDAY", "HOURENDING", "rt_hub"]], on=["MARKETDAY", "HOURENDING"], how="left")
ye["basis"] = ye["rt"] - pd.to_numeric(ye["rt_hub"], errors="coerce")

# ---------- 2. Day regimes ----------
regimes = []
for d, g in ye.groupby("date"):
    peak_nl = g["netload_fc"].max()
    ev = g[g["he"].isin(EVENING_HE)]
    basis_ev = ev["basis"].mean()
    h20 = g[g["he"] == WIND_HE]
    ws20 = float(h20["wind_south_fc"].iloc[0]) if len(h20) else float("nan")
    wc20 = float(h20["wind_coastal_fc"].iloc[0]) if len(h20) else float("nan")
    if pd.isna(peak_nl):
        reg = "unknown"
    elif peak_nl <= NETLOAD_THRESH:
        reg = "normal"
    elif ws20 >= WIND_THRESH and wc20 >= WIND_THRESH:
        reg = "scarcity_bearish"
    else:
        reg = "scarcity_lambda"
    if peak_nl <= NETLOAD_THRESH:
        reg_rlz = "normal"
    else:
        reg_rlz = "scarcity_bearish_rlz" if basis_ev <= -15.0 else "scarcity_lambda_rlz"
    regimes.append({"date": d, "peak_netload_fc": round(float(peak_nl), 1),
                    "wind_south_fc_he20": round(ws20, 1),
                    "wind_coastal_fc_he20": round(wc20, 1),
                    "evening_basis_rt": round(float(basis_ev), 1),
                    "regime": reg, "regime_realized": reg_rlz})
day_reg = pd.DataFrame(regimes)
day_reg.to_csv(DERIVED / "day_regimes.csv", index=False)
ye = ye.merge(day_reg[["date", "regime", "regime_realized"]], on="date")

# ---------- 3. Tenaska hourly positions ----------
rows = []
missing_days = []
for d in sorted(ye["date"].unique()):
    p = PNL_DIR / f"{d}_energy_as_detail.json"
    if not p.exists():
        missing_days.append(d)
        continue
    data = json.loads(p.read_text(encoding="utf-8"))
    for r in data:
        if r.get("datapoint") in ("DA_Sales_Qty", "DA_Purchases_Qty",
                                  "RT_Generation_Qty", "RT_Consumption_Qty"):
            rows.append(r)
if missing_days:
    print(f"WARN missing Tenaska days ({len(missing_days)}): {missing_days}")

tk = pd.DataFrame(rows)
tk["value"] = pd.to_numeric(tk["value"], errors="coerce").fillna(0.0)
ts = pd.to_datetime(tk["interval_start_utc"], utc=True).dt.tz_convert("America/Chicago")
tk["date"] = ts.dt.date.astype(str)
tk["he"] = ts.dt.hour + 1
pos = tk.pivot_table(index=["date", "he"], columns="datapoint", values="value",
                     aggfunc="sum").reset_index().fillna(0.0)
for c in ["DA_Sales_Qty", "DA_Purchases_Qty", "RT_Generation_Qty", "RT_Consumption_Qty"]:
    if c not in pos.columns:
        pos[c] = 0.0
pos["short_mwh"] = (pos["DA_Sales_Qty"] - pos["RT_Generation_Qty"]).clip(lower=0)
pos["long_mwh"] = (pos["DA_Purchases_Qty"] - pos["RT_Consumption_Qty"]).clip(lower=0)

m = ye.merge(pos[["date", "he", "short_mwh", "long_mwh",
                  "DA_Sales_Qty", "DA_Purchases_Qty",
                  "RT_Generation_Qty", "RT_Consumption_Qty"]],
             on=["date", "he"], how="left")
m[["short_mwh", "long_mwh"]] = m[["short_mwh", "long_mwh"]].fillna(0.0)
m["our_pnl"] = m["short_mwh"] * m["spread"] - m["long_mwh"] * m["spread"]
m["has_pos"] = (m["short_mwh"] + m["long_mwh"]) >= MIN_POS_MWH
m.to_csv(DERIVED / "hourly_master.csv", index=False)


# ---------- 4. Stats ----------
def market_stats(g: pd.DataFrame) -> dict:
    s = g["spread"].dropna()
    n = len(s)
    wins, losses = s[s > 0], s[s < 0]
    wr = len(wins) / n if n else None
    pl = (wins.mean() / -losses.mean()) if len(wins) and len(losses) else None
    return {
        "n_hours": n,
        "short_winrate": round(wr, 3) if wr is not None else None,
        "short_pl_ratio": round(float(pl), 2) if pl is not None else None,
        "avg_spread": round(float(s.mean()), 2) if n else None,
        "avg_win_spread": round(float(wins.mean()), 2) if len(wins) else None,
        "avg_loss_spread": round(float(-losses.mean()), 2) if len(losses) else None,
    }


def our_stats(g: pd.DataFrame) -> dict:
    gp = g[g["has_pos"]]
    n = len(gp)
    pnl = gp["our_pnl"]
    wins, losses = pnl[pnl > 0], pnl[pnl < 0]
    wr = len(wins) / n if n else None
    pl = (wins.mean() / -losses.mean()) if len(wins) and len(losses) else None
    return {
        "n_hours_with_pos": n,
        "n_short_hours": int((gp["short_mwh"] >= MIN_POS_MWH).sum()),
        "n_long_hours": int((gp["long_mwh"] >= MIN_POS_MWH).sum()),
        "short_mwh_sum": round(float(gp["short_mwh"].sum()), 1),
        "long_mwh_sum": round(float(gp["long_mwh"].sum()), 1),
        # per-leg average volume per participating hour (sum / leg hours)
        "short_mwh_avg": round(float(gp.loc[gp["short_mwh"] >= MIN_POS_MWH, "short_mwh"].mean()), 1)
                         if (gp["short_mwh"] >= MIN_POS_MWH).any() else None,
        "long_mwh_avg": round(float(gp.loc[gp["long_mwh"] >= MIN_POS_MWH, "long_mwh"].mean()), 1)
                        if (gp["long_mwh"] >= MIN_POS_MWH).any() else None,
        "participation": round(n / len(g), 3) if len(g) else None,
        "winrate": round(wr, 3) if wr is not None else None,
        "pl_ratio": round(float(pl), 2) if pl is not None else None,
        "avg_short_mwh": round(float(gp["short_mwh"].mean()), 1) if n else None,
        "avg_long_mwh": round(float(gp["long_mwh"].mean()), 1) if n else None,
        "total_pnl_usd": round(float(pnl.sum()), 0) if n else 0,
        "avg_pnl_per_hr": round(float(pnl.mean()), 1) if n else None,
        "share_short_hours": round(float((gp["short_mwh"] > gp["long_mwh"]).mean()), 3) if n else None,
    }


out: dict = {
    "period": {"start": START, "end": END},
    "thresholds": {"peak_netload_mw": NETLOAD_THRESH,
                   "wind_per_region_he20_mw": WIND_THRESH,
                   "evening_he": [min(EVENING_HE), max(EVENING_HE)], "min_pos_mwh": MIN_POS_MWH},
    "day_counts": day_reg["regime"].value_counts().to_dict(),
    "missing_tenaska_days": missing_days,
    "regimes": {},
}

def regime_block(gr: pd.DataFrame, n_days: int) -> dict:
    r: dict = {"n_days": n_days,
               "overall": {"market": market_stats(gr), "ours": our_stats(gr)},
               "by_he": {}, "by_block": {}}
    for he, gh in gr.groupby("he"):
        r["by_he"][int(he)] = {"market": market_stats(gh), "ours": our_stats(gh)}
    for bname, hes in BLOCKS.items():
        gb = gr[gr["he"].isin(list(hes))]
        r["by_block"][bname] = {"market": market_stats(gb), "ours": our_stats(gb)}
    return r


for reg, gr in m.groupby("regime"):
    out["regimes"][reg] = regime_block(gr, int((day_reg["regime"] == reg).sum()))

out["regimes_realized"] = {}
out["day_counts_realized"] = day_reg["regime_realized"].value_counts().to_dict()
for reg, gr in m.groupby("regime_realized"):
    if reg == "normal":
        continue  # identical to forecast-based normal
    out["regimes_realized"][reg] = regime_block(gr, int((day_reg["regime_realized"] == reg).sum()))

(DERIVED / "regime_stats.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

print("day counts:", out["day_counts"])
print(day_reg.groupby("regime")[["peak_netload_fc", "wind_south_fc_he20", "wind_coastal_fc_he20", "evening_basis_rt"]].mean().round(0))
for reg, r in out["regimes"].items():
    mk, us = r["overall"]["market"], r["overall"]["ours"]
    print(f"\n[{reg}] days={r['n_days']}")
    print(f"  market: short WR={mk['short_winrate']} PL={mk['short_pl_ratio']} avg_spread={mk['avg_spread']}")
    print(f"  ours  : WR={us['winrate']} PL={us['pl_ratio']} part={us['participation']} "
          f"pnl=${us['total_pnl_usd']:,.0f}")
print("\n-> derived/regime_stats.json, hourly_master.csv, day_regimes.csv")
