"""RT binding (PRICE>0) for La Palma-family + RGV constraints, 2024-07-03..2026-06-30 (Q3-2026 already cached)."""
import sys, pandas as pd, concurrent.futures as cf
sys.path.insert(0, "."); import dl
PAT = "LA_PAL|HAINE|WESLCO|VCAVAZ|RGV|RAYMND|RAYRI"
hrs = pd.date_range("2024-07-03 00:00", "2026-06-30 23:00", freq="h")
def f(h):
    try: df = dl.read_rt(h.strftime("%Y%m%d%H"))
    except Exception as e: print("ERR", h, e, flush=True); return None
    if df is None: return None
    df = df[(df.PRICE > 0) & df.CONSTRAINTNAME.astype(str).str.contains(PAT, case=False)]
    return df
parts = []
with cf.ThreadPoolExecutor(32) as ex:
    for i, x in enumerate(ex.map(f, hrs)):
        if x is not None and len(x): parts.append(x)
        if i % 2000 == 0: print(i, len(hrs), flush=True)
pd.concat(parts).to_parquet("../raw/rt_lapalma_2024_2026H1.parquet"); print("done")
