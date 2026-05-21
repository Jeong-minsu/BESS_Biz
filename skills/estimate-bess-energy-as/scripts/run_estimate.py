#!/usr/bin/env python
"""
run_estimate.py — all-BESS energy + AS revenue estimator (ERCOT SCED/DAM disclosure).

Orchestration runner for the `estimate-bess-energy-as` skill. It is the ONLY
file in scripts/ that is not vendored verbatim from ERCOT_SCED_PJT — everything
under scripts/src/ and scripts/config.py is the project's pipeline, unchanged.

What it does:
  1. Load ERCOT + Yes Energy Datalake credentials from BESS_Biz/.env.
  2. Run the vendored Two-Settlement pipeline (run_pipeline) over a date range,
     which auto-handles the pre/post RTC+B dual-era data sources.
  3. Write hourly revenue, per-resource summary, and TB-index tables to
     shared/data/pnl/all_bess/energy_as/ as parquet (+ summary csv).

Usage (run from the BESS_Biz repo root):
    python skills/estimate-bess-energy-as/scripts/run_estimate.py \
        --start 2026-01-01 --end 2026-05-20

    # custom output directory
    python skills/estimate-bess-energy-as/scripts/run_estimate.py \
        --start 2026-01-01 --end 2026-05-20 --out-dir path/to/dir

See ../SKILL.md for method, output schema, gotchas, and credentials.
"""
import argparse
import os
import sys
from datetime import date, datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)  # so vendored `config` and `src.*` resolve

# BESS_Biz root: skills/estimate-bess-energy-as/scripts -> up 3 levels
BESS_BIZ_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
DEFAULT_OUT = os.path.join(
    BESS_BIZ_ROOT, "shared", "data", "pnl", "all_bess", "energy_as"
)


def _load_credentials() -> None:
    """Populate os.environ with ERCOT + Yes Energy Datalake creds from BESS_Biz/.env.

    Uses the project's section-aware loader (shared/scripts/_env_loader.py) so the
    vendor-prefixed keys are read from the right '# <Vendor>' section. Must run
    BEFORE importing `config` — config.py reads os.getenv() at import time.
    """
    loader_dir = os.path.join(BESS_BIZ_ROOT, "shared", "scripts")
    try:
        sys.path.insert(0, loader_dir)
        from _env_loader import load_env_sections

        sections = load_env_sections()
        for sec in ("ercot", "yes_energy_s3"):
            for k, v in sections.get(sec, {}).items():
                os.environ.setdefault(k, v)
    except Exception as e:  # fallback: prefixed keys are unique, so flat load is safe
        try:
            from dotenv import load_dotenv

            load_dotenv(os.path.join(BESS_BIZ_ROOT, ".env"))
        except Exception:
            print(f"[warn] credential load failed: {e}", file=sys.stderr)


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Estimate all-BESS energy + AS revenue from ERCOT SCED/DAM disclosure."
    )
    ap.add_argument("--start", required=True, type=_parse_date,
                    help="flow start date, YYYY-MM-DD (inclusive)")
    ap.add_argument("--end", required=True, type=_parse_date,
                    help="flow end date, YYYY-MM-DD (inclusive)")
    ap.add_argument("--out-dir", default=DEFAULT_OUT,
                    help=f"output directory (default: {DEFAULT_OUT})")
    args = ap.parse_args()

    if args.start > args.end:
        ap.error("--start must be on or before --end")

    _load_credentials()

    # Import AFTER credentials are set — config.py reads os.getenv at import time.
    from src.pipeline import run_pipeline
    from src.data_fetcher import load_bess_capacity

    cap = load_bess_capacity()
    if not cap.empty:
        cap = cap[cap["settlement_point"] != "-"]
    print(f"BESS capacity reference: {len(cap)} settlement points")

    print(f"Running SCED Two-Settlement pipeline  {args.start} -> {args.end} ...")
    result = run_pipeline(args.start, args.end, bess_capacity=cap)

    revenue = result["revenue"]
    summary = result["summary"]
    tb = result["tb_index"]

    if summary is None or summary.empty:
        print("[error] pipeline returned no data. Check credentials, date range, "
              "and that 60-day disclosure is published for the requested dates.",
              file=sys.stderr)
        return 1

    os.makedirs(args.out_dir, exist_ok=True)
    tag = f"{args.start}_{args.end}"
    rev_path = os.path.join(args.out_dir, f"revenue_hourly_{tag}.parquet")
    sum_pq = os.path.join(args.out_dir, f"summary_{tag}.parquet")
    sum_csv = os.path.join(args.out_dir, f"summary_{tag}.csv")
    tb_path = os.path.join(args.out_dir, f"tb_index_{tag}.parquet")

    revenue.to_parquet(rev_path, index=False)
    summary.to_parquet(sum_pq, index=False)
    summary.to_csv(sum_csv, index=False)
    if tb is not None and not tb.empty:
        tb.to_parquet(tb_path, index=False)

    print("\nWrote:")
    print(f"  {rev_path}  ({len(revenue)} hourly rows)")
    print(f"  {sum_pq}  ({len(summary)} resources)")
    print(f"  {sum_csv}")
    if tb is not None and not tb.empty:
        print(f"  {tb_path}  ({len(tb)} resource-days)")

    if "total_rev" in summary.columns:
        print(f"\nFleet total energy+AS revenue: ${summary['total_rev'].sum():,.0f}")
    if "optimization_rate" in summary.columns:
        valid = summary[summary["optimization_rate"] > 0]
        if not valid.empty:
            print(f"Median optimization rate: {valid['optimization_rate'].median():.1f}%"
                  f"  ({len(valid)} resources with a TB benchmark)")
    if "total_rev" in summary.columns:
        print("\nTop 10 by total revenue:")
        for _, r in summary.nlargest(10, "total_rev").iterrows():
            print(f"  {str(r['resource_name']):<28} ${r['total_rev']:>13,.0f}"
                  f"   opt={r.get('optimization_rate', 0):>6.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
