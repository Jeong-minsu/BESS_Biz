"""ITEM 3a — extract a small node-filtered DA/RT panel from raw/price_panel/*.parquet.
Nodes: RVN_RN, GKS_BESS_RN, hubs (BUSAVG/HUBAVG/HOUSTON/SOUTH), proxy candidates.
DATETIME in the panel is period-ending (hour-ending) America/Chicago; HE derived per FLOWDAY.
Output: derived/item3a_node_panel.parquet  (one row per node x hour)
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
NODES = {
    10019925379: "RVN_RN", 10017907494: "GKS_BESS_RN",
    10000698380: "HB_BUSAVG", 10000698382: "HB_HUBAVG",
    10000697077: "HB_HOUSTON", 10000697079: "HB_SOUTH",
    10017290064: "RBN_BESS1", 10016969364: "TAV_RN", 10001765766: "CBEC_ALL",
}
parts = []
for f in sorted((ROOT / "raw/price_panel").glob("*.parquet")):
    df = pd.read_parquet(f, columns=["OBJECTID", "DATETIME", "DALMP", "RTLMP", "FLOWDAY"])
    df = df[df.OBJECTID.isin(NODES)]
    parts.append(df)
p = pd.concat(parts, ignore_index=True)
p["NODE"] = p.OBJECTID.map(NODES)
p["DATETIME"] = pd.to_datetime(p.DATETIME, format="%m/%d/%Y %H:%M:%S")
p["FLOWDAY"] = pd.to_datetime(p.FLOWDAY).dt.normalize()
# hour-ending: HE = rank of the period within the flowday (1..24; 23/25 on DST days)
p = p.sort_values(["NODE", "FLOWDAY", "DATETIME"])
p["HE"] = p.groupby(["NODE", "FLOWDAY"]).cumcount() + 1
p["SPREAD"] = p.DALMP - p.RTLMP  # spread = DA - RT (positive => short wins)
p = p.drop(columns="OBJECTID")
p.to_parquet(ROOT / "derived/item3a_node_panel.parquet", index=False)
print(p.groupby("NODE").agg(n=("HE", "size"), first=("FLOWDAY", "min"), last=("FLOWDAY", "max"),
                            da_nan=("DALMP", lambda s: s.isna().sum()), rt_nan=("RTLMP", lambda s: s.isna().sum())))
# encoding check: how is midnight represented? sample one flowday
s = p[(p.NODE == "RVN_RN") & (p.FLOWDAY == "2026-08-01")][["DATETIME", "HE", "DALMP", "RTLMP"]]
print(s.head(3).to_string(), "\n", s.tail(3).to_string())
print(p[p.NODE == "RVN_RN"].groupby("FLOWDAY").size().value_counts())
