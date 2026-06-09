"""Fetch ddl.json for shift-factor + constraint tables to get authoritative columns."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(r"C:/Users/00904/ERCOT Projects/BESS_Biz/shared/data/adhoc/2026-06-09_houston-constraint-validation/scripts")))
import dl

for sub in ["market_shift_factors","ercot_sced_shift_factors","da","rt"]:
    base = f"ercot/transmission/constraints/{sub}/"
    print(f"\n===== {base} =====")
    # find ddl.json
    for cand in [base+"ddl.json", base.rstrip('/')+".ddl.json"]:
        try:
            d = json.loads(dl.raw(cand))
            print("  FOUND", cand)
            print("  ", json.dumps(d, indent=2)[:1500])
            break
        except Exception as e:
            pass
    else:
        # list to find any json
        keys = dl.ls(base, max_keys=2000)
        jsons = [k for k,_ in keys if k.endswith(".json")]
        print("  json files:", jsons[:10])
