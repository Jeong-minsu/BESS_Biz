"""Single-day case study 2026-06-08: MDOPHR99_A & STPWAP39_1.
Pulls DA binding, RT/SCED binding, active outages, COAST load + coastal temps.
Reuses dl.py datalake client. REAL data only."""
import concurrent.futures as cf
import pandas as pd
import re
import dl

TARGETS = {"MDOPHR99_A", "STPWAP39_1"}
DAY = "20260608"
WZ_COAST = 10002211345
STATIONS = ["TX - Galveston/Scholes", "TX - Houston/William P. Hobby", "TX - Victoria/Regional Airport"]
PAT = re.compile(r"PHR|ROBINSON|MEADOW|MDO|PARISH|WAP|\bSTP\b|S_TEXAS|HILLJE|BLESSING|VELASCO|HOLMAN|SMITHER|THOMPSON|DOW|JACK|HLP|BAILEY|STX", re.I)
OUT_COLS = ["ISO","FACILITY","FROMSTATION","TOSTATION","KV","FROMZONE","TOZONE",
            "FACILITY_TYPE","TYPE","TYPE_DETAIL","STATUS","STATUS_DETAIL","STARTDATE",
            "ENDDATE","PLANNED_STARTDATE","PLANNED_ENDDATE","OPEN_CLOSE","TICKETID",
            "FACILITYID","LASTCHANGEDATE","PUBLISHDATE","REPORTED_NAME","FROMSTATIONID","TOSTATIONID"]

def section(t): print(f"\n{'='*70}\n{t}\n{'='*70}")

# ---------- 1. DA binding ----------
section("1. DAM binding 2026-06-08")
da = dl.read_da(DAY)
if da is None:
    print("DA FILE NOT PUBLISHED / INSUFFICIENT-DATA")
else:
    sub = da[da.CONSTRAINTNAME.isin(TARGETS)].copy()
    if sub.empty:
        print("Neither constraint bound in DAM 2026-06-08")
    else:
        sub["hr"] = pd.to_datetime(sub.DATETIME).dt.hour + 1
        for c, g in sub.groupby("CONSTRAINTNAME"):
            print(f"\n--- {c} ({g.REPORTED_NAME.iloc[0]}) DAM ---")
            print("  binding HEs:", sorted(g.hr.tolist()))
            print("  lambda: mean %.1f median %.1f max %.1f" % (g.PRICE.mean(), g.PRICE.median(), g.PRICE.max()))
            pk = g.loc[g.PRICE.idxmax()]
            print("  peak HE%d lambda=%.1f limit=%.0f flow=%.0f" % (pk.hr, pk.PRICE, pk.LIMITMW, pk.VALUEMW))
            print("  contingencies:", g.CONTINGENCY.fillna("(blank)").value_counts().to_dict())

# ---------- 2. RT/SCED binding ----------
section("2. RT/SCED binding 2026-06-08")
def rt_one(hh):
    df = dl.read_rt(hh)
    if df is None: return None
    s = df[df.CONSTRAINTNAME.isin(TARGETS)]
    return s.copy() if not s.empty else None
hours = [f"{DAY}{h:02d}" for h in range(24)]
rows, nofile = [], 0
with cf.ThreadPoolExecutor(max_workers=24) as ex:
    for hh, r in zip(hours, ex.map(rt_one, hours)):
        if r is not None: rows.append(r)
# detect file availability
probe = dl.read_rt(f"{DAY}12")
if probe is None:
    print("RT/SCED files NOT PUBLISHED for 2026-06-08 / INSUFFICIENT-DATA")
elif not rows:
    print("RT files present but neither constraint bound in SCED 2026-06-08")
else:
    rt = pd.concat(rows, ignore_index=True)
    rt["dt"] = pd.to_datetime(rt.DATETIME)
    for c, g in rt.groupby("CONSTRAINTNAME"):
        print(f"\n--- {c} RT/SCED ---")
        print("  5-min binding intervals:", len(g))
        print("  HE range:", sorted(set((g.dt.dt.hour+1).tolist())))
        print("  lambda: mean %.1f median %.1f max %.1f" % (g.PRICE.mean(), g.PRICE.median(), g.PRICE.max()))
        pk = g.loc[g.PRICE.idxmax()]
        print("  peak:", pk.DATETIME, "lambda=%.1f limit=%.0f flow=%.0f" % (pk.PRICE, pk.LIMITMW, pk.VALUEMW))
        print("  CONTINGENCY text:", g.CONTINGENCY.fillna("(blank)").value_counts().head(5).to_dict())

# ---------- 3. Outages ----------
section("3. Active corridor outages 2026-06-08 (HE15 snapshot)")
od = dl.try_read_csv(f"ercot/transmission/outages/actual/{DAY}15.csv.gz", header=None)
if od is None:
    # try a couple other hours
    for h in ("12","18","09"):
        od = dl.try_read_csv(f"ercot/transmission/outages/actual/{DAY}{h}.csv.gz", header=None)
        if od is not None: break
if od is None:
    print("OUTAGE FILE NOT PUBLISHED / INSUFFICIENT-DATA")
else:
    od.columns = OUT_COLS[:od.shape[1]]
    m = (od.FROMSTATION.astype(str).str.contains(PAT) | od.TOSTATION.astype(str).str.contains(PAT) |
         od.REPORTED_NAME.astype(str).str.contains(PAT))
    hit = od[m]
    print(f"total active outages={len(od)}  corridor-relevant={len(hit)}")
    cols = ["FROMSTATION","TOSTATION","KV","TYPE","STATUS","STARTDATE","ENDDATE","REPORTED_NAME"]
    with pd.option_context("display.max_colwidth", 30, "display.width", 260, "display.max_rows", 60):
        print(hit[cols].to_string())

# ---------- 4. Load + temp ----------
section("4. COAST load & coastal temps 2026-06-08")
ld = dl.try_read_csv(f"ercot/load/rtload_hourly_wz/{DAY}.csv.gz", header=None)
if ld is None:
    print("LOAD FILE NOT PUBLISHED / INSUFFICIENT-DATA")
else:
    ld.columns = ["OBJECTID","DATATYPEID","DATETIME","TIMEZONE","VALUE","LOADID"]
    g = ld[ld.OBJECTID == WZ_COAST][["DATETIME","VALUE"]].copy()
    g["hr"] = pd.to_datetime(g.DATETIME).dt.hour + 1
    print("  COAST load peak: HE%d  %.0f MW | daily mean %.0f MW" %
          (g.loc[g.VALUE.idxmax()].hr, g.VALUE.max(), g.VALUE.mean()))
wx = dl.try_read_csv(f"ercot/weather/actual/{DAY}.csv.gz", header=None)
if wx is None:
    print("WEATHER FILE NOT PUBLISHED / INSUFFICIENT-DATA")
else:
    wx.columns = ["OBJECTID","DATETIME_UTC","DATETIME","TIMEZONE","NAME","WBAN","ISO","DRYBULB",
                  "WETBULB","DEWPT","WINDMPH","RH","PRESS","SKY","PRECIP"]
    w = wx[wx.NAME.isin(STATIONS)]
    for nm, gg in w.groupby("NAME"):
        print("  %-32s max DRYBULB %.0fF  mean wind %.1f mph" % (nm, gg.DRYBULB.max(), gg.WINDMPH.mean()))
