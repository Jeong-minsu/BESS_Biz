"""
YoY comparison #03 — Batch driver: fetch 2025-02-14..2025-04-30 GKS PTP
Energy & AS Details + HSL via fetch_pnl_data.py per flowday.

Calls shared/scripts/fetch_pnl_data.py --flowday YYYY-MM-DD --skip-smartbidder
which writes to shared/data/pnl/gks/hourly/<date>_energy_as_detail.json (+ HSL).

Skips dates that already have *_energy_as_detail.json present.

Usage:
    python 03_fetch_2025_ptp_batch.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[5]
PNL_DIR      = PROJECT_ROOT / "shared" / "data" / "pnl" / "gks" / "hourly"
FETCH_PY     = PROJECT_ROOT / "shared" / "scripts" / "fetch_pnl_data.py"

START = date(2025, 2, 14)
END   = date(2025, 4, 30)


def daterange(s, e):
    d = s
    while d <= e:
        yield d
        d += timedelta(days=1)


def main():
    total = (END - START).days + 1
    print(f"[03_fetch_2025_ptp_batch] {START}..{END}  ({total} days)")
    print(f"   FETCH: {FETCH_PY}")
    print(f"   OUT:   {PNL_DIR}")
    PNL_DIR.mkdir(parents=True, exist_ok=True)

    todo, skipped = [], []
    for d in daterange(START, END):
        out = PNL_DIR / f"{d.isoformat()}_energy_as_detail.json"
        if out.exists() and out.stat().st_size > 200:
            skipped.append(d)
        else:
            todo.append(d)

    print(f"   to fetch: {len(todo)}, already present: {len(skipped)}")
    if not todo:
        print("   nothing to do")
        return

    fail = []
    for i, d in enumerate(todo, 1):
        print(f"\n[{i}/{len(todo)}] flowday={d.isoformat()}")
        cmd = [sys.executable, str(FETCH_PY),
               "--flowday", d.isoformat(),
               "--skip-smartbidder"]
        try:
            r = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True,
                               text=True, timeout=180, encoding="utf-8", errors="replace")
            if r.returncode != 0:
                print(f"  ❌ rc={r.returncode}")
                print(f"  STDOUT tail: {r.stdout[-500:]}")
                print(f"  STDERR tail: {r.stderr[-500:]}")
                fail.append(d)
                continue
            tail_lines = [ln for ln in r.stdout.splitlines()
                          if "saved →" in ln or "saved -> " in ln
                          or "Quick stats" in ln or "✅" in ln]
            for ln in tail_lines[-6:]:
                print("  ", ln)
        except subprocess.TimeoutExpired:
            print("  ❌ timeout (>180s)")
            fail.append(d)
        time.sleep(0.5)  # polite

    print(f"\n========== DONE ==========")
    print(f"  success: {len(todo) - len(fail)} / {len(todo)}")
    if fail:
        print(f"  failed: {[d.isoformat() for d in fail]}")


if __name__ == "__main__":
    main()
