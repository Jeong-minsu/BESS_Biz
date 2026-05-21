"""
Data Fetcher – download & cache ERCOT data from Yes Energy S3 Datalake
Supports dual-era: Pre-RTC+B (before 2025-12-05) and Post-RTC+B.
"""
import os, gzip, io, hashlib
from datetime import date, timedelta
import boto3
import pandas as pd
from config import (
    S3_BUCKET, AWS_ACCESS_KEY, AWS_SECRET_KEY, S3_PATHS,
    DAM_GEN_RES_COLS, SCED_GEN_RES_COLS, SCED_SMNE_COLS,
    DAM_AS_OFF_COLS, DAM_EN_OFF_AWRD_COLS, COP_COLS,
    TS_COLS, SPP_LMP_COLS, ESR_RESOURCE_TYPE, ESR_NAME_PATTERNS,
    DATA_CACHE_DIR, RTCB_CUTOVER_DATE, COP_AS_MAP,
    AS_MCPC_PATH_MAP, METADATA_OBJECTS_KEY,
)

_s3 = None


def _get_s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
        )
    return _s3


def _cache_path(key: str) -> str:
    os.makedirs(DATA_CACHE_DIR, exist_ok=True)
    h = hashlib.md5(key.encode()).hexdigest()
    return os.path.join(DATA_CACHE_DIR, f"{h}.parquet")


def _download_csv_gz(s3_key: str) -> pd.DataFrame:
    """Download a csv.gz from S3 and return as DataFrame (no header)."""
    cache = _cache_path(s3_key)
    if os.path.exists(cache):
        return pd.read_parquet(cache)

    s3 = _get_s3()
    obj = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
    body = obj["Body"].read()
    with gzip.open(io.BytesIO(body)) as f:
        df = pd.read_csv(f, header=None, low_memory=False)
    df.to_parquet(cache, index=False)
    return df


def _date_range(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def _fetch_multi_day(path_key: str, start: date, end: date) -> pd.DataFrame:
    """Fetch data for a date range, concatenate."""
    prefix = S3_PATHS[path_key]
    frames = []
    for d in _date_range(start, end):
        s3_key = f"{prefix}/{d.strftime('%Y%m%d')}.csv.gz"
        try:
            df = _download_csv_gz(s3_key)
            frames.append(df)
        except Exception:
            continue
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _rename_cols(df: pd.DataFrame, col_map: dict) -> pd.DataFrame:
    """Rename columns using a mapping, only for existing columns.
    Handles both integer and string column names (parquet cache converts int->str).
    """
    rename = {}
    for k, v in col_map.items():
        if k in df.columns:
            rename[k] = v
        elif str(k) in df.columns:
            rename[str(k)] = v
        elif isinstance(k, int) and k < len(df.columns):
            rename[k] = v
    return df.rename(columns=rename)


def _is_esr_name(name: str) -> bool:
    """Check if a resource/settlement point name is ESR/BESS."""
    if pd.isna(name):
        return False
    name_upper = str(name).upper()
    return any(pat in name_upper for pat in ESR_NAME_PATTERNS)


# ══════════════════════════════════════════════════════════════════════
# Metadata & SPP LMP
# ══════════════════════════════════════════════════════════════════════

_price_node_cache = None


def fetch_price_node_metadata() -> pd.DataFrame:
    """
    Fetch objectid -> name mapping for all ERCOT price nodes.
    Uses ercot/metadata/objects/all.csv.gz (cached after first load).
    Returns DataFrame with [objectid, objectname] for OBJECTTYPE == 'price_node'.
    """
    global _price_node_cache
    if _price_node_cache is not None:
        return _price_node_cache

    cache = _cache_path("metadata_price_nodes")
    if os.path.exists(cache):
        _price_node_cache = pd.read_parquet(cache)
        return _price_node_cache

    s3 = _get_s3()
    obj = s3.get_object(Bucket=S3_BUCKET, Key=METADATA_OBJECTS_KEY)
    body = obj["Body"].read()
    with gzip.open(io.BytesIO(body)) as f:
        meta = pd.read_csv(f, low_memory=False)

    pn = meta[meta["OBJECTTYPE"] == "price_node"][["OBJECTID", "OBJECTNAME"]].copy()
    pn.columns = ["objectid", "objectname"]
    pn["objectid"] = pd.to_numeric(pn["objectid"], errors="coerce")
    pn = pn.dropna(subset=["objectid"])
    pn["objectid"] = pn["objectid"].astype(int)
    pn.to_parquet(cache, index=False)
    _price_node_cache = pn
    return pn


def fetch_objectid_to_name_map() -> dict:
    """Return {objectid: settlement_point_name} for all price nodes."""
    pn = fetch_price_node_metadata()
    return dict(zip(pn["objectid"], pn["objectname"]))


def fetch_name_to_objectid_map() -> dict:
    """Return {settlement_point_name: objectid} for all price nodes."""
    pn = fetch_price_node_metadata()
    return dict(zip(pn["objectname"], pn["objectid"]))


def _fetch_spp_multi_hour(start: date, end: date) -> pd.DataFrame:
    """
    Fetch SPP LMP data for a date range.
    Files are hourly: {prefix}/{YYYYMMDDHH}.csv.gz (HH = 00-23).
    """
    prefix = S3_PATHS["spp_lmp"]
    frames = []
    for d in _date_range(start, end):
        date_str = d.strftime("%Y%m%d")
        for hour in range(24):
            s3_key = f"{prefix}/{date_str}{hour:02d}.csv.gz"
            try:
                df = _download_csv_gz(s3_key)
                frames.append(df)
            except Exception:
                continue
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def fetch_spp_lmp(
    start: date,
    end: date,
    objectids: set = None,
) -> pd.DataFrame:
    """
    Fetch Settlement Point Price LMP (15-min intervals).
    Optionally filter to a set of objectids for efficiency.

    Returns DataFrame with [objectid, datetime, rt_lmp].
    """
    cache_key = f"spp_lmp_{start}_{end}"
    if objectids:
        oid_hash = hashlib.md5(str(sorted(objectids)).encode()).hexdigest()[:8]
        cache_key += f"_{oid_hash}"
    cache = _cache_path(cache_key)

    if os.path.exists(cache):
        return pd.read_parquet(cache)

    df = _fetch_spp_multi_hour(start, end)
    if df.empty:
        return df
    df = _rename_cols(df, SPP_LMP_COLS)

    if "objectid" in df.columns:
        df["objectid"] = pd.to_numeric(df["objectid"], errors="coerce")
    if "rt_lmp" in df.columns:
        df["rt_lmp"] = pd.to_numeric(df["rt_lmp"], errors="coerce").fillna(0)
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])

    # Filter to requested objectids
    if objectids and "objectid" in df.columns:
        df = df[df["objectid"].isin(objectids)].copy()

    # Keep only needed columns
    keep = ["objectid", "datetime", "rt_lmp"]
    df = df[[c for c in keep if c in df.columns]]

    if not df.empty:
        df.to_parquet(cache, index=False)

    return df


def get_era(target_date: date) -> str:
    """Determine which data era a date falls in."""
    if target_date < RTCB_CUTOVER_DATE:
        return "pre_rtcb"
    return "post_rtcb"


# ══════════════════════════════════════════════════════════════════════
# Pre-RTC+B Fetchers (before 2025-12-05)
# ══════════════════════════════════════════════════════════════════════

def fetch_dam_gen_resource(start: date, end: date, esr_only: bool = True) -> pd.DataFrame:
    """Fetch DAM Gen Resource Data (pre-RTC+B), filter to PWRSTR."""
    df = _fetch_multi_day("dam_gen_res", start, end)
    if df.empty:
        return df
    df = _rename_cols(df, DAM_GEN_RES_COLS)
    if esr_only and "resource_type" in df.columns:
        df = df[df["resource_type"] == ESR_RESOURCE_TYPE].copy()
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def fetch_sced_gen_resource(start: date, end: date, esr_only: bool = True) -> pd.DataFrame:
    """Fetch SCED Gen Resource Data (pre-RTC+B)."""
    df = _fetch_multi_day("sced_gen_res", start, end)
    if df.empty:
        return df
    df = _rename_cols(df, SCED_GEN_RES_COLS)
    if esr_only and "resource_type" in df.columns:
        df = df[df["resource_type"] == ESR_RESOURCE_TYPE].copy()
    if "sced_timestamp" in df.columns:
        df["sced_timestamp"] = pd.to_datetime(df["sced_timestamp"])
    if "interval_start" in df.columns:
        df["interval_start"] = pd.to_datetime(df["interval_start"])
    return df


def fetch_dam_as_offers(start: date, end: date, esr_names: list = None) -> pd.DataFrame:
    """Fetch DAM AS Offers (pre-RTC+B only, no ESR data post-RTC+B)."""
    df = _fetch_multi_day("dam_as_off", start, end)
    if df.empty:
        return df
    df = _rename_cols(df, DAM_AS_OFF_COLS)
    if esr_names and "resource_name" in df.columns:
        df = df[df["resource_name"].isin(esr_names)].copy()
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])
    return df


# ══════════════════════════════════════════════════════════════════════
# Post-RTC+B Fetchers (2025-12-05 onward)
# ══════════════════════════════════════════════════════════════════════

def fetch_dam_energy_awards(start: date, end: date, esr_only: bool = True) -> pd.DataFrame:
    """
    Fetch DAM Energy-Only Offer Awards (post-RTC+B).
    Awards may have multiple segments per hour per resource — sum them.

    Returns DataFrame with columns:
        [datetime, settlement_point, qse, awarded_mw, da_lmp]
    """
    df = _fetch_multi_day("dam_en_off_awrd", start, end)
    if df.empty:
        return df
    df = _rename_cols(df, DAM_EN_OFF_AWRD_COLS)

    if esr_only and "settlement_point" in df.columns:
        df = df[df["settlement_point"].apply(_is_esr_name)].copy()

    if df.empty:
        return df

    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])

    # Numeric conversion
    for col in ["awarded_mw", "da_lmp", "hour_ending"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Sum multi-segment awards per (hour, settlement_point)
    # Use weighted average for price: sum(mw*price) / sum(mw)
    grouped = df.groupby(["datetime", "settlement_point", "qse"]).agg(
        awarded_mw=("awarded_mw", "sum"),
        _mw_price=pd.NamedAgg(
            column="awarded_mw",
            aggfunc=lambda x: (x * df.loc[x.index, "da_lmp"]).sum(),
        ),
    ).reset_index()
    grouped["da_lmp"] = (grouped["_mw_price"] / grouped["awarded_mw"].replace(0, float("nan"))).fillna(0)
    grouped.drop(columns=["_mw_price"], inplace=True)

    # Use settlement_point as resource_name for consistency
    grouped["resource_name"] = grouped["settlement_point"]

    return grouped


def fetch_cop_data(start: date, end: date, esr_only: bool = True) -> pd.DataFrame:
    """
    Fetch COP All Updates (post-RTC+B).
    Contains per-resource HSL, LSL, AS awards (RegUp/Dn, RRS*, ECRS, NSpin), SOC.

    Returns latest COP update per (hour, resource_name).
    """
    df = _fetch_multi_day("cop_all_updates", start, end)
    if df.empty:
        return df
    df = _rename_cols(df, COP_COLS)

    if esr_only and "resource_name" in df.columns:
        df = df[df["resource_name"].apply(_is_esr_name)].copy()

    if df.empty:
        return df

    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])

    # Numeric conversion for key columns
    numeric_cols = ["hsl", "lsl", "regup", "regdn", "rrspfr", "rrsffr",
                    "rrsufr", "nspin", "ecrs", "min_soc", "max_soc",
                    "hour_beg_plan_soc"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Keep only latest COP update per (hour, resource)
    # COP has cancel_flag and update_time; exclude cancelled, take latest update
    if "cancel_flag" in df.columns:
        df = df[df["cancel_flag"] != "Y"].copy()
    if "update_time" in df.columns:
        df["update_time"] = pd.to_datetime(df["update_time"], errors="coerce")
        df = df.sort_values("update_time").groupby(
            ["datetime", "resource_name"], as_index=False
        ).last()

    # Compute combined RRS = RRSPFR + RRSFFR + RRSUFR
    df["rrs"] = df[["rrspfr", "rrsffr", "rrsufr"]].sum(axis=1)

    return df


# ══════════════════════════════════════════════════════════════════════
# Common Fetchers (available for both eras)
# ══════════════════════════════════════════════════════════════════════

def fetch_rt_lmp(start: date, end: date) -> pd.DataFrame:
    """Fetch RT bus LMP data."""
    df = _fetch_multi_day("rt_lmp", start, end)
    if df.empty:
        return df
    df = _rename_cols(df, TS_COLS)
    df.rename(columns={"value": "rt_lmp"}, inplace=True)
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def fetch_as_mcpc(product: str, market: str, start: date, end: date) -> pd.DataFrame:
    """
    Fetch AS MCPC prices (system-level).
    product: regup, regdn, rrs, ecrs, nonspin
    market: 'rt' for real-time, 'da' for day-ahead
    """
    # Map product name to S3 path key suffix (e.g., nonspin → nspin)
    s3_suffix = AS_MCPC_PATH_MAP.get(product, product)

    if market == "rt":
        path_key = f"rtc_mcpc_{s3_suffix}"
    else:
        path_key = f"da_mcpc_{s3_suffix}" if f"da_mcpc_{s3_suffix}" in S3_PATHS else None
        if path_key is None:
            return pd.DataFrame()

    if path_key not in S3_PATHS:
        return pd.DataFrame()

    df = _fetch_multi_day(path_key, start, end)
    if df.empty:
        return df
    df = _rename_cols(df, TS_COLS)
    df.rename(columns={"value": f"{market}_{product}_mcpc"}, inplace=True)
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def fetch_settlement_point_map(start: date, end: date) -> dict:
    """
    Build settlement_point_name → objectid mapping from DAM Energy Awards data.
    This data has both objectid (numeric) and settlement_point (name) columns.
    Returns dict: {settlement_point_name: objectid}
    """
    df = _fetch_multi_day("dam_en_off_awrd", start, end)
    if df.empty:
        return {}
    df = _rename_cols(df, DAM_EN_OFF_AWRD_COLS)
    if "settlement_point" not in df.columns or "objectid" not in df.columns:
        return {}
    # Take the most common objectid per settlement_point name
    mapping = (
        df.groupby("settlement_point")["objectid"]
        .agg(lambda x: x.mode().iloc[0] if len(x) > 0 else None)
        .dropna()
        .to_dict()
    )
    return mapping


def fetch_hsl(start: date, end: date) -> pd.DataFrame:
    """Fetch HSL (High Sustained Limit) data."""
    df = _fetch_multi_day("hsl", start, end)
    if df.empty:
        return df
    df = _rename_cols(df, TS_COLS)
    df.rename(columns={"value": "hsl"}, inplace=True)
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])
    return df


# ══════════════════════════════════════════════════════════════════════
# Unified Fetcher: auto-selects era-appropriate sources
# ══════════════════════════════════════════════════════════════════════

def fetch_esr_data(start: date, end: date) -> dict:
    """
    Unified entry point: fetch all ESR data for a date range.
    Automatically handles dual-era data sources.

    If date range spans the RTC+B cutover, splits into two sub-ranges
    and merges the results.

    Returns dict with keys:
        'da_energy':  DA energy awards + LMP per resource per hour
        'rt_output':  RT output per resource (sub-hourly if available)
        'as_awards':  AS awards per resource per hour per product
        'cop':        COP data (HSL, LSL, SOC) per resource per hour
        'rt_lmp':     RT LMP per settlement point (sub-hourly)
        'resource_info': resource metadata (name, settlement_point, qse, company, hsl)
        'era':        'pre_rtcb', 'post_rtcb', or 'mixed'
    """
    era_start = get_era(start)
    era_end = get_era(end)

    if era_start == era_end:
        if era_start == "pre_rtcb":
            return _fetch_pre_rtcb(start, end)
        else:
            return _fetch_post_rtcb(start, end)
    else:
        # Mixed range: split at cutover
        pre = _fetch_pre_rtcb(start, RTCB_CUTOVER_DATE - timedelta(days=1))
        post = _fetch_post_rtcb(RTCB_CUTOVER_DATE, end)
        return _merge_era_results(pre, post)


def _fetch_rt_spp_for_esr(start: date, end: date, settlement_points: list = None) -> pd.DataFrame:
    """
    Fetch RT SPP LMP, filtered to ESR settlement points.
    Uses metadata-based name->objectid mapping.
    """
    name_to_oid = fetch_name_to_objectid_map()

    if settlement_points:
        esr_oids = {name_to_oid[sp] for sp in settlement_points if sp in name_to_oid}
    else:
        # Get all ESR-like settlement points from metadata
        esr_oids = {oid for name, oid in name_to_oid.items() if _is_esr_name(name)}

    if not esr_oids:
        return pd.DataFrame()

    return fetch_spp_lmp(start, end, objectids=esr_oids)


def _fetch_pre_rtcb(start: date, end: date) -> dict:
    """Fetch ESR data for pre-RTC+B era using 60d disclosure reports."""
    dam_df = fetch_dam_gen_resource(start, end, esr_only=True)
    sced_df = fetch_sced_gen_resource(start, end, esr_only=True)
    esr_names = dam_df["resource_name"].unique().tolist() if not dam_df.empty else []
    dam_as_df = fetch_dam_as_offers(start, end, esr_names=esr_names)

    # Get ESR settlement points for filtering RT LMP
    sp_list = dam_df["settlement_point"].unique().tolist() if not dam_df.empty and "settlement_point" in dam_df.columns else None
    # Pre-RTC+B also uses hour-ending timestamps; fetch +1 day for alignment
    rt_lmp_df = _fetch_rt_spp_for_esr(start, end + timedelta(days=1), sp_list)

    # Build da_energy (consistent columns)
    # DAM datetime is operating date only; combine with hour_ending for actual timestamp
    da_energy = pd.DataFrame()
    if not dam_df.empty:
        da_energy = dam_df[["datetime", "resource_name", "settlement_point"]].copy()
        da_energy["datetime"] = pd.to_datetime(da_energy["datetime"])
        if "hour_ending" in dam_df.columns:
            he = pd.to_numeric(dam_df["hour_ending"], errors="coerce").fillna(1).astype(int)
            da_energy["datetime"] = da_energy["datetime"] + pd.to_timedelta(he, unit="h")
        da_energy["da_mw"] = pd.to_numeric(dam_df["scheduled_output"], errors="coerce").fillna(0)
        da_energy["da_lmp"] = pd.to_numeric(dam_df["da_lmp"], errors="coerce").fillna(0)
        da_energy["qse"] = dam_df.get("qse", "")

    # Build rt_output from SCED
    rt_output = pd.DataFrame()
    if not sced_df.empty:
        rt_output = sced_df[["sced_timestamp", "resource_name"]].copy()
        rt_output.rename(columns={"sced_timestamp": "datetime"}, inplace=True)
        rt_output["rt_mw"] = pd.to_numeric(sced_df["telemetered_net_output"], errors="coerce").fillna(0)
        rt_output["base_point"] = pd.to_numeric(sced_df["base_point"], errors="coerce").fillna(0)

    # Build as_awards from dam_as_off
    as_awards = pd.DataFrame()
    if not dam_as_df.empty:
        as_rows = dam_as_df[["datetime", "resource_name"]].copy()
        for product in ["regup", "regdn", "rrs", "nonspin", "ecrs"]:
            col = f"{product}_awarded"
            if col in dam_as_df.columns:
                as_rows[f"da_{product}_mw"] = pd.to_numeric(dam_as_df[col], errors="coerce").fillna(0)
            else:
                as_rows[f"da_{product}_mw"] = 0.0
        as_awards = as_rows

    # Resource info
    resource_info = pd.DataFrame()
    if not dam_df.empty:
        resource_info = dam_df.groupby("resource_name").agg({
            "settlement_point": "first",
            "hsl": "max",
            "qse": "first",
            "company": "first",
        }).reset_index()
        resource_info["hsl"] = pd.to_numeric(resource_info["hsl"], errors="coerce").fillna(0)

    return {
        "da_energy": da_energy,
        "rt_output": rt_output,
        "as_awards": as_awards,
        "cop": pd.DataFrame(),
        "rt_lmp": rt_lmp_df,
        "resource_info": resource_info,
        "era": "pre_rtcb",
    }


def _fetch_post_rtcb(start: date, end: date) -> dict:
    """
    Fetch ESR data for post-RTC+B era using ERCOT Public API.

    Data sources:
        - ERCOT API: 60d DAM ESR Data, 60d ESR Data in SCED, 60d DAM ESR AS Offers
        - Yes Energy S3: RT LMP (bus_lmp), AS MCPC (system-level)
        - Yes Energy S3: COP All Updates (fallback for AS/HSL if ERCOT API unavailable)

    Falls back to Yes Energy S3 (dam_en_only_off_awrd + cop_all_updates)
    if ERCOT API credentials are not configured.
    """
    from config import ERCOT_API_USERNAME

    # ── Try ERCOT API first ──
    # RT LMP is fetched AFTER loading DAM data so we know the actual
    # settlement points (many ESR SPs don't contain "ESR"/"BESS" in their name).
    if ERCOT_API_USERNAME:
        # RT LMP is fetched inside _fetch_post_rtcb_via_ercot_api
        # after DAM data reveals settlement points
        return _fetch_post_rtcb_via_ercot_api(start, end)

    # ── Fallback: Yes Energy S3 (limited ESR data) ──
    rt_lmp_df = _fetch_rt_spp_for_esr(start, end + timedelta(days=1))
    return _fetch_post_rtcb_via_s3_fallback(start, end, rt_lmp_df)


def _fetch_post_rtcb_via_ercot_api(start: date, end: date) -> dict:
    """Post-RTC+B fetch using ERCOT Public API for full ESR disclosure data."""
    try:
        from src.ercot_api_fetcher import ErcotApiFetcher
    except ImportError:
        from ercot_api_fetcher import ErcotApiFetcher

    fetcher = ErcotApiFetcher()
    disclosure = fetcher.fetch_esr_disclosure(start, end)

    dam_esr = disclosure.get("dam_esr", pd.DataFrame())
    sced_esr = disclosure.get("sced_esr", pd.DataFrame())

    # ── DA Energy from DAM ESR Data ──
    da_energy = pd.DataFrame()
    if not dam_esr.empty:
        da_energy = _parse_dam_esr(dam_esr)

    # ── RT Output from SCED ESR Data ──
    rt_output = pd.DataFrame()
    if not sced_esr.empty:
        rt_output = _parse_sced_esr(sced_esr)

    # ── AS Awards from DAM ESR Data (awards embedded in same file) ──
    as_awards = pd.DataFrame()
    if not dam_esr.empty:
        as_awards = _parse_dam_esr_as_awards(dam_esr)

    # ── Resource Info ──
    resource_info = _build_resource_info_from_ercot(dam_esr, sced_esr)

    # ── RT LMP: fetch after DAM so we know actual settlement points ──
    sp_list = da_energy["settlement_point"].unique().tolist() if (
        not da_energy.empty and "settlement_point" in da_energy.columns
    ) else None
    rt_lmp_df = _fetch_rt_spp_for_esr(start, end + timedelta(days=1), sp_list)

    return {
        "da_energy": da_energy,
        "rt_output": rt_output,
        "as_awards": as_awards,
        "cop": pd.DataFrame(),
        "rt_lmp": rt_lmp_df,
        "resource_info": resource_info,
        "era": "post_rtcb",
    }


def _fetch_post_rtcb_via_s3_fallback(start: date, end: date, rt_lmp_df: pd.DataFrame) -> dict:
    """Post-RTC+B fallback using Yes Energy S3 (limited: dam_en_only_off_awrd + COP)."""
    awards_df = fetch_dam_energy_awards(start, end, esr_only=True)
    cop_df = fetch_cop_data(start, end, esr_only=True)

    da_energy = pd.DataFrame()
    if not awards_df.empty:
        da_energy = awards_df[["datetime", "resource_name", "settlement_point",
                                "qse", "awarded_mw", "da_lmp"]].copy()
        da_energy.rename(columns={"awarded_mw": "da_mw"}, inplace=True)

    rt_output = pd.DataFrame()  # Not available via S3

    as_awards = pd.DataFrame()
    if not cop_df.empty:
        as_rows = cop_df[["datetime", "resource_name"]].copy()
        for product, cop_cols in COP_AS_MAP.items():
            existing = [c for c in cop_cols if c in cop_df.columns]
            if existing:
                as_rows[f"da_{product}_mw"] = cop_df[existing].sum(axis=1)
            else:
                as_rows[f"da_{product}_mw"] = 0.0
        as_awards = as_rows

    resource_info = pd.DataFrame()
    if not cop_df.empty:
        resource_info = cop_df.groupby("resource_name").agg({
            "qse": "first",
            "hsl": "max",
        }).reset_index()
        resource_info["company"] = resource_info["qse"]
        if not awards_df.empty:
            sp_map = awards_df.groupby("resource_name")["settlement_point"].first().to_dict()
            resource_info["settlement_point"] = resource_info["resource_name"].map(sp_map).fillna("")
        else:
            resource_info["settlement_point"] = ""

    return {
        "da_energy": da_energy,
        "rt_output": rt_output,
        "as_awards": as_awards,
        "cop": cop_df,
        "rt_lmp": rt_lmp_df,
        "resource_info": resource_info,
        "era": "post_rtcb",
    }


# ── ERCOT API data parsers ──

def _parse_dam_esr(dam_esr: pd.DataFrame) -> pd.DataFrame:
    """
    Parse ERCOT 60d_DAM_ESR_Data into standard da_energy format.

    Verified columns (48 total):
        Delivery Date, Hour Ending, QSE, DME, Resource Name, Resource Type,
        QSE submitted Curve-MW1..MW10, Price1..Price10,
        Start Up Hot/Inter/Cold, Min Gen Cost,
        HSL, LSL, Resource Status, Awarded Quantity,
        Settlement Point Name, Energy Settlement Point Price,
        RegUp Awarded, RegUp MCPC, RegDown Awarded, RegDown MCPC,
        RRSPFR Awarded, RRSFFR Awarded, RRSUFR Awarded, RRS MCPC,
        ECRSSD Awarded, ECRS MCPC, NonSpin Awarded, NonSpin MCPC
    """
    df = dam_esr.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    col_map = {
        "delivery_date": "date",
        "settlement_point_name": "settlement_point",
        "awarded_quantity": "da_mw",
        "energy_settlement_point_price": "da_lmp",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # Build datetime from date + hour_ending
    if "date" in df.columns and "hour_ending" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df["hour_ending"] = pd.to_numeric(df["hour_ending"], errors="coerce").fillna(1)
        df["datetime"] = df["date"] + pd.to_timedelta(df["hour_ending"], unit="h")

    for col in ["da_mw", "da_lmp"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    keep = ["datetime", "resource_name", "settlement_point", "qse", "da_mw", "da_lmp",
            "_operating_date"]
    return df[[c for c in keep if c in df.columns]]


def _parse_sced_esr(sced_esr: pd.DataFrame) -> pd.DataFrame:
    """
    Parse ERCOT 60d_ESR_Data_in_SCED into standard rt_output format.
    Returns sub-hourly (~5 min) data.

    Verified columns (198 total):
        SCED Time Stamp, Repeated Hour Flag, QSE, DME, Resource Name, Resource Type,
        SCED1/SCED2 Curve-MW1..MW35, Price1..Price35 (offer curves),
        Output Schedule, HSL, HDL, LSL, LDL,
        Telemetered Resource Status, Base Point, Telemetered Net Output,
        Ramp Rate Up/Down,
        AS Capability REGUP/REGDN/ECRS/NSPIN/RRSPF/RRSFF,
        State of Charge, Minimum SOC, Maximum SOC,
        AS Awards NSPIN/RRSFFR/RRSPFR/RRSUFR/ECRS/REGUP/REGDN,
        Bid_Type, startup costs, TPO curves, Proxy Extension
    """
    df = sced_esr.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    col_map = {
        "sced_time_stamp": "datetime",
        "telemetered_net_output": "rt_mw",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])
    for col in ["rt_mw", "base_point", "state_of_charge", "hsl", "lsl"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Parse RT AS Awards from SCED (5-min co-optimization results)
    as_award_map = {
        "as_awards_regup": "rt_regup_mw",
        "as_awards_regdn": "rt_regdn_mw",
        "as_awards_nspin": "rt_nonspin_mw",
        "as_awards_ecrs": "rt_ecrs_mw",
        "as_awards_rrspfr": "_rt_rrs_pfr",
        "as_awards_rrsffr": "_rt_rrs_ffr",
        "as_awards_rrsufr": "_rt_rrs_ufr",
    }
    for src_col, dst_col in as_award_map.items():
        if src_col in df.columns:
            df[dst_col] = pd.to_numeric(df[src_col], errors="coerce").fillna(0)
        else:
            df[dst_col] = 0.0
    # RRS = PFR + FFR + UFR (same as DA aggregation)
    df["rt_rrs_mw"] = df["_rt_rrs_pfr"] + df["_rt_rrs_ffr"] + df["_rt_rrs_ufr"]

    keep = ["datetime", "resource_name", "rt_mw", "base_point",
            "state_of_charge", "hsl", "lsl", "_operating_date",
            "rt_regup_mw", "rt_regdn_mw", "rt_rrs_mw", "rt_ecrs_mw", "rt_nonspin_mw"]
    return df[[c for c in keep if c in df.columns]]


def _parse_dam_esr_as_awards(dam_esr: pd.DataFrame) -> pd.DataFrame:
    """
    Extract AS awards AND DA MCPC from ERCOT 60d_DAM_ESR_Data.
    AS awards and MCPC are embedded in the same file as energy awards.

    Verified award columns:
        RegUp Awarded, RegDown Awarded,
        RRSPFR Awarded, RRSFFR Awarded, RRSUFR Awarded,
        ECRSSD Awarded, NonSpin Awarded
    Verified MCPC columns:
        RegUp MCPC, RegDown MCPC, RRS MCPC, ECRS MCPC, NonSpin MCPC
    """
    df = dam_esr.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Build datetime
    if "delivery_date" in df.columns and "hour_ending" in df.columns:
        df["date"] = pd.to_datetime(df["delivery_date"])
        df["hour_ending"] = pd.to_numeric(df["hour_ending"], errors="coerce").fillna(1)
        df["datetime"] = df["date"] + pd.to_timedelta(df["hour_ending"], unit="h")

    # Map AS award columns
    df["da_regup_mw"] = pd.to_numeric(df.get("regup_awarded", 0), errors="coerce").fillna(0)
    df["da_regdn_mw"] = pd.to_numeric(df.get("regdown_awarded", 0), errors="coerce").fillna(0)
    # RRS = RRSPFR + RRSFFR + RRSUFR
    rrspfr = pd.to_numeric(df.get("rrspfr_awarded", 0), errors="coerce").fillna(0)
    rrsffr = pd.to_numeric(df.get("rrsffr_awarded", 0), errors="coerce").fillna(0)
    rrsufr = pd.to_numeric(df.get("rrsufr_awarded", 0), errors="coerce").fillna(0)
    df["da_rrs_mw"] = rrspfr + rrsffr + rrsufr
    df["da_ecrs_mw"] = pd.to_numeric(df.get("ecrssd_awarded", 0), errors="coerce").fillna(0)
    df["da_nonspin_mw"] = pd.to_numeric(df.get("nonspin_awarded", 0), errors="coerce").fillna(0)

    # Map DA MCPC columns (system-level prices embedded per resource row)
    df["da_regup_mcpc"] = pd.to_numeric(df.get("regup_mcpc", 0), errors="coerce").fillna(0)
    df["da_regdn_mcpc"] = pd.to_numeric(df.get("regdown_mcpc", 0), errors="coerce").fillna(0)
    df["da_rrs_mcpc"] = pd.to_numeric(df.get("rrs_mcpc", 0), errors="coerce").fillna(0)
    df["da_ecrs_mcpc"] = pd.to_numeric(df.get("ecrs_mcpc", 0), errors="coerce").fillna(0)
    df["da_nonspin_mcpc"] = pd.to_numeric(df.get("nonspin_mcpc", 0), errors="coerce").fillna(0)

    keep = ["datetime", "resource_name",
            "da_regup_mw", "da_regdn_mw", "da_rrs_mw", "da_ecrs_mw", "da_nonspin_mw",
            "da_regup_mcpc", "da_regdn_mcpc", "da_rrs_mcpc", "da_ecrs_mcpc", "da_nonspin_mcpc"]
    return df[[c for c in keep if c in df.columns]]


def _build_resource_info_from_ercot(
    dam_esr: pd.DataFrame,
    sced_esr: pd.DataFrame,
) -> pd.DataFrame:
    """Build resource_info from ERCOT API data.

    DAM ESR Data has: Resource Name, Settlement Point Name, HSL, QSE, DME
    SCED ESR Data has: Resource Name, HSL
    """
    if dam_esr.empty and sced_esr.empty:
        return pd.DataFrame(columns=["resource_name", "settlement_point", "hsl", "qse", "company"])

    # Prefer DAM ESR Data which has settlement_point and QSE
    if not dam_esr.empty:
        df = dam_esr.copy()
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        df["hsl"] = pd.to_numeric(df.get("hsl", 0), errors="coerce").fillna(0)

        rename = {"settlement_point_name": "settlement_point", "dme": "company"}
        df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

        info = df.groupby("resource_name").agg({
            "settlement_point": "first",
            "hsl": "max",
            "qse": "first",
            "company": "first",
        }).reset_index()
        return info

    # Fallback: SCED only
    df = sced_esr.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df["hsl"] = pd.to_numeric(df.get("hsl", 0), errors="coerce").fillna(0)

    info = df.groupby("resource_name").agg({"hsl": "max"}).reset_index()
    for col in ["settlement_point", "qse", "company"]:
        info[col] = ""
    return info


def _merge_era_results(pre: dict, post: dict) -> dict:
    """Merge results from pre and post RTC+B eras."""
    merged = {}
    for key in ["da_energy", "rt_output", "as_awards", "cop", "rt_lmp", "resource_info"]:
        frames = []
        if not pre[key].empty if isinstance(pre[key], pd.DataFrame) else pre[key]:
            frames.append(pre[key])
        if not post[key].empty if isinstance(post[key], pd.DataFrame) else post[key]:
            frames.append(post[key])
        if frames:
            merged[key] = pd.concat(frames, ignore_index=True)
        else:
            merged[key] = pd.DataFrame()
    merged["era"] = "mixed"
    return merged


def load_bess_capacity(filepath: str = None) -> pd.DataFrame:
    """
    Load BESS capacity data from Excel file.
    Computes duration_hours and builds settlement_point-level aggregation
    for mapping to ERCOT resource data.

    Excel columns: Site, Pnode Name, Owner, Capacity (MW), Energy capacity (MWh)
    Pnode Name == ERCOT settlement_point (e.g., ANCHOR_ALL, ALVIN_RN)

    For duplicate Pnode Names (multiple units at same node),
    computes MW-weighted average duration.

    Returns DataFrame with columns:
        [settlement_point, site, owner, capacity_mw, energy_mwh, duration_hours]
    """
    from config import BESS_CAPACITY_FILE
    fp = filepath or BESS_CAPACITY_FILE
    if not os.path.exists(fp):
        return pd.DataFrame()

    if fp.endswith(".csv"):
        raw = pd.read_csv(fp)
    else:
        raw = pd.read_excel(fp)

    # Standardize column names
    raw = raw.rename(columns={
        "Pnode Name": "settlement_point",
        "Site": "site",
        "Owner": "owner",
        "Capacity (MW)": "capacity_mw",
        "Energy capacity (MWh)": "energy_mwh",
    })

    raw["capacity_mw"] = pd.to_numeric(raw["capacity_mw"], errors="coerce").fillna(0)
    raw["energy_mwh"] = pd.to_numeric(raw["energy_mwh"], errors="coerce").fillna(0)

    # Per-unit duration
    raw["duration_hours"] = (
        raw["energy_mwh"] / raw["capacity_mw"].replace(0, float("nan"))
    ).fillna(0)

    # Aggregate by settlement_point (weighted average duration for multi-unit sites)
    def _agg_sp(g):
        total_mw = g["capacity_mw"].sum()
        total_mwh = g["energy_mwh"].sum()
        duration = total_mwh / total_mw if total_mw > 0 else 0
        return pd.Series({
            "site": g["site"].iloc[0],
            "owner": g["owner"].iloc[0],
            "capacity_mw": total_mw,
            "energy_mwh": total_mwh,
            "duration_hours": duration,
        })

    result = raw.groupby("settlement_point", as_index=False).apply(
        _agg_sp, include_groups=False
    )
    return result
