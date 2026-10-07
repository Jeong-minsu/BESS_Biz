"""
GKS AS recap v2 — WITH real RT AS data (2026-01-01 .. 2026-05-10).
Supersedes script 70 (which assumed RT AS = 0; that was wrong — RT AS imbalance
revenue lives in Settlement-Charge-Details, backfilled by scripts 72/73).

Products: NSPIN, RRS, ECRS.
ERCOT RTC+B settlement (sign confirmed by script 73):
  net AS revenue = DA_AS_revenue - RT{P}IMBAMT
  RT{P}IMBAMT    = (DA_qty - RT_qty) * RT_MCPC   = cost of buying back capacity in RT
  buyback_qty    = RT{P}IMBAMT / RT_MCPC
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ADHOC = Path(__file__).resolve().parents[1]
DERIVED = ADHOC / "derived"
CAP = 100.0

m = pd.read_parquet(DERIVED / "master_hourly.parquet")
m["hour_ct"] = pd.to_datetime(m["datetime_ct"], utc=True).dt.tz_convert("America/Chicago").dt.floor("h")
hr = pd.read_parquet(DERIVED / "gks_as_hourly_full.parquet")  # product, hour_ct, da/rt/buyback/extra/rt_mcpc/imb_amt

PROD = {
    "NSPIN": ("GKS_DA_NS_Amt",   "AS_MCPC_NSPIN"),
    "RRS":   ("GKS_DA_RRS_Amt",  "AS_MCPC_RRS"),
    "ECRS":  ("GKS_DA_ECRS_Amt", "AS_MCPC_ECRS"),
}
H = len(m)
print(f"=== GKS AS RECAP v2  {m.hour_ct.min():%Y-%m-%d} .. {m.hour_ct.max():%Y-%m-%d}  ({H} hours) ===\n")

# merge DA price/revenue onto the hourly RT-AS frame
rows = []
detail = {}
for p, (da_amt_col, da_px_col) in PROD.items():
    s = hr[hr["product"] == p].merge(
        m[["hour_ct", da_amt_col, da_px_col]], on="hour_ct", how="left")
    s = s.rename(columns={da_amt_col: "da_rev", da_px_col: "da_mcpc"})
    s["da_rev"] = s["da_rev"].fillna(0.0)
    da_rev   = s["da_rev"].sum()
    rt_imb   = s["imb_amt"].sum()                    # cost of buyback
    net_rev  = da_rev - rt_imb
    # net AS = RT_qty*DA_MCPC + buyback_qty*(DA_MCPC-RT_MCPC)
    #   term2 = financial spread captured on the MW that were bought back
    #   vs. holding those MW to delivery, the AS-$ opportunity cost = RT_buyback_cost (=rt_imb)
    s["buyback_pnl"] = (s["da_mcpc"] - s["rt_mcpc"]) * s["buyback_qty"]
    bb_pnl = s["buyback_pnl"].sum()
    bb_mwh = s["buyback_qty"].sum()
    rows.append(dict(
        product=p,
        avg_DA_qty=s["da_qty"].mean(),
        avg_RT_delivered_qty=s["rt_qty"].mean(),
        avg_RT_buyback_qty=s["buyback_qty"].mean(),
        avg_RT_extra_sale_qty=s["extra_sale_qty"].mean(),
        buyback_rate_pct=s["buyback_qty"].sum() / max(s["da_qty"].sum(), 1e-9) * 100,
        avg_DA_price=s["da_mcpc"].mean(),
        avg_RT_price=s["rt_mcpc"].mean(),
        avg_DA_price_when_sold=s.loc[s["da_qty"] > 0, "da_mcpc"].mean(),
        avg_RT_price_when_buyback=s.loc[s["buyback_qty"] > 0.05, "rt_mcpc"].mean(),
        DA_revenue=da_rev,
        RT_buyback_cost=rt_imb,                # = AS-$ opportunity cost vs holding to delivery
        net_AS_revenue=net_rev,
        spread_captured_on_buyback=bb_pnl,     # (DA-RT)*buyback_qty: financial spread on bought-back MW
        buyback_MWh=bb_mwh,
    ))
    detail[p] = s

rec = pd.DataFrame(rows).set_index("product")
pd.set_option("display.width", 240)
pd.set_option("display.float_format", lambda x: f"{x:,.2f}")
print("--- Q1+Q2: per-product actuals (hourly-mean MW, $/MW prices, $ totals) ---")
print(rec.T.to_string())
print()

tot_da   = rec["DA_revenue"].sum()
tot_imb  = rec["RT_buyback_cost"].sum()
tot_net  = rec["net_AS_revenue"].sum()
tot_bbpnl= rec["spread_captured_on_buyback"].sum()
print(f"TOTAL  DA AS revenue = ${tot_da:,.0f}   - RT buyback cost ${tot_imb:,.0f}   "
      f"= net AS ${tot_net:,.0f}")
print(f"       spread captured on bought-back MW (DA-RT)*bb = ${tot_bbpnl:+,.0f}")
print(f"       (RT buyback cost ${tot_imb:,.0f} = AS-$ given up vs holding; justified only if "
      f"freed battery earned more in RT energy)\n")

# --- Q3: was the buyback profitable? per-hour spread on bought-back MW ---
print("--- Q3: was GKS's RT buyback profitable?  (P&L = (DA_MCPC - RT_MCPC) * buyback_qty) ---")
for p in PROD:
    s = detail[p]
    bb = s[s["buyback_qty"] > 0.05]
    if len(bb) == 0:
        continue
    win = (bb["buyback_pnl"] > 0).mean() * 100
    print(f"  {p:6s}  hrs w/ buyback={len(bb):4d}  avg buyback={bb['buyback_qty'].mean():5.1f}MW  "
          f"avg DA_MCPC={bb['da_mcpc'].mean():5.2f}  avg RT_MCPC={bb['rt_mcpc'].mean():5.2f}  "
          f"spread={bb['da_mcpc'].mean()-bb['rt_mcpc'].mean():+5.2f}  win%={win:4.1f}  "
          f"P&L=${bb['buyback_pnl'].sum():+,.0f}")
print()

# --- Q3b: counterfactual — sell 100MW NSPIN DA every hour + buy 100MW back in RT ---
print("--- Q3b: counterfactual 'sell 100MW DA + buy 100MW back in RT, every hour' = pure DA-RT spread ---")
for p in PROD:
    s = detail[p]
    sp = s["da_mcpc"] - s["rt_mcpc"]
    print(f"  {p:6s}  DA-RT spread mean=${sp.mean():5.2f}  median=${sp.median():5.2f}  win%={(sp>0).mean()*100:4.1f}  "
          f"100MW all-hours P&L=${(sp*CAP).sum():+,.0f}  worst hr=${(sp*CAP).min():,.0f}")
print()

rec.reset_index().to_json(DERIVED / "gks_as_recap_v2.json", orient="records", indent=1)
out = {
    "window": [str(m.hour_ct.min().date()), str(m.hour_ct.max().date())], "hours": H,
    "total": {"DA_revenue": tot_da, "RT_buyback_cost": tot_imb, "net_AS_revenue": tot_net,
              "buyback_PnL_vs_hold": tot_bbpnl},
    "by_product": rec.to_dict(orient="index"),
}
(DERIVED / "gks_as_recap_v2_summary.json").write_text(json.dumps(out, indent=1, default=float))
print(f"saved -> derived/gks_as_recap_v2.json, gks_as_recap_v2_summary.json")
