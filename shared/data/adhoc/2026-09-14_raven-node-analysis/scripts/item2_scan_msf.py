"""ITEM 2 Part B — 3-year congestion scan for the Raven location.
S3 Select on ercot/transmission/constraints/market_shift_factors/{YYYYMMDD}.csv.gz (SF x lambda pre-joined
per pricenode, MARKET=DA/RT; RT rows = SCED 5-min intervals). Pulls RVN_RN + proxy-candidate nodes only
(server-side filter) — same methodology as 2026-06-09_gks-congestion-impact/scripts/scan_gks.py.
Incremental: one parquet per month in raw/msf_nodes/YYYYMM.parquet (idempotent, skips existing).
Real data only.
"""
import sys, io, time, calendar
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl

OUT = Path(__file__).resolve().parents[1] / "raw" / "msf_nodes"; OUT.mkdir(parents=True, exist_ok=True)
NODES = {10019925379: "RVN_RN", 10016934052: "SBE_RN_1", 10016969364: "TAV_RN", 10016239529: "WGU_RN",
         10017290064: "RBN_BESS1", 10001765766: "CBEC_ALL", 10016920911: "WES_ALL", 10016986325: "DAG_ALL",
         10016736811: "NCO_RN", 10017318830: "OR_BESS_RN", 10018682155: "WAL_RN"}
SEL = "SELECT s._1,s._2,s._3,s._4,s._6,s._7,s._8,s._9,s._11 FROM s3object s WHERE s._1 IN (%s)" % ",".join(f"'{k}'" for k in NODES)
NAMES = ["PRICENODEID", "FACILITYID", "CONTINGENCYID", "DATETIME", "MARKET", "SHIFTFACTOR", "SHADOWPRICE", "LIMIT", "CONSTRAINTNAME"]
START, END = date(2023, 9, 1), date(2026, 9, 13)


def fetch(day):
    key = f"ercot/transmission/constraints/market_shift_factors/{day:%Y%m%d}.csv.gz"
    for attempt in range(3):
        try:
            resp = dl.cli().select_object_content(
                Bucket="yedatalake", Key=key, ExpressionType="SQL", Expression=SEL,
                InputSerialization={"CSV": {"FileHeaderInfo": "NONE"}, "CompressionType": "GZIP"},
                OutputSerialization={"CSV": {}})
            buf = io.BytesIO()
            for ev in resp["Payload"]:
                if "Records" in ev: buf.write(ev["Records"]["Payload"])
            buf.seek(0)
            if buf.getbuffer().nbytes == 0: return None
            df = pd.read_csv(buf, header=None, names=NAMES, dtype={"CONSTRAINTNAME": str})
            return df
        except Exception as e:
            if "NoSuchKey" in str(type(e)) + str(e): return None
            if attempt == 2: print("ERR", day, str(e)[:120], flush=True); return None
            time.sleep(2)


def main():
    m = date(START.year, START.month, 1)
    while m <= END:
        fp = OUT / f"{m:%Y%m}.parquet"
        if fp.exists(): print("skip", fp.name, flush=True)
        else:
            last = date(m.year, m.month, calendar.monthrange(m.year, m.month)[1])
            days = [max(m, START) + timedelta(i) for i in range((min(last, END) - max(m, START)).days + 1)]
            t0 = time.time()
            with ThreadPoolExecutor(20) as ex: parts = [p for p in ex.map(fetch, days) if p is not None]
            if parts:
                out = pd.concat(parts, ignore_index=True)
                out["PRICENODEID"] = out["PRICENODEID"].astype("int64")
                for c in ("SHIFTFACTOR", "SHADOWPRICE", "LIMIT"): out[c] = pd.to_numeric(out[c], errors="coerce").astype("float32")
                out.to_parquet(fp, index=False)
                print(f"wrote {fp.name}: {len(out):,} rows, {len(parts)}/{len(days)} days, {time.time()-t0:.0f}s", flush=True)
            else: print("no data", m, flush=True)
        m = date(m.year + (m.month == 12), (m.month % 12) + 1, 1)


if __name__ == "__main__":
    main()
