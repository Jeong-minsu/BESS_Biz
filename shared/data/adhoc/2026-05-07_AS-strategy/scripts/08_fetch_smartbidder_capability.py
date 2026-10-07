"""
Adhoc AS-strategy backfill #08 — Smartbidder /power-availability + /soc-detailed + /outages

Pulls GKS (Kiskadee Storage) physical capability for 2026-01-01 ~ 2026-05-10:
- /power-availability   → hourly charge_power / discharge_power (MW)
- /soc-detailed         → 5-min soc_mwh_max, soc_mwh_min (MWh capability)
- /outages              → planned/unplanned derates (charge/discharge, MW)

Output (per-source raw + derived):
    raw/sb_power_availability.json
    raw/sb_soc_detailed.parquet         (5-min raw)
    raw/sb_outages.json
    derived/sb_capability_hourly.parquet
        cols: datetime_ct, avail_discharge_mw, avail_charge_mw, soc_mwh_max
              (gaps filled with nameplate 100 MW / 200 MWh)
    derived/sb_capability_daily.parquet
        cols: date, avail_discharge_mw_min, avail_charge_mw_min, soc_mwh_max_min

Notes:
- Smartbidder docs: "Power availability data is not required unless an adjustment
  should be made to the node max availability configuration" — many days will
  be 204 / empty (= no derate, use nameplate).
- We pull in monthly chunks to keep per-request payloads bounded.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "shared" / "scripts"))
from _env_loader import load_env_sections, first  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ADHOC = Path(__file__).resolve().parents[1]
RAW = ADHOC / "raw"
DERIVED = ADHOC / "derived"
RAW.mkdir(parents=True, exist_ok=True)
DERIVED.mkdir(parents=True, exist_ok=True)

CPT = ZoneInfo("America/Chicago")
BASE = "https://data.ascendanalytics.com"

START = date(2026, 1, 1)
END   = date(2026, 5, 11)  # exclusive; covers 1/1 ~ 5/10

NAMEPLATE_MW = 100.0
NAMEPLATE_MWH = 200.0


def get_token(sb_section: dict[str, str]) -> str:
    try:
        from msal import ConfidentialClientApplication
    except ImportError:
        sys.exit("pip install msal — required for Smartbidder")
    app_id   = sb_section.get("APPLICATION_ID",
                              "https://dataascendanalyticscom.azurewebsites.net")
    cid      = sb_section.get("CLIENT_ID")
    csecret  = sb_section.get("CLIENT_SECRET")
    tenant   = sb_section.get("_TENANT", "onascend.com")
    if not cid or not csecret:
        sys.exit("Missing Smartbidder CLIENT_ID / CLIENT_SECRET")
    auth = ConfidentialClientApplication(cid, csecret, f"https://login.microsoftonline.com/{tenant}")
    tok = auth.acquire_token_for_client([f"{app_id}/.default"])
    if "access_token" not in tok:
        sys.exit(f"Smartbidder token error: {tok.get('error_description', tok)}")
    return tok["access_token"]


def month_chunks(start: date, end: date):
    cur = start
    while cur < end:
        # advance to first of next month
        if cur.month == 12:
            nxt = date(cur.year + 1, 1, 1)
        else:
            nxt = date(cur.year, cur.month + 1, 1)
        yield cur, min(nxt, end)
        cur = nxt


def sb_get(token: str, path: str, params: dict, retries: int = 4):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    for attempt in range(retries):
        try:
            r = requests.get(f"{BASE}{path}", params=params, headers=headers, timeout=180)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 204:
                return None
            if r.status_code in (401, 403):
                sys.exit(f"Smartbidder {r.status_code} on {path}: {r.text[:200]!r}")
            print(f"  HTTP {r.status_code} {path} try={attempt+1}/{retries}: {r.text[:200]!r}")
        except requests.RequestException as e:
            print(f"  {type(e).__name__} {e} {path} try={attempt+1}/{retries}")
        time.sleep([5, 15, 30, 60][min(attempt, 3)])
    print(f"  ! gave up on {path} {params.get('start_date')}")
    return None


def fetch_paginated_chunked(token, path, client, resource):
    """Returns list of raw records merged across monthly chunks."""
    all_records = []
    for s, e in month_chunks(START, END):
        params = {
            "client": client, "iso": "ERCOT", "resource": resource,
            "start_date": f"{s.isoformat()}T00:00:00-06:00",
            "end_date":   f"{e.isoformat()}T00:00:00-06:00",
            "return_format": "json",
        }
        j = sb_get(token, path, params)
        if j is None:
            print(f"  {path} {s}~{e}: empty (204) or failed")
            continue
        if isinstance(j, dict) and "data" in j and "columns" in j:
            df = pd.DataFrame(j["data"], columns=j["columns"])
            all_records.append(df)
            print(f"  {path} {s}~{e}: {len(df)} rows")
        elif isinstance(j, list):
            df = pd.DataFrame(j)
            all_records.append(df)
            print(f"  {path} {s}~{e}: {len(df)} rows (list)")
        else:
            print(f"  {path} {s}~{e}: unexpected payload shape: {str(j)[:200]!r}")
    if not all_records:
        return pd.DataFrame()
    return pd.concat(all_records, ignore_index=True)


def main():
    print(f"[08_fetch_smartbidder_capability] {START} -> {END} (exclusive)")
    sec = load_env_sections(PROJECT_ROOT / ".env").get("smartbidder", {})
    token = get_token(sec)
    client   = first(sec, "SMARTBIDDER_CLIENT", default="apex")
    resource = first(sec, "Resource", "SMARTBIDDER_RESOURCE", default="Kiskadee Storage")
    print(f"  client={client!r}  resource={resource!r}")

    # -------- /power-availability --------
    print("\n📥 /power-availability ...")
    pa_df = fetch_paginated_chunked(token, "/power-availability", client, resource)
    if not pa_df.empty:
        pa_df.to_json(RAW / "sb_power_availability.json", orient="records", date_format="iso")
        print(f"  saved raw → sb_power_availability.json  shape={pa_df.shape}  cols={pa_df.columns.tolist()}")
    else:
        print("  (no power-availability rows found across full range — using nameplate 100 MW)")

    # -------- /soc-detailed --------
    print("\n📥 /soc-detailed ...")
    soc_df = fetch_paginated_chunked(token, "/soc-detailed", client, resource)
    if not soc_df.empty:
        soc_df.to_parquet(RAW / "sb_soc_detailed.parquet", index=False)
        print(f"  saved raw → sb_soc_detailed.parquet  shape={soc_df.shape}  cols={soc_df.columns.tolist()}")
    else:
        print("  (no soc-detailed rows — using nameplate 200 MWh)")

    # -------- /outages --------
    print("\n📥 /outages ...")
    out_df = fetch_paginated_chunked(token, "/outages", client, resource)
    if not out_df.empty:
        out_df.to_json(RAW / "sb_outages.json", orient="records", date_format="iso")
        print(f"  saved raw → sb_outages.json  shape={out_df.shape}  cols={out_df.columns.tolist()}")
    else:
        print("  (no outages recorded)")

    # ============================================================
    # Derive hourly capability table (datetime_ct hour-start basis)
    # ============================================================
    print("\n🛠  building hourly capability table ...")
    hours = pd.date_range(
        start=pd.Timestamp(START, tz=CPT),
        end=pd.Timestamp(END, tz=CPT),
        freq="h", inclusive="left",
    )
    cap = pd.DataFrame({"datetime_ct": hours})
    cap["avail_discharge_mw"] = NAMEPLATE_MW
    cap["avail_charge_mw"] = NAMEPLATE_MW
    cap["soc_mwh_max"] = NAMEPLATE_MWH

    # Apply /power-availability overrides (period-ending → HE start = ts - 1h)
    if not pa_df.empty:
        ts_col = next((c for c in pa_df.columns if "timestamp" in c.lower()), None)
        if ts_col is not None:
            pa = pa_df.copy()
            pa["ts"] = pd.to_datetime(pa[ts_col], utc=True).dt.tz_convert(CPT)
            # period-ending → period-start
            pa["datetime_ct"] = pa["ts"] - pd.Timedelta(hours=1)
            # power.charge_power / power.discharge_power may be nested or flat
            def _get(d, k):
                if isinstance(d, dict):
                    return d.get(k)
                return None
            if "power" in pa.columns:
                pa["charge_power"] = pa["power"].apply(lambda d: _get(d, "charge_power"))
                pa["discharge_power"] = pa["power"].apply(lambda d: _get(d, "discharge_power"))
            for c in ("charge_power", "discharge_power"):
                if c not in pa.columns:
                    pa[c] = None
            pa = pa[["datetime_ct", "charge_power", "discharge_power"]].dropna(how="all", subset=["charge_power", "discharge_power"])
            print(f"  /power-availability override rows: {len(pa)}")
            cap = cap.merge(pa, on="datetime_ct", how="left")
            cap["avail_discharge_mw"] = cap["discharge_power"].combine_first(cap["avail_discharge_mw"]).clip(0, NAMEPLATE_MW)
            cap["avail_charge_mw"]    = cap["charge_power"].combine_first(cap["avail_charge_mw"]).clip(0, NAMEPLATE_MW)
            cap = cap.drop(columns=["charge_power", "discharge_power"])

    # Apply /soc-detailed: take 5-min soc_mwh_max → hourly min (most conservative cap)
    if not soc_df.empty and "soc_mwh_max" in soc_df.columns:
        soc = soc_df.copy()
        ts_col = next((c for c in soc.columns if "timestamp" in c.lower()), None)
        if ts_col is not None:
            soc["ts"] = pd.to_datetime(soc[ts_col], utc=True).dt.tz_convert(CPT)
            soc["soc_mwh_max"] = pd.to_numeric(soc["soc_mwh_max"], errors="coerce")
            # period-ending 5-min ts → assign to hour start (ts - 5m → floor to 1h)
            soc["datetime_ct"] = (soc["ts"] - pd.Timedelta(minutes=5)).dt.floor("h")
            hourly_soc_max = soc.groupby("datetime_ct")["soc_mwh_max"].min().reset_index()
            print(f"  /soc-detailed hourly soc_mwh_max rows: {len(hourly_soc_max)}")
            cap = cap.merge(hourly_soc_max.rename(columns={"soc_mwh_max": "soc_mwh_max_override"}),
                            on="datetime_ct", how="left")
            cap["soc_mwh_max"] = cap["soc_mwh_max_override"].combine_first(cap["soc_mwh_max"]).clip(0, NAMEPLATE_MWH)
            cap = cap.drop(columns=["soc_mwh_max_override"])

    # Apply /outages — full or partial derate windows
    if not out_df.empty:
        oo = out_df.copy()
        # required: start_date, end_date, charge_direction, outage_capacity
        sd_col = next((c for c in oo.columns if c.lower() == "start_date"), None)
        ed_col = next((c for c in oo.columns if c.lower() == "end_date"), None)
        dir_col = next((c for c in oo.columns if "direction" in c.lower()), None)
        cap_col = next((c for c in oo.columns if c.lower() == "outage_capacity"), None)
        if all([sd_col, ed_col, dir_col, cap_col]):
            oo["sd"] = pd.to_datetime(oo[sd_col], utc=True).dt.tz_convert(CPT)
            oo["ed"] = pd.to_datetime(oo[ed_col], utc=True).dt.tz_convert(CPT)
            oo[cap_col] = pd.to_numeric(oo[cap_col], errors="coerce")
            print(f"  applying {len(oo)} outage rows ...")
            # For each hour, check overlap with each outage row
            cap_idx = cap.set_index("datetime_ct").copy()
            for _, r in oo.iterrows():
                sd, ed, direction, mw = r["sd"], r["ed"], str(r[dir_col]).lower(), r[cap_col]
                if pd.isna(mw):
                    continue
                # outage_capacity = magnitude removed (0 = full outage). MW remaining = NAMEPLATE_MW - mw.
                remaining = max(NAMEPLATE_MW - float(mw), 0.0)
                # but per the doc, outage_capacity "is the magnitude of the outage in MW" — interpret
                # as MW unavailable. So MW available = NAMEPLATE - mw.
                idx = cap_idx.index[(cap_idx.index >= sd) & (cap_idx.index < ed)]
                if direction.startswith("disch"):
                    cap_idx.loc[idx, "avail_discharge_mw"] = cap_idx.loc[idx, "avail_discharge_mw"].clip(upper=remaining)
                elif direction.startswith("char"):
                    cap_idx.loc[idx, "avail_charge_mw"] = cap_idx.loc[idx, "avail_charge_mw"].clip(upper=remaining)
                else:
                    cap_idx.loc[idx, "avail_discharge_mw"] = cap_idx.loc[idx, "avail_discharge_mw"].clip(upper=remaining)
                    cap_idx.loc[idx, "avail_charge_mw"] = cap_idx.loc[idx, "avail_charge_mw"].clip(upper=remaining)
            cap = cap_idx.reset_index()

    # ensure no NaN / out-of-range
    cap["avail_discharge_mw"] = cap["avail_discharge_mw"].fillna(NAMEPLATE_MW).clip(0, NAMEPLATE_MW)
    cap["avail_charge_mw"]    = cap["avail_charge_mw"].fillna(NAMEPLATE_MW).clip(0, NAMEPLATE_MW)
    cap["soc_mwh_max"]        = cap["soc_mwh_max"].fillna(NAMEPLATE_MWH).clip(0, NAMEPLATE_MWH)

    hourly_path = DERIVED / "sb_capability_hourly.parquet"
    cap.to_parquet(hourly_path, index=False)
    print(f"  saved hourly → {hourly_path.name}  ({len(cap)} rows)")
    print(f"  hours with discharge derate (< {NAMEPLATE_MW}): {(cap['avail_discharge_mw'] < NAMEPLATE_MW).sum()}")
    print(f"  hours with charge derate    (< {NAMEPLATE_MW}): {(cap['avail_charge_mw'] < NAMEPLATE_MW).sum()}")
    print(f"  hours with MWh derate       (< {NAMEPLATE_MWH}): {(cap['soc_mwh_max'] < NAMEPLATE_MWH).sum()}")

    # daily summary — most conservative cap per day
    daily = cap.copy()
    daily["date"] = daily["datetime_ct"].dt.date
    daily = daily.groupby("date").agg(
        avail_discharge_mw_min=("avail_discharge_mw", "min"),
        avail_charge_mw_min=("avail_charge_mw", "min"),
        soc_mwh_max_min=("soc_mwh_max", "min"),
    ).reset_index()
    daily_path = DERIVED / "sb_capability_daily.parquet"
    daily.to_parquet(daily_path, index=False)
    print(f"  saved daily → {daily_path.name}  ({len(daily)} rows)")
    print(f"  daily MWh-cap distribution: min={daily['soc_mwh_max_min'].min():.0f}  median={daily['soc_mwh_max_min'].median():.0f}  max={daily['soc_mwh_max_min'].max():.0f}")
    print(f"  daily MW-discharge cap dist: min={daily['avail_discharge_mw_min'].min():.0f}  median={daily['avail_discharge_mw_min'].median():.0f}")
    print(f"  daily MW-charge cap dist:    min={daily['avail_charge_mw_min'].min():.0f}  median={daily['avail_charge_mw_min'].median():.0f}")


if __name__ == "__main__":
    main()
