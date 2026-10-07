import sys, json, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); import dl
pd.set_option("display.width",260); pd.set_option("display.max_columns",40)
for t in ["lmp","bus_lmp"]:
    print(f"\n########## {t} ddl.json ##########")
    try: print(dl.raw(f"ercot/prices/{t}/ddl.json").decode()[:1500])
    except Exception as e: print("  err", e)
print("\n########## catalog ##########")
cat = dl.read_csv("ercot/metadata/catalog.csv.gz")
print(cat.to_string()[:6000])
