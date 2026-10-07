"""12 - 2026(1~7월) 전체 BESS 플릿 일별 실적 (post-RTC+B, ERCOT API ESR 공시).

한 윈도우(기본 15일)씩 서브프로세스로 실행 — 플릿 5분 SCED 전체를 메모리에 올리므로.
  python 12_fleet_2026.py --start 2026-01-01 --end 2026-01-15

출력: derived/fleet_2026/daily_<start>_<end>.parquet, node_<...>.parquet
  방전/충전 : ESR SCED 5분 Telemetered Net Output (부호로 구분)
  AS        : DA 낙찰 x DA MCPC + (RT 낙찰 - DA 낙찰) x RT MCPC   (RTC+B 되사기 반영)
  가격      : SPP 15분 (settlement point)
  duration  : SCED State of Charge 레인지 / 실측 용량
"""
from __future__ import annotations
import argparse, os, sys
from datetime import date, datetime, timedelta
from pathlib import Path

import truststore; truststore.inject_into_ssl()

ADHOC = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "skills" / "estimate-bess-energy-as" / "scripts"))
sys.path.insert(0, str(ROOT / "shared" / "scripts"))
from _env_loader import load_env_sections  # noqa: E402
for _s in ("ercot", "yes_energy_s3"):
    for _k, _v in load_env_sections(ROOT / ".env").get(_s, {}).items():
        os.environ.setdefault(_k, _v)

import numpy as np, pandas as pd  # noqa: E402
from src.data_fetcher import fetch_esr_data, fetch_as_mcpc, fetch_name_to_objectid_map  # noqa: E402
from config import AS_PRODUCTS  # noqa: E402

OUT = ADHOC / "derived" / "fleet_2026"


def _d(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, type=_d)
    ap.add_argument("--end", required=True, type=_d)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    tag = f"{a.start}_{a.end}"

    data = fetch_esr_data(a.start, a.end)
    rt = data["rt_output"]
    if rt is None or rt.empty:
        print(f"[{tag}] rt_output 없음"); return 0
    rt = rt.copy()
    rt["datetime"] = pd.to_datetime(rt["datetime"])
    rt["date"] = rt["datetime"].dt.date
    rt["slot"] = rt["datetime"].dt.floor("15min")
    rt["rt_mw"] = pd.to_numeric(rt["rt_mw"], errors="coerce").fillna(0.0)

    info = data["resource_info"]
    sp_map = dict(zip(info["resource_name"], info["settlement_point"])) if not info.empty else {}
    rt["sp"] = rt["resource_name"].map(sp_map)

    # ── 가격 (15분 SPP) ──
    name_to_oid = fetch_name_to_objectid_map()
    oid_to_name = {v: k for k, v in name_to_oid.items()}
    px = data["rt_lmp"]
    px = px.copy()
    px["datetime"] = pd.to_datetime(px["datetime"])
    px["slot"] = px["datetime"].dt.floor("15min")
    px["sp"] = px["objectid"].map(oid_to_name)
    px = px.groupby(["sp", "slot"], as_index=False)["rt_lmp"].mean()

    # ── 5분 간격 에너지 ──
    ivl = 5.0 / 60.0
    rt["dis_mwh"] = rt["rt_mw"].clip(lower=0) * ivl
    rt["chg_mwh"] = (-rt["rt_mw"]).clip(lower=0) * ivl
    e = rt.merge(px, on=["sp", "slot"], how="left")
    e["dis_rev"] = e["dis_mwh"] * e["rt_lmp"]
    e["chg_cost"] = e["chg_mwh"] * e["rt_lmp"]
    daily = e.groupby(["resource_name", "sp", "date"], as_index=False).agg(
        dis_mwh=("dis_mwh", "sum"), dis_rev=("dis_rev", "sum"),
        chg_mwh=("chg_mwh", "sum"), chg_cost=("chg_cost", "sum"),
        hsl_max=("hsl", "max") if "hsl" in e.columns else ("rt_mw", "max"),
        mw_max=("rt_mw", "max"), n5=("rt_mw", "size"))
    if "state_of_charge" in rt.columns:
        soc = rt.groupby(["resource_name", "date"], as_index=False)["state_of_charge"].agg(
            soc_max="max", soc_min="min")
        daily = daily.merge(soc, on=["resource_name", "date"], how="left")

    # ── AS: DA 낙찰 x DA MCPC + (RT - DA) x RT MCPC ──
    aw = data["as_awards"].copy()
    as_daily = pd.DataFrame()
    if not aw.empty:
        aw["datetime"] = pd.to_datetime(aw["datetime"])
        aw["_hour"] = aw["datetime"] - pd.Timedelta(hours=1)
        aw["_hour"] = aw["_hour"].dt.floor("h")
        rt["_hour"] = rt["datetime"].dt.floor("h")
        parts = []
        for p in AS_PRODUCTS:
            da_col, rt_col, mc_col = f"da_{p}_mw", f"rt_{p}_mw", f"da_{p}_mcpc"
            if da_col not in aw.columns:
                continue
            t = aw[["resource_name", "_hour", da_col]].copy()
            t[da_col] = pd.to_numeric(t[da_col], errors="coerce").fillna(0.0)
            if mc_col in aw.columns:
                t["da_mcpc"] = pd.to_numeric(aw[mc_col], errors="coerce").fillna(0.0)
            else:
                t["da_mcpc"] = 0.0
            if rt_col in rt.columns:
                h = rt.groupby(["resource_name", "_hour"], as_index=False)[rt_col].mean()
                t = t.merge(h, on=["resource_name", "_hour"], how="left")
                t[rt_col] = t[rt_col].fillna(t[da_col])
            else:
                t[rt_col] = t[da_col]
            mc = fetch_as_mcpc(p, "rt", a.start, a.end)
            if not mc.empty:
                mc = mc.copy()
                mc["_hour"] = pd.to_datetime(mc["datetime"]).dt.floor("h")
                vcol = f"rt_{p}_mcpc"
                if vcol not in mc.columns:
                    cand = [c for c in mc.columns if c.endswith("_mcpc") or c == "value"]
                    vcol = cand[0] if cand else None
                if vcol is None:
                    mc = pd.DataFrame(columns=["_hour", "rt_mcpc"])
                else:
                    mc["_v"] = pd.to_numeric(mc[vcol], errors="coerce")
                    mc = mc.groupby("_hour", as_index=False)["_v"].mean().rename(columns={"_v": "rt_mcpc"})
                t = t.merge(mc, on="_hour", how="left")
            if "rt_mcpc" not in t.columns:
                t["rt_mcpc"] = 0.0
            t["rt_mcpc"] = t["rt_mcpc"].fillna(0.0)
            t["as_rev"] = t[da_col] * t["da_mcpc"] + (t[rt_col] - t[da_col]) * t["rt_mcpc"]
            t["as_mwh"] = t[da_col]
            t["date"] = t["_hour"].dt.date
            parts.append(t.groupby(["resource_name", "date"], as_index=False)[["as_rev", "as_mwh"]].sum())
        if parts:
            as_daily = pd.concat(parts).groupby(["resource_name", "date"], as_index=False).sum()
    daily = daily.merge(as_daily, on=["resource_name", "date"], how="left") if not as_daily.empty else daily
    for c in ("as_rev", "as_mwh"):
        if c not in daily.columns:
            daily[c] = 0.0
        daily[c] = pd.to_numeric(daily[c], errors="coerce").fillna(0.0)

    daily = daily.rename(columns={"resource_name": "resource"})
    daily.to_parquet(OUT / f"daily_{tag}.parquet", index=False)
    node = px.copy()
    node.to_parquet(OUT / f"node_{tag}.parquet", index=False)
    print(f"[{tag}] {daily['resource'].nunique()} resources, {len(daily)} rows", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
