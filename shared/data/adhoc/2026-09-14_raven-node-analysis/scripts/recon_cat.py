import sys, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl
cat = dl.read_csv("ercot/metadata/catalog.csv.gz")
c = cat[["DATATYPEID","SERIESNAME","PATH","OBJECT_TYPE","INTERVAL","FILEINTERVAL","UNITS"]]
m = c.PATH.astype(str).str.contains("prices|lmp|spp", case=False, na=False) | \
    c.SERIESNAME.astype(str).str.contains("LMP|SPP|PRICE|MCPC", case=False, na=False)
pd.set_option("display.width",300); pd.set_option("display.max_colwidth",60)
print(c[m].to_string())
