"""(1) GKS node msf 2026-06-09..09-30 (extend prior panel)  (2) all-node SFs for La Palma constraints on sample days."""
import sys, io, pandas as pd
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "."); import dl
NAMES = ["PNODE","FACILITYID","CONTINGENCYID","DATETIME","MARKET","SHIFTFACTOR","SHADOWPRICE","CONSTRAINTNAME"]
def sel(day, where):
    key = f"ercot/transmission/constraints/market_shift_factors/{day}.csv.gz"
    try:
        resp = dl.cli().select_object_content(Bucket="yedatalake", Key=key, ExpressionType="SQL",
            Expression="SELECT s._1,s._2,s._3,s._4,s._6,s._7,s._8,s._11 FROM s3object s WHERE " + where,
            InputSerialization={"CSV": {"FileHeaderInfo": "NONE"}, "CompressionType": "GZIP"}, OutputSerialization={"CSV": {}})
        buf = io.BytesIO()
        for ev in resp["Payload"]:
            if "Records" in ev: buf.write(ev["Records"]["Payload"])
        if buf.getbuffer().nbytes == 0: return None
        buf.seek(0); d = pd.read_csv(buf, header=None, names=NAMES, dtype={"CONSTRAINTNAME": str, "PNODE": str}); d["day"] = day; return d
    except Exception as e:
        if "NoSuchKey" in str(e): return None
        print("ERR", day, str(e)[:150]); return None
days = [d.strftime("%Y%m%d") for d in pd.date_range("2026-06-09", "2026-09-30")]
with ThreadPoolExecutor(16) as ex: g = [x for x in ex.map(lambda d: sel(d, "s._1='10017907494'"), days) if x is not None]
pd.concat(g).to_parquet("../raw/gks_msf_2026Q3.parquet"); print("gks rows", sum(map(len, g)))
sd = ["20260917", "20260922", "20260925", "20260928", "20260815", "20260720"]
with ThreadPoolExecutor(6) as ex: a = [x for x in ex.map(lambda d: sel(d, "s._11 LIKE '%LA_PAL%'"), sd) if x is not None]
pd.concat(a).to_parquet("../raw/allnode_sf_lapalma_sample.parquet"); print("allnode rows", sum(map(len, a)))
