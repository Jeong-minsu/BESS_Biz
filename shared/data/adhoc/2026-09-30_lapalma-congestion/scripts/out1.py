import sys, pandas as pd
sys.path.insert(0, "."); import dl
pd.set_option("display.width", 260); pd.set_option("display.max_rows", 300); pd.set_option("display.max_colwidth", 45)
OUT_COLS = ["ISO","FACILITY","FROMSTATION","TOSTATION","KV","FROMZONE","TOZONE","FACILITY_TYPE","TYPE","TYPE_DETAIL","STATUS","STATUS_DETAIL","STARTDATE","ENDDATE","PLANNED_STARTDATE","PLANNED_ENDDATE","OPEN_CLOSE","TICKETID","FACILITYID","LASTCHANGEDATE","PUBLISHDATE","REPORTED_NAME","FROMSTATIONID","TOSTATIONID"]
print(dl.ls("ercot/transmission/outages/")[:5]); print([k for k,_ in dl.ls("ercot/transmission/outages/actual/202609", 2000)][-5:])
df = dl.read_csv("ercot/transmission/outages/actual/2026092217.csv.gz", header=None); df.columns = OUT_COLS[:df.shape[1]]
print(df.shape, df.STATUS.value_counts().to_dict(), df.FACILITY_TYPE.value_counts().head(10).to_dict())
VAL = "LA PALMA|HAINE|RIO HONDO|GULCH|KINGFISHER|KNGFSHER|LAURELES|LOS FRESNOS|VILLA CAVAZOS|BROWNSVILLE|SILAS|HARLINGEN|RAYMOND|RANGERVILLE|KELVIN|EDINBURG|MCALLEN|PHARR|WESLACO|FRONTERA|MERCEDES|SAN BENITO|OLEANDER|ALBERTA|AJO|PALMITO|RAILROAD|NORTH EDINBURG|HIDALGO|MILHWY|MV|LON HILL|CAMERON|PORT ISABEL|BAYVIEW|OLMITO|LOMA ALTA|ELSA|DONNA|ALAMO|MISSION|STEWART|LA VILLA"
a = df[(df.STATUS.astype(str).str.upper()=="ACTIVE") & (df.FROMZONE=="SOUTH")]
m = a.FROMSTATION.astype(str).str.upper().str.contains(VAL) | a.TOSTATION.astype(str).str.upper().str.contains(VAL)
b=a[m]; b=b[b.FACILITY_TYPE.isin(["LINE","XFMR","UN","CAP","SVC","REAC"]) | (b.KV>=345)]; print(b[["FACILITY","FROMSTATION","TOSTATION","KV","FACILITY_TYPE","TYPE","STATUS_DETAIL","STARTDATE","ENDDATE"]].sort_values(["KV","FACILITY_TYPE"], ascending=False).to_string()); print(sorted(df.FACILITY_TYPE.dropna().unique()))
