"""Driver test for cluster D border transformers/line: South-zone wind (GR_SOUTH) vs binding.
For representative top months, compare mean GR_SOUTH wind in DA binding HE vs non-binding HE.
Also South wind diurnal shape vs the constraint's binding-hour profile. Real datalake only."""
import sys, io
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd, numpy as np
sys.path.insert(0, r'C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts')
import dl

GR_SOUTH = 10004189447
D = Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived")

def wind_days(days):
    def f(d):
        try:
            df = dl.read_csv(f"ercot/gen/wind_rti/{d}.csv.gz", header=None)
            df = df[df[0] == GR_SOUTH]
            return df
        except Exception:
            return None
    out = []
    with ThreadPoolExecutor(max_workers=16) as ex:
        for r in ex.map(f, days):
            if r is not None: out.append(r)
    w = pd.concat(out, ignore_index=True)
    w.columns = ["OBJ","DTYPE","DATETIME","TZ","WIND_MW","LOADID"][:w.shape[1]]
    w["dt"] = pd.to_datetime(w["DATETIME"], format="%m/%d/%Y %H:%M:%S")
    w["date"] = w.dt.dt.date
    w["he"] = w.dt.dt.hour  # period-ending hourly; hour 0..23
    return w[["dt","date","he","WIND_MW"]]

raw = pd.read_parquet(D/"gks_msf_raw.parquet")
raw = raw[raw.SHADOWPRICE>0].copy()
raw["dt"] = pd.to_datetime(raw.DATETIME, format="%m/%d/%Y %H:%M:%S")
raw["date"] = raw.dt.dt.date
raw["he"] = raw.dt.dt.hour

TESTS = [("LOYOLA_69_1","2025-05"), ("BRUNI_69_1","2025-04"), ("LASCRU_MILO1_1","2026-01")]
for cname, ym in TESTS:
    yr,mo = map(int, ym.split("-"))
    days = [d.strftime("%Y%m%d") for d in pd.date_range(f"{ym}-01", periods=pd.Period(ym).days_in_month, freq="D")]
    w = wind_days(days)
    # DA binding hours of this constraint in this month
    b = raw[(raw.CONSTRAINTNAME==cname)&(raw.MARKET=="DA")&(raw.dt.dt.year==yr)&(raw.dt.dt.month==mo)]
    bind_keys = set(zip(b.date, b.he))
    w["binding"] = [(r.date, r.he) in bind_keys for r in w.itertuples()]
    g = w.groupby("binding").WIND_MW.agg(["mean","median","count"])
    south_total = w.WIND_MW.mean()
    print(f"\n=== {cname} {ym} (South-zone GR_SOUTH wind, DA binding vs not) ===")
    print(g.round(0).to_string())
    if True in g.index and False in g.index:
        print(f"  binding-hr mean wind = {g.loc[True,'mean']:.0f} MW vs non-binding {g.loc[False,'mean']:.0f} MW  (ratio {g.loc[True,'mean']/g.loc[False,'mean']:.2f})")
    # diurnal: binding count by HE vs mean wind by HE
    diur = w.groupby("he").WIND_MW.mean()
    bc = b.groupby("he").size().reindex(range(24)).fillna(0)
    print("  HE | meanWind | bindingDArows")
    for h in range(24):
        print(f"   {h:2d} | {diur.get(h,float('nan')):7.0f} | {int(bc.get(h,0)):4d}")
