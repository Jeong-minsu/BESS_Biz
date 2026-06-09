"""Full-history GKS_BESS_RN congestion scan via S3 Select on market_shift_factors.
Pulls only GKS pricenode rows (server-side). Both DA + RT markets. Real data only.
Output: derived/gks_msf_raw.parquet  (one row per binding constraint-interval affecting GKS).
"""
import sys, io, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
sys.path.insert(0, str(Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")))
import dl

GKS = "10017907494"
DERIVED = Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")
# selected cols: _2 FACILITYID, _3 CONTINGENCYID, _4 DATETIME, _6 MARKET, _7 SHIFTFACTOR, _8 SHADOWPRICE, _11 CONSTRAINTNAME
SEL = "SELECT s._2,s._3,s._4,s._6,s._7,s._8,s._11 FROM s3object s WHERE s._1='%s'" % GKS
NAMES = ["FACILITYID","CONTINGENCYID","DATETIME","MARKET","SHIFTFACTOR","SHADOWPRICE","CONSTRAINTNAME"]

def fetch(day):
    key = f"ercot/transmission/constraints/market_shift_factors/{day}.csv.gz"
    try:
        resp = dl.cli().select_object_content(
            Bucket="yedatalake", Key=key, ExpressionType="SQL", Expression=SEL,
            InputSerialization={"CSV": {"FileHeaderInfo": "NONE"}, "CompressionType": "GZIP"},
            OutputSerialization={"CSV": {}})
        buf=io.BytesIO()
        for ev in resp["Payload"]:
            if "Records" in ev: buf.write(ev["Records"]["Payload"])
        buf.seek(0)
        if buf.getbuffer().nbytes==0: return None
        df = pd.read_csv(buf, header=None, names=NAMES, dtype={"CONSTRAINTNAME":str})
        df["day"]=day
        return df
    except Exception as e:
        if "NoSuchKey" in str(type(e))+str(e): return None
        return ("ERR", day, str(e)[:120])

days = [d.strftime("%Y%m%d") for d in pd.date_range("2023-01-01","2026-06-08",freq="D")]
print(f"scanning {len(days)} days...")
out=[]; errs=[]; miss=0; t0=time.time()
with ThreadPoolExecutor(max_workers=24) as ex:
    futs={ex.submit(fetch,d):d for d in days}
    done=0
    for f in as_completed(futs):
        r=f.result(); done+=1
        if r is None: miss+=1
        elif isinstance(r,tuple): errs.append(r)
        else: out.append(r)
        if done%200==0: print(f"  {done}/{len(days)}  elapsed {time.time()-t0:.0f}s  rows={sum(len(x) for x in out)}")
print(f"done in {time.time()-t0:.0f}s. files-with-data={len(out)} missing={miss} errs={len(errs)}")
if errs[:5]: print("sample errs:", errs[:5])
raw = pd.concat(out, ignore_index=True)
raw.to_parquet(DERIVED/"gks_msf_raw.parquet", index=False)
print("saved", DERIVED/"gks_msf_raw.parquet", "rows=", len(raw))
print(raw["MARKET"].value_counts().to_dict())
