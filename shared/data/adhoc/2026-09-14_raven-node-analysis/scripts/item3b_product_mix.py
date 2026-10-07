"""item3b: Houston-zone ESS actual product mix, DA/RT lean, capture vs own-node TB, capacity sanity.
Inputs (all real, no mock):
  - skill chunk outputs shared/data/pnl/all_bess/energy_as/chunks/{revenue_hourly,summary,tb_index}_*.parquet
    (ERCOT 60-day disclosure, post-RTC+B era only: all windows here are >= 2025-12-05)
  - skill SCED-ESR cache (5-min HSL / Telemetered Net Output / SOC) -> measured capacity & duration
  - raw/price_panel -> own-node RT hourly LMP for TB recompute
Usage: python item3b_product_mix.py --start 2026-06-01 --end 2026-08-31 --tag summer
"""
import argparse, hashlib, sys
from datetime import timedelta
import numpy as np, pandas as pd
from pathlib import Path
A = Path(__file__).resolve().parents[1]; ROOT = A.parents[3]
SK = ROOT/"skills/estimate-bess-energy-as/scripts"; sys.path.insert(0, str(SK))
from src.tb_index import calculate_tb_index_fractional
CH = ROOT/"shared/data/pnl/all_bess/energy_as/chunks"
ap = argparse.ArgumentParser(); ap.add_argument("--start", required=True); ap.add_argument("--end", required=True); ap.add_argument("--tag", required=True)
a = ap.parse_args(); S, E = pd.Timestamp(a.start), pd.Timestamp(a.end)
AS = ["regup_rev","regdn_rev","rrs_rev","ecrs_rev","nonspin_rev"]

# ── 1. chunk windows overlapping [S,E] ──
def win(p):
    s, e = p.stem.split("_")[-2:]; return pd.Timestamp(s), pd.Timestamp(e)
chunks = [p for p in CH.glob("revenue_hourly_*.parquet") if not (win(p)[1] < S or win(p)[0] > E)]
assert chunks, "no chunk outputs in window"
rev = pd.concat([pd.read_parquet(p) for p in chunks])
rev["_operating_date"] = pd.to_datetime(rev["_operating_date"]); rev = rev[(rev._operating_date>=S)&(rev._operating_date<=E)]
print("chunks:", sorted(str(win(p)[0].date())+".."+str(win(p)[1].date()) for p in chunks))
print("days covered:", rev._operating_date.nunique(), rev._operating_date.min().date(), rev._operating_date.max().date())
summ = pd.concat([pd.read_parquet(CH/("summary_"+p.stem.split("revenue_hourly_")[1]+".parquet")) for p in chunks])
sp_map = summ.groupby("resource_name").agg(settlement_point=("settlement_point","first"), qse=("qse","first"), company=("company","first"),
                                            csv_cap=("capacity_mw","first"), csv_mwh=("energy_mwh","first")).reset_index()

# ── 2. zone via metadata ──
meta = pd.read_parquet(A/"raw/metadata_objects_all.parquet")
pn = meta[meta.OBJECTTYPE=="price_node"].drop_duplicates("OBJECTNAME").set_index("OBJECTNAME")
sp_map["zone"] = sp_map.settlement_point.map(pn.ZONE); sp_map["sp_objectid"] = sp_map.settlement_point.map(pn.OBJECTID)
keep = sp_map[(sp_map.zone=="HOUSTON") | (sp_map.resource_name=="GKS_BESS_ESR1")].copy()

# ── 3. measured capacity from SCED-ESR cache (5-min) ──
def cache(key): return SK/"data/cache"/("ercot_api_"+hashlib.md5(key.encode()).hexdigest()+".parquet")
caps = []
d = S.date() - timedelta(days=1)          # API date d -> delivery d+1
while d <= E.date() - timedelta(days=1):
    f = cache(f"sced_disclosure_{d}")
    if f.exists():
        x = pd.read_parquet(f, columns=["Resource Name","HSL","Telemetered Net Output","State of Charge","Minimum SOC","Maximum SOC"])
        x = x[x["Resource Name"].isin(keep.resource_name)]
        g = x.groupby("Resource Name").agg(hsl_max=("HSL","max"), out_max=("Telemetered Net Output","max"), out_min=("Telemetered Net Output","min"),
              soc_max=("Maximum SOC","max"), soc_min=("Minimum SOC","min"), soc_obs_max=("State of Charge","max"), soc_obs_min=("State of Charge","min"),
              hsl_mean=("HSL","mean"), n=("HSL","size"))
        g["date"] = pd.Timestamp(d+timedelta(days=1)); caps.append(g.reset_index())
    d += timedelta(days=1)
caps = pd.concat(caps)
cap = caps.groupby("Resource Name").agg(hsl_max=("hsl_max","max"), out_max=("out_max","max"), out_min=("out_min","min"), soc_max=("soc_max","max"), soc_min=("soc_min","min"),
        soc_obs_max=("soc_obs_max","max"), soc_obs_min=("soc_obs_min","min"), hsl_mean=("hsl_mean","mean"), days_in_sced=("date","nunique")).reset_index().rename(columns={"Resource Name":"resource_name"})
cap["cap_meas"] = cap[["hsl_max","out_max"]].max(axis=1)
cap["dur_meas"] = ((cap.soc_max - cap.soc_min) / cap.cap_meas).round(2)
cap["dur_obs"] = ((cap.soc_obs_max - cap.soc_obs_min) / cap.cap_meas).round(2)
cap["avail"] = (cap.hsl_mean / cap.cap_meas).round(3)     # mean HSL / rated -> availability proxy
keep = keep.merge(cap, on="resource_name", how="left")
caps = caps.merge(keep[["resource_name","cap_meas"]].rename(columns={"resource_name":"Resource Name"}), on="Resource Name")
caps["avail_d"] = (caps.hsl_mean/caps.cap_meas).clip(0,1)

# ── 4. own-node TB at measured duration from price panel (RT hourly) ──
months = sorted({f"{t.year}{t.month:02d}" for t in pd.date_range(S,E)})
pp = pd.concat([pd.read_parquet(A/f"raw/price_panel/{m}.parquet", columns=["OBJECTID","DATETIME","RTLMP","DALMP","FLOWDAY"]) for m in months])
pp = pp[pp.OBJECTID.isin(keep.sp_objectid.dropna().astype(int))]; pp["FLOWDAY"]=pd.to_datetime(pp.FLOWDAY); pp = pp[(pp.FLOWDAY>=S)&(pp.FLOWDAY<=E)]
pp["he"] = pd.to_datetime(pp.DATETIME, format="%m/%d/%Y %H:%M:%S").dt.hour.replace(0,24)
tb_rows = []
for _, r in keep.iterrows():
    if pd.isna(r.sp_objectid) or pd.isna(r.dur_meas): continue
    node = pp[pp.OBJECTID==int(r.sp_objectid)]
    dur = float(np.clip(r.dur_meas, 0.25, 6))
    for fd, g in node.groupby("FLOWDAY"):
        g = g.sort_values("he"); rt = g.RTLMP.dropna().values; da = g.DALMP.dropna().values
        if len(rt) < 23: continue
        tb_rt = calculate_tb_index_fractional(rt, dur); tb2_rt = np.sort(rt)[-2:].mean()-np.sort(rt)[:2].mean()
        tb2_da = np.sort(da)[-2:].mean()-np.sort(da)[:2].mean() if len(da)>=23 else np.nan
        tb_rows.append({"resource_name":r.resource_name,"date":fd,"tb_dur_rt":tb_rt,"tb2_rt":tb2_rt,"tb2_da":tb2_da})
tb = pd.DataFrame(tb_rows).merge(caps[["Resource Name","date","avail_d"]].rename(columns={"Resource Name":"resource_name"}), on=["resource_name","date"], how="left")
tb = tb.merge(keep[["resource_name","cap_meas"]], on="resource_name")
tb["tb_rev"] = tb.tb_dur_rt*tb.cap_meas                       # $/day, ordered TB at measured duration, static capacity
tb["tb_rev_avail"] = tb.tb_rev*tb.avail_d.fillna(1)           # availability-adjusted (HSL-derated) benchmark
tb["tb2_rev_200"] = tb.tb2_rt*2*tb.cap_meas                   # BRIEF-style unordered TB2 x (cap x 2h)
tbagg = tb.groupby("resource_name").agg(days_px=("date","count"), tb_rev=("tb_rev","sum"), tb_rev_avail=("tb_rev_avail","sum"), tb2_rev_200=("tb2_rev_200","sum"),
        tb2_rt_mean=("tb2_rt","mean"), tb2_da_mean=("tb2_da","mean")).reset_index()

# ── 5. revenue mix ──
r = rev[rev.resource_name.isin(keep.resource_name)]
mix = r.groupby("resource_name")[["da_energy_rev","rt_energy_rev","deviation_penalty"]+AS+["total_rev"]].sum().reset_index()
mix["energy_rev"] = mix.da_energy_rev+mix.rt_energy_rev; mix["as_rev"] = mix[AS].sum(axis=1)
mix = mix.merge(r.groupby("resource_name")._operating_date.nunique().rename("days_rev").reset_index(), on="resource_name")
out = keep.merge(mix, on="resource_name", how="left").merge(tbagg, on="resource_name", how="left")
out["energy_share"] = out.energy_rev/out.total_rev; out["as_share"] = out.as_rev/out.total_rev
for c in AS: out[c.replace("_rev","_share")] = out[c]/out.total_rev
out["da_share_of_energy"] = out.da_energy_rev/out.energy_rev
out["opt_energy_pct"] = 100*out.energy_rev/out.tb_rev          # energy-only capture vs own-node ordered TB(dur)
out["opt_total_pct"] = 100*out.total_rev/out.tb_rev            # total (energy+AS) vs same energy-only TB
out["opt_energy_avail_pct"] = 100*out.energy_rev/out.tb_rev_avail
out["opt_total_avail_pct"] = 100*out.total_rev/out.tb_rev_avail
out["capture_tb2_200_pct"] = 100*out.total_rev/out.tb2_rev_200
out["rev_per_mw_day"] = out.total_rev/out.cap_meas/out.days_rev
out["rev_per_avail_mw_day"] = out.total_rev/(out.cap_meas*out.avail.clip(lower=0.01))/out.days_rev
out["flag"] = np.where(out.cap_meas.isna() | (out.cap_meas<1), "no-SCED", np.where(out.avail<0.2, "mostly-offline", np.where(out.dur_meas<0.5, "dur<0.5h", "")))
out = out.sort_values("rev_per_mw_day", ascending=False)
out.to_csv(A/f"derived/item3b_houston_mix_{a.tag}.csv", index=False)
tb.to_parquet(A/f"derived/item3b_houston_tb_daily_{a.tag}.parquet", index=False)

# hour-of-day mix for Houston fleet (>=50MW, avail>0.5) + GKS
big = out[(out.cap_meas>=50)&(out.avail>0.5)].resource_name
h = r[r.resource_name.isin(big)].copy(); h["he"] = pd.to_datetime(h.datetime).dt.hour+1
hod = h.groupby(["resource_name","he"])[["da_energy_rev","rt_energy_rev"]+AS].sum().reset_index()
hod.to_csv(A/f"derived/item3b_houston_hourly_mix_{a.tag}.csv", index=False)

pd.set_option("display.width",320); pd.set_option("display.max_columns",40)
cols = ["resource_name","settlement_point","zone","cap_meas","csv_cap","dur_meas","avail","days_rev","total_rev","energy_share","da_share_of_energy",
        "regup_share","regdn_share","rrs_share","ecrs_share","nonspin_share","opt_energy_pct","opt_total_pct","opt_total_avail_pct","rev_per_mw_day","flag"]
print(out[cols].round(3).to_string())
