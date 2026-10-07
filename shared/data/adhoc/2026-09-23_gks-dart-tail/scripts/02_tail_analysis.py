"""GKS_BESS_RN DART virtual: win rate / payoff / tail-risk check, 2024-07-04 .. 2026-09-22.

Unit bet = 1 MW for 1 hour. SHORT pnl = DA - RT ; LONG pnl = RT - DA  ($/MWh = $ per MW-h).
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
d = pd.read_csv(ROOT / "raw" / "ye_gks_lmp.csv")
d.columns = ["dt", "da", "rt", "he", "md", "pk", "mo", "yr"]
d = d.dropna(subset=["da", "rt"]).copy()
d["md"] = pd.to_datetime(d["md"])
d["short"] = d["da"] - d["rt"]
d["month"] = d["md"].dt.month
d["era"] = np.where(d["md"] >= "2025-12-05", "post-RTC+B", "pre-RTC+B")
d["period"] = d["md"].dt.year.astype(str)
d.to_parquet(ROOT / "derived" / "hourly.parquet")


def stats(x: pd.Series) -> dict:
    x = x.dropna().to_numpy()
    w, l = x[x > 0], x[x < 0]
    tot = x.sum()
    cum = np.cumsum(x)
    mdd = (cum - np.maximum.accumulate(np.r_[0, cum])[1:]).min()
    srt_loss = np.sort(l)  # most negative first
    # how many worst bets erase all net profit
    k_wipe = int(np.searchsorted(-np.cumsum(srt_loss), tot) + 1) if tot > 0 else 0
    srt_win = np.sort(w)[::-1]
    k_flip = int(np.searchsorted(np.cumsum(srt_win), tot) + 1) if tot > 0 else 0
    q01 = np.quantile(x, 0.01)
    avg_w, avg_l = (w.mean() if len(w) else 0), (-l.mean() if len(l) else 0)
    R = avg_w / avg_l if avg_l else np.nan
    return dict(
        n=len(x), win=len(w) / len(x), avg_win=avg_w, avg_loss=avg_l, payoff=R,
        be_win=1 / (1 + R) if R == R else np.nan,
        PF=w.sum() / -l.sum() if len(l) else np.nan, EV=x.mean(), median=np.median(x),
        total=tot, skew=pd.Series(x).skew(), p01=q01, p001=np.quantile(x, 0.001),
        CVaR1=x[x <= q01].mean(), worst=x.min(), best=x.max(), MDD=mdd,
        k_wipe=k_wipe, k_wipe_pct=k_wipe / len(x), k_flip=k_flip,
        loss_top1pct_share=(-np.sort(l)[: max(1, int(len(x) * 0.01))].sum()) / -l.sum() if len(l) else np.nan,
        EV_trim1=pd.Series(x).clip(np.quantile(x, 0.01), np.quantile(x, 0.99)).mean(),
    )


out = {}
S = d["short"]
out["hourly_all"] = pd.DataFrame({"SHORT": stats(S), "LONG": stats(-S)}).T
out["hourly_by_year_short"] = pd.DataFrame({k: stats(g["short"]) for k, g in d.groupby("period")}).T
out["hourly_by_era_short"] = pd.DataFrame({k: stats(g["short"]) for k, g in d.groupby("era")}).T
out["by_HE_short"] = pd.DataFrame({h: stats(g["short"]) for h, g in d.groupby("he")}).T

# daily bet: short all 24h (24 MWh/day) and block HE15-19
day24 = d.groupby("md")["short"].sum()
blk = d[d.he.between(15, 19)].groupby("md")["short"].sum()
out["daily_short"] = pd.DataFrame({"SHORT 24h/day": stats(day24), "SHORT HE15-19/day": stats(blk),
                                  "LONG 24h/day": stats(-day24)}).T

# DA offer-price floor on SHORT (clears only if DA >= floor) - ex-ante lever, leakage-free
rows = {}
for f in [-1e9, 0, 20, 30, 40, 50, 75, 100]:
    s = d.loc[d.da >= f, "short"]
    rows["all" if f < -1e8 else f"DA>={f}"] = stats(s)
out["short_da_floor"] = pd.DataFrame(rows).T

# worst days / hours for SHORT
worst_days = day24.sort_values().head(15).rename("short_24h_day")
worst_hours = d.nsmallest(20, "short")[["md", "he", "da", "rt", "short"]]

# monthly equity (short 24h)
monthly = d.groupby(d.md.dt.to_period("M"))["short"].agg(["sum", lambda s: (s > 0).mean()])
monthly.columns = ["short_pnl_per_MW", "win_rate"]
monthly["cum"] = monthly["short_pnl_per_MW"].cumsum()

pd.set_option("display.width", 250, "display.max_columns", 40, "display.float_format", "{:,.2f}".format)
cols = ["n", "win", "avg_win", "avg_loss", "payoff", "be_win", "PF", "EV", "median", "EV_trim1", "total",
        "skew", "p01", "CVaR1", "worst", "best", "MDD", "k_wipe", "k_wipe_pct", "k_flip", "loss_top1pct_share"]
with pd.ExcelWriter(ROOT / "derived" / "gks_dart_tail.xlsx") as xw:
    for k, v in out.items():
        print(f"\n=== {k} ===")
        print(v[cols].to_string())
        v[cols].to_excel(xw, sheet_name=k[:31])
    print("\n=== worst days (SHORT 24h, $/MW) ===\n", worst_days.to_string())
    print("\n=== worst hours ===\n", worst_hours.to_string())
    print("\n=== monthly ===\n", monthly.to_string())
    worst_days.to_excel(xw, sheet_name="worst_days")
    worst_hours.to_excel(xw, sheet_name="worst_hours")
    monthly.to_excel(xw, sheet_name="monthly")
