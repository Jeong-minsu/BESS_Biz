"""zone_ recon: find zonal load / generation / fuel-mix series in the datalake catalog."""
import sys, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl
cat = dl.read_csv("ercot/metadata/catalog.csv.gz")
print(cat.columns.tolist())
c = cat[["DATATYPEID","SERIESNAME","PATH","OBJECT_TYPE","INTERVAL","FILEINTERVAL","UNITS"]]
m = c.PATH.astype(str).str.contains("load|gen|fuel|capacity|outage", case=False, na=False) | \
    c.SERIESNAME.astype(str).str.contains("LOAD|GEN|FUEL|CAP|HSL", case=False, na=False)
pd.set_option("display.width", 300); pd.set_option("display.max_colwidth", 70); pd.set_option("display.max_rows", 500)
print(c[m].to_string())
