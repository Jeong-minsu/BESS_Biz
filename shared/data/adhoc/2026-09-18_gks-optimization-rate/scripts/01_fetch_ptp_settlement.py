"""01 — GKS Battery-Settlement-Details 일별 수집 (2025-01-01 .. 2026-09-16).

per-day JSON → shared/data/pnl/gks/hourly/<date>_battery_settlement.json
이미 있는 파일은 건너뜀. PTP rate limit 회피용 0.7s 간격.
"""
from __future__ import annotations
import json, sys, time
from datetime import date, timedelta
from pathlib import Path

import truststore; truststore.inject_into_ssl()   # 사내 프록시 루트 CA (Windows 인증서 저장소)

ROOT = Path(__file__).resolve().parents[5]          # BESS_Biz
sys.path.insert(0, str(ROOT / "shared" / "scripts"))
from _env_loader import load_env_sections           # noqa: E402
from fetch_pnl_data import tenaska_token, tenaska_query, flatten_query  # noqa: E402

OUT = ROOT / "shared" / "data" / "pnl" / "gks" / "hourly"
START, END = date(2025, 1, 1), date(2026, 9, 16)


def main():
    sec = load_env_sections(ROOT / ".env")
    token = tenaska_token(sec.get("tenaska", {}))
    OUT.mkdir(parents=True, exist_ok=True)
    d, n, fails = START, 0, []
    issued = time.time()
    while d <= END:
        f = OUT / f"{d.isoformat()}_battery_settlement.json"
        if f.exists() and f.stat().st_size > 1000:
            d += timedelta(days=1); continue
        if time.time() - issued > 20 * 3600:          # 토큰 24h TTL
            token = tenaska_token(sec.get("tenaska", {})); issued = time.time()
        try:
            rows = flatten_query(tenaska_query(
                token, "ERCOTNodal", "Battery-Settlement-Details", d, "",
                datapoints=None, element_definition="Entity", path="query"))
            f.write_text(json.dumps(rows), encoding="utf-8")
            n += 1
            if n % 25 == 0:
                print(f"[{d}] {n} days fetched", flush=True)
        except Exception as e:
            fails.append((d.isoformat(), repr(e)[:120]))
            print(f"[{d}] FAIL {repr(e)[:120]}", flush=True)
        time.sleep(0.7)
        d += timedelta(days=1)
    print(f"done: {n} new days, {len(fails)} failures", flush=True)
    if fails:
        print(fails[:20], flush=True)


if __name__ == "__main__":
    main()
