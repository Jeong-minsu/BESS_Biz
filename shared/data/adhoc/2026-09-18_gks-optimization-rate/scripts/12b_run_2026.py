"""12b - 2026 플릿 빌더를 15일 윈도우 서브프로세스로 순차 실행 (OOM 회피).
SCED 타임스탬프가 조회일+1이라 12/31부터 시작해 2026-01-01~07-31을 커버한다."""
import os, subprocess, sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "derived" / "fleet_2026"
W = HERE / "12_fleet_2026.py"
start, end, n = date(2025, 12, 31), date(2026, 7, 31), 15

d = start
todo = []
while d <= end:
    e = min(d + timedelta(days=n - 1), end)
    todo.append((d, e)); d = e + timedelta(days=1)

for i, (s, e) in enumerate(todo, 1):
    f = OUT / f"daily_{s}_{e}.parquet"
    if f.exists():
        print(f"[skip] {s}_{e}", flush=True); continue
    print(f"[{i}/{len(todo)}] {s}_{e} ...", flush=True)
    r = subprocess.run([sys.executable, str(W), "--start", str(s), "--end", str(e)],
                       capture_output=True, text=True)
    last = [l for l in r.stdout.splitlines() if l.startswith("[")]
    print("  " + (last[-1] if last else f"FAILED rc={r.returncode} {r.stderr[-400:]}"), flush=True)
print("done", flush=True)
