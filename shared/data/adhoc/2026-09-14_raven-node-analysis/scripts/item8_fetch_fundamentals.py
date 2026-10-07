"""ITEM 8 - fetch daily fundamentals for the TB2 driver decomposition (real data only, Yes Energy datalake).

Series (system-wide, daily aggregates) 2021-01-01 .. 2026-09-13, one row per flowday:
  hub prices  : ercot/prices/lmp/hourly   -> HB_HUBAVG (10000698382) + HB_HOUSTON (10000697077) DA/RT hourly
                (only fetched for 2021-01-01..2023-08-31; 2023-09+ already in raw/price_panel)
  fundamentals: ercot/load/rtload_hourly, ercot/gen/wind_rti, ercot/gen/generation_solar_rt  (SYS 10000712973)
                (only 2021-01-01..2023-11-30; 2023-12+ already in raw/item6_fundamentals.parquet)
  gas         : ercot/prices/gas/weighted_avg -> Houston Ship Channel (10000002639), Katy (10000002647)
  op reserve  : ercot/gen/op_reserve_5min -> daily min / p05 / mean  (starts 2022-07-21)
  storage gen : ercot/gen/ercotpwrstgenrt -> daily max discharge MW  (starts 2023-01-24)
Idempotent: each series has its own parquet in raw/item8/; days already present are skipped.
"""
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import dl  # noqa: E402

OUT = ROOT / "raw" / "item8"
OUT.mkdir(parents=True, exist_ok=True)
SYS = 10000712973
HUBS = {10000698382: "HB_HUBAVG", 10000697077: "HB_HOUSTON"}
GAS = {10000002639: "gas_hsc", 10000002647: "gas_katy"}
END = "2026-09-13"


def _dt(s):
    return pd.to_datetime(s, format="%m/%d/%Y %H:%M:%S")


def hub_prices(d):
    ds = d.strftime("%Y%m%d")
    df = dl.try_read_csv(f"ercot/prices/lmp/hourly/{ds}.csv.gz", header=None)
    if df is None:
        return None
    df = df[df[0].isin(HUBS)]
    out = pd.DataFrame({"node": df[0].map(HUBS), "hour_end": _dt(df[1]), "DALMP": df[3], "RTLMP": df[6]})
    out["flowday"] = d
    return out


def fundamentals(d):
    ds = d.strftime("%Y%m%d")
    cols = {}
    for c, path in {"load_mw": "ercot/load/rtload_hourly", "wind_mw": "ercot/gen/wind_rti",
                    "solar_mw": "ercot/gen/generation_solar_rt"}.items():
        df = dl.try_read_csv(f"{path}/{ds}.csv.gz", header=None)
        if df is None:
            continue
        df = df[df[0] == SYS]
        s = pd.Series(df[4].values, index=_dt(df[2]).values)
        cols[c] = s.groupby(level=0).mean()
    if not cols:
        return None
    out = pd.DataFrame(cols)
    out.index.name = "hour_end"
    out["flowday"] = d
    return out.reset_index()


def gas(d):
    ds = d.strftime("%Y%m%d")
    df = dl.try_read_csv(f"ercot/prices/gas/weighted_avg/{ds}.csv.gz", header=None)
    if df is None:
        return None
    df = df[df[0].isin(GAS)]
    row = {GAS[k]: v for k, v in zip(df[0], df[4])}
    row["flowday"] = d
    return pd.DataFrame([row])


def op_reserve(d):
    ds = d.strftime("%Y%m%d")
    df = dl.try_read_csv(f"ercot/gen/op_reserve_5min/{ds}.csv.gz", header=None)
    if df is None or df.empty:
        return None
    v = pd.to_numeric(df[4], errors="coerce").dropna()
    return pd.DataFrame([{"flowday": d, "opres_min": v.min(), "opres_p05": v.quantile(0.05),
                          "opres_mean": v.mean(), "opres_n": len(v)}])


def storage(d):
    ds = d.strftime("%Y%m%d")
    df = dl.try_read_csv(f"ercot/gen/ercotpwrstgenrt/{ds}.csv.gz", header=None)
    if df is None or df.empty:
        return None
    v = pd.to_numeric(df[4], errors="coerce").dropna()
    return pd.DataFrame([{"flowday": d, "stor_max_mw": v.max(), "stor_mean_mw": v.mean()}])


JOBS = {
    "hub_prices": (hub_prices, "2021-01-01", "2023-08-31"),
    "fundamentals": (fundamentals, "2021-01-01", "2023-11-30"),
    "gas": (gas, "2021-01-01", END),
    "op_reserve": (op_reserve, "2022-07-21", END),
    "storage": (storage, "2023-01-24", END),
}


def run(name):
    fn, a, b = JOBS[name]
    path = OUT / f"{name}.parquet"
    days = pd.date_range(a, b, freq="D")
    have, parts = set(), []
    if path.exists():
        old = pd.read_parquet(path)
        have = set(pd.to_datetime(old.flowday).unique())
        parts = [old]
    todo = [d for d in days if d not in have]
    print(f"[{name}] cached {len(have)} / todo {len(todo)}", flush=True)
    with ThreadPoolExecutor(max_workers=16) as ex:
        for i, r in enumerate(ex.map(fn, todo)):
            if r is not None:
                parts.append(r)
            if i % 200 == 0:
                print(f"[{name}] {i}/{len(todo)}", flush=True)
    if parts:
        f = pd.concat(parts, ignore_index=True)
        f["flowday"] = pd.to_datetime(f["flowday"])
        f = f.sort_values("flowday").reset_index(drop=True)
        f.to_parquet(path, index=False)
        print(f"[{name}] saved {f.shape} {f.flowday.min().date()} .. {f.flowday.max().date()}", flush=True)


if __name__ == "__main__":
    names = sys.argv[1:] or list(JOBS)
    for n in names:
        run(n)
