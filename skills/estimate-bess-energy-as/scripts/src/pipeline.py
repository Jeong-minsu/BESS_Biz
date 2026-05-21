"""
Pipeline – Orchestrate data fetching, revenue calculation, and TB index
for all BESS nodes across a date range.

Supports dual-era:
  - Pre-RTC+B (before 2025-12-05): full per-resource SCED + DAM data
  - Post-RTC+B (2025-12-05+): DA awards + COP-based AS, no per-resource RT
"""
import pandas as pd
import numpy as np
from datetime import date
from config import AS_PRODUCTS, COP_AS_MAP

from src.data_fetcher import (
    fetch_esr_data, load_bess_capacity,
    fetch_as_mcpc, fetch_settlement_point_map,
    fetch_spp_lmp, fetch_name_to_objectid_map,
)
from src.revenue_calculator import (
    calculate_energy_revenue,
    calculate_as_revenue,
    calculate_deviation_penalty,
    aggregate_revenue,
    aggregate_to_hourly,
)
from src.tb_index import calculate_tb_index_single_day, calculate_tb_index_fractional


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_energy_table(data: dict, sp_map: dict = None) -> pd.DataFrame:
    """
    Build merged energy table with columns:
        [datetime, resource_name, da_mw, da_lmp, rt_mw, rt_lmp, base_point]

    Pre-RTC+B:  DA (hourly) merged with SCED RT output (sub-hourly)
    Post-RTC+B: DA awards + SCED ESR sub-hourly (if available)

    sp_map: settlement_point_name → objectid mapping for RT LMP join
    """
    da = data["da_energy"]
    if da.empty:
        return pd.DataFrame()

    da = da.copy()
    da["datetime"] = pd.to_datetime(da["datetime"])
    da["da_mw"] = pd.to_numeric(da["da_mw"], errors="coerce").fillna(0)
    da["da_lmp"] = pd.to_numeric(da["da_lmp"], errors="coerce").fillna(0)
    # DA timestamps are hour-ending (01:00 = midnight-1am), convert to hour-beginning
    # so they align with RT timestamps (00:00:17 floors to 00:00)
    da["_hour"] = da["datetime"].dt.floor("h") - pd.Timedelta(hours=1)

    rt = data["rt_output"]
    rt_lmp_df = data["rt_lmp"]

    if not rt.empty:
        # Sub-hourly SCED data available (pre-RTC+B or post-RTC+B via ERCOT API)
        rt = rt.copy()
        rt["datetime"] = pd.to_datetime(rt["datetime"])
        rt["rt_mw"] = pd.to_numeric(rt["rt_mw"], errors="coerce").fillna(0)
        rt["base_point"] = pd.to_numeric(rt.get("base_point", 0), errors="coerce").fillna(0)
        rt["_hour"] = rt["datetime"].dt.floor("h")

        # Merge DA (hourly) → RT (sub-hourly)
        # Use _operating_date if available (ERCOT API data has inconsistent timestamps)
        # SCED timestamps may be on operating date or delivery date depending on the day
        has_opdate = "_operating_date" in rt.columns and "_operating_date" in da.columns
        if has_opdate:
            # Match by operating date + hour-of-day + resource (ignores calendar date mismatch)
            rt["_hod"] = rt["datetime"].dt.hour
            da["_hod"] = (da["datetime"].dt.hour - 1) % 24  # hour-ending to hour-beginning
            da_merge = da[["_operating_date", "_hod", "resource_name",
                           "da_mw", "da_lmp", "settlement_point"]].drop_duplicates()
            merged = rt.merge(
                da_merge,
                on=["_operating_date", "_hod", "resource_name"],
                how="left",
            )
            merged.drop(columns=["_hod"], inplace=True, errors="ignore")
        else:
            # Fallback: match by _hour (pre-RTC+B, timestamps are consistent)
            merged = rt.merge(
                da[["_hour", "resource_name", "da_mw", "da_lmp", "settlement_point"]].drop_duplicates(),
                on=["_hour", "resource_name"],
                how="left",
            )
        merged["da_mw"] = merged["da_mw"].fillna(0)
        merged["da_lmp"] = merged["da_lmp"].fillna(0)

        # Add DA-only rows for operating dates that have no RT data
        # (e.g., ERCOT published duplicate SCED ZIP, dedup removed one copy)
        if has_opdate:
            rt_op_dates = set(rt["_operating_date"].unique())
            da_op_dates = set(da["_operating_date"].unique())
            missing_op_dates = da_op_dates - rt_op_dates
            if missing_op_dates:
                da_only = da[da["_operating_date"].isin(missing_op_dates)].copy()
                # Convert hour-ending DA to hour-beginning datetime
                da_only["datetime"] = da_only["datetime"] - pd.Timedelta(hours=1)
                da_only["rt_mw"] = da_only["da_mw"]
                da_only["base_point"] = 0.0
                merged = pd.concat([merged, da_only], ignore_index=True)
    else:
        # No per-resource RT data → use DA as proxy
        merged = da.copy()
        merged["rt_mw"] = merged["da_mw"]
        merged["base_point"] = 0.0
        if "settlement_point" not in merged.columns:
            merged["settlement_point"] = ""

    # ── Match RT LMP via settlement point ──
    if not rt_lmp_df.empty and "settlement_point" in merged.columns:
        lmp = rt_lmp_df.copy()
        lmp["rt_lmp"] = pd.to_numeric(lmp["rt_lmp"], errors="coerce").fillna(0)
        lmp["datetime"] = pd.to_datetime(lmp["datetime"])

        # Use sp_map (name -> objectid) to join
        if sp_map:
            merged["_sp_objectid"] = merged["settlement_point"].map(sp_map)
            lmp_join_col = "objectid"
            merged_join_col = "_sp_objectid"
        else:
            lmp.rename(columns={"objectid": "settlement_point"}, inplace=True)
            lmp_join_col = "settlement_point"
            merged_join_col = "settlement_point"

        # Round to 15-min for SPP LMP matching.
        # RT LMP uses interval-ending convention (00:15 covers 00:00-00:15).
        # SCED timestamps are ~interval-beginning (00:00:17 = first 5-min of 00:00-00:15).
        # Use ceil on SCED side so 00:00:17 → 00:15 (correct interval-ending match).
        # Subtract 1s before ceil to avoid exact-boundary edge cases.
        lmp["_round"] = lmp["datetime"].dt.floor("15min")
        merged["_round"] = (merged["datetime"] - pd.Timedelta(seconds=1)).dt.ceil("15min")

        merged_with_lmp = merged.merge(
            lmp[["_round", lmp_join_col, "rt_lmp"]].drop_duplicates(),
            left_on=["_round", merged_join_col],
            right_on=["_round", lmp_join_col],
            how="left",
        )

        if merged_with_lmp["rt_lmp"].notna().sum() == 0:
            # Fallback: use DA LMP as RT LMP proxy
            merged["rt_lmp"] = merged["da_lmp"]
        else:
            merged = merged_with_lmp
            merged["rt_lmp"] = merged["rt_lmp"].fillna(merged["da_lmp"])

        merged.drop(
            columns=["_round", "_sp_objectid", lmp_join_col],
            inplace=True,
            errors="ignore",
        )
    else:
        merged["rt_lmp"] = merged["da_lmp"]

    merged.drop(columns=["_hour", "settlement_point"], inplace=True, errors="ignore")

    # If _operating_date is available, use it as the canonical date for revenue attribution.
    # ERCOT SCED timestamps are inconsistent (some days use operating date, others delivery date),
    # so the calendar date from RT timestamps can skip days (e.g., Jan 5 missing).
    if "_operating_date" in merged.columns:
        merged["_operating_date"] = pd.to_datetime(merged["_operating_date"])

    return merged


def _build_as_tables(data: dict) -> dict:
    """
    Build AS tables per product.

    Pre-RTC+B: DA AS awards from dam_gen_res_as_off
    Post-RTC+B: DA AS awards from DAM ESR Data (includes DA MCPC)
                RT AS awards from SCED ESR Data (5-min co-optimization)

    Returns dict {product: DataFrame with [datetime, resource_name,
                  da_{p}_mw, rt_{p}_mw, da_{p}_mcpc, rt_{p}_mcpc]}
    """
    as_df = data["as_awards"]
    if as_df.empty:
        return {}

    as_df = as_df.copy()
    as_df["datetime"] = pd.to_datetime(as_df["datetime"])

    # Build hourly RT AS awards from SCED (5-min → hourly time-weighted average)
    # per Protocol Section 6.7.2: RT award = TWAP of SCED awards over 15-min intervals
    rt_output = data.get("rt_output", pd.DataFrame())
    rt_as_hourly = {}  # {product: DataFrame[resource_name, _hour, rt_{p}_mw]}
    if not rt_output.empty:
        rt = rt_output.copy()
        rt["datetime"] = pd.to_datetime(rt["datetime"])
        # Use _operating_date for grouping if available
        if "_operating_date" in rt.columns:
            rt["_hod"] = rt["datetime"].dt.hour
        rt["_hour"] = rt["datetime"].dt.floor("h")
        for product in AS_PRODUCTS:
            rt_col = f"rt_{product}_mw"
            if rt_col in rt.columns:
                # Time-weighted average per hour per resource (mean of 5-min awards)
                hourly = rt.groupby(["resource_name", "_hour"])[rt_col].mean().reset_index()
                rt_as_hourly[product] = hourly

    # Build per-product tables
    tables = {}
    for product in AS_PRODUCTS:
        da_col = f"da_{product}_mw"
        if da_col not in as_df.columns:
            continue

        tbl = as_df[["datetime", "resource_name"]].copy()
        tbl[da_col] = pd.to_numeric(as_df[da_col], errors="coerce").fillna(0)

        # Attach RT AS awards from SCED if available
        rt_col = f"rt_{product}_mw"
        if product in rt_as_hourly:
            # AS datetime is hour-ending; convert to hour-beginning for matching
            tbl["_hour"] = pd.to_datetime(tbl["datetime"]) - pd.Timedelta(hours=1)
            tbl["_hour"] = tbl["_hour"].dt.floor("h")
            tbl = tbl.merge(
                rt_as_hourly[product],
                on=["resource_name", "_hour"],
                how="left",
            )
            # Fall back to DA award where RT is missing (e.g., resource not in SCED)
            tbl[rt_col] = tbl[rt_col].fillna(tbl[da_col])
            tbl.drop(columns=["_hour"], inplace=True, errors="ignore")
        else:
            # No SCED data → RT AS ≈ DA AS (fallback)
            tbl[rt_col] = tbl[da_col]

        # Use embedded DA MCPC if available (post-RTC+B DAM ESR Data has MCPC)
        da_mcpc_col = f"da_{product}_mcpc"
        if da_mcpc_col in as_df.columns:
            tbl[da_mcpc_col] = pd.to_numeric(as_df[da_mcpc_col], errors="coerce").fillna(0)
        else:
            tbl[da_mcpc_col] = 0.0
        # RT MCPC placeholder — will be filled by _attach_system_rt_mcpc
        tbl[f"rt_{product}_mcpc"] = 0.0

        tables[product] = tbl

    return tables


def _attach_system_rt_mcpc(
    as_tables: dict,
    start: date,
    end: date,
) -> dict:
    """
    Fetch system-level RT MCPC from S3 and attach to AS tables.
    RT MCPC is the same for all resources per interval.
    """
    for product in AS_PRODUCTS:
        if product not in as_tables:
            continue

        rt_mcpc_df = fetch_as_mcpc(product, "rt", start, end)
        if rt_mcpc_df.empty:
            continue

        rt_mcpc_col = f"rt_{product}_mcpc"
        rt_mcpc_df["datetime"] = pd.to_datetime(rt_mcpc_df["datetime"])
        rt_mcpc_df[rt_mcpc_col] = pd.to_numeric(
            rt_mcpc_df[rt_mcpc_col], errors="coerce"
        ).fillna(0)
        # MCPC is 5-min SCED-aligned (00:00:17, 00:05:17, ..., 01:00:20).
        # floor("h") correctly groups all HE1 intervals to 00:00, HE2 to 01:00.
        # (01:00:20 is the first SCED of HE2, not the last of HE1.)
        rt_mcpc_df["_hour"] = rt_mcpc_df["datetime"].dt.floor("h")
        hourly_mcpc = (
            rt_mcpc_df.groupby("_hour")[rt_mcpc_col]
            .mean()
            .reset_index()
        )

        tbl = as_tables[product]
        # AS datetime is hour-ending (01:00 = HE1); convert to hour-beginning
        # for correct alignment with MCPC hour groups.
        tbl["_hour"] = (pd.to_datetime(tbl["datetime"]) - pd.Timedelta(hours=1)).dt.floor("h")
        tbl = tbl.drop(columns=[rt_mcpc_col], errors="ignore")
        tbl = tbl.merge(hourly_mcpc, on="_hour", how="left")
        tbl[rt_mcpc_col] = tbl[rt_mcpc_col].fillna(0)
        tbl.drop(columns=["_hour"], inplace=True, errors="ignore")
        as_tables[product] = tbl

    return as_tables


def _attach_mcpc_from_dam(as_tables: dict, dam_df: pd.DataFrame) -> dict:
    """Attach DA MCPC from pre-RTC+B dam_gen_res data to AS tables."""
    if dam_df.empty:
        return as_tables

    # DAM datetime may be operating-date-only; combine with hour_ending
    dam = dam_df.copy()
    dam["datetime"] = pd.to_datetime(dam["datetime"])
    if "hour_ending" in dam.columns:
        he = pd.to_numeric(dam["hour_ending"], errors="coerce").fillna(1).astype(int)
        dam["datetime"] = dam["datetime"] + pd.to_timedelta(he, unit="h")

    for product in AS_PRODUCTS:
        if product not in as_tables:
            continue

        mcpc_col = f"{product}_mcpc"
        if mcpc_col not in dam.columns:
            continue

        # Get system-level MCPC per hour (constant across resources)
        # DAM datetime is now hour-ending; convert to hour-beginning for grouping
        mcpc = dam.copy()
        mcpc["_hour"] = (mcpc["datetime"] - pd.Timedelta(hours=1)).dt.floor("h")
        mcpc = mcpc.groupby("_hour")[mcpc_col].first().reset_index()
        mcpc.rename(columns={mcpc_col: f"da_{product}_mcpc"}, inplace=True)
        mcpc[f"da_{product}_mcpc"] = pd.to_numeric(mcpc[f"da_{product}_mcpc"], errors="coerce").fillna(0)

        tbl = as_tables[product]
        # AS datetime is hour-ending; convert to hour-beginning
        tbl["_hour"] = (pd.to_datetime(tbl["datetime"]) - pd.Timedelta(hours=1)).dt.floor("h")
        tbl = tbl.drop(columns=[f"da_{product}_mcpc"], errors="ignore")
        tbl = tbl.merge(mcpc, on="_hour", how="left")
        tbl[f"da_{product}_mcpc"] = tbl[f"da_{product}_mcpc"].fillna(0)
        tbl[f"rt_{product}_mcpc"] = tbl[f"da_{product}_mcpc"]  # same as DA for now
        tbl.drop(columns=["_hour"], inplace=True, errors="ignore")
        as_tables[product] = tbl

    return as_tables


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_pipeline(
    start: date,
    end: date,
    bess_capacity: pd.DataFrame = None,
) -> dict:
    """
    Full pipeline: fetch data → compute revenue → TB index → optimization rate.
    Automatically handles pre/post RTC+B data sources.

    Returns dict:
        'revenue':  hourly revenue DataFrame per node
        'summary':  aggregated summary per node
        'tb_index': TB index per node per day
    """
    empty = {"revenue": pd.DataFrame(), "summary": pd.DataFrame(), "tb_index": pd.DataFrame()}

    # ── 1. Fetch Data (dual-era aware) ──
    data = fetch_esr_data(start, end)

    if data["da_energy"].empty:
        return empty

    # ── 1b. Settlement point name → objectid mapping for RT LMP join ──
    sp_map = fetch_settlement_point_map(start, end)

    # ── 2. Energy Revenue ──
    energy_table = _build_energy_table(data, sp_map=sp_map)
    if energy_table.empty:
        return empty

    energy_table = calculate_energy_revenue(energy_table)

    # ── 3. AS Revenue ──
    as_tables = _build_as_tables(data)

    # Attach DA MCPC from pre-RTC+B DAM data if available
    if data["era"] in ("pre_rtcb", "mixed"):
        from src.data_fetcher import fetch_dam_gen_resource
        dam_df = fetch_dam_gen_resource(start, min(end, date(2025, 12, 4)), esr_only=True)
        as_tables = _attach_mcpc_from_dam(as_tables, dam_df)

    # Attach system-level RT MCPC from S3 (all eras)
    as_tables = _attach_system_rt_mcpc(as_tables, start, end)

    as_revs = {}
    for product, tbl in as_tables.items():
        tbl = calculate_as_revenue(tbl, product)
        as_revs[product] = tbl

    # ── 4. Deviation Penalty (pre-RTC+B only, requires sub-hourly data) ──
    deviation = pd.DataFrame()
    if (data["era"] in ("pre_rtcb", "mixed")
        and "base_point" in energy_table.columns
        and "rt_mw" in energy_table.columns):
        dev_input = energy_table[["datetime", "resource_name", "base_point", "rt_lmp"]].copy()
        dev_input["telemetered_net_output"] = energy_table["rt_mw"]
        deviation = calculate_deviation_penalty(dev_input)

    # ── 5. Aggregate revenue → hourly ──
    # Energy + deviation are sub-hourly (5-min SCED); AS is hourly (DAM).
    # Aggregate energy to hourly FIRST, then merge AS at hourly level to avoid
    # granularity mismatch (previously AS merge on exact datetime failed for
    # SCED rows, losing ~87% of AS revenue).
    energy_combined = aggregate_revenue(energy_table, {}, deviation)

    if "resource_name" not in energy_combined.columns and "resource_name" in energy_table.columns:
        energy_combined["resource_name"] = energy_table["resource_name"]

    revenue_df = aggregate_to_hourly(energy_combined)
    if revenue_df.empty:
        return empty

    # Merge hourly AS revenue onto hourly energy revenue.
    # AS datetime is hour-ending (01:00 = HE1); convert to hour-beginning (00:00)
    # to align with energy hourly timestamps (floored to hour-beginning).
    revenue_df["_hour"] = pd.to_datetime(revenue_df["datetime"]).dt.floor("h")
    for product, as_df in as_revs.items():
        rev_col = f"{product}_rev"
        as_hr = as_df[["datetime", "resource_name", rev_col]].copy()
        # Hour-ending → hour-beginning
        as_hr["_hour"] = pd.to_datetime(as_hr["datetime"]) - pd.Timedelta(hours=1)
        as_hr["_hour"] = as_hr["_hour"].dt.floor("h")
        # Sum per resource per hour (should already be 1 row, but be safe)
        as_hourly = as_hr.groupby(["resource_name", "_hour"])[rev_col].sum().reset_index()
        revenue_df = revenue_df.merge(as_hourly, on=["resource_name", "_hour"], how="left")
        revenue_df[rev_col] = revenue_df[rev_col].fillna(0)
    revenue_df.drop(columns=["_hour"], inplace=True, errors="ignore")

    # Recompute total_rev including AS
    rev_cols_for_total = ["da_energy_rev", "rt_energy_rev", "deviation_penalty"]
    for p in AS_PRODUCTS:
        col = f"{p}_rev"
        if col in revenue_df.columns:
            rev_cols_for_total.append(col)
    revenue_df["total_rev"] = revenue_df[
        [c for c in rev_cols_for_total if c in revenue_df.columns]
    ].sum(axis=1)

    # ── 6. Summary per Node ──
    # Exclude total_rev and total_energy_rev to avoid double-counting
    rev_cols = [
        c for c in revenue_df.columns
        if (c.endswith("_rev") or c == "deviation_penalty")
        and c not in ("total_rev", "total_energy_rev")
    ]
    summary = revenue_df.groupby("resource_name")[rev_cols].sum().reset_index()
    summary["total_rev"] = summary[[c for c in rev_cols if c in summary.columns]].sum(axis=1)

    resource_info = data["resource_info"]
    if not resource_info.empty:
        summary = summary.merge(resource_info, on="resource_name", how="left")

    # ── 6b. Map ESS capacity from CSV via settlement_point ──
    # ESS CSV has site-level capacity_mw / energy_mwh (aggregated by pnode)
    # ERCOT resource_info has per-unit HSL which may differ from total site capacity
    sp_capacity_map = {}  # settlement_point -> {capacity_mw, energy_mwh, duration_hours, owner, site}
    if bess_capacity is not None and not bess_capacity.empty:
        for _, row in bess_capacity.iterrows():
            sp = row.get("settlement_point", "")
            if sp:
                sp_capacity_map[sp] = {
                    "capacity_mw": row.get("capacity_mw", 0),
                    "energy_mwh": row.get("energy_mwh", 0),
                    "duration_hours": row.get("duration_hours", 0),
                    "owner": row.get("owner", ""),
                    "site": row.get("site", ""),
                }

    # Build resource_name -> capacity mapping via resource_info.settlement_point
    # When multiple ESR units share a settlement point, split capacity proportionally
    resource_capacity = {}  # resource_name -> {capacity_mw, energy_mwh, duration_hours, ...}
    if not resource_info.empty and "settlement_point" in resource_info.columns:
        # Count how many resources share each settlement point
        sp_resource_count = (
            resource_info.groupby("settlement_point")["resource_name"]
            .count()
            .to_dict()
        )
        for _, row in resource_info.iterrows():
            sp = row.get("settlement_point", "")
            rname = row.get("resource_name", "")
            if sp in sp_capacity_map:
                n_units = sp_resource_count.get(sp, 1)
                cap_info = sp_capacity_map[sp].copy()
                # Split total site capacity among units at same settlement point
                cap_info["capacity_mw"] = cap_info["capacity_mw"] / n_units
                cap_info["energy_mwh"] = cap_info["energy_mwh"] / n_units
                # Duration stays the same (it's a ratio, not split)
                resource_capacity[rname] = cap_info

    # Attach CSV capacity to summary
    if resource_capacity:
        summary["capacity_mw"] = summary["resource_name"].map(
            lambda r: resource_capacity.get(r, {}).get("capacity_mw", np.nan)
        )
        summary["energy_mwh"] = summary["resource_name"].map(
            lambda r: resource_capacity.get(r, {}).get("energy_mwh", np.nan)
        )
        summary["csv_owner"] = summary["resource_name"].map(
            lambda r: resource_capacity.get(r, {}).get("owner", "")
        )
        summary["site"] = summary["resource_name"].map(
            lambda r: resource_capacity.get(r, {}).get("site", "")
        )
        # Use CSV owner if ERCOT company is just a QSE code
        if "company" in summary.columns:
            summary["company"] = summary.apply(
                lambda r: r["csv_owner"] if r.get("csv_owner") else r.get("company", ""),
                axis=1,
            )
        else:
            summary["company"] = summary["csv_owner"]
        summary.drop(columns=["csv_owner"], inplace=True, errors="ignore")

    # ── 6c. Estimate duration from SCED SOC data for unmapped resources ──
    # duration_hours = (MaxSOC - MinSOC) / HSL  (SOC in MWh)
    sced_duration_map = {}  # resource_name -> estimated duration_hours
    rt_output = data.get("rt_output", pd.DataFrame())
    if not rt_output.empty and "state_of_charge" in rt_output.columns:
        rt_soc = rt_output.copy()
        for col in ["state_of_charge", "hsl"]:
            if col in rt_soc.columns:
                rt_soc[col] = pd.to_numeric(rt_soc[col], errors="coerce")
        # Use per-resource max of MaxSOC proxy (max observed SOC) and max HSL
        soc_stats = rt_soc.groupby("resource_name").agg(
            max_soc=("state_of_charge", "max"),
            min_soc=("state_of_charge", "min"),
            max_hsl=("hsl", "max"),
        ).reset_index()
        soc_stats["usable_mwh"] = soc_stats["max_soc"] - soc_stats["min_soc"]
        soc_stats["duration_est"] = np.where(
            soc_stats["max_hsl"] > 0,
            soc_stats["usable_mwh"] / soc_stats["max_hsl"],
            np.nan,
        )
        valid = soc_stats[soc_stats["duration_est"].between(0.1, 10.0)]
        sced_duration_map = dict(zip(valid["resource_name"], valid["duration_est"]))

    # Median duration from CSV-mapped nodes as final fallback
    csv_durations = [v.get("duration_hours", np.nan) for v in resource_capacity.values()]
    csv_durations = [d for d in csv_durations if d > 0 and not np.isnan(d)]
    fallback_duration = float(np.median(csv_durations)) if csv_durations else 1.5

    # ── 7. TB Index (RT LMP based) ──
    # TB Index per MW per day, using hourly RT LMP from revenue_df.
    # Also compute daily actual revenue per node for matched optimization rate.
    tb_results = []
    if not revenue_df.empty and "rt_lmp" in revenue_df.columns:
        rev_daily = revenue_df.copy()
        rev_daily["datetime"] = pd.to_datetime(rev_daily["datetime"])
        rev_daily["rt_lmp"] = pd.to_numeric(rev_daily["rt_lmp"], errors="coerce").fillna(0)
        # Use _operating_date for date grouping when available (ERCOT timestamps are inconsistent)
        if "_operating_date" in rev_daily.columns:
            rev_daily["_date"] = pd.to_datetime(rev_daily["_operating_date"]).dt.date
        else:
            rev_daily["_date"] = rev_daily["datetime"].dt.date

        # Use CSV capacity; fall back to ERCOT HSL
        if "capacity_mw" not in summary.columns:
            summary["capacity_mw"] = np.nan
        if "hsl" not in summary.columns:
            summary["hsl"] = np.nan
        summary["hsl"] = pd.to_numeric(summary.get("hsl"), errors="coerce")
        summary["capacity_mw"] = pd.to_numeric(summary["capacity_mw"], errors="coerce")
        summary["eff_capacity_mw"] = summary["capacity_mw"].fillna(summary["hsl"])
        eff_cap_map = dict(zip(summary["resource_name"], summary["eff_capacity_mw"]))

        # Compute daily actual revenue (exclude total_rev/total_energy_rev to avoid double-counting)
        daily_rev_cols = [
            c for c in rev_daily.columns
            if (c.endswith("_rev") or c == "deviation_penalty")
            and c not in ("total_rev", "total_energy_rev")
        ]
        daily_actual = rev_daily.groupby(["resource_name", "_date"])[daily_rev_cols].sum().reset_index()
        daily_actual["daily_actual_rev"] = daily_actual[daily_rev_cols].sum(axis=1)

        for (name, d), group in rev_daily.groupby(["resource_name", "_date"]):
            prices = group.sort_values("datetime")["rt_lmp"].values

            cap_info = resource_capacity.get(name, {})
            # Duration priority: CSV → SCED SOC estimate → median fallback
            duration = cap_info.get("duration_hours", 0)
            if not duration or duration <= 0:
                duration = sced_duration_map.get(name, fallback_duration)
            cap_mw = eff_cap_map.get(name, np.nan)

            tb_per_mw = calculate_tb_index_fractional(prices, duration)
            # Daily theoretical revenue = TB ($/MW) × capacity (MW)
            tb_rev = tb_per_mw * cap_mw if pd.notna(cap_mw) else 0.0
            # Daily actual revenue
            day_rev = daily_actual.loc[
                (daily_actual["resource_name"] == name) & (daily_actual["_date"] == d),
                "daily_actual_rev"
            ]
            day_rev_val = day_rev.iloc[0] if len(day_rev) > 0 else 0.0

            tb_results.append({
                "resource_name": name,
                "date": d,
                "tb_index": tb_per_mw,
                "tb_rev": tb_rev,
                "daily_actual_rev": day_rev_val,
                "duration_hours": round(duration, 2),
                "capacity_mw": cap_mw if pd.notna(cap_mw) else 0.0,
            })

    tb_df = pd.DataFrame(tb_results)

    # ── 8. Optimization Rate ──
    # opt_rate = sum(daily_actual_rev) / sum(daily_tb_rev) × 100
    # Both numerator and denominator cover the exact same days per node.
    if not tb_df.empty:
        tb_agg = tb_df.groupby("resource_name").agg({
            "tb_index": "sum",       # sum of daily $/MW
            "tb_rev": "sum",         # sum of daily theoretical $ revenue
            "daily_actual_rev": "sum",  # sum of daily actual $ revenue
            "duration_hours": "first",
            "capacity_mw": "first",
        }).reset_index()
        tb_agg.rename(columns={"tb_rev": "theoretical_rev"}, inplace=True)

        summary = summary.merge(
            tb_agg[["resource_name", "tb_index", "theoretical_rev", "duration_hours"]],
            on="resource_name", how="left",
        )
        summary["optimization_rate"] = np.where(
            summary["theoretical_rev"] > 0,
            (summary["total_rev"] / summary["theoretical_rev"]) * 100.0,
            0.0,
        )

    return {
        "revenue": revenue_df,
        "summary": summary,
        "tb_index": tb_df,
    }
