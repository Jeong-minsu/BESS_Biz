"""Valley-pocket unit output (ERCOT 60-day SMNE, telemetered net output, 15-min) 2024-07-03..latest."""
import sys, io, pandas as pd
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "."); import dl
U = ['CAMWIND_UNIT1','CFLATS_U1','CITRUSCY_15UNITS','DUKE_CC1','E_HARRIS_15UNITS','FRONT_EC_CC1','LV5_UNIT_1','MESQCRK_WND1','MESQCRK_WND2',
     'NEBULA_UNIT1','NEDIN_CC1','NFAL_SLR_SOLAR1','PALMWIND_UNIT1','REDGATE_AGR_A','REDGATE_AGR_B','REDGATE_AGR_C','REDGATE_AGR_D',
     'SILASRAY_CC1','SILASRAY_SILAS_10','SILASRAY_SILAS_6','SILASRAY_SILAS_9','STAR_SLR_UNIT1','STAR_SLR_UNIT2','VANCOURT_UNIT1',
     'VENADO_UNIT1','VENADO_UNIT2','WMOOREII_WMOOREII','ELSAUZ_UNIT1','ELSAUZ_UNIT2','LA_PALMA_UNIT4','FAL_FALCONG1','FAL_FALCONG2','FAL_FALCONG3']
Q = "SELECT s._2, s._7, s._8 FROM s3object s WHERE s._7 IN (" + ",".join(f"'{u}'" for u in U) + ")"
def f(d):
    key = f"ercot/gen/ercot_60d_sced_smne_gen_res/{d:%Y%m%d}.csv.gz"
    try:
        r = dl.cli().select_object_content(Bucket="yedatalake", Key=key, ExpressionType="SQL", Expression=Q,
            InputSerialization={"CSV": {"FileHeaderInfo": "NONE"}, "CompressionType": "GZIP"}, OutputSerialization={"CSV": {}})
        b = io.BytesIO()
        for ev in r["Payload"]:
            if "Records" in ev: b.write(ev["Records"]["Payload"])
        if b.getbuffer().nbytes == 0: return None
        b.seek(0); return pd.read_csv(b, header=None, names=["dt", "unit", "mw"])
    except Exception as e:
        if "NoSuchKey" not in str(e): print("ERR", d, str(e)[:100])
        return None
with ThreadPoolExecutor(24) as ex: parts = [x for x in ex.map(f, pd.date_range("2024-07-03", "2026-08-02")) if x is not None]
x = pd.concat(parts); x["dt"] = pd.to_datetime(x.dt); x.to_parquet("../raw/valley_units_smne.parquet")
print(x.shape, x.dt.min(), x.dt.max()); print(x.groupby("unit").mw.agg(["count","mean","max"]).round(1).to_string())
