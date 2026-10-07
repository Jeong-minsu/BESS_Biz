"""
#88 — Backfill Tenaska HSL (Generator-Performance) for Jan 1 - May 4, 2026.

Calls fetch_pnl_data.py --flowday <date> --skip-smartbidder for each missing date.
Rate-limits to 1 call / 2s (Tenaska rate limit is >1/s sustained → 429).

Only re-fetches dates where {flowday}_hsl.json is empty.
"""
from __future__ import annotations
import json, subprocess, sys, time
from datetime import date, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[5]
PNL_DIR = ROOT / "shared" / "data" / "pnl" / "gks" / "hourly"
FETCH = ROOT / "shared" / "scripts" / "fetch_pnl_data.py"

START = date(2026, 1, 1)
END   = date(2026, 5, 17)   # inclusive

# Find dates needing backfill
to_backfill: list[date] = []
d = START
while d <= END:
    hsl_file = PNL_DIR / f"{d.isoformat()}_hsl.json"
    needs_fetch = True
    if hsl_file.exists():
        try:
            with open(hsl_file) as f:
                rows = json.load(f)
            if isinstance(rows, list) and len(rows) > 0:
                needs_fetch = False
        except Exception:
            pass
    if needs_fetch:
        to_backfill.append(d)
    d += timedelta(days=1)

print(f"Total dates in range:    {(END - START).days + 1}")
print(f"Dates needing backfill:  {len(to_backfill)}")
print(f"First needs:             {to_backfill[0].isoformat() if to_backfill else 'none'}")
print(f"Last needs:              {to_backfill[-1].isoformat() if to_backfill else 'none'}")
print()
print("Backfill plan: 1 call per ~3 seconds (rate-limit safe).")
print(f"Estimated time: ~{len(to_backfill) * 3 / 60:.0f} minutes")
print()

# Backfill loop
ok = fail = 0
t0 = time.time()
for i, d in enumerate(to_backfill, 1):
    print(f"[{i}/{len(to_backfill)}] {d.isoformat()} ...", end=" ", flush=True)
    cmd = ["python", str(FETCH), "--flowday", d.isoformat(), "--skip-smartbidder"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                                cwd=str(ROOT))
        if result.returncode == 0:
            # Verify HSL file got data
            hsl_file = PNL_DIR / f"{d.isoformat()}_hsl.json"
            try:
                with open(hsl_file) as f:
                    n = len(json.load(f))
                print(f"OK ({n} HSL rows)")
                ok += 1
            except Exception as e:
                print(f"check-fail ({e})")
                fail += 1
        else:
            print(f"FAIL (exit {result.returncode})")
            # Show stderr tail
            err_tail = result.stderr.strip().split("\n")[-3:]
            for line in err_tail:
                print(f"     {line}")
            fail += 1
    except subprocess.TimeoutExpired:
        print("TIMEOUT")
        fail += 1
    except Exception as e:
        print(f"EXC {type(e).__name__}: {e}")
        fail += 1
    # Pace
    time.sleep(2)

elapsed = time.time() - t0
print()
print(f"Done. ok={ok}, fail={fail}, elapsed={elapsed/60:.1f} min")
