"""
Configuration for ERCOT BESS Revenue Analysis
- S3 data paths, column mappings, and constants
- Dual-era support: Pre-RTC+B (before 2025-12-05) and Post-RTC+B
"""
import os
from datetime import date
from dotenv import load_dotenv

load_dotenv()

# ── AWS / Yes Energy Datalake ──
S3_BUCKET = "yedatalake"
AWS_ACCESS_KEY = os.getenv("YES_ENERGY_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("YES_ENERGY_SECRET_KEY")

# ── RTC+B Cutover Date ──
# ESR resources disappeared from general 60d disclosure after this date.
# Post-RTC+B uses separate ESR-specific data sources.
RTCB_CUTOVER_DATE = date(2025, 12, 5)

# ── S3 Data Paths ──
S3_PATHS = {
    # === Pre-RTC+B: 60-day disclosure reports (ESR/PWRSTR data up to 2025-12-04) ===
    "dam_gen_res": "ercot/gen/ercot_60d_dam_gen_resource_data",
    "sced_gen_res": "ercot/gen/ercot_60d_sced_gen_resource_data",
    "sced_smne": "ercot/gen/ercot_60d_sced_smne_gen_res",
    "dam_as_off": "ercot/gen/ercot_60d_dam_gen_res_as_off",

    # === Post-RTC+B: ESR data from separate sources (2025-12-05 onward) ===
    "dam_en_off_awrd": "ercot/gen/ercot_60d_dam_en_only_off_awrd",  # DA energy awards (all resources incl ESR)
    "dam_energy_bids": "ercot/gen/ercot_60d_dam_energy_bids",       # DA energy bid curves
    "cop_all_updates": "ercot/gen/ercot_60d_cop_all_updates",       # COP: HSL/LSL/AS awards/SOC per resource

    # === Common: available across both eras ===
    # Price data
    "rt_lmp": "ercot/prices/bus_lmp",
    "spp_lmp": "ercot/prices/lmp/15min",  # Settlement Point Price (15-min, hourly files)
    # Ancillary services MCPC (real-time)
    "rtc_mcpc_regup": "ercot/ancillary/rtc_mcpc_regup",
    "rtc_mcpc_regdn": "ercot/ancillary/rtc_mcpc_regdn",
    "rtc_mcpc_rrs": "ercot/ancillary/rtc_mcpc_rrs",
    "rtc_mcpc_ecrs": "ercot/ancillary/rtc_mcpc_ecrs",
    "rtc_mcpc_nspin": "ercot/ancillary/rtc_mcpc_nspin",
    # DA AS volumes (system-level awarded MW)
    "da_asmvol_regup": "ercot/ancillary/da_asmvol_reg_u",
    "da_asmvol_regdn": "ercot/ancillary/da_asmvol_reg_d",
    "da_asmvol_rrs": "ercot/ancillary/da_asmvol_rrs",
    "da_asmvol_nspin": "ercot/ancillary/da_asmvol_nospn",
    "da_asmvol_ecrs": "ercot/ancillary/da_ecrs_vol",
    # DA AS prices (MCPC)
    "da_mcpc_ecrs": "ercot/ancillary/da_ecrs",
    # HSL data
    "hsl": "ercot/ancillary/hsl",
}

# ──────────────────────────────────────────────────────────────────────
# Column Mappings: Pre-RTC+B 60-day Disclosure Reports
# ──────────────────────────────────────────────────────────────────────

# DAM Gen Resource Data (53 columns, no header)
DAM_GEN_RES_COLS = {
    0: "datetime",
    1: "hour_ending",
    2: "resource_name",
    3: "resource_id",
    4: "resource_type",
    # cols 5-28: energy offer curve (12 price/MW pairs)
    29: "hsl",
    30: "lsl",
    31: "status",
    32: "scheduled_output",  # DA energy output
    33: "settlement_point",
    34: "da_lmp",
    35: "regup_award",
    36: "regup_mcpc",
    37: "regdn_award",
    38: "regdn_mcpc",
    39: "rrs_award",
    40: "rrs_mcpc",
    41: "nonspin_award",
    42: "nonspin_mcpc",
    # cols 43-45: additional fields
    46: "ecrs_award",
    47: "ecrs_mcpc",
    48: "col48",
    49: "col49",
    50: "col50",
    51: "qse",
    52: "company",
}

# SCED Gen Resource Data (207 columns, no header)
SCED_GEN_RES_COLS = {
    0: "objectid",
    1: "sced_timestamp",
    2: "interval_start",
    3: "interval_end",
    4: "num_segments",
    5: "flag",
    6: "resource_name",
    7: "resource_id",
    8: "resource_type",
    # cols 9-148: offer curves
    149: "lsl",
    150: "hsl",
    151: "base_point",
    152: "telemetered_net_output",
    153: "regup_award",
    154: "regdn_award",
    155: "rrs_award",
    156: "status",
    157: "actual_output",
    158: "output2",
}

# SCED SMNE (Telemetered Net Output, 9 columns)
SCED_SMNE_COLS = {
    0: "objectid",
    1: "datetime",
    2: "interval_time",
    3: "hour",
    4: "timezone",
    5: "resource_id",
    6: "resource_name",
    7: "telemetered_net_output",
    8: "loadid",
}

# DAM AS Offers (66 columns)
DAM_AS_OFF_COLS = {
    0: "objectid",
    1: "datetime",
    2: "timezone",
    3: "operating_date",
    4: "hour_ending",
    5: "qse",
    6: "company",
    7: "resource_id",
    8: "resource_name",
    9: "flag",
    10: "regup_valid",
    # cols 11-19: RegUp offer curve
    20: "regup_awarded",
    21: "regdn_valid",
    # cols 22-30: RegDn offer curve
    31: "regdn_awarded",
    32: "rrs_valid",
    # cols 33-41: RRS offer curve
    42: "rrs_awarded",
    43: "nonspin_valid",
    # cols 44-52: NonSpin offer curve
    53: "nonspin_awarded",
    54: "ecrs_valid",
    # cols 55-63: ECRS offer curve
    64: "ecrs_awarded",
    65: "loadid",
}

# ──────────────────────────────────────────────────────────────────────
# Column Mappings: Post-RTC+B Sources
# ──────────────────────────────────────────────────────────────────────

# DAM Energy-Only Offer Awards (12 columns, DDL verified)
DAM_EN_OFF_AWRD_COLS = {
    0: "recordid",
    1: "datetime",          # period ending
    2: "delivery_date",
    3: "hour_ending",
    4: "timezone",
    5: "objectid",          # settlement point objectid
    6: "settlement_point",  # e.g., GARC_BESS_RN, N_MRD_ESR_RN
    7: "qse",
    8: "awarded_mw",        # DA awarded MW (may be multi-segment per hour)
    9: "da_lmp",            # settlement point price
    10: "offer_id",
    11: "loadid",
}

# COP All Updates (27 columns, DDL verified)
COP_COLS = {
    0: "recordid",
    1: "datetime",          # period ending
    2: "delivery_date",
    3: "hour_ending",
    4: "timezone",
    5: "objectid",          # price_node objectid
    6: "qse",
    7: "resource_name",     # e.g., CR_ESR1, WAL_ESR1
    8: "status",            # ON/OFF
    9: "hsl",
    10: "lsl",
    11: "hel",              # high emergency limit
    12: "lel",              # low emergency limit
    13: "regup",
    14: "regdn",
    15: "rrspfr",
    16: "rrsffr",
    17: "rrsufr",
    18: "nspin",
    19: "ecrs",
    20: "min_soc",
    21: "max_soc",
    22: "hour_beg_plan_soc",
    23: "cancel_flag",
    24: "update_time",
    25: "submit_time",
    26: "loadid",
}

# Standard timeseries format (6 columns: MCPC, LMP, HSL, AS volumes)
TS_COLS = {
    0: "objectid",
    1: "datatypeid",
    2: "datetime",
    3: "timezone",
    4: "value",
    5: "loadid",
}

# Settlement Point Price LMP format (8 columns, 15-min intervals)
SPP_LMP_COLS = {
    0: "objectid",
    1: "datetime",
    2: "timezone",
    3: "rt_lmp",
    # cols 4-5: unused
    6: "loadid",
    7: "iso",
}

# Yes Energy metadata
METADATA_OBJECTS_KEY = "ercot/metadata/objects/all.csv.gz"

# ── ESR / BESS Identification ──
ESR_RESOURCE_TYPE = "PWRSTR"  # Pre-RTC+B resource type filter
# Post-RTC+B: ESR resources identified by name patterns
ESR_NAME_PATTERNS = ["_ESR", "_BESS"]

# ── Ancillary Service Products ──
AS_PRODUCTS = ["regup", "regdn", "rrs", "ecrs", "nonspin"]

# AS product name → S3 MCPC path key suffix mapping
# S3 uses "nspin" instead of "nonspin"
AS_MCPC_PATH_MAP = {
    "regup": "regup",
    "regdn": "regdn",
    "rrs": "rrs",
    "ecrs": "ecrs",
    "nonspin": "nspin",
}

# COP column name → AS_PRODUCTS key mapping
# COP splits RRS into RRSPFR, RRSFFR, RRSUFR; we sum them as "rrs"
COP_AS_MAP = {
    "regup": ["regup"],
    "regdn": ["regdn"],
    "rrs": ["rrspfr", "rrsffr", "rrsufr"],
    "ecrs": ["ecrs"],
    "nonspin": ["nspin"],
}

# ── ERCOT Public API (Post-RTC+B ESR data) ──
ERCOT_API_USERNAME = os.getenv("ERCOT_USERNAME")
ERCOT_API_PASSWORD = os.getenv("ERCOT_PASSWORD")
ERCOT_API_SUBSCRIPTION_KEY = os.getenv("ERCOT_SUBSCRIPTION_KEY")

# ── Local Data Cache ──
DATA_CACHE_DIR = os.path.join(os.path.dirname(__file__), "data", "cache")
BESS_CAPACITY_FILE = os.path.join(os.path.dirname(__file__), "ESS capacity.csv")

# ── Deviation Penalty Threshold ──
DEVIATION_THRESHOLD_MW = 5  # MW difference threshold for penalty calculation
DEVIATION_PENALTY_RATE = 50  # $/MWh penalty rate (placeholder, per ERCOT protocols)
