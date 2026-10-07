"""15 - AS opt 분해.

  AS_opt = AS수익 / TB
         = [AS수익 / (MW x 24h x days)]  /  [TB / (MW x 24h x days)]
         = (AS $/MW-day) / (TB $/MW-day)
  분자 AS $/MW-day = Q_as x P_as x 24
      Q_as = Σ AS낙찰MWh / (MW x 24h x days)     <- AS 용량 커밋률 (0~1)
      P_as = AS수익 / AS낙찰MWh                  <- 실현 단가 $/MW-h (RT 되사기 반영 후)
  분모 TB $/MW-day = TB스프레드($/MWh) x duration(h)
  => AS_opt = (Q_as x P_as x 24) / (TB스프레드 x duration)
"""
from pathlib import Path
import pandas as pd

D = Path(__file__).resolve().parents[1] / "derived"
d = pd.read_csv(D / "fleet_opt_by_resource.csv")
d["mwday"] = d["mw"] * d["days"]
d["Q_as"] = d["as_mwh"] / (d["mw"] * 24 * d["days"])
d["P_as"] = d["as_rev"] / d["as_mwh"].replace(0, pd.NA)
d["as_per_mwday"] = d["as_rev"] / d["mwday"]
d["tb_per_mwday"] = d["tb"] / d["mwday"]
d["as_opt_check"] = d["as_per_mwday"] / d["tb_per_mwday"]
d.to_csv(D / "fleet_opt_with_as_decomp.csv", index=False)

COLS = ["opt_as", "Q_as", "P_as", "as_per_mwday", "tb_per_mwday", "tb_sp", "dur", "as_opt_check"]
pd.set_option("display.width", 240)
fmt = lambda v: f"{v:,.3f}"
for lbl, x in d.groupby("label"):
    x = x.sort_values("opt", ascending=False)
    top = x.head(10)
    gk = x[x["resource"].str.contains("GKS")]
    rows = pd.DataFrame({
        "Top10 평균": top[COLS].mean(),
        "Top10 중 AS형(상위3)": top.nlargest(3, "opt_as")[COLS].mean(),
        "플릿 중앙값": x[COLS].median(),
        "GKS": gk[COLS].iloc[0],
    }).T
    print(f"\n=== {lbl} ===")
    print(rows.to_string(float_format=fmt))
    print("  GKS %ile —  Q_as {:.0f} / P_as {:.0f} / AS$per MW-day {:.0f}".format(
        (x["Q_as"] < gk["Q_as"].iloc[0]).mean() * 100,
        (x["P_as"] < gk["P_as"].iloc[0]).mean() * 100,
        (x["as_per_mwday"] < gk["as_per_mwday"].iloc[0]).mean() * 100))
    print("  AS형 Top3:", ", ".join(top.nlargest(3, "opt_as")["resource"]))
