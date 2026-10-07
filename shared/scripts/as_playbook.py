"""
as_playbook.py — Production AS DA-RT product/venue selection module.

Encapsulates the Medium (25 cohort) and Fine (86 cohort) playbook rules
derived from 2026-01-01~2026-05-17 historical backtest. Other agents
(bess-optimizer, dart-virtual-trader) can import and call.

Rules trained under HSL=100 MW flat + SoC=200 MWh nameplate (so the playbook
gives WHICH product+venue, separate from MW sizing decisions). Bidding MW is
determined at bid-time from actual HSL/SoC forecast.

Usage:
    from shared.scripts.as_playbook import ASPlaybook

    pb = ASPlaybook()                       # loads default rules
    rec = pb.recommend(
        he=22,
        netload_fc_mw=58000,                # D-1 NET_LOAD_FORECAST_BID_CLOSE for HE
        solar_fc_mw=0,                      # D-1 SOLAR_COPHSL_BIDCLOSE for HE
        level="medium",                     # or "fine"
    )
    # rec = {"product": "NSPIN", "venue": "RT", "cohort": "Evening|Q5", "source": "medium_rule"}

    # Day-wide:
    day_forecast = {
        1: {"netload_fc_mw": 25000, "solar_fc_mw": 0},
        ...
        24: {"netload_fc_mw": 22000, "solar_fc_mw": 0},
    }
    day_plan = pb.recommend_day(day_forecast, level="medium")
    # day_plan[22] = {"product": "NSPIN", "venue": "RT", ...}
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

DEFAULT_RULES_PATH = (Path(__file__).resolve().parents[1]
                      / "data" / "forecasts" / "as_playbook_rules.json")
VALID_PRODUCTS = ("RRS", "ECRS", "NSPIN")
VALID_VENUES   = ("DA", "RT")


class ASPlaybook:
    """Stateless lookup of the (product, venue) recommendation per hour."""

    def __init__(self, rules_path: Optional[Path] = None,
                 min_fine_hours: int = 10):
        """min_fine_hours: a Fine cohort trained on fewer hours than this is
        considered too sparse to trust and falls back to its Medium cohort rule
        (overfitting guard). Set to 0 to disable the sparsity fallback."""
        path = Path(rules_path) if rules_path else DEFAULT_RULES_PATH
        if not path.exists():
            raise FileNotFoundError(
                f"Playbook rules JSON not found at {path}. "
                "Run scripts/97_build_playbook_rules.py first."
            )
        with open(path, encoding="utf-8") as f:
            self.rules = json.load(f)
        # Normalize keys (he buckets need str → int conversion)
        self.he_bucket_map = {int(k): v for k, v in self.rules["he_bucket_map"].items()}
        self.nl_thr        = {int(k): v for k, v in self.rules["nl_quintile_thresholds_per_he"].items()}
        self.solar_thr     = {int(k): v for k, v in self.rules["solar_quintile_thresholds_per_he"].items()}
        self.medium_rules  = self.rules["medium_cohort_rules"]
        self.fine_rules    = self.rules["fine_cohort_rules"]
        self.fine_trained  = self.rules.get("fine_cohort_trained_revenue", {})
        self.min_fine_hours = min_fine_hours
        self.default_combo = self.rules.get("default_combo", "NSPIN_DA")

    # ---------- helpers (public for testing) ----------
    def he_bucket(self, he: int) -> str:
        return self.he_bucket_map.get(he, "Midday")

    def assign_quintile(self, value: float, thresholds: list[float]) -> str:
        if value <= thresholds[0]: return "Q1"
        if value <= thresholds[1]: return "Q2"
        if value <= thresholds[2]: return "Q3"
        if value <= thresholds[3]: return "Q4"
        return "Q5"

    def nl_quintile(self, he: int, netload_fc_mw: float) -> str:
        thr = self.nl_thr.get(he)
        if thr is None:   # fallback: middle quintile
            return "Q3"
        return self.assign_quintile(netload_fc_mw, thr)

    def solar_quintile(self, he: int, solar_fc_mw: float) -> str:
        thr = self.solar_thr.get(he)
        if thr is None:
            return "Q3"
        return self.assign_quintile(solar_fc_mw, thr)

    # ---------- recommendation API ----------
    def recommend(self, he: int, netload_fc_mw: float,
                  solar_fc_mw: float = 0.0,
                  level: str = "medium") -> dict:
        """Return recommended (product, venue) for one hour.

        Returns dict:
          {
            "product": "NSPIN" | "ECRS" | "RRS",
            "venue":   "DA" | "RT",
            "cohort":  cohort key string,
            "source":  "medium_rule" | "fine_rule" | "fine_fallback_to_medium"
                       | "fine_sparse_fallback_to_medium" | "default",
            "he_bucket": ..., "nl_q": ..., "solar_q": ..., (diagnostic)
          }
        """
        if level not in ("medium", "fine"):
            raise ValueError("level must be 'medium' or 'fine'")
        bucket = self.he_bucket(he)
        nl_q   = self.nl_quintile(he, netload_fc_mw)
        solar_q = self.solar_quintile(he, solar_fc_mw)

        # Fine: look up (bucket, nl_q, solar_q). Fall back to the Medium cohort
        # if the Fine cohort is missing OR was trained on too few hours.
        if level == "fine":
            cohort = f"{bucket}|{nl_q}|{solar_q}"
            combo  = self.fine_rules.get(cohort)
            n_tr   = self.fine_trained.get(cohort, {}).get("n_hours_trained", 0)
            if combo and n_tr >= self.min_fine_hours:
                src = "fine_rule"
            else:
                # Missing cohort, or too sparse to trust → use Medium cohort
                reason = "fine_sparse_fallback_to_medium" if combo else "fine_fallback_to_medium"
                mc = f"{bucket}|{nl_q}"
                if mc in self.medium_rules:
                    combo, src = self.medium_rules[mc], reason
                else:
                    combo, src = self.default_combo, "default"
                cohort = mc
        else:  # medium
            cohort = f"{bucket}|{nl_q}"
            combo  = self.medium_rules.get(cohort, self.default_combo)
            src    = "medium_rule" if cohort in self.medium_rules else "default"

        product, venue = combo.split("_")
        return {
            "product":   product,
            "venue":     venue,
            "combo":     combo,
            "cohort":    cohort,
            "source":    src,
            "he_bucket": bucket,
            "nl_q":      nl_q,
            "solar_q":   solar_q,
        }

    def recommend_day(self, day_forecast: dict, level: str = "medium") -> dict:
        """Return 24 recommendations for a full day.

        day_forecast: {he (1-24): {"netload_fc_mw": float, "solar_fc_mw": float}}
        """
        return {he: self.recommend(he,
                                    day_forecast[he]["netload_fc_mw"],
                                    day_forecast[he].get("solar_fc_mw", 0.0),
                                    level=level)
                for he in sorted(day_forecast.keys())}

    # ---------- metadata ----------
    def trained_meta(self) -> dict:
        return self.rules.get("trained_on", {})

    def cohort_stats(self, cohort_key: str, level: str = "medium") -> dict:
        """Return the trained (n_hours, revenue) for a specific cohort, if available."""
        meta = self.rules.get(f"{level}_cohort_trained_revenue", {}).get(cohort_key)
        return meta or {}


# ---------- CLI demo ----------
def _demo() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    pb = ASPlaybook()
    meta = pb.trained_meta()
    print(f"Playbook trained: {meta.get('date_range')}  "
          f"({meta.get('n_hours')} hours, HSL={meta.get('hsl_mw')} MW)")
    print()

    # Demo: evening peak HE 22, varying net-load
    print("Demo: HE 22 (Evening peak), varying Net-Load forecast — Medium playbook:")
    print(f"  {'Net-Load FC (MW)':>20s}  {'Solar FC (MW)':>15s}  {'Recommendation':>30s}")
    for nl_fc, sol_fc in [(20000, 0), (35000, 0), (45000, 0), (58000, 0)]:
        rec = pb.recommend(22, nl_fc, sol_fc, level="medium")
        print(f"  {nl_fc:>20,}  {sol_fc:>15,}  "
              f"{rec['product'] + ' ' + rec['venue']:>15s}  ({rec['cohort']})")

    print()
    print("Demo: Morning HE 9 (Net-Load extreme), Medium vs Fine:")
    for nl_fc, sol_fc in [(48000, 5000), (48000, 0)]:
        med = pb.recommend(9, nl_fc, sol_fc, level="medium")
        fin = pb.recommend(9, nl_fc, sol_fc, level="fine")
        print(f"  Net-Load {nl_fc:,}  Solar {sol_fc:,}:  "
              f"Medium = {med['combo']:>9s}  ({med['cohort']:>14s})  ·  "
              f"Fine = {fin['combo']:>9s}  ({fin['cohort']:>20s})  [{fin['source']}]")

    print()
    print("Demo: full-day plan for a hypothetical D-1 forecast (Q3 net-load throughout)")
    day_fc = {h: {"netload_fc_mw": 28000, "solar_fc_mw": 5000 if 9 <= h <= 18 else 0}
              for h in range(1, 25)}
    plan = pb.recommend_day(day_fc, level="medium")
    print(f"  {'HE':>3s}  {'Bucket':>10s}  {'NL_q':>5s}  {'Recommendation':>15s}")
    for he, rec in plan.items():
        print(f"  {he:>3d}  {rec['he_bucket']:>10s}  {rec['nl_q']:>5s}  "
              f"{rec['product'] + ' ' + rec['venue']:>15s}")


if __name__ == "__main__":
    _demo()
