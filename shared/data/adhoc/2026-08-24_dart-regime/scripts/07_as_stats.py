# -*- coding: utf-8 -*-
"""
DART regime analysis #07 — DA-RT AS MCPC spread stats (RRS / ECRS / NSPIN),
normal vs scarcity day, same format as the DART market stats.

spread = DA_MCPC - RT_MCPC (hourly; RT = mean of intra-hour intervals).
AS MCPC is ERCOT system-wide (not nodal) -> no GKS/congestion dimension.

Output: derived/as_stats.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ADHOC = Path(__file__).resolve().parents[1]
DERIVED = ADHOC / "derived"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PRODUCTS = ["RRS", "ECRS", "NSPIN"]
BLOCKS = {
    "HE1-6 overnight": range(1, 7),
    "HE7-14 solar": range(7, 15),
    "HE15-17 ramp": range(15, 18),
    "HE18-22 evening": range(18, 23),
    "HE23-24 late": range(23, 25),
}

dam = pd.read_parquet(ADHOC / "raw" / "as_dam_hourly.parquet")
rt = pd.read_parquet(ADHOC / "raw" / "as_rt_hourly.parquet")
day_reg = pd.read_csv(DERIVED / "day_regimes.csv")
day_reg["bucket"] = day_reg["regime"].map(
    lambda r: "normal" if r == "normal" else "scarcity")

m = dam.merge(rt, on=["date", "he"], suffixes=("_da", "_rt"))
m = m.merge(day_reg[["date", "bucket", "regime"]], on="date")
for p in PRODUCTS:
    m[f"sp_{p}"] = pd.to_numeric(m[f"{p}_da"], errors="coerce") - \
                   pd.to_numeric(m[f"{p}_rt"], errors="coerce")


def stats(s: pd.Series) -> dict:
    s = s.dropna()
    n = len(s)
    wins, losses = s[s > 0], s[s < 0]
    wr = len(wins) / n if n else None
    pl = (wins.mean() / -losses.mean()) if len(wins) and len(losses) else None
    return {
        "n_hours": n,
        "short_winrate": round(wr, 3) if wr is not None else None,
        "short_pl_ratio": round(float(pl), 2) if pl is not None else None,
        "avg_spread": round(float(s.mean()), 2) if n else None,
        "avg_da": None, "avg_rt": None,
    }


out = {"period": {"start": m["date"].min(), "end": m["date"].max()},
       "note": "AS MCPC is ERCOT system-wide; spread = DA_MCPC - hourly-mean RT MCPC "
               "(np6-331 15-min through 2026-07-30, np6-332 SCED-interval after).",
       "day_counts": day_reg["bucket"].value_counts().to_dict(),
       "products": {}}

for p in PRODUCTS:
    pr: dict = {}
    for bucket, gb in m.groupby("bucket"):
        r: dict = {"overall": stats(gb[f"sp_{p}"]),
                   "avg_da": round(float(pd.to_numeric(gb[f"{p}_da"], errors="coerce").mean()), 2),
                   "avg_rt": round(float(pd.to_numeric(gb[f"{p}_rt"], errors="coerce").mean()), 2),
                   "by_block": {}, "by_he": {}}
        for bname, hes in BLOCKS.items():
            r["by_block"][bname] = stats(gb[gb["he"].isin(list(hes))][f"sp_{p}"])
        for he, gh in gb.groupby("he"):
            r["by_he"][int(he)] = stats(gh[f"sp_{p}"])
        pr[bucket] = r
    out["products"][p] = pr

(DERIVED / "as_stats.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

print("day counts:", out["day_counts"])
for p in PRODUCTS:
    for bucket in ["normal", "scarcity"]:
        r = out["products"][p][bucket]
        o = r["overall"]
        print(f"{p:6} {bucket:9} DA~{r['avg_da']:>6} RT~{r['avg_rt']:>6} | "
              f"sWR={o['short_winrate']} sPL={o['short_pl_ratio']} avg_sp={o['avg_spread']}")
print("-> derived/as_stats.json")
