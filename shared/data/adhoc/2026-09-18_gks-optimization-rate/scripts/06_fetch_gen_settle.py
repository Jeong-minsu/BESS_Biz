"""06 - Generator-Settlement-Data (ERCOT statement line items) 전 구간 수집.

net revenue = -Σ(*AMT)  — PTP 부호 규약: 음수 = ERCOT가 자원에 지급(수익).
era별 UUID: pre-RTC+B 'Great Kiskadee BESS', post 'Great Kiskadee Storage ESR'.
"""
from __future__ import annotations
import json, sys, time
from datetime import date, timedelta
from pathlib import Path

import truststore; truststore.inject_into_ssl()

ROOT_DIR = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT_DIR / "shared" / "scripts"))
from _env_loader import load_env_sections            # noqa: E402
from fetch_pnl_data import tenaska_token, tenaska_query, flatten_query  # noqa: E402

OUT = ROOT_DIR / "shared" / "data" / "pnl" / "gks" / "hourly"
ROOT, EP = "ERCOTNodal", "Generator-Settlement-Data"
UUID_PRE = "565ab4f2-af92-462a-8f86-c8efd3d0a986"    # Great Kiskadee BESS (pre-RTC+B)
UUID_POST = "b94b48e7-51ac-4d6c-abf4-26531ab91384"   # Great Kiskadee Storage ESR
RTCB = date(2025, 12, 5)
START, END = date(2025, 1, 1), date(2026, 9, 16)


def main():
    sec = load_env_sections(ROOT_DIR / ".env")
    token = tenaska_token(sec.get("tenaska", {}))
    issued = time.time()
    d, n, fails = START, 0, []
    while d <= END:
        f = OUT / f"{d.isoformat()}_gen_settle.json"
        if f.exists() and f.stat().st_size > 1000:
            d += timedelta(days=1); continue
        if time.time() - issued > 20 * 3600:
            token = tenaska_token(sec.get("tenaska", {})); issued = time.time()
        try:
            rows = flatten_query(tenaska_query(
                token, ROOT, EP, d, "", datapoints=None, element_definition=None,
                path="query", element_identifiers=[UUID_PRE if d < RTCB else UUID_POST]))
            f.write_text(json.dumps(rows), encoding="utf-8")
            n += 1
            if n % 25 == 0:
                print(f"[{d}] {n} days", flush=True)
        except Exception as e:
            fails.append(d.isoformat()); print(f"[{d}] FAIL {repr(e)[:110]}", flush=True)
        time.sleep(0.7)
        d += timedelta(days=1)
    print(f"done: {n} new days, {len(fails)} failures", flush=True)
main()
