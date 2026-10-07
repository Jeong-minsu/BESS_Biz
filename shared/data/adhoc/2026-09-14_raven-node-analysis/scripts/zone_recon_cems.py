"""zone_ recon: which units appear in ercot/cems (fossil only or all techs?) and column meaning."""
import sys, pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); import dl
pd.set_option("display.width", 300); pd.set_option("display.max_colwidth", 60)
obj = pd.read_parquet(ROOT / "raw/objects_all.parquet")
df = dl.read_csv("ercot/cems/20260601.csv.gz", header=None)
print(df.shape); print(df.describe().T)
for c in (3, 4):
    j = obj[obj.OBJECTID.isin(df[c].unique())]
    print("col", c, "n ids", df[c].nunique(), "matched", len(j)); print(j.OBJECTTYPE.value_counts()); print(j.head(8).to_string())
u = obj[obj.OBJECTTYPE == "unit"]
hit = u[u.OBJECTID.isin(set(df[3]) | set(df[4]))]
print("unit objects in cems today:", len(hit))
print(hit.OBJECTNAME.str.contains("Solar|Wind|Storage|BESS|Battery", case=False).sum(), "look like renewables/storage")
print(hit[hit.OBJECTNAME.str.contains("Solar|Wind|Storage|BESS|Battery", case=False)].head(10).to_string())
# column 5 vs 9: gen MW vs capacity?
print(df.groupby(3)[[5, 6, 7, 8, 9]].max().head(10))
