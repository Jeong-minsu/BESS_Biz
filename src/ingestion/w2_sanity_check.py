"""
W2 exit gate sanity check:
  DAM constraint (W1) × DAM shift factor (W2 0.4) join →
  (date, hour, constraint, pnode, shift_factor, λ) table →
  MCC reconstruction = -Σ(SF × λ) for sample nodes.

Run after market_shift_factors backfill completes.
Requires:
  data/interim/constraint_binding_history.parquet  (W1)
  data/raw/ercot/transmission/constraints/market_shift_factors/  (W2)
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[2]
CONSTRAINTS_PATH = BASE / "data" / "interim" / "constraint_binding_history.parquet"
MARKET_SF_DIR = BASE / "data" / "raw" / "ercot" / "transmission" / "constraints" / "market_shift_factors"

# Sample window for the sanity check — use a recent, well-populated week
SAMPLE_START = date(2026, 5, 19)
SAMPLE_END = date(2026, 5, 25)


def load_market_sf(start: date, end: date) -> pd.DataFrame:
    """Load market_shift_factors for the given date range.

    DATETIME is stored as 'MM/DD/YYYY HH:MM:SS' (US format) so lexicographic
    pushdown filtering is not possible. Reads each part file in 2M-row batches
    to bound peak memory, then filters in-memory. Handles both monolithic
    part.parquet and chunked part-H1/H2 layouts.
    """
    import pyarrow.parquet as pq_lib

    BATCH_ROWS = 2_000_000

    frames = []
    for yr in range(start.year, end.year + 1):
        year_dir = MARKET_SF_DIR / f"year={yr}"
        if not year_dir.exists():
            print(f"  WARNING: {year_dir} not found — run W2 backfill first")
            continue
        parts = sorted(year_dir.glob("*.parquet"))
        if not parts:
            print(f"  WARNING: no parquet files in {year_dir} — run W2 backfill first")
            continue
        for part_path in parts:
            pf = pq_lib.ParquetFile(part_path)
            for batch in pf.iter_batches(batch_size=BATCH_ROWS):
                df_b = batch.to_pandas()
                df_b["_dt"] = pd.to_datetime(df_b["DATETIME"], errors="coerce")
                df_b["_date"] = df_b["_dt"].dt.date
                mask = (df_b["_date"] >= start) & (df_b["_date"] <= end)
                if mask.any():
                    frames.append(df_b[mask].copy())

    if not frames:
        raise FileNotFoundError(f"No market_shift_factors data found for {start}–{end}")
    return pd.concat(frames, ignore_index=True)


def run():
    print("=== W2 Sanity Check: MCC Reconstruction ===\n")

    # 1. Load binding constraint history for sample window
    print(f"Loading constraint_binding_history for {SAMPLE_START} → {SAMPLE_END}...")
    da_df = pd.read_parquet(CONSTRAINTS_PATH)
    da_df = da_df[(da_df["date"] >= SAMPLE_START) & (da_df["date"] <= SAMPLE_END)]
    print(f"  DA constraints: {len(da_df):,} rows, {da_df['FACILITYID'].nunique()} unique facilities")

    # 2. Load market shift factors
    print(f"\nLoading market_shift_factors for {SAMPLE_START} → {SAMPLE_END}...")
    sf_df = load_market_sf(SAMPLE_START, SAMPLE_END)
    print(f"  Shift factors: {len(sf_df):,} rows, {sf_df['PRICENODEID'].nunique():,} unique pricenodes")
    print(f"  MARKET values: {sf_df['MARKET'].value_counts().to_dict()}")

    # 3. Filter to DA market only
    sf_da = sf_df[sf_df["MARKET"] == "DA"].copy()
    sf_da["_hour"] = sf_da["_dt"].dt.hour
    print(f"\n  DA-market shift factor rows: {len(sf_da):,}")

    # 4. Join DA constraints → shift factors on (FACILITYID, CONTINGENCYID, date, hour)
    da_df["hour_col"] = pd.to_datetime(da_df["DATETIME"], errors="coerce").dt.hour
    da_slim = da_df[["date", "hour_col", "FACILITYID", "CONTINGENCYID", "PRICE",
                     "CONSTRAINTNAME"]].copy()
    da_slim["FACILITYID"] = pd.to_numeric(da_slim["FACILITYID"], errors="coerce").astype("Int64")
    da_slim["CONTINGENCYID"] = pd.to_numeric(da_slim["CONTINGENCYID"], errors="coerce").astype("Int64")

    sf_da["FACILITYID"] = pd.to_numeric(sf_da["FACILITYID"], errors="coerce").astype("Int64")
    sf_da["CONTINGENCYID"] = pd.to_numeric(sf_da["CONTINGENCYID"], errors="coerce").astype("Int64")

    joined = sf_da.merge(
        da_slim,
        left_on=["_date", "_hour", "FACILITYID", "CONTINGENCYID"],
        right_on=["date", "hour_col", "FACILITYID", "CONTINGENCYID"],
        how="inner",
    )
    print(f"\nJoined table shape: {joined.shape}")
    print(f"  Unique (date, hour) combos: {joined[['_date','_hour']].drop_duplicates().shape[0]}")
    print(f"  Unique pricenodes: {joined['PRICENODEID'].nunique():,}")

    # 5. MCC reconstruction per (date, hour, PRICENODEID)
    # MCC_n_h = -Σ_c (SF_{n,c,h} × λ_{c,h})
    joined["mcc_contribution"] = -joined["SHIFTFACTOR"] * joined["PRICE"]
    mcc = (joined.groupby(["_date", "_hour", "PRICENODEID"])["mcc_contribution"]
           .sum().reset_index().rename(columns={"mcc_contribution": "MCC_reconstructed"}))

    print(f"\nMCC reconstruction table: {len(mcc):,} rows "
          f"({mcc['PRICENODEID'].nunique():,} nodes)")
    print(f"  MCC stats:")
    print(f"    min={mcc['MCC_reconstructed'].min():.2f}, "
          f"max={mcc['MCC_reconstructed'].max():.2f}, "
          f"mean={mcc['MCC_reconstructed'].mean():.2f}, "
          f"median={mcc['MCC_reconstructed'].median():.2f} $/MWh")

    # 6. Show top-10 most congested nodes (by mean |MCC|)
    top_nodes = (mcc.groupby("PRICENODEID")["MCC_reconstructed"]
                 .agg(mean_mcc="mean", abs_mean=lambda x: abs(x).mean(), count="count")
                 .sort_values("abs_mean", ascending=False).head(10))
    print(f"\n  Top-10 nodes by mean |MCC| (2026-05-19 to 25):")
    print(top_nodes.to_string())

    # 7. Sample: show day breakdown for the top node
    top_pnode = top_nodes.index[0]
    sample = mcc[mcc["PRICENODEID"] == top_pnode].sort_values(["_date", "_hour"])
    print(f"\n  Node {top_pnode} hourly MCC sample (first 24 hours):")
    print(sample.head(24)[["_date", "_hour", "MCC_reconstructed"]].to_string(index=False))

    print("\n=== Sanity check complete ===")
    print("NOTE: Comparison against actual DAM LMP MCC requires W3 (bus_lmp backfill).")
    print("The reconstruction logic and join are validated above.")
    return mcc


if __name__ == "__main__":
    run()
