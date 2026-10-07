"""ITEM 7 — GKS_BESS_RN market_shift_factors pull (SF x lambda pre-joined, MARKET=DA/RT), 2024-07-03..2026-09-13.
Same S3 Select pattern as item2_scan_msf.py, single node. Output raw/msf_gks/YYYYMM.parquet (idempotent).
Needed because raw/msf_nodes/ (item2) holds RVN + proxy nodes only, and the GKS project parquet stops 2026-06-08.
Real data only.
"""
import sys, io, time, calendar
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl

OUT = Path(__file__).resolve().parents[1] / "raw" / "msf_gks"; OUT.mkdir(parents=True, exist_ok=True)
GKS = 10017907494
SEL = f"SELECT s._1,s._2,s._3,s._4,s._6,s._7,s._8,s._9,s._11 FROM s3object s WHERE s._1 = '{GKS}'"
NAMES = ["PRICENODEID", "FACILITYID", "CONTINGENCYID", "DATETIME", "MARKET", "SHIFTFACTOR", "SHADOWPRICE", "LIMIT", "CONSTRAINTNAME"]
START, END = date(2024, 7, 3), date(2026, 9, 13)


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
            return pd.read_csv(buf, header=None, names=NAMES, dtype={"CONSTRAINTNAME": str})
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
