"""Houston-zone BESS product mix from ALREADY-CACHED 60-day disclosure chunks
(2026-01-01..2026-05-25). Summer chunks were not downloaded (user stopped the run),
so this is a winter+spring read, not a summer read. Real data only.
Per memory estimate-bess-energy-as-oom-chunking: optimization_rate must be RECOMPUTED
on summed totals, never averaged across chunks.
"""
import sys, glob, json
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl

OUT = Path(__file__).resolve().parents[1] / "derived"
REV = ["da_energy_rev","rt_energy_rev","deviation_penalty","regup_rev","regdn_rev",
       "rrs_rev","ecrs_rev","nonspin_rev","total_rev","theoretical_rev"]

files = sorted(glob.glob(str(ROOT/"shared/data/pnl/all_bess/energy_as/chunks/summary_*.parquet")))
print(f"chunks: {len(files)}")
d = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
print("rows:", len(d), "resources:", d.resource_name.nunique())

agg = d.groupby("resource_name")[REV].sum()
meta = (d.sort_values("hsl").groupby("resource_name")
          .agg(settlement_point=("settlement_point","last"), company=("company","last"),
               site=("site","last"), hsl_max=("hsl","max"),
               duration_hours=("duration_hours","median")))
f = agg.join(meta)
# capacity: SCED-observed max HSL, not the static capacity csv (prior denominator bug)
f["cap_mw"] = f.hsl_max
f = f[(f.cap_mw > 5) & (f.total_rev.abs() > 0)]
f["opt_rate_pct"] = 100 * f.total_rev / f.theoretical_rev.replace(0, pd.NA)
f["energy_rev"] = f.da_energy_rev + f.rt_energy_rev + f.deviation_penalty
f["as_rev"] = f[["regup_rev","regdn_rev","rrs_rev","ecrs_rev","nonspin_rev"]].sum(axis=1)
f["as_share_pct"] = 100 * f.as_rev / f.total_rev.replace(0, pd.NA)
f["da_share_of_energy_pct"] = 100 * f.da_energy_rev / (f.da_energy_rev + f.rt_energy_rev).replace(0, pd.NA)
f["rev_per_mw"] = f.total_rev / f.cap_mw
f = f.reset_index()

# zone from metadata price_node
obj = dl.read_csv("ercot/metadata/objects/all.csv.gz")
pn = obj[obj.OBJECTTYPE == "price_node"][["OBJECTNAME","ZONE"]].drop_duplicates("OBJECTNAME")
f = f.merge(pn, left_on="settlement_point", right_index=False, right_on="OBJECTNAME", how="left")

f.to_csv(OUT/"draft_fleet_mix_jan_may2026.csv", index=False)
hou = f[f.ZONE == "HOUSTON"].sort_values("rev_per_mw", ascending=False)
print(f"\nfleet with zone: {f.ZONE.notna().sum()} / {len(f)}; HOUSTON: {len(hou)}")
cols = ["resource_name","settlement_point","company","cap_mw","duration_hours","rev_per_mw",
        "opt_rate_pct","as_share_pct","da_share_of_energy_pct","total_rev"]
pd.set_option("display.width", 220)
print("\n=== HOUSTON-zone BESS, 2026-01-01..05-25 (ranked by $/MW) ===")
print(hou[cols].head(25).to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
gks = f[f.settlement_point == "GKS_BESS_RN"]
print("\n=== GKS (SOUTH, incumbent reference) ===")
print(gks[cols].to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
print("\n=== fleet-wide medians ===")
for lbl, s in [("ALL", f), ("HOUSTON", hou)]:
    print(f"  {lbl:8s} n={len(s):3d}  rev/MW={s.rev_per_mw.median():,.0f}  "
          f"opt%={s.opt_rate_pct.median():.1f}  AS share%={s.as_share_pct.median():.1f}  "
          f"DA share of energy%={s.da_share_of_energy_pct.median():.1f}")
hou[cols].to_csv(OUT/"draft_houston_mix_jan_may2026.csv", index=False)
print("\nwrote draft_fleet_mix_jan_may2026.csv / draft_houston_mix_jan_may2026.csv")
