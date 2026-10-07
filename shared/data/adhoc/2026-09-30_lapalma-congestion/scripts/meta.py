import sys, pandas as pd
sys.path.insert(0, "."); import dl
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30); pd.set_option("display.max_colwidth", 60)
fac = dl.read_csv("ercot/metadata/objects/facility.csv.gz", low_memory=False)
print(fac.columns.tolist())
s = fac.astype(str)
m = s.apply(lambda c: c.str.contains("LA_PAL|LA PALMA|LAPALMA|VCAVAZ|HAINE", case=False)).any(axis=1)
print(fac[m].head(80).to_string())
fac[m].to_csv("../derived/lapalma_facilities.csv", index=False)
for f in ["station.csv.gz","ercot_plant.csv.gz","ercot_unit.csv.gz"]:
    d = dl.read_csv("ercot/metadata/objects/"+f, low_memory=False); print("\n==", f, d.columns.tolist())
    mm = d.astype(str).apply(lambda c: c.str.contains("PALMA|SILAS|FRONTERA|HIDALGO|MAGIC|BROWNSV|HARLINGEN|SAN BENITO|WESLACO|RAYMOND|CAVAZOS|EDINBURG|MCALLEN|PHARR", case=False)).any(axis=1)
    print(d[mm].head(60).to_string())
