"""item3b: hourly RT AS MCPC (system-wide, ERCOT has no nodal AS) for 2026 from datalake rtc_mcpc_* (5-min).
Real fetch from Yes Energy datalake. Hourly = mean of 5-min MCPC within the hour (HE convention, CT)."""
import sys, pandas as pd
from pathlib import Path
A = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(A/"scripts")); import dl
PROD = {"regup":"rtc_mcpc_regup","regdn":"rtc_mcpc_regdn","rrs":"rtc_mcpc_rrs","ecrs":"rtc_mcpc_ecrs","nspin":"rtc_mcpc_nspin"}
out = A/"derived/item3b_rt_as_mcpc_hourly_2026.parquet"
have = pd.read_parquet(out) if out.exists() else pd.DataFrame()
done = set(have.flowday.astype(str)) if len(have) else set()
days = pd.date_range("2026-01-01","2026-09-13")
rows = []
for d in days:
    ds = d.strftime("%Y%m%d")
    if d.strftime("%Y-%m-%d") in done: continue
    parts = {}
    for p, path in PROD.items():
        df = dl.try_read_csv(f"ercot/ancillary/{path}/{ds}.csv.gz", header=None)
        if df is None: continue
        t = pd.to_datetime(df[2], format="%m/%d/%Y %H:%M:%S")
        # 5-min interval stamps are interval-start (00:00:30 etc.) -> HE = floor hour + 1
        he = (t.dt.floor("h") + pd.Timedelta(hours=1))
        parts[p] = pd.Series(df[4].values, index=he).groupby(level=0).mean()
    if not parts: print("missing", ds, flush=True); continue
    h = pd.DataFrame(parts); h.index.name = "he_ts"; h = h.reset_index(); h["flowday"] = d.strftime("%Y-%m-%d")
    rows.append(h)
    if len(rows) % 30 == 0: print(ds, flush=True)
if rows:
    new = pd.concat(rows); allx = pd.concat([have, new]) if len(have) else new
    allx.to_parquet(out, index=False); print("wrote", len(allx))
