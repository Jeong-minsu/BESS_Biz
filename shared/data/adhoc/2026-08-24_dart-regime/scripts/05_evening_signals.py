# -*- coding: utf-8 -*-
"""
DART regime analysis #05 — screen ex-ante (bid-close) macro signals for
HE20-22 DART short/long at GKS, 2026-06-01 .. 2026-08-23.

Target per day: HE20-22 avg spread (DA-RT) and per-hour sign.
All features are D-1 bid-close vintage (leakage-free).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ADHOC = Path(__file__).resolve().parents[1]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ye = pd.read_csv(ADHOC / "raw" / "ye_signals_jun_aug.csv").rename(columns={
    "GKS_BESS_RN (DALMP)": "da", "GKS_BESS_RN (RTLMP)": "rt",
    "HB_BUSAVG (RTLMP)": "rt_hub",
    "ERCOT (NET_LOAD_FORECAST_BID_CLOSE)": "nl",
    "GR_SOUTH (WIND_STWPF_BIDCLOSE)": "ws",
    "GR_COASTAL (WIND_STWPF_BIDCLOSE)": "wc",
    "GR_WEST (WIND_STWPF_BIDCLOSE)": "ww",
    "ERCOT (WIND_COPHSL_BIDCLOSE)": "wsys",
    "ERCOT (SOLAR_COPHSL_BIDCLOSE)": "ssys",
})
for c in ["da", "rt", "rt_hub", "nl", "ws", "wc", "ww", "wsys", "ssys"]:
    ye[c] = pd.to_numeric(ye[c], errors="coerce")
ye["date"] = pd.to_datetime(ye["MARKETDAY"]).dt.date.astype(str)
ye["he"] = ye["HOURENDING"].astype(int)
ye["spread"] = ye["da"] - ye["rt"]
ye["basis"] = ye["rt"] - ye["rt_hub"]

# ---- per-day features (all FC, bid-close) ----
rows = []
for d, g in ye.groupby("date"):
    gi = g.set_index("he")
    w2021 = gi.loc[[20, 21]]
    tgt = gi.loc[[20, 21, 22]]
    ramp = gi.loc[21, "nl"] - gi.loc[17, "nl"]
    rows.append({
        "date": d,
        "peak_nl": g["nl"].max(),
        "nl_ev": tgt["nl"].mean(),
        "ws2021": w2021["ws"].mean(), "wc2021": w2021["wc"].mean(),
        "ww2021": w2021["ww"].mean(),
        "wsys_ev": tgt["wsys"].mean(),
        "ramp_17_21": ramp,
        "solar_he19": gi.loc[19, "ssys"],
        # targets (realized)
        "sp_ev": tgt["spread"].mean(),
        "sp_pos_hrs": int((tgt["spread"] > 0).sum()),
        "basis_ev": tgt["basis"].mean(),
    })
f = pd.DataFrame(rows)
f["w_sc"] = f["ws2021"] + f["wc2021"]
f["west_ratio"] = f["ww2021"] / f["w_sc"]          # west vs south+coastal
f["scarcity"] = f["peak_nl"] > 68_000
f["user_rule"] = (f["ws2021"] >= 2500) & (f["wc2021"] >= 2500)
f["v2_rule"] = (f["ws2021"] >= 2000) & (f["wc2021"] >= 2000)

f.to_csv(ADHOC / "derived" / "evening_signals.csv", index=False)


def bucket_report(name, mask):
    a, b = f[mask], f[~mask]
    def s(x):
        if not len(x):
            return "n=0"
        wr = (x["sp_ev"] > 0).mean()
        return (f"n={len(x):>2} | short day-WR {wr*100:3.0f}% | E[spread] {x['sp_ev'].mean():+6.1f} "
                f"| med {x['sp_ev'].median():+6.1f} | worst {x['sp_ev'].min():+7.1f} | basis {x['basis_ev'].mean():+6.1f}")
    print(f"--- {name}")
    print(f"  TRUE : {s(a)}")
    print(f"  FALSE: {s(b)}")


print(f"days={len(f)}  (HE20-22 avg spread; day counted short-win if avg>0)")
print(f"all days: E[spread]={f['sp_ev'].mean():+.1f}, short day-WR={(f['sp_ev']>0).mean()*100:.0f}%")
print()
bucket_report("user rule: ws&wc HE20-21 each >= 2.5GW", f["user_rule"])
bucket_report("v2 rule:   ws&wc HE20-21 each >= 2.0GW", f["v2_rule"])
bucket_report("scarcity only (peak NL > 68GW)", f["scarcity"])
bucket_report("scarcity & v2 wind", f["scarcity"] & f["v2_rule"])
bucket_report("scarcity & NOT v2 wind", f["scarcity"] & ~f["v2_rule"])
bucket_report("west_ratio < 1.0 (west wind < S+C)", f["west_ratio"] < 1.0)
bucket_report("v2 wind & west_ratio < 1.0", f["v2_rule"] & (f["west_ratio"] < 1.0))
bucket_report("scarcity & v2 & west_ratio<1.0", f["scarcity"] & f["v2_rule"] & (f["west_ratio"] < 1.0))
bucket_report("high ramp (NL HE17->21 rise > +3GW)", f["ramp_17_21"] > 3000)
bucket_report("nl_ev > 66GW (evening NL FC)", f["nl_ev"] > 66_000)
print()
print("corr with sp_ev (evening spread):")
for c in ["ws2021", "wc2021", "ww2021", "w_sc", "west_ratio", "wsys_ev",
          "peak_nl", "nl_ev", "ramp_17_21", "solar_he19"]:
    print(f"  {c:12} {f[c].corr(f['sp_ev']):+.2f}   (corr w/ basis {f[c].corr(f['basis_ev']):+.2f})")
