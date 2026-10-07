"""11 - 2025 전체 BESS 플릿 일별 실적 재구축 (pre-RTC+B, 공개 공시 원본에서 직접).

vendored estimate-bess-energy-as skill은 pre-RTC+B 컬럼 인덱스가 어긋나 못 쓴다.
검증된 원본 매핑 (GKS PTP 정산 실적 앵커로 확인):
  방전  : ercot_60d_sced_smne_gen_res  col6=resource, col7=MWh/15min   (PTP와 100% 일치)
  충전  : ercot_60d_sced_load_resource_data col6=LR명, col10=MW        (PTP 대비 +2~8% 텔레메트리 편의)
  AS    : ercot_60d_dam_gen_resource_data
          RegUp 35x36, RegDn 37x38, NonSpin 41x42, RRS 46x40, ECRS 49x50  (4개 날짜 PTP 일치 확인)
          col2=resource, col4=type(PWRSTR), col29=HSL, col33=settlement point
  가격  : ercot/prices/lmp/15min (SPP)  - settlement point -> objectid 매핑

출력: derived/fleet_2025_daily.parquet, derived/fleet_2025_node_hourly.parquet
"""
from __future__ import annotations
import os, sys, re
from datetime import date, timedelta
from pathlib import Path

import truststore; truststore.inject_into_ssl()

ADHOC = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "skills" / "estimate-bess-energy-as" / "scripts"))
sys.path.insert(0, str(ROOT / "shared" / "scripts"))
from _env_loader import load_env_sections  # noqa: E402
for _sec in ("ercot", "yes_energy_s3"):
    for _k, _v in load_env_sections(ROOT / ".env").get(_sec, {}).items():
        os.environ.setdefault(_k, _v)

import numpy as np, pandas as pd  # noqa: E402
from src.data_fetcher import _download_csv_gz, fetch_spp_lmp, fetch_name_to_objectid_map  # noqa: E402

DERIVED = ADHOC / "derived"
START, END = date(2025, 1, 1), date(2025, 12, 31)
AS_PAIRS = {"regup": (35, 36), "regdn": (37, 38), "nonspin": (41, 42),
            "rrs": (46, 40), "ecrs": (49, 50)}
LD_RE = re.compile(r"_(LD|LOAD)\d*$")


def _num(df, c):
    return pd.to_numeric(df[c], errors="coerce").fillna(0.0)


def day_frame(d: date, name_to_oid: dict):
    ds = d.strftime("%Y%m%d")
    try:
        dam = _download_csv_gz(f"ercot/gen/ercot_60d_dam_gen_resource_data/{ds}.csv.gz")
    except Exception:
        return None, None
    dam.columns = range(dam.shape[1])
    dam = dam[dam[4].astype(str).str.upper() == "PWRSTR"].copy()
    if dam.empty:
        return None, None
    dam["resource"] = dam[2].astype(str)
    dam["sp"] = dam[33].astype(str)
    as_rev = pd.Series(0.0, index=dam.index)
    as_mwh = pd.Series(0.0, index=dam.index)
    for p, (aw, mc) in AS_PAIRS.items():
        q = _num(dam, aw)
        as_rev = as_rev + q * _num(dam, mc)
        as_mwh = as_mwh + q
    dam["as_rev"], dam["as_mwh"], dam["hsl"] = as_rev, as_mwh, _num(dam, 29)
    g_dam = dam.groupby(["resource", "sp"]).agg(
        as_rev=("as_rev", "sum"), as_mwh=("as_mwh", "sum"), hsl_max=("hsl", "max")
    ).reset_index()

    # ── 가격: 이 날의 ESR settlement point 15분 SPP ──
    oids = {name_to_oid[s] for s in g_dam["sp"].unique() if s in name_to_oid}
    spp = fetch_spp_lmp(d, d + timedelta(days=1), objectids=oids)
    if spp.empty:
        return None, None
    oid_to_name = {v: k for k, v in name_to_oid.items()}
    spp = spp.copy()
    spp["sp"] = spp["objectid"].map(oid_to_name)
    spp["datetime"] = pd.to_datetime(spp["datetime"])
    spp = spp[spp["datetime"].dt.date == d]
    spp["slot"] = spp["datetime"].dt.floor("15min")
    px = spp.groupby(["sp", "slot"], as_index=False)["rt_lmp"].mean()

    # ── 방전 (SMNE, 15분 MWh) ──
    try:
        sm = _download_csv_gz(f"ercot/gen/ercot_60d_sced_smne_gen_res/{ds}.csv.gz")
        sm.columns = range(sm.shape[1])
        sm = sm[sm[6].astype(str).isin(set(g_dam["resource"]))].copy()
        sm["slot"] = pd.to_datetime(sm[1], errors="coerce").dt.floor("15min")
        sm["mwh"] = _num(sm, 7)
        sm["resource"] = sm[6].astype(str)
        dis = sm.groupby(["resource", "slot"], as_index=False)["mwh"].sum()
    except Exception:
        dis = pd.DataFrame(columns=["resource", "slot", "mwh"])

    # ── 충전 (Load Resource 텔레메트리 MW -> MWh) ──
    try:
        lr = _download_csv_gz(f"ercot/load/ercot_60d_sced_load_resource_data/{ds}.csv.gz")
        lr.columns = range(lr.shape[1])
        lr["lr"] = lr[6].astype(str)
        lr = lr[lr["lr"].str.match(r".*_(?:LD|LOAD)\d*$")].copy()
        lr["slot"] = pd.to_datetime(lr[1], errors="coerce").dt.floor("15min")
        lr["mw"] = _num(lr, 10)
        lrs = lr.groupby(["lr", "slot"], as_index=False)["mw"].mean()
        lrs["mwh"] = lrs["mw"] * 0.25
        lrs["prefix"] = lrs["lr"].str.replace(LD_RE, "", regex=True)
    except Exception:
        lrs = pd.DataFrame(columns=["lr", "slot", "mw", "mwh", "prefix"])

    # LR prefix -> gen resource (접두사 일치). 다유닛 사이트는 방전량 비율로 배분.
    res = g_dam["resource"].tolist()
    m = []
    for pfx in lrs["prefix"].unique() if len(lrs) else []:
        hit = [r for r in res if r.startswith(pfx)]
        for r in hit:
            m.append({"prefix": pfx, "resource": r, "n": len(hit)})
    mp = pd.DataFrame(m)

    # ── 일별 집계 ──
    rows = g_dam.copy()
    rows["dis_mwh"] = 0.0; rows["dis_rev"] = 0.0
    rows["chg_mwh"] = 0.0; rows["chg_cost"] = 0.0
    if not dis.empty:
        dd = dis.merge(g_dam[["resource", "sp"]], on="resource", how="left")
        dd = dd.merge(px, on=["sp", "slot"], how="left")
        dd["rev"] = dd["mwh"] * dd["rt_lmp"]
        agg = dd.groupby("resource").agg(dis_mwh=("mwh", "sum"), dis_rev=("rev", "sum")).reset_index()
        rows = rows.drop(columns=["dis_mwh", "dis_rev"]).merge(agg, on="resource", how="left")
    if not lrs.empty and not mp.empty:
        cc = lrs.merge(mp, on="prefix", how="inner")
        cc = cc.merge(g_dam[["resource", "sp"]], on="resource", how="left")
        cc = cc.merge(px, on=["sp", "slot"], how="left")
        cc["mwh_a"] = cc["mwh"] / cc["n"]
        cc["cost"] = cc["mwh_a"] * cc["rt_lmp"]
        agg = cc.groupby("resource").agg(chg_mwh=("mwh_a", "sum"), chg_cost=("cost", "sum")).reset_index()
        rows = rows.drop(columns=["chg_mwh", "chg_cost"]).merge(agg, on="resource", how="left")
    for c in ["dis_mwh", "dis_rev", "chg_mwh", "chg_cost"]:
        rows[c] = pd.to_numeric(rows.get(c), errors="coerce").fillna(0.0)
    rows["date"] = d
    node = px.rename(columns={"rt_lmp": "price"}).copy()
    node["date"] = d
    return rows, node


def main():
    out = DERIVED / "fleet_2025"
    out.mkdir(parents=True, exist_ok=True)
    name_to_oid = fetch_name_to_objectid_map()
    d = START
    cur_month, days, nodes = None, [], []

    def flush():
        if not days:
            return
        pd.concat(days, ignore_index=True).to_parquet(out / f"daily_{cur_month}.parquet", index=False)
        pd.concat(nodes, ignore_index=True).to_parquet(out / f"node_{cur_month}.parquet", index=False)
        print(f"  wrote {cur_month}: {sum(len(x) for x in days)} rows", flush=True)

    while d <= END:
        mk = d.strftime("%Y-%m")
        if mk != cur_month:
            flush()
            cur_month, days, nodes = mk, [], []
            if (out / f"daily_{mk}.parquet").exists():
                print(f"[skip] {mk}", flush=True)
                # 해당 월 건너뛰기
                while d <= END and d.strftime("%Y-%m") == mk:
                    d += timedelta(days=1)
                cur_month = None
                continue
        try:
            r, nd = day_frame(d, name_to_oid)
            if r is not None:
                days.append(r); nodes.append(nd)
            else:
                print(f"[{d}] 데이터 없음", flush=True)
        except Exception as e:
            import traceback
            print(f"[{d}] FAIL {repr(e)[:140]}", flush=True)
            traceback.print_exc()
        d += timedelta(days=1)
    flush()
    print("done", flush=True)


main()
