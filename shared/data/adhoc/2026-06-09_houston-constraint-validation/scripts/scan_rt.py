"""Pass 2: pull RT (SCED, NP6-86-CD) 5-min binding for the two constraints
on selected strong-binding days. Confirms physical binding + contingency text.
"""
import sys, concurrent.futures as cf
import pandas as pd
import dl

TARGETS = {"MDOPHR99_A", "STPWAP39_1"}

def one(yyyymmddhh):
    df = dl.read_rt(yyyymmddhh)
    if df is None:
        return None
    sub = df[df["CONSTRAINTNAME"].isin(TARGETS)]
    if sub.empty:
        return None
    return sub[["CONSTRAINTNAME","DATETIME","CONTINGENCY","CONTROLLINGACTION","PRICE",
                "LIMITMW","VALUEMW","VIOLATEDMW","CONSTRAINT_TYPE"]].copy()

def pull_days(days):
    hours = [f"{d}{h:02d}" for d in days for h in range(24)]
    rows = []
    with cf.ThreadPoolExecutor(max_workers=24) as ex:
        for r in ex.map(one, hours):
            if r is not None:
                rows.append(r)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)

if __name__ == "__main__":
    days = sys.argv[1:]
    out = pull_days(days)
    if out.empty:
        print("NO RT BINDING on", days); sys.exit()
    out["dt"] = pd.to_datetime(out["DATETIME"])
    for c, g in out.groupby("CONSTRAINTNAME"):
        print(f"\n=== {c} RT/SCED on {days} ===")
        print("  5-min binding intervals:", len(g))
        print("  lambda: mean %.1f median %.1f max %.1f" % (g.PRICE.mean(), g.PRICE.median(), g.PRICE.max()))
        print("  CONTINGENCY text value_counts:")
        print(g["CONTINGENCY"].fillna("(blank)").value_counts().head(6).to_string())
        print("  CONSTRAINT_TYPE:", g["CONSTRAINT_TYPE"].fillna("(blank)").unique().tolist())
        vmax = g.loc[g.PRICE.idxmax()]
        print("  peak interval:", vmax["DATETIME"], "lambda=%.1f" % vmax.PRICE,
              "limit=%.0f flow=%.0f viol=%.1f" % (vmax.LIMITMW, vmax.VALUEMW, vmax.VIOLATEDMW),
              "| cont:", vmax["CONTINGENCY"])
