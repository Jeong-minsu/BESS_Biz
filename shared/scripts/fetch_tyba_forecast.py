"""
Tyba D+1 price forecast fetch (production) — replaces Smartbidder forecasts.

Run from BESS_Biz/ root:
    python shared/scripts/fetch_tyba_forecast.py               # D+1
    python shared/scripts/fetch_tyba_forecast.py 2026-10-15
Also called by fetch_market_data.py in the daily cycle.

Output: shared/data/raw/tyba/{date}_GKS_forecast.csv — one row per HE (CT):
    DA_LMP, RT_LMP                     GKS_BESS_RN energy, P50     ($/MWh)
    P_RT_gt_DA, P_DA_gt_RT             spread-direction probability (sum = 1)
    NSPIN, REGDN, REGUP, RRS, ECRS     ERCOT DA AS (system-wide), P50 ($/MW-h)

RT AS (rt_reserves etc.) is NOT pulled: Tyba serves it only as rolling-24hr 15-min,
and the morning run covers just D+1 HE01–HE10 (verified 2026-10-14).

Auth: .env section '# Tyba API' → TOKEN (raw token in Authorization header, no 'Bearer').
Tyba datetimes are hour-beginning (00:00 CT = HE01). Vintage is D-1 ~06:00 CT,
i.e. before the D-1 10:00 CT bid close (leakage-free).
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

try:  # corporate SSL interception — harmless where not needed (e.g. cloud)
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

from _env_loader import load_env_sections

PROJECT_ROOT = Path(__file__).resolve().parents[2]   # BESS_Biz/
OUT_DIR      = PROJECT_ROOT / "shared" / "data" / "raw" / "tyba"
TYBA_BASE    = "https://dev.tybaenergy.com/public/0.1/forecasts"
NODE         = "GKS_BESS_RN"
TZ           = "America/Chicago"

# rt_lmp must use the day-ahead model shape to cover all 24 HE
# (rolling-24hr from the morning run ends around HE10).
PROB = dict(quantiles="0.5", forecast_type="day-ahead", predictions_per_hour=1, horizon_mins=1440)

ENERGY = [("DA_LMP", "da"), ("RT_LMP", "rt_lmp")]
AS_DA  = [("NSPIN", "non_spin_reserves"), ("REGDN", "reg_down"), ("REGUP", "reg_up"),
          ("RRS", "reserves"), ("ECRS", "ecrs")]
PROBS  = [("P_RT_gt_DA", "rt_energy_gt_da_energy_probability"),
          ("P_DA_gt_RT", "da_energy_gt_rt_energy_probability")]


def _get(token: str, endpoint: str, params: dict) -> list[dict] | None:
    r = requests.get(f"{TYBA_BASE}/{endpoint}", headers={"Authorization": token},
                     params=params, timeout=60)
    if r.status_code != 200:
        print(f"   ⚠️ Tyba {endpoint} {params.get('product')} HTTP {r.status_code}: {r.text[:200]}",
              file=sys.stderr)
        return None
    js = r.json()
    if isinstance(js, dict):  # tolerate a wrapped list
        js = next((v for v in js.values() if isinstance(v, list)), None)
    return js


def _to_series(recs: list[dict] | None, name: str) -> pd.Series:
    if not recs:
        return pd.Series(name=name, dtype=float)
    rows = {}
    for rec in recs:
        v = rec.get("mean_value")
        if v is None:
            vals = rec.get("values")
            v = vals[0] if isinstance(vals, list) and vals else rec.get("value")
        rows[rec["datetime"]] = v
    s = pd.Series(rows, name=name, dtype=float)
    s.index = pd.to_datetime(s.index, utc=True).tz_convert(TZ)
    return s


def fetch_tyba_forecast(token: str, target: date) -> pd.DataFrame:
    """Return the HE-indexed D+1 forecast table for `target` (CT operating day)."""
    # CT local-day window in UTC — DST-aware (23/24/25 h)
    start = pd.Timestamp(target).tz_localize(TZ)
    end   = pd.Timestamp(target + timedelta(days=1)).tz_localize(TZ)
    window = dict(start_time=start.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
                  end_time=end.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"))

    cols = {}
    for col, prod in ENERGY:
        cols[col] = _to_series(_get(token, "most_recent_probabilistic_forecast",
                                    dict(object_name=NODE, product=prod, **PROB, **window)), col)
    for col, prod in PROBS:  # point forecast only — probabilistic endpoint returns 400
        cols[col] = _to_series(_get(token, "most_recent_forecast",
                                    dict(object_name=NODE, product=prod, **window)), col)
    for col, prod in AS_DA:
        cols[col] = _to_series(_get(token, "most_recent_probabilistic_forecast",
                                    dict(object_name="ERCOT", product=prod, **PROB, **window)), col)

    df = pd.concat(cols.values(), axis=1).sort_index()
    df = df[(df.index >= start) & (df.index < end)]
    if df.dropna(how="all").empty:
        raise RuntimeError(f"Tyba returned no data for {target}")
    df.insert(0, "HE", range(1, len(df) + 1))   # hour-beginning → HE01..HE24 (23/25 on DST days)
    return df.set_index("HE")[[c for c, _ in ENERGY + PROBS + AS_DA]].round(3)


def save(df: pd.DataFrame, target: date) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    p = OUT_DIR / f"{target.isoformat()}_GKS_forecast.csv"
    df.to_csv(p)
    return p


def load_token() -> str:
    token = load_env_sections().get("tyba", {}).get("TOKEN")
    if not token:
        sys.exit("❌ Tyba TOKEN missing in '# Tyba API' section of .env")
    return token


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    target = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today() + timedelta(days=1)
    df = fetch_tyba_forecast(load_token(), target)
    print(df.to_string())
    print(f"\nrows: {len(df)}  →  {save(df, target).relative_to(PROJECT_ROOT)}")
