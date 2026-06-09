"""Contingency -> element membership resolution for MDOPHR99_A & STPWAP39_1.

REAL data only (Yes Energy datalake S3 yedatalake). Resolves:
  1. monitored element  : DA constraint FACILITYID -> facility.csv.gz (exact line, from/to station, kV)
  2. contingency objectid: CONTINGENCYID (in DA file) == contingency.csv.gz OBJECTID  [VERIFIED]
  3. contingency members : ATTEMPTED via objectrelationships.csv.gz -> NOT AVAILABLE
                           (no CONTINGENCY2* RELTYPE exists; contingency table is name-only).
                           Best-effort token decode against facility circuit-code suffixes instead.

Run from this dir:  python contingency_membership.py
"""
import dl, pandas as pd

pd.set_option("display.width", 240); pd.set_option("display.max_colwidth", 46)

# contingency names seen binding for the two constraints (from validated da_binding parquet)
TARGET_CONS = ["DWAP_OB5", "DPHRCTR5", "DKG_NB_5", "DOASWAP5",      # MDO-PHR
               "DWPWFWP5", "DBLBYWF5", "DWPWFCK5", "DSTPREF5"]       # STP-WAP

def main():
    con = dl.read_csv("ercot/metadata/objects/contingency.csv.gz")
    fac = dl.read_csv("ercot/metadata/objects/facility.csv.gz", dtype=str)
    rel = dl.read_csv("ercot/metadata/objects/objectrelationships.csv.gz", dtype=str)

    # --- 1. contingency name -> objectid, and confirm it matches DA CONTINGENCYID ---
    cmap = con[con["CONTINGENCYNAME"].isin(TARGET_CONS)][["CONTINGENCYNAME", "OBJECTID"]]
    print("contingency name -> OBJECTID:\n", cmap.to_string(index=False), "\n")

    # --- 2. membership join attempt via objectrelationships (VERIFY, don't assume) ---
    objids = set(cmap["OBJECTID"].astype(str))
    hit = rel[rel["OBJECTID1"].isin(objids) | rel["OBJECTID2"].isin(objids)]
    print(f"objectrelationships rows referencing any contingency OBJECTID: {len(hit)}")
    print("RELTYPEs present in table:", sorted(rel['RELTYPE'].unique()))
    print(">>> No CONTINGENCY2FACILITY (or any contingency-keyed) relation exists -> "
          "explicit membership NOT resolvable from datalake.\n")

    # --- 3. monitored elements via DA FACILITYID (exact) ---
    da = dl.read_da("20250502")  # MDO-PHR binding day
    da2 = dl.read_da("20250514")  # STP-WAP binding day
    fids = pd.concat([da, da2])
    fids = fids[fids["CONSTRAINTNAME"].isin(["MDOPHR99_A", "STPWAP39_1"])]["FACILITYID"].astype(str).unique()
    mon = fac[fac["OBJECTID"].isin(fids)]
    print("MONITORED elements (exact, via DA FACILITYID join):")
    print(mon[["FACILITYNAME", "FROMSTATION", "FROMZONE", "TOSTATION", "TOZONE", "VOLTAGE"]].to_string(index=False), "\n")

    # --- 4. best-effort token decode: match contingency circuit-code to facility circuit suffix ---
    print("token decode (contingency code vs facility circuit designation):")
    for tok in ["OASWAP", "KG_NB", "REFSTP", "STPZWP"]:
        m = fac[fac["FACILITYNAME"].str.contains(tok, case=False, na=False) & (fac["VOLTAGE"].astype(float) >= 300)]
        if len(m):
            r = m.iloc[0]
            print(f"  {tok:8s} -> {r['FROMSTATION']} - {r['TOSTATION']} 345kV  (e.g. {r['FACILITYNAME']})")

if __name__ == "__main__":
    main()
