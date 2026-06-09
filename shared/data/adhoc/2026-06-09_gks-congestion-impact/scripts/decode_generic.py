"""Check nature of generic-named constraints E_PASP/VALEXP/WESTEX + GKS own SF stats."""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")))
import dl
pd.set_option("display.width", 240)
raw = pd.read_parquet(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_gks-congestion-impact/derived/gks_msf_raw.parquet")
raw = raw[raw.SHADOWPRICE>0]
fac = dl.read_csv("ercot/metadata/objects/facility.csv.gz")
for cn in ["E_PASP","VALEXP","WESTEX","HAINE__LA_PAL1_1"]:
    s = raw[raw.CONSTRAINTNAME==cn]
    fid = s["FACILITYID"].iloc[0]
    frow = fac[fac["OBJECTID"]==fid]
    print(f"\n{cn}: FACILITYID={fid}  SF range [{s.SHIFTFACTOR.min():.3f},{s.SHIFTFACTOR.max():.3f}] mean {s.SHIFTFACTOR.mean():.3f}")
    print("  facility meta:", frow.to_dict("records"))
