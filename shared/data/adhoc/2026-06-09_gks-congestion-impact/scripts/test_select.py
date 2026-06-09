"""Test S3 Select server-side filter for GKS pricenode in market_shift_factors."""
import sys, io, time
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")))
import dl

GKS = "10017907494"
key = "ercot/transmission/constraints/market_shift_factors/20260501.csv.gz"
t0=time.time()
resp = dl.cli().select_object_content(
    Bucket="yedatalake", Key=key,
    ExpressionType="SQL",
    Expression=f"SELECT * FROM s3object s WHERE s._1 = '{GKS}'",
    InputSerialization={"CSV": {"FileHeaderInfo": "NONE"}, "CompressionType": "GZIP"},
    OutputSerialization={"CSV": {}},
)
buf=io.BytesIO()
for ev in resp["Payload"]:
    if "Records" in ev:
        buf.write(ev["Records"]["Payload"])
buf.seek(0)
df = pd.read_csv(buf, header=None)
print(f"S3 Select returned {len(df)} rows in {time.time()-t0:.1f}s")
print(df.head(3).to_string())
print("MARKET col (idx5) values:", df[5].value_counts().to_dict())
