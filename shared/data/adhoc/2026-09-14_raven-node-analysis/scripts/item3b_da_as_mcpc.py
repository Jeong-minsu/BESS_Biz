"""item3b: hourly DA AS MCPC (system-wide) for 2026, extracted from the estimate-bess-energy-as skill's
DAM-ESR disclosure cache (ERCOT NP3-966-ER, real). MCPC is identical on every resource row -> one row per
(Delivery Date, Hour Ending). Incremental: re-run after new chunks are cached."""
import hashlib, pandas as pd
from datetime import date, timedelta
from pathlib import Path
A = Path(__file__).resolve().parents[1]; SK = A.parents[3]/"skills/estimate-bess-energy-as/scripts"
def cache(key): return SK/"data/cache"/("ercot_api_"+hashlib.md5(key.encode()).hexdigest()+".parquet")
cols = {"RegUp MCPC":"regup","RegDown MCPC":"regdn","RRS MCPC":"rrs","ECRS MCPC":"ecrs","NonSpin MCPC":"nspin"}
rows = []
d = date(2025,12,31)
while d <= date(2026,9,13):
    f = cache(f"sced_disclosure_{d}".replace("sced","dam"))
    if f.exists():
        x = pd.read_parquet(f, columns=["Delivery Date","Hour Ending"]+list(cols))
        x = x.groupby(["Delivery Date","Hour Ending"], as_index=False).first()
        rows.append(x)
    d += timedelta(days=1)
da = pd.concat(rows).rename(columns=cols)
da["flowday"] = pd.to_datetime(da["Delivery Date"], format="%m/%d/%Y").dt.strftime("%Y-%m-%d")
da["he"] = da["Hour Ending"].astype(int)
da = da.drop(columns=["Delivery Date","Hour Ending"]).drop_duplicates(["flowday","he"]).sort_values(["flowday","he"])
da.to_parquet(A/"derived/item3b_da_as_mcpc_hourly_2026.parquet", index=False)
print(len(da), da.flowday.min(), da.flowday.max()); print(da.groupby(da.flowday.str[:7])[list(cols.values())].mean().round(2))
