"""12c - 2025-12-05~12-31 (RTC+B 이후) 구간을 post-RTC 경로로 보완."""
import subprocess, sys
from datetime import date, timedelta
from pathlib import Path
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "derived" / "fleet_2026"
W = HERE / "12_fleet_2026.py"
d, end = date(2025, 12, 3), date(2025, 12, 30)
while d <= end:
    e = min(d + timedelta(days=13), end)
    f = OUT / f"daily_{d}_{e}.parquet"
    if not f.exists():
        print(f"[{d}_{e}] ...", flush=True)
        r = subprocess.run([sys.executable, str(W), "--start", str(d), "--end", str(e)],
                           capture_output=True, text=True)
        last = [l for l in r.stdout.splitlines() if l.startswith("[")]
        print("  " + (last[-1] if last else f"FAILED {r.stderr[-300:]}"), flush=True)
    d = e + timedelta(days=1)
print("done", flush=True)
