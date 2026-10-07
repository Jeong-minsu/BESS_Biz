"""Fetch panel for rain vs regional wind forecast-error study (real data only, no mock).

1) Regional wind STWPF D+1 forecast, leakage-free vintage (<= D-1 13:59 GMT), 2024-01-01..2026-09-30
2) Regional wind actuals (ercot/gen/wind_rti), same period
3) AG2 hourly observed precipitation, 6 stations (Coastal: KCRP KVCT KIAH / South: KBRO KMFE KLRD),
   6-month chunks
Outputs raw/wind_fc.parquet, raw/wind_act.parquet, raw/precip.parquet (idempotent per part).
"""
from __future__ import annotations
import sys, io, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import requests
import truststore; truststore.inject_into_ssl()

ROOT = Path(__file__).resolve().parents[1]
RAVEN = ROOT.parent / "2026-09-14_raven-node-analysis" / "scripts"
sys.path.insert(0, str(RAVEN))
sys.path.insert(0, str(ROOT.parents[2] / "scripts"))
import dl  # noqa: E402
from _env_loader import load_env_sections  # noqa: E402

OUT = ROOT / "raw"; OUT.mkdir(exist_ok=True)
REGIONS = {10004189450: "west", 10004189446: "coastal", 10004189447: "south",
           10004189449: "north", 10004189445: "panhandle", 10004189442: "gr_ercot"}
START, END = pd.Timestamp("2024-01-01"), pd.Timestamp("2026-09-30")
DAYS = list(pd.date_range(START, END, freq="D"))
STATIONS = {"KCRP": "coastal", "KVCT": "coastal", "KIAH": "coastal",
            "KBRO": "south", "KMFE": "south", "KLRD": "south"}
AG2_BASE = "https://www.wsitrader.com/Services/CSVDownloadService.svc"


def _dt(s):
    return pd.to_datetime(s, format="%m/%d/%Y %H:%M:%S")


# ---------- 1) forecast vintage ----------
def fc_day(d):
    dm1 = (d - pd.Timedelta(days=1)).strftime("%Y%m%d")
    try:
        keys = [k for k, _ in dl.ls(f"ercot/vintage/wind_stwpf/{dm1}")]
        keys = [k for k in keys if Path(k).name[8:12] <= "1359"]
        if not keys:
            return None
        key = sorted(keys)[-1]
        df = dl.read_csv(key, header=None)
    except Exception as e:
        print(f"  !! fc {d.date()} {type(e).__name__}: {e}")
        return None
    df["dt"] = _dt(df[2])
    nxt = d + pd.Timedelta(days=1)
    df = df[(df["dt"] > d) & (df["dt"] <= nxt)]
    df = df[df[0].isin(REGIONS)].copy()
    if df.empty:
        return None
    df["region"] = df[0].map(REGIONS)
    p = df.pivot_table(index="dt", columns="region", values=4, aggfunc="mean")
    p.columns = [f"fc_{c}" for c in p.columns]
    p.index.name = "hour_end"
    p = p.reset_index()
    p["flowday"] = d
    p["vintage"] = Path(key).name[:12]
    return p


def fetch_fc():
    f = OUT / "wind_fc.parquet"
    have = set(pd.read_parquet(f)["flowday"].unique()) if f.exists() else set()
    days = [d for d in DAYS if d not in have]
    print(f"  fc: fetching {len(days)} days")
    with ThreadPoolExecutor(16) as ex:
        parts = [p for p in ex.map(fc_day, days) if p is not None]
    if parts:
        new = pd.concat(parts, ignore_index=True)
        if f.exists():
            new = pd.concat([pd.read_parquet(f), new], ignore_index=True)
        new = new.drop_duplicates(subset=["hour_end"]).sort_values("hour_end")
        new.to_parquet(f, index=False)
        print(f"  fc rows={len(new)} days={new.flowday.nunique()}")


# ---------- 2) actuals ----------
def act_day(d):
    try:
        df = dl.try_read_csv(f"ercot/gen/wind_rti/{d:%Y%m%d}.csv.gz", header=None)
    except Exception as e:
        print(f"  !! act {d.date()} {type(e).__name__}: {e}")
        return None
    if df is None:
        return None
    df = df[df[0].isin(REGIONS)].copy()
    if df.empty:
        return None
    df["region"] = df[0].map(REGIONS)
    p = df.pivot_table(index=_dt(df[2]), columns="region", values=4, aggfunc="mean")
    p.columns = [f"act_{c}" for c in p.columns]
    p.index.name = "hour_end"
    p = p.reset_index()
    p["flowday"] = d
    return p


def fetch_act():
    f = OUT / "wind_act.parquet"
    have = set(pd.read_parquet(f)["flowday"].unique()) if f.exists() else set()
    days = [d for d in DAYS if d not in have]
    print(f"  act: fetching {len(days)} days")
    with ThreadPoolExecutor(16) as ex:
        parts = [p for p in ex.map(act_day, days) if p is not None]
    if parts:
        new = pd.concat(parts, ignore_index=True)
        if f.exists():
            new = pd.concat([pd.read_parquet(f), new], ignore_index=True)
        new = new.drop_duplicates(subset=["hour_end"]).sort_values("hour_end")
        new.to_parquet(f, index=False)
        print(f"  act rows={len(new)} days={new.flowday.nunique()}")


# ---------- 3) AG2 precipitation ----------
def ag2_auth():
    s = load_env_sections().get("ag2", {})
    return {"Account": s["USER"], "Profile": s["Profile"], "Password": s["PASSWORD"]}


def ag2_chunk(auth, station, s, e):
    params = {**auth, "HistoricalProductID": "HISTORICAL_HOURLY_OBSERVED",
              "DataTypes[]": ["precipitation", "windSpeed"], "TempUnits": "F",
              "StartDate": s.strftime("%m/%d/%Y"), "EndDate": e.strftime("%m/%d/%Y"),
              "CityIds[]": station, "timeutc": "false"}
    for attempt in range(3):
        try:
            r = requests.get(f"{AG2_BASE}/GetHistoricalObservations", params=params, timeout=300)
            if r.status_code == 200 and len(r.text) > 50:
                return r.text
            print(f"  AG2 {station} {s.date()} HTTP {r.status_code} len={len(r.text)}")
        except requests.RequestException as ex:
            print(f"  AG2 {station} {s.date()} {type(ex).__name__}: {ex}")
        time.sleep(5 * (attempt + 1))
    return None


def parse_ag2(text, station):
    lines = text.splitlines()
    # first line is station header, second is column names
    df = pd.read_csv(io.StringIO("\n".join(lines[1:])))
    df["station"] = station
    return df


def fetch_precip():
    f = OUT / "precip.parquet"
    if f.exists():
        print("  precip exists, skip"); return
    auth = ag2_auth()
    edges = list(pd.date_range(START, END + pd.Timedelta(days=1), freq="6MS")) + [END + pd.Timedelta(days=1)]
    edges = sorted(set(edges))
    parts, rawdir = [], OUT / "ag2_raw"; rawdir.mkdir(exist_ok=True)
    for st in STATIONS:
        for a, b in zip(edges[:-1], edges[1:]):
            p = rawdir / f"{st}_{a:%Y%m%d}.csv"
            if p.exists():
                txt = p.read_text(encoding="utf-8")
            else:
                txt = ag2_chunk(auth, st, a, b - pd.Timedelta(days=1))
                if txt is None:
                    print(f"  !! {st} {a.date()} failed"); continue
                p.write_text(txt, encoding="utf-8")
            try:
                parts.append(parse_ag2(txt, st))
            except Exception as ex:
                print(f"  !! parse {st} {a.date()}: {ex}\n{txt[:300]}")
            print(f"  {st} {a.date()}..{b.date()} ok")
    if parts:
        df = pd.concat(parts, ignore_index=True)
        df.to_parquet(f, index=False)
        print(f"  precip rows={len(df)} cols={list(df.columns)}")


if __name__ == "__main__":
    which = sys.argv[1:] or ["fc", "act", "precip"]
    if "precip" in which:
        print("[3] AG2 precipitation"); fetch_precip()
    if "fc" in which:
        print("[1] wind STWPF vintage"); fetch_fc()
    if "act" in which:
        print("[2] wind actuals"); fetch_act()
