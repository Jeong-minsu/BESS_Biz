"""07 - 수익 분자를 ERCOT 정산명세(Generator-Settlement-Data)로 교체.

PTP 부호 규약: *AMT 필드는 음수 = ERCOT가 자원에 지급(수익). net = -sum(*AMT).
Battery-Settlement-Details 기반 수익(물리에너지 x RTSPP + DA AS)은 RTC+B의 RT AS 되사기
(buy-back)를 놓쳐 2026을 과대계상했다. 물량(Quantity)과 TB2는 기존대로 유지.
"""
from __future__ import annotations
import glob, json, os
from pathlib import Path
import pandas as pd

ADHOC = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[5]
PTP = ROOT / "shared" / "data" / "pnl" / "gks" / "hourly"
DERIVED = ADHOC / "derived"

AS_DA = ["PCNSAMT", "PCRRAMT", "PCECRAMT", "PCRUAMT", "PCRDAMT"]
AS_RT = ["RTNSIMBAMT", "RTRRIMBAMT", "RTECRIMBAMT", "RTRUIMBAMT", "RTRDIMBAMT",
         "RTASIAMT", "LAASIRNAMT", "RTPCNSAMT", "RTPCRRAMT", "RTPCECRAMT",
         "RTPCRUAMT", "RTPCRDAMT"]
ENERGY = ["RTEIAMT", "RTRDASIAMT", "RTESOGSAMT", "DAEPAMT", "DAESAMT", "DAMWAMT",
          "EMREAMT", "BPDAMT"]
DEV = ["SPDAMT", "BLTRAMT", "BSSAMT"]


def main():
    rows = []
    for f in sorted(glob.glob(str(PTP / "*_gen_settle.json"))):
        day = os.path.basename(f)[:10]
        try:
            a = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception:
            continue
        if not a:
            continue
        df = pd.DataFrame(a)
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        amt = df[df["datapoint"].str.endswith("AMT")]
        s = amt.groupby("datapoint")["value"].sum()
        pick = lambda keys: -sum(s.get(k, 0.0) for k in keys)
        known = set(AS_DA + AS_RT + ENERGY + DEV)
        rows.append({
            "date": day,
            "gsd_rev": -s.sum(),
            "gsd_energy": pick(ENERGY),
            "gsd_as_da": pick(AS_DA),
            "gsd_as_rt": pick(AS_RT),
            "gsd_dev": pick(DEV),
            "gsd_other": -sum(v for k, v in s.items() if k not in known),
        })
    g = pd.DataFrame(rows)
    g["date"] = pd.to_datetime(g["date"])
    d = pd.read_parquet(DERIVED / "gks_daily_opt.parquet")
    d["date"] = pd.to_datetime(d["date"])
    out = d.merge(g, on="date", how="left")
    out.to_parquet(DERIVED / "gks_daily_opt_v2.parquet", index=False)
    out.to_csv(DERIVED / "gks_daily_opt_v2.csv", index=False)
    cov = out["gsd_rev"].notna()
    print(f"{len(out)} days, GSD 있음 {cov.sum()}  ({out.loc[cov,'date'].min().date()} ~ {out.loc[cov,'date'].max().date()})")
    print(out[cov].groupby(out["date"].dt.year)[["gsd_rev", "gsd_energy", "gsd_as_da",
                                                 "gsd_as_rt", "gsd_dev", "gsd_other"]]
          .sum().round(0).to_string())


main()
