"""zone_ recon: 60d DAM Gen Resource Data pre/post RTC+B - shape, resource_type, settlement_point -> ZONE match, HSL."""
import sys, pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); import dl
pd.set_option("display.width", 300); pd.set_option("display.max_rows", 100)
obj = pd.read_parquet(ROOT / "raw/objects_all.parquet")
pn = obj[(obj.OBJECTTYPE == "price_node") & obj.ZONE.notna()].drop_duplicates("OBJECTNAME").set_index("OBJECTNAME").ZONE
P = "ercot/gen/ercot_60d_dam_gen_resource_data"
for ds in ("20230715", "20250715", "20260715"):
    print("\n=====", ds, dl.ls(f"{P}/{ds}", 1))
    df = dl.try_read_csv(f"{P}/{ds}.csv.gz", header=None)
    if df is None: print("missing"); continue
    print(df.shape); print(df.head(2).to_string())
    # locate resource_type / settlement_point / hsl columns by content
    for c in df.columns:
        s = df[c].astype(str)
        if s.isin(["PWRSTR", "PVGR", "WIND", "CCGT90", "SCGT90", "NUC", "CLLIG"]).mean() > 0.3: print("resource_type col", c)
        if s.str.endswith(("_RN", "_ALL", "_HOUSTON", "_NORTH")).mean() > 0.3: print("settlement_point-like col", c, s.head(3).tolist())
    rt, sp, rn, hsl = (4, 33, 2, 29)
    if df.shape[1] != 53:
        print("non-53-col layout; columns:", df.shape[1]); continue
    d = df.rename(columns={rt: "rtype", sp: "sp", rn: "res", hsl: "hsl"})
    d["zone"] = d.sp.map(pn)
    cap = d.groupby(["res", "rtype", "sp", "zone"], dropna=False).hsl.max().reset_index()
    print("resources:", len(cap), "zone matched:", cap.zone.notna().sum(), "unmatched MW:", cap[cap.zone.isna()].hsl.sum())
    print(cap[cap.zone.isna()].sort_values("hsl", ascending=False).head(10).to_string())
    print(cap.pivot_table(index="rtype", columns="zone", values="hsl", aggfunc="sum").round(0))
