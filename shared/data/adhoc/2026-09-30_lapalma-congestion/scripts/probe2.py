import sys, pandas as pd, io, gzip
sys.path.insert(0, "."); import dl
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 100)
allo = dl.read_csv("ercot/metadata/objects/all.csv.gz", low_memory=False)
def peek(key, n=3):
    d = dl.read_csv(key, header=None, nrows=20000); print("\n#", key, d.shape); print(d.head(n).to_string())
    ids = d[0].unique(); print(allo[allo.OBJECTID.isin(ids)][["OBJECTID","OBJECTNAME","OBJECTTYPE","ZONE"]].to_string()); return d
peek("ercot/load/rtload_hourly_wz/20260922.csv.gz")
peek("ercot/gen/generation_solar_rt/20260922.csv.gz")
w = peek("ercot/weather/actual/20260922.csv.gz")
ws = dl.read_csv("ercot/metadata/objects/wx_station.csv.gz", low_memory=False)
print(ws.columns.tolist()); print(ws[ws.astype(str).apply(lambda c: c.str.contains("BROWNSV|MCALLEN|HARLINGEN|KBRO|KMFE|KHRL|EDINBURG|WESLACO|PORT ISABEL", case=False)).any(axis=1)].to_string())
k = sorted(k for k,_ in dl.ls("ercot/gen/ercot_60d_sced_gen_resource_data/2026", 400))[-2:]; print(k)
