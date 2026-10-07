"""
recommend_as_position.py — Daily D+1 hourly AS product/venue recommendation.

Wires a date's D-1 bidclose net-load + solar forecast into the Fine playbook
(as_playbook.ASPlaybook) and prints the HE 1-24 recommendation.

The playbook gives WHICH AS product + venue (RRS / ECRS / NSPIN x DA / RT) to
lean into per hour. MW sizing is a SEPARATE bess-optimizer decision made at bid
time from actual HSL / SoC — this tool does not size positions.

Scope note: playbook covers RRS / ECRS / NSPIN only (not Reg-up/down) and picks
ONE combo per hour. Use as a prior into bess-optimizer's co-optimized stack.

Forecast source (priority order):
  1. --forecast-csv PATH                     columns: he, netload_fc_mw, solar_fc_mw
  2. shared/data/raw/yes-energy/<date>.csv    daily pipeline output (operational source)
  3. master_hourly.parquet                   adhoc backtest table (2026-01-01..2026-05-17)

Daily operation — run right after the market-data fetch (both default to D+1):
  python shared/scripts/fetch_market_data.py        # writes yes-energy/<D+1>.csv
  python shared/scripts/recommend_as_position.py    # auto-reads it, no args needed

Usage:
  python shared/scripts/recommend_as_position.py                       # D+1 (tomorrow)
  python shared/scripts/recommend_as_position.py --date 2026-05-10
  python shared/scripts/recommend_as_position.py --date 2026-05-10 --level medium
  python shared/scripts/recommend_as_position.py --date 2026-06-01 --forecast-csv fc.csv

Output:
  - stdout table
  - shared/data/forecasts/as-playbook/<date>.json
"""
from __future__ import annotations
import sys, json, argparse
from datetime import datetime, date, timedelta
from pathlib import Path
from collections import Counter

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
from as_playbook import ASPlaybook  # noqa: E402

MASTER_HOURLY = (PROJECT_ROOT / "shared" / "data" / "adhoc" / "2026-05-07_AS-strategy"
                 / "derived" / "master_hourly.parquet")
YES_RAW_DIR = PROJECT_ROOT / "shared" / "data" / "raw" / "yes-energy"
OUT_DIR = PROJECT_ROOT / "shared" / "data" / "forecasts" / "as-playbook"

# Short label per source for the stdout table (full string kept in JSON)
SOURCE_LABEL = {
    "fine_rule":                      "fine",
    "fine_sparse_fallback_to_medium": "med (sparse fine)",
    "fine_fallback_to_medium":        "med (no fine cohort)",
    "medium_rule":                    "medium",
    "default":                        "DEFAULT",
}


def load_forecast_from_master(target: date) -> dict | None:
    """Return {he: {netload_fc_mw, solar_fc_mw}} from the adhoc master table, or None."""
    if not MASTER_HOURLY.exists():
        return None
    df = pd.read_parquet(MASTER_HOURLY,
                         columns=["datetime_ct", "NET_LOAD_FORECAST_BID_CLOSE",
                                  "SOLAR_COPHSL_BIDCLOSE"])
    df["datetime_ct"] = pd.to_datetime(df["datetime_ct"], utc=True).dt.tz_convert("America/Chicago")
    df = df[df["datetime_ct"].dt.date == target]
    if df.empty:
        return None
    out = {}
    for _, r in df.iterrows():
        he = int(r["datetime_ct"].hour) + 1
        out[he] = {"netload_fc_mw": r["NET_LOAD_FORECAST_BID_CLOSE"],
                   "solar_fc_mw":   r["SOLAR_COPHSL_BIDCLOSE"]}
    return out


def _find_col(cols, needle: str) -> str | None:
    """First column whose name contains `needle` (case-insensitive)."""
    nl = needle.lower()
    for c in cols:
        if nl in str(c).lower():
            return c
    return None


def load_forecast_from_yes_energy(target: date) -> dict | None:
    """Return {he: {...}} from the daily pipeline's yes-energy raw CSV, or None if absent.

    Handles both observed Yes Energy schemas: plain item columns
    (`NET_LOAD_FORECAST_BID_CLOSE:ERCOT`) and node-prefixed columns
    (`ERCOT (NET_LOAD_FORECAST_BID_CLOSE)`). HE = the HOURENDING column (1-24).
    """
    path = YES_RAW_DIR / f"{target.isoformat()}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    he_col  = _find_col(df.columns, "HOURENDING")
    nl_col  = _find_col(df.columns, "NET_LOAD_FORECAST_BID_CLOSE")
    sol_col = _find_col(df.columns, "SOLAR_COPHSL_BIDCLOSE")
    if not (he_col and nl_col and sol_col):
        raise ValueError(
            f"{path.name}: missing required columns (need HOURENDING / "
            f"NET_LOAD_FORECAST_BID_CLOSE / SOLAR_COPHSL_BIDCLOSE). "
            f"Got: {list(df.columns)} — feed may have errored; re-run fetch_market_data.py")
    out = {}
    for _, r in df.iterrows():
        he = pd.to_numeric(r[he_col], errors="coerce")
        if pd.isna(he):
            continue
        out[int(he)] = {"netload_fc_mw": pd.to_numeric(r[nl_col], errors="coerce"),
                        "solar_fc_mw":   pd.to_numeric(r[sol_col], errors="coerce")}
    return out or None


def load_forecast_from_csv(path: Path) -> dict:
    """Return {he: {netload_fc_mw, solar_fc_mw}} from a CSV (he, netload_fc_mw, solar_fc_mw)."""
    df = pd.read_csv(path)
    df.columns = [c.lower().strip() for c in df.columns]
    need = {"he", "netload_fc_mw", "solar_fc_mw"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}. "
                         f"Required: he, netload_fc_mw, solar_fc_mw")
    return {int(r["he"]): {"netload_fc_mw": r["netload_fc_mw"],
                           "solar_fc_mw":   r["solar_fc_mw"]}
            for _, r in df.iterrows()}


def main() -> int:
    ap = argparse.ArgumentParser(description="Daily D+1 hourly AS position recommendation.")
    ap.add_argument("--date", default=None,
                    help="target date YYYY-MM-DD (default: tomorrow, matches fetch_market_data.py)")
    ap.add_argument("--level", default="fine", choices=["fine", "medium"],
                    help="playbook granularity (default: fine)")
    ap.add_argument("--forecast-csv", default=None,
                    help="CSV with columns he, netload_fc_mw, solar_fc_mw")
    ap.add_argument("--min-fine-hours", type=int, default=10,
                    help="Fine cohort trained on fewer hours falls back to Medium (default: 10)")
    args = ap.parse_args()

    if args.date:
        try:
            target = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print(f"ERROR: bad --date '{args.date}' (expected YYYY-MM-DD)")
            return 1
    else:
        target = date.today() + timedelta(days=1)

    # Resolve forecast
    if args.forecast_csv:
        src_path = Path(args.forecast_csv)
        if not src_path.exists():
            print(f"ERROR: --forecast-csv not found: {src_path}")
            return 1
        day_fc = load_forecast_from_csv(src_path)
        fc_source = f"csv:{src_path.name}"
    else:
        # Operational source first: the daily pipeline's yes-energy raw CSV.
        day_fc = load_forecast_from_yes_energy(target)
        if day_fc is not None:
            fc_source = f"yes-energy/{target}.csv (daily pipeline)"
        else:
            day_fc = load_forecast_from_master(target)
            if day_fc is not None:
                fc_source = "master_hourly.parquet (backtest)"
            else:
                print(f"ERROR: no forecast for {target}.\n"
                      f"       Expected daily pipeline output {YES_RAW_DIR.name}/{target}.csv "
                      f"— run: python shared/scripts/fetch_market_data.py --target-date {target}\n"
                      f"       Or supply --forecast-csv PATH (columns: he, netload_fc_mw, solar_fc_mw).")
                return 1

    missing_he = [h for h in range(1, 25) if h not in day_fc]
    if missing_he:
        print(f"WARN: forecast missing HE {missing_he} — those hours skipped.")

    pb = ASPlaybook(min_fine_hours=args.min_fine_hours)
    meta = pb.trained_meta()

    # Build recommendations (skip HE with NaN forecast)
    hours, bad = {}, []
    for he in sorted(day_fc):
        fc = day_fc[he]
        nl, sol = fc["netload_fc_mw"], fc["solar_fc_mw"]
        if pd.isna(nl) or pd.isna(sol):
            bad.append(he)
            continue
        rec = pb.recommend(he, float(nl), float(sol), level=args.level)
        stat_lvl = "fine" if rec["cohort"].count("|") == 2 else "medium"
        n_tr = pb.cohort_stats(rec["cohort"], stat_lvl).get("n_hours_trained")
        hours[he] = {**rec, "netload_fc_mw": round(float(nl), 1),
                     "solar_fc_mw": round(float(sol), 1),
                     "cohort_trained_hours": n_tr}
    if bad:
        print(f"WARN: HE {bad} had NaN forecast — skipped.")

    # ---- stdout ----
    print()
    print("=" * 92)
    print(f"  D+1 AS POSITION RECOMMENDATION  —  {target}  ({args.level.upper()} playbook)")
    print("=" * 92)
    print(f"  Forecast source : {fc_source}")
    print(f"  Playbook        : trained {meta.get('date_range')} · {meta.get('n_hours')}h · "
          f"HSL={meta.get('hsl_mw')}MW flat (in-sample) · min_fine_hours={args.min_fine_hours}")
    print(f"  Reminder        : product+venue only — MW sizing is bess-optimizer's call at bid time")
    print("-" * 92)
    print(f"  {'HE':>2s}  {'Bucket':<8s}  {'NetLoad':>9s}  {'NL_q':>4s}  {'Solar':>8s}  "
          f"{'Sol_q':>5s}   {'AS POSITION':<11s}  {'TrainedOn':>9s}  {'Rule':<20s}")
    print("-" * 92)
    for he in sorted(hours):
        r = hours[he]
        n_tr = r["cohort_trained_hours"]
        print(f"  {he:>2d}  {r['he_bucket']:<8s}  {r['netload_fc_mw']:>9,.0f}  {r['nl_q']:>4s}  "
              f"{r['solar_fc_mw']:>8,.0f}  {r['solar_q']:>5s}   "
              f"{r['product'] + '-' + r['venue']:<11s}  "
              f"{(str(n_tr) + 'h') if n_tr else '—':>9s}  "
              f"{SOURCE_LABEL.get(r['source'], r['source']):<20s}")
    print("-" * 92)

    combo_counts  = Counter(r["combo"] for r in hours.values())
    source_counts = Counter(r["source"] for r in hours.values())
    print(f"  Combo mix : " + " · ".join(f"{k} {v}h" for k, v in combo_counts.most_common()))
    print(f"  Rule mix  : " + " · ".join(f"{SOURCE_LABEL.get(k, k)} {v}h"
                                          for k, v in source_counts.most_common()))
    print("=" * 92)

    # ---- JSON ----
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Fine is the canonical playbook consumed by bess-optimizer at <date>.json.
    # Medium is saved as a sidecar (<date>_medium.json) for human comparison only.
    suffix = "" if args.level == "fine" else f"_{args.level}"
    out_path = OUT_DIR / f"{target}{suffix}.json"
    payload = {
        "date":             str(target),
        "level":            args.level,
        "generated_at":     datetime.now().isoformat(timespec="seconds"),
        "forecast_source":  fc_source,
        "min_fine_hours":   args.min_fine_hours,
        "playbook_trained_on": meta,
        "scope_note": ("AS product+venue selection only (RRS/ECRS/NSPIN x DA/RT); "
                       "MW sizing decided separately by bess-optimizer at bid time."),
        "hours":   {str(h): hours[h] for h in sorted(hours)},
        "summary": {"combo_counts":  dict(combo_counts),
                    "source_counts": dict(source_counts)},
    }
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"  saved -> {out_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
