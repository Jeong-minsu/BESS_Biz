"""
Revenue Calculator – DA/RT Energy & Ancillary Service revenue estimation
Uses Two-Settlement System unified formula (no case branching).

Core formula (energy & AS alike):
    Total Revenue = DA_MW * DA_Price + (RT_MW - DA_MW) * RT_Price

Revenue is computed at the source data's native granularity (5-min / 15-min)
first, then aggregated to hourly sums to avoid mean(P)*mean(Q) distortion.
"""
import pandas as pd
import numpy as np
from config import AS_PRODUCTS, DEVIATION_THRESHOLD_MW, DEVIATION_PENALTY_RATE


# ---------------------------------------------------------------------------
# Interval detection helper
# ---------------------------------------------------------------------------

def _detect_interval_hours(df: pd.DataFrame, dt_col: str = "datetime") -> float:
    """
    Detect the data interval in hours from consecutive unique timestamps.
    Returns fraction of an hour (e.g. 5-min -> 1/12, 15-min -> 0.25, hourly -> 1.0).
    Falls back to 1.0 (hourly) if detection fails.

    Uses unique timestamps to handle multi-resource DataFrames where multiple
    rows share the same timestamp (one per resource).
    """
    if len(df) < 2 or dt_col not in df.columns:
        return 1.0
    # Use unique timestamps to avoid 0-diffs from multi-resource rows
    ts = pd.to_datetime(df[dt_col]).drop_duplicates().sort_values()
    if len(ts) < 2:
        return 1.0
    diffs = ts.diff().dropna()
    if diffs.empty:
        return 1.0
    # Use median of positive diffs to handle gaps (e.g. missing intervals)
    pos_diffs = diffs[diffs > pd.Timedelta(0)]
    if pos_diffs.empty:
        return 1.0
    median_sec = pos_diffs.dt.total_seconds().median()
    if median_sec <= 0:
        return 1.0
    return median_sec / 3600.0


# ---------------------------------------------------------------------------
# Two-Settlement: unified vectorized formula
# ---------------------------------------------------------------------------

def calculate_energy_revenue(
    merged: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate DA + RT energy revenue using the Two-Settlement unified formula.

    Input DataFrame must contain columns:
        [datetime, da_mw, rt_mw, da_lmp, rt_lmp]
    Rows can be at ANY granularity (5-min, 15-min, hourly).

    Revenue is scaled by the interval length so that sub-hourly rows
    represent the correct fraction of an hour (e.g. 5-min row × 1/12).

    Adds columns: [da_energy_rev, rt_energy_rev, total_energy_rev, interval_hours]
    Returns the same DataFrame with revenue columns appended.
    """
    df = merged.copy()
    df["da_mw"] = pd.to_numeric(df["da_mw"], errors="coerce").fillna(0)
    df["rt_mw"] = pd.to_numeric(df["rt_mw"], errors="coerce").fillna(0)
    df["da_lmp"] = pd.to_numeric(df["da_lmp"], errors="coerce").fillna(0)
    df["rt_lmp"] = pd.to_numeric(df["rt_lmp"], errors="coerce").fillna(0)

    # Detect interval and scale: MW * LMP gives $/hr, multiply by interval_hours
    interval_h = _detect_interval_hours(df)
    df["interval_hours"] = interval_h

    # Two-Settlement: Total = DA_MW * DA_LMP + (RT_MW - DA_MW) * RT_LMP
    # Scaled by interval fraction so sub-hourly rows sum correctly to hourly
    df["da_energy_rev"] = df["da_mw"] * df["da_lmp"] * interval_h
    df["rt_energy_rev"] = (df["rt_mw"] - df["da_mw"]) * df["rt_lmp"] * interval_h
    df["total_energy_rev"] = df["da_energy_rev"] + df["rt_energy_rev"]

    return df


def calculate_as_revenue(
    merged: pd.DataFrame,
    product: str,
) -> pd.DataFrame:
    """
    Calculate AS revenue for a single product using the Two-Settlement formula.

    Input DataFrame must contain columns:
        [datetime, da_{product}_mw, rt_{product}_mw,
         da_{product}_mcpc, rt_{product}_mcpc]
    Rows can be at ANY granularity.

    Adds column: [{product}_rev]
    Returns the same DataFrame with the revenue column appended.
    """
    da_mw = f"da_{product}_mw"
    rt_mw = f"rt_{product}_mw"
    da_p = f"da_{product}_mcpc"
    rt_p = f"rt_{product}_mcpc"

    df = merged.copy()
    for c in [da_mw, rt_mw, da_p, rt_p]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # Scale by interval fraction (same logic as energy revenue)
    interval_h = _detect_interval_hours(df)

    # Two-Settlement: Rev = DA_MW * DA_MCPC + (RT_MW - DA_MW) * RT_MCPC
    df[f"{product}_rev"] = (df[da_mw] * df[da_p] + (df[rt_mw] - df[da_mw]) * df[rt_p]) * interval_h

    return df


# ---------------------------------------------------------------------------
# Deviation penalty (already vectorized, kept as-is)
# ---------------------------------------------------------------------------

def calculate_deviation_penalty(
    merged: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate deviation penalty when base point and telemetered net output
    differ significantly.

    Input DataFrame must contain columns:
        [datetime, base_point, telemetered_net_output, rt_lmp]
    Rows can be at ANY granularity.

    Adds columns: [deviation_mw, deviation_penalty]
    """
    df = merged.copy()
    df["base_point"] = pd.to_numeric(df["base_point"], errors="coerce").fillna(0)
    df["telemetered_net_output"] = pd.to_numeric(
        df["telemetered_net_output"], errors="coerce"
    ).fillna(0)
    df["rt_lmp"] = pd.to_numeric(df["rt_lmp"], errors="coerce").fillna(0)

    interval_h = _detect_interval_hours(df)

    df["deviation_mw"] = (df["telemetered_net_output"] - df["base_point"]).abs()
    df["deviation_penalty"] = np.where(
        df["deviation_mw"] > DEVIATION_THRESHOLD_MW,
        -df["deviation_mw"] * DEVIATION_PENALTY_RATE * interval_h,
        0.0,
    )
    return df


# ---------------------------------------------------------------------------
# Hourly aggregation (compute revenue at native granularity, then sum)
# ---------------------------------------------------------------------------

def aggregate_to_hourly(df: pd.DataFrame, dt_col: str = "datetime") -> pd.DataFrame:
    """
    Aggregate sub-hourly revenue rows to hourly sums.

    Only numeric columns are summed; non-numeric columns (except the groupby
    keys) are dropped. 'resource_name' is preserved if present.
    """
    df = df.copy()
    df[dt_col] = pd.to_datetime(df[dt_col])
    df["_hour"] = df[dt_col].dt.floor("h")

    group_keys = ["_hour"]
    if "resource_name" in df.columns:
        group_keys.append("resource_name")
    # Preserve _operating_date through aggregation
    if "_operating_date" in df.columns:
        group_keys.append("_operating_date")

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    # Drop helper columns from aggregation
    numeric_cols = [c for c in numeric_cols if c not in ("interval_hours",)]
    # Price columns should be averaged, not summed
    price_cols = [c for c in numeric_cols if c.endswith("_lmp") or c.endswith("_mcpc")]
    sum_cols = [c for c in numeric_cols if c not in price_cols]

    agg_dict = {c: "sum" for c in sum_cols}
    agg_dict.update({c: "mean" for c in price_cols})

    hourly = df.groupby(group_keys, as_index=False).agg(agg_dict)
    hourly.rename(columns={"_hour": dt_col}, inplace=True)
    return hourly


def aggregate_revenue(
    energy_rev: pd.DataFrame,
    as_revs: dict,
    deviation: pd.DataFrame = None,
) -> pd.DataFrame:
    """
    Combine all revenue streams into a single DataFrame.
    Works at whatever granularity the inputs are in.

    energy_rev: output of calculate_energy_revenue
    as_revs: dict {product: DataFrame with [{product}_rev, datetime, ...]}
    deviation: output of calculate_deviation_penalty (optional)

    Returns DataFrame with all revenue columns + total_rev.
    """
    keep_cols = ["datetime", "da_energy_rev", "rt_energy_rev", "da_lmp", "rt_lmp"]
    if "resource_name" in energy_rev.columns:
        keep_cols.insert(0, "resource_name")
    if "_operating_date" in energy_rev.columns:
        keep_cols.append("_operating_date")
    result = energy_rev[[c for c in keep_cols if c in energy_rev.columns]].copy()

    for product, as_df in as_revs.items():
        rev_col = f"{product}_rev"
        merge_cols = ["datetime", rev_col]
        if "resource_name" in as_df.columns and "resource_name" in result.columns:
            merge_cols.insert(0, "resource_name")
        on_cols = [c for c in ["datetime", "resource_name"] if c in merge_cols and c in result.columns]
        result = result.merge(
            as_df[[c for c in merge_cols if c in as_df.columns]],
            on=on_cols,
            how="left",
        )

    if deviation is not None and not deviation.empty:
        dev_cols = ["datetime", "deviation_penalty"]
        if "resource_name" in deviation.columns and "resource_name" in result.columns:
            dev_cols.insert(0, "resource_name")
        on_cols = [c for c in ["datetime", "resource_name"] if c in dev_cols and c in result.columns]
        result = result.merge(
            deviation[[c for c in dev_cols if c in deviation.columns]],
            on=on_cols,
            how="left",
        )
    else:
        result["deviation_penalty"] = 0.0

    result = result.fillna(0)

    # Total revenue
    rev_cols = ["da_energy_rev", "rt_energy_rev", "deviation_penalty"]
    for p in AS_PRODUCTS:
        col = f"{p}_rev"
        if col in result.columns:
            rev_cols.append(col)

    result["total_rev"] = result[[c for c in rev_cols if c in result.columns]].sum(axis=1)
    return result
