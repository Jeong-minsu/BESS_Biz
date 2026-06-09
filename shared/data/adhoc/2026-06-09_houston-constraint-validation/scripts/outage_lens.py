"""Outage lens: at a given hour snapshot, list ACTIVE transmission outages
on Houston/coastal corridor stations relevant to MDO-PHR & STP-WAP."""
import sys
import pandas as pd
import re
import dl

OUT_COLS = ["ISO","FACILITY","FROMSTATION","TOSTATION","KV","FROMZONE","TOZONE",
            "FACILITY_TYPE","TYPE","TYPE_DETAIL","STATUS","STATUS_DETAIL","STARTDATE",
            "ENDDATE","PLANNED_STARTDATE","PLANNED_ENDDATE","OPEN_CLOSE","TICKETID",
            "FACILITYID","LASTCHANGEDATE","PUBLISHDATE","REPORTED_NAME","FROMSTATIONID","TOSTATIONID"]

PAT = re.compile(r"PHR|ROBINSON|MEADOW|MDO|PARISH|WAP|\bSTP\b|S_TEXAS|HILLJE|BLESSING|VELASCO|HOLMAN|SMITHER|THOMPSON|DOW|JACK|HLP|BAILEY|STX", re.I)

def snap(yyyymmddhh):
    df = dl.try_read_csv(f"ercot/transmission/outages/actual/{yyyymmddhh}.csv.gz", header=None)
    if df is None:
        return None
    df.columns = OUT_COLS[:df.shape[1]]
    return df

if __name__ == "__main__":
    for hh in sys.argv[1:]:
        df = snap(hh)
        if df is None:
            print(hh, "NO FILE"); continue
        active = df[df["STATUS"].astype(str).str.upper().isin(["ACTIVE","IN","OUT","CONTINUOUS"]) | df["STATUS"].notna()]
        m = (active["FROMSTATION"].astype(str).str.contains(PAT) |
             active["TOSTATION"].astype(str).str.contains(PAT) |
             active["REPORTED_NAME"].astype(str).str.contains(PAT))
        hit = active[m]
        print(f"\n===== {hh}  total active outages={len(active)}  corridor-relevant={len(hit)} =====")
        cols = ["FROMSTATION","TOSTATION","KV","TYPE","TYPE_DETAIL","STATUS","STARTDATE","ENDDATE","REPORTED_NAME"]
        with pd.option_context("display.max_colwidth", 32, "display.width", 240):
            print(hit[cols].to_string())
