"""item3b: run estimate-bess-energy-as in ~15-day subprocess chunks (OOM workaround, see memory
estimate-bess-energy-as-oom-chunking). Outputs to the shared fleet chunks dir so other work can reuse.
Real data: ERCOT 60-day disclosure (NP3-965/966-ER) + Yes Energy datalake. No mock.
Download-bound (~3 min/date via proxy) -> run several disjoint chunk lists in parallel processes:
  python item3b_run_chunks.py 2026-06-01:2026-06-15 2026-06-16:2026-06-30
60-day disclosure for flow date D is published ~D+60 -> as of 2026-09-14 nothing after ~2026-07-15 exists."""
import subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[5]
RUN = ROOT / "skills/estimate-bess-energy-as/scripts/run_estimate.py"
OUT = ROOT / "shared/data/pnl/all_bess/energy_as/chunks"
for arg in sys.argv[1:]:
    s, e = arg.split(":")
    lock = OUT / f".lock_{s}_{e}"
    if (OUT / f"summary_{s}_{e}.parquet").exists() or lock.exists():
        print(f"skip {s}..{e} (exists/locked)", flush=True); continue
    lock.touch(); t = time.time(); print(f"=== {s}..{e}", flush=True)
    r = subprocess.run([sys.executable, str(RUN), "--start", s, "--end", e, "--out-dir", str(OUT)],
                       cwd=ROOT, capture_output=True, text=True)
    print(r.stdout[-3000:], flush=True)
    if r.returncode: print("STDERR:", r.stderr[-3000:], flush=True)
    print(f"--- rc={r.returncode} {time.time()-t:.0f}s", flush=True); lock.unlink(missing_ok=True)
