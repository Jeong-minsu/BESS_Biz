"""13 - 플릿 최적화율 분해: opt = (에너지 + AS) / TB,  에너지 = P(타점) x Q(사이클)

  TB_d      = 노드 시간별 RT 가격의 (상위 d시간 평균 - 하위 d시간 평균) x E_cap   (duration 선형보간)
  Q         = 방전MWh / E_cap                       (사이클/일)
  P         = (방전WAP - 충전WAP x 충방전비) / TB스프레드
  P x Q     = 에너지 opt,  + AS opt = 전체 opt
E_cap: SCED SOC 레인지(2026 실측) 우선, 없으면 vendored ESS capacity.csv, 최후 MW_max x 2h.
"""
from __future__ import annotations
import glob, sys
from pathlib import Path

import numpy as np, pandas as pd

ADHOC = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "skills" / "estimate-bess-energy-as" / "scripts"))
from src.tb_index import calculate_tb_index_fractional  # noqa: E402

DERIVED = ADHOC / "derived"
GKS = {"GKS_BESS_BESS1", "GKS_BESS_ESR1"}
MIN_MW = 10.0          # 소형 자원 제외
MIN_DAYS_FRAC = 0.6    # 해당 구간 일수의 60% 이상 데이터가 있는 자원만


def load_year(tag):
    # RTC+B 경계(2025-12-05)를 넘는 구간이 있어 두 디렉터리를 모두 읽고 날짜로 거른다
    dd = sorted(glob.glob(str(DERIVED / "fleet_2025" / "daily_*.parquet")) +
                glob.glob(str(DERIVED / "fleet_2026" / "daily_*.parquet")))
    nn = sorted(glob.glob(str(DERIVED / "fleet_2025" / "node_*.parquet")) +
                glob.glob(str(DERIVED / "fleet_2026" / "node_*.parquet")))
    if not dd:
        return None, None
    d = pd.concat([pd.read_parquet(f) for f in dd], ignore_index=True)
    n = pd.concat([pd.read_parquet(f) for f in nn], ignore_index=True)
    d["date"] = pd.to_datetime(d["date"])
    n["slot"] = pd.to_datetime(n["slot"])
    # 2025 빌더는 'price', 2026 빌더는 'rt_lmp' 로 저장 -> 합치고 결측 보완
    if "price" not in n.columns:
        n["price"] = np.nan
    if "rt_lmp" in n.columns:
        n["price"] = n["price"].fillna(n["rt_lmp"])
    n["date"] = n["slot"].dt.normalize()
    n["hour"] = n["slot"].dt.hour
    hourly = n.groupby(["sp", "date", "hour"], as_index=False)["price"].mean()
    return d.drop_duplicates(["resource", "date"]), hourly


def ess_capacity():
    """pnode -> (capacity_mw, energy_mwh, owner, site).  vendored ESS capacity.csv."""
    f = ROOT / "skills" / "estimate-bess-energy-as" / "scripts" / "ESS capacity.csv"
    c = pd.read_csv(f)
    c.columns = [x.strip().lower().replace(" ", "_") for x in c.columns]
    c = c.rename(columns={"pnode_name": "sp", "capacity_(mw)": "mw",
                          "energy_capacity_(mwh)": "mwh"})
    c = c[c["sp"].notna()]
    g = c.groupby(c["sp"].astype(str)).agg(mw=("mw", "sum"), mwh=("mwh", "sum"),
                                           owner=("owner", "first"), site=("site", "first"))
    return {k: (float(v.mw), float(v.mwh), v.owner, v.site) for k, v in g.iterrows()}


def build(tag, d0, d1):
    d, hourly = load_year(tag)
    if d is None:
        return None
    d = d[(d["date"] >= d0) & (d["date"] <= d1)].copy()
    cap_csv = ess_capacity()

    # ── 자원별 용량/duration ──
    g = d.groupby("resource")
    prof = g.agg(sp=("sp", "first"), days=("date", "nunique"),
                 mw_hsl=("hsl_max", "max"), dis_max=("dis_mwh", "max")).reset_index()
    if "soc_max" in d.columns:
        soc = g.agg(soc_hi=("soc_max", "max"), soc_lo=("soc_min", "min")).reset_index()
        prof = prof.merge(soc, on="resource", how="left")
    else:
        prof["soc_hi"] = np.nan; prof["soc_lo"] = np.nan
    prof["mw_hsl"] = prof["mw_hsl"].where(prof["mw_hsl"] > 0, np.nan)
    prof["csv_mw"] = prof["sp"].map(lambda x: cap_csv.get(x, (np.nan,) * 4)[0])
    prof["csv_mwh"] = prof["sp"].map(lambda x: cap_csv.get(x, (np.nan,) * 4)[1])
    prof["owner"] = prof["sp"].map(lambda x: cap_csv.get(x, (np.nan,) * 4)[2])
    prof["site"] = prof["sp"].map(lambda x: cap_csv.get(x, (np.nan,) * 4)[3])
    # MW: 실측 HSL 최대와 CSV 중 큰 값 (증설 반영), 둘 다 없으면 제외
    prof["mw"] = prof[["mw_hsl", "csv_mw"]].max(axis=1)
    # duration: CSV(큐레이션) > SOC 실측 > 2h 기본
    prof["dur_csv"] = prof["csv_mwh"] / prof["csv_mw"]
    prof["e_soc"] = prof["soc_hi"] - prof["soc_lo"]
    prof["dur_soc"] = prof["e_soc"] / prof["mw"]
    # duration: 큐레이션 CSV 우선. 단 CSV가 오래돼 과소평가된 경우(SOC 실측이 1.5배 이상)
    # SOC 실측으로 교체 — 신규/증설 자원의 분모 붕괴 방지.
    ds = prof["dur_soc"].where(prof["dur_soc"].between(0.4, 6.0))
    prof["duration"] = prof["dur_csv"]
    stale = prof["duration"].notna() & ds.notna() & (ds > 1.5 * prof["duration"])
    prof.loc[stale, "duration"] = ds[stale]
    prof["duration"] = prof["duration"].fillna(ds).fillna(2.0).clip(0.5, 8.0)
    prof = prof[prof["mw"].notna() & (prof["mw"] > 0)].copy()
    prof["e_cap"] = prof["mw"] * prof["duration"]

    # ── 노드·일별 TB (duration별) ──
    dur = dict(zip(prof["resource"], prof["duration"]))
    spm = dict(zip(prof["resource"], prof["sp"]))
    px = {(sp, dt): grp["price"].to_numpy()
          for (sp, dt), grp in hourly.sort_values("hour").groupby(["sp", "date"])}
    tb_sp, tb_rev = [], []
    for r, dt in zip(d["resource"], d["date"]):
        arr = px.get((spm.get(r), dt))
        if arr is None or len(arr) < 20:
            tb_sp.append(np.nan); tb_rev.append(np.nan); continue
        u = dur.get(r, 2.0)
        if u is None or not np.isfinite(u):
            tb_sp.append(np.nan); tb_rev.append(np.nan); continue
        tb = calculate_tb_index_fractional(arr, u)      # $/MW (하루)
        tb_sp.append(tb / u)                            # $/MWh 스프레드 환산
        tb_rev.append(tb)
    d["tb_per_mw"] = tb_rev
    d["tb_spread"] = tb_sp
    d = d.merge(prof[["resource", "mw", "e_cap", "duration"]], on="resource", how="left")
    d["tb_rev"] = d["tb_per_mw"] * d["mw"]
    return d, prof


def summarize(d, prof, label, min_days):
    x = d.dropna(subset=["tb_rev"])
    x = x[x["tb_rev"] > 0]
    meta = prof.set_index("resource")[["owner", "site"]]
    agg = x.groupby("resource").agg(
        sp=("sp", "first"), days=("date", "nunique"), mw=("mw", "first"),
        dur=("duration", "first"), e_cap=("e_cap", "first"),
        dis=("dis_mwh", "sum"), dis_rev=("dis_rev", "sum"),
        chg=("chg_mwh", "sum"), chg_cost=("chg_cost", "sum"),
        as_rev=("as_rev", "sum"), as_mwh=("as_mwh", "sum"),
        tb=("tb_rev", "sum"), tb_sp=("tb_spread", "mean")).reset_index()
    agg = agg[(agg["mw"] >= MIN_MW) & (agg["days"] >= min_days)]
    agg["energy_rev"] = agg["dis_rev"] - agg["chg_cost"]
    agg["rev"] = agg["energy_rev"] + agg["as_rev"]
    agg["opt"] = agg["rev"] / agg["tb"]
    agg["opt_energy"] = agg["energy_rev"] / agg["tb"]
    agg["opt_as"] = agg["as_rev"] / agg["tb"]
    agg["Q_cycles"] = agg["dis"] / agg["e_cap"] / agg["days"]
    wap_d = agg["dis_rev"] / agg["dis"]
    wap_c = agg["chg_cost"] / agg["chg"]
    ratio = agg["chg"] / agg["dis"]
    agg["P_capture"] = (wap_d - wap_c * ratio) / agg["tb_sp"]
    agg["P_naive"] = (wap_d - wap_c) / agg["tb_sp"]
    agg["PxQ"] = agg["P_capture"] * agg["Q_cycles"]
    agg["util_mw"] = agg["dis"] / agg["days"] / 24 / agg["mw"]
    agg["label"] = label
    agg = agg.merge(meta, on="resource", how="left")
    return agg
