"""
#98 — Reorganize 81_render_dashboard.py into 3 logical phases.

Phase A — 현황분석: KPI → Q1 → Q2 → Q3 → Q6 → GKS Actual+Monthly
Phase B — 최적화 / Oracle: Q4 → Q5 → Q7 → Q8 → Q9
Phase C — Playbook 구현: Q10 → Q11 → Q12 → C4 (production module guide)
"""
from __future__ import annotations
import sys, re
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPT = Path(__file__).resolve().parents[0] / "81_render_dashboard.py"
src = SCRIPT.read_text(encoding="utf-8")

# Section markers as found in current file (after edits so far)
SECTION_MARKERS = [
    ("KPI",      "<!-- ───── KPI 카드 (3 products × 평균 spread / 음수 확률 / 누적 손실) ───── -->"),
    ("Q1",       "<!-- ───── Q1: 일별 spread 추이 + Hour-Ending × Day-of-Week heatmap ───── -->"),
    ("Q2",       "<!-- ───── Q2: Negative spread 분석 ───── -->"),
    ("Q3",       "<!-- ───── Q3: D-1 Flag Logistic Regression ───── -->"),
    ("Q4",       "<!-- ───── Q4: Optimal Day-Ahead vs Real-Time split ───── -->"),
    ("Q5",       "<!-- ───── Q5: Product mix optimization ───── -->"),
    ("Q6",       "<!-- ───── Q6: Winner cohort characterization ───── -->"),
    ("GKS_NEW",  "<!-- ───── GKS 실제 매출 현황 (Phase A 마지막) ───── -->"),
    ("PHASE_B",  "<!-- ──────────────────────────────────────────────────────────────────────\n     PHASE B"),
    ("Q8",       "<!-- ───── Q8: GKS Actual vs Optimal — per-product comparison ───── -->"),
    ("Q10",      "<!-- ───── Q10: Operational Playbook — situation-based 룰북 ───── -->"),
    ("Q11",      "<!-- ───── Q11: Playbook Upside vs Always-NSPIN-DA Baseline ───── -->"),
    ("Q12",      "<!-- ───── Q12: Daily strategy revenue time series ───── -->"),
    ("Q9",       "<!-- ───── Q9: Filtered comparison — only GKS-participated days ───── -->"),
    ("Q7",       "<!-- ───── Q7: HSL Sensitivity Analysis ───── -->"),
    ("FOOTER",   "<div class=\"section\" style=\"margin-top:32px; color: var(--text-muted); font-size: 11px; line-height:1.6;\">"),
]

# Find start indices of each marker
positions = {}
for name, marker in SECTION_MARKERS:
    idx = src.find(marker)
    if idx < 0:
        print(f"  ✗ MISS: {name}: {marker[:80]}")
        sys.exit(1)
    positions[name] = idx
    print(f"  ✓ {name:8s} at char {idx}")

# Extract each section's content (from marker to next marker)
ordered_names = [n for n, _ in SECTION_MARKERS]
sections = {}
for i, name in enumerate(ordered_names):
    start = positions[name]
    end = positions[ordered_names[i + 1]] if i + 1 < len(ordered_names) else len(src)
    sections[name] = src[start:end]
    print(f"  {name:8s}: {end - start:>6d} chars")

print()
print(f"All sections extracted. Reassembling...")

# Build new ordered body
# (PHASE_B marker text and FOOTER stay as anchors)
new_body = (
    sections["KPI"]      # Phase A start (KPI is right after Phase A header already inserted)
    + sections["Q1"]
    + sections["Q2"]
    + sections["Q3"]
    + sections["Q6"]       # ← moved before Q4
    + sections["GKS_NEW"]  # ← GKS Actual + Monthly (Phase A end)
    + sections["PHASE_B"]  # ← Phase B header (already created)
    + sections["Q4"]       # ← moved into Phase B
    + sections["Q5"]
    + sections["Q7"]       # ← moved from end
    + sections["Q8"]
    + sections["Q9"]       # ← moved from end
    # Phase C divider
    + ('<!-- ──────────────────────────────────────────────────────────────────────\n'
       '     PHASE C — Playbook 구현 (Concrete Implementation)\n'
       '     ────────────────────────────────────────────────────────────────────── -->\n'
       '<div class="section" style="background:linear-gradient(90deg, rgba(8,153,129,0.10), transparent); '
       'padding:14px 16px; border-radius:6px; border-left:4px solid var(--accent-up); margin-top:32px;">\n'
       '  <h2 style="border:none; padding:0; margin:0;">PHASE C — Playbook 구현 (Concrete Implementation)</h2>\n'
       '  <div class="sub" style="margin-top:4px;">시황별 운영 룰북 · 매출 upside 검증 · 일자별 시계열 · '
       'Production module 사용 가이드</div>\n'
       '</div>\n\n')
    + sections["Q10"]
    + sections["Q11"]
    + sections["Q12"]
    # NEW: C4 production module guide
    + ('<!-- ───── C4: Production module guide (as_playbook.py) ───── -->\n'
       '<div class="section">\n'
       '  <h2>C4. Production Module — as_playbook.py 사용 가이드</h2>\n'
       '  <div class="sub">Medium / Fine playbook 룰을 다른 agent (bess-optimizer, dart-virtual-trader 등) 에서 '
       'import 해서 사용하는 방법. D-1 forecast 입력 → 매시간 (product, venue) 추천 산출.</div>\n'
       '\n'
       '  <div class="panel">\n'
       '    <h3>Module 파일 구조</h3>\n'
       '    <table>\n'
       '      <thead><tr><th>파일</th><th>역할</th></tr></thead>\n'
       '      <tbody>\n'
       '        <tr><td><code>shared/scripts/as_playbook.py</code></td>'
       '<td>Importable Python class — <code>ASPlaybook</code></td></tr>\n'
       '        <tr><td><code>shared/data/forecasts/as_playbook_rules.json</code></td>'
       '<td>Cohort rules + quintile thresholds (22 KB, auto-loaded)</td></tr>\n'
       '        <tr><td><code>shared/data/adhoc/2026-05-07_AS-strategy/scripts/97_build_playbook_rules.py</code></td>'
       '<td>재학습 script — 새 데이터 추가 시 실행해 rules 갱신</td></tr>\n'
       '      </tbody>\n'
       '    </table>\n'
       '  </div>\n'
       '\n'
       '  <div class="panel" style="margin-top:12px;">\n'
       '    <h3>사용 예시 (Python)</h3>\n'
       '    <div class="callout" style="background:var(--bg-panel-2); border-left-color: var(--accent-up);">\n'
       '      <pre style="font-family: \'JetBrains Mono\', monospace; font-size: 11px; line-height: 1.6; '
       'white-space: pre-wrap; margin:0;">\n'
       'from shared.scripts.as_playbook import ASPlaybook\n'
       '\n'
       '# 1. 모듈 초기화 (rules JSON 자동 load)\n'
       'pb = ASPlaybook()\n'
       '\n'
       '# 2. 단일 시간 추천 — Medium playbook (25 cohort)\n'
       'rec = pb.recommend(\n'
       '    he=22,                         # Hour Ending\n'
       '    netload_fc_mw=58000,           # D-1 NET_LOAD_FORECAST_BID_CLOSE\n'
       '    solar_fc_mw=0,                 # D-1 SOLAR_COPHSL_BIDCLOSE\n'
       '    level="medium",                # or "fine" (more granular)\n'
       ')\n'
       '# rec = {\n'
       '#   "product": "NSPIN", "venue": "RT", "combo": "NSPIN_RT",\n'
       '#   "cohort":  "Evening|Q5",\n'
       '#   "source":  "medium_rule",\n'
       '#   "he_bucket": "Evening", "nl_q": "Q5", "solar_q": "Q4"\n'
       '# }\n'
       '\n'
       '# 3. 24시간 전체 plan (D-1 forecast 입력)\n'
       'day_fc = {\n'
       '    1:  {"netload_fc_mw": 25000, "solar_fc_mw": 0},\n'
       '    ...\n'
       '    24: {"netload_fc_mw": 22000, "solar_fc_mw": 0},\n'
       '}\n'
       'plan = pb.recommend_day(day_fc, level="medium")\n'
       '# plan[22] = {"product": "NSPIN", "venue": "RT", ...}\n'
       '      </pre>\n'
       '    </div>\n'
       '  </div>\n'
       '\n'
       '  <div class="panel" style="margin-top:12px;">\n'
       '    <h3>학습 메타데이터 + 룰 분포</h3>\n'
       '    <ul style="margin: 6px 0 0 18px; line-height: 1.7; font-size: 12px;">\n'
       '      <li><strong>학습 기간</strong>: 2026-01-01 ~ 2026-05-17 (3,287 hours, 137일)</li>\n'
       '      <li><strong>학습 가정</strong>: HSL = 100 MW flat · SoC = 200 MWh nameplate '
       '(pure rule quality 신호 추출)</li>\n'
       '      <li><strong>Medium 룰</strong>: 25 cohort (5 HE bucket × 5 Net-load quintile). '
       'NSPIN_DA 18 · NSPIN_RT 4 · RRS_DA 2 · ECRS_RT 1</li>\n'
       '      <li><strong>Fine 룰</strong>: 86 cohort (학습 가능한 sparsity 기준). '
       'NSPIN_DA 59 · ECRS_RT 10 · NSPIN_RT 6 · ECRS_DA 6 · RRS_DA 4 · RRS_RT 1</li>\n'
       '    </ul>\n'
       '  </div>\n'
       '\n'
       '  <div class="panel" style="margin-top:12px;">\n'
       '    <h3>Fallback 동작 (production-safe)</h3>\n'
       '    <ol style="margin: 6px 0 0 18px; line-height: 1.7; font-size: 12px;">\n'
       '      <li>Fine 룰 없으면 → Medium 룰 fallback (<code>source: "fine_fallback_to_medium"</code>)</li>\n'
       '      <li>Medium 룰 없으면 → <code>default_combo: "NSPIN_DA"</code> 사용</li>\n'
       '      <li>HE 가 1-24 범위 밖 → "Midday" bucket 으로 fallback</li>\n'
       '    </ol>\n'
       '  </div>\n'
       '\n'
       '  <div class="panel" style="margin-top:12px;">\n'
       '    <h3>재학습 (새 데이터 추가 시)</h3>\n'
       '    <div class="callout" style="background:var(--bg-panel-2);">\n'
       '      <pre style="font-family: \'JetBrains Mono\', monospace; font-size: 11px; margin:0;">\n'
       '# 새 데이터 fetch 후 모델 재학습 (예: 6월 데이터 도착 시)\n'
       'python shared/data/adhoc/2026-05-07_AS-strategy/scripts/97_build_playbook_rules.py\n'
       '# → shared/data/forecasts/as_playbook_rules.json 자동 갱신\n'
       '# 다른 agent 는 변경 없이 즉시 새 rules 사용 (다음 ASPlaybook() init 시)\n'
       '      </pre>\n'
       '    </div>\n'
       '  </div>\n'
       '\n'
       '  <div class="panel" style="margin-top:12px;">\n'
       '    <h3>통합 권장 agent</h3>\n'
       '    <ul style="margin: 6px 0 0 18px; line-height: 1.8; font-size: 12px;">\n'
       '      <li><strong>bess-optimizer</strong>: D-1 forecast 받아 <code>pb.recommend_day()</code> 로 '
       '24시간 (product, venue) plan 산출 → AS bid 자동화</li>\n'
       '      <li><strong>dart-virtual-trader</strong>: 동일 forecast input 으로 AS 매출 forecast 도 도출 가능</li>\n'
       '      <li><strong>reporter</strong>: 매일 07:30 daily report 에 "today\'s playbook plan" 자동 포함</li>\n'
       '      <li><strong>pnl-manager</strong>: 익일 실적 vs playbook 추천 의 gap 분석</li>\n'
       '    </ul>\n'
       '  </div>\n'
       '</div>\n\n')
    + sections["FOOTER"]
    # APPENDIX: Glossary at end
    + ('\n<!-- ───── APPENDIX: 용어집 (Glossary) — 분석 마지막에 reference 로 배치 ───── -->\n'
       '<div class="section" style="margin-top:32px;">\n'
       '  <h2>Appendix — 용어집 (Glossary)</h2>\n'
       '  <div class="panel">\n'
       '    <div class="glossary">\n'
       '      <div><strong>Day-Ahead Market (DAM)</strong> — 하루 전 청산되는 전력 시장. 보조서비스도 여기서 청산.</div>\n'
       '      <div><strong>Real-Time Market (RTM)</strong> — 실시간 (5분 또는 15분) 청산되는 전력 시장.</div>\n'
       '      <div><strong>Market Clearing Price for Capacity (MCPC)</strong> — 보조서비스 시장 청산 가격 ($/MWh).</div>\n'
       '      <div><strong>Spread</strong> — Day-Ahead MCPC − Real-Time MCPC. 양수면 Day-Ahead 에서 sell이 유리.</div>\n'
       '      <div><strong>Hour Ending (HE)</strong> — 시간대 라벨. HE1 = 00:00~01:00, HE24 = 23:00~24:00.</div>\n'
       '      <div><strong>Day of Week</strong> — 요일 (월요일=0 ··· 일요일=6).</div>\n'
       '      <div><strong>Responsive Reserve Service (RRS)</strong> — 주파수 응동 보조서비스 (10분 이내).</div>\n'
       '      <div><strong>ERCOT Contingency Reserve Service (ECRS)</strong> — 비상 대응 보조서비스 (10분).</div>\n'
       '      <div><strong>Non-Spinning Reserve (Non-Spin / NSPIN)</strong> — 비회전 예비력 (30분 내).</div>\n'
       '      <div><strong>Logistic Regression</strong> — 이진 분류용 로지스틱 회귀.</div>\n'
       '      <div><strong>Area Under ROC Curve (AUC)</strong> — 분류기 성능 지표, 1.0이 완벽 / 0.5는 무작위.</div>\n'
       '      <div><strong>F1 score</strong> — Precision과 Recall의 조화평균.</div>\n'
       '      <div><strong>Top-decile lift</strong> — 모델 예측 확률 상위 10%의 적중률 ÷ 전체 base rate.</div>\n'
       '      <div><strong>High Sustained Limit (HSL)</strong> — 배터리 최대 지속 출력 (MW). 본 분석 strategy 비교는 100 MW flat 가정.</div>\n'
       '      <div><strong>State of Charge (SoC)</strong> — 배터리 충전 상태 (MWh). GKS = 200 MWh.</div>\n'
       '      <div><strong>SoC Duration</strong> — RRS 0.5h · ECRS 1h · NSPIN 4h. Real-Time cap = min(HSL, SoC / duration).</div>\n'
       '      <div><strong>Oracle (Perfect Foresight)</strong> — 매시간 정답을 알 때의 상한선. Binary rule family 의 이론 천장.</div>\n'
       '      <div><strong>τ* (tau-star)</strong> — Binary D-1 Flag Rule 의 매출 최대화 임계값.</div>\n'
       '      <div><strong>Gross vs Net DA AS Revenue</strong> — Gross = Tenaska 보고치 (a_DA × DAM_MCPC). Net = 가정 #1 적용 (a_DA × spread).</div>\n'
       '      <div><strong>Cohort</strong> — Playbook 학습 단위. Medium = (HE bucket × Net-load quintile). Fine = + Solar quintile.</div>\n'
       '    </div>\n'
       '  </div>\n'
       '</div>\n')
)

# Replace the body portion: from first marker (KPI) to end of FOOTER section
first_marker_pos = positions["KPI"]
# The footer is a single self-closing <div class="section">...</div>.
# Find the closing </div> that ends the footer section (NOT the body wrap's closing).
# Look for the pattern "</div>\n\n</div>" — first </div> = footer section close, second = body wrap close.
wrap_close_pattern = "</div>\n\n</div>"
wrap_close_pos = src.find(wrap_close_pattern, positions["FOOTER"])
if wrap_close_pos < 0:
    print("ERROR: couldn't find footer section closing")
    sys.exit(1)
footer_section_end = wrap_close_pos + len("</div>")  # include first </div> (footer close), exclude wrap close

# Sections["FOOTER"] currently extends from FOOTER marker to end of file (we extracted it as last segment).
# Trim it to just the footer's <div class="section">...</div> block.
footer_only = src[positions["FOOTER"]:footer_section_end]
print(f"\nFooter section: {positions['FOOTER']} → {footer_section_end}  ({footer_section_end - positions['FOOTER']} chars)")

# Rebuild new_body using trimmed footer
# Replace the sections["FOOTER"] in new_body with the trimmed footer_only
new_body = new_body.replace(sections["FOOTER"], footer_only)

# Old body: from KPI start to footer section end (inclusive)
old_body = src[first_marker_pos:footer_section_end]
print(f"Old body chars: {len(old_body):,}")
print(f"New body chars: {len(new_body):,}")

# Replace
new_src = src.replace(old_body, new_body)
if new_src == src:
    print("ERROR: replace failed (old_body not found exactly in src)")
    sys.exit(1)

# Write back
SCRIPT.write_text(new_src, encoding="utf-8")
print(f"\nReordered → {SCRIPT.name}")
print(f"  old size: {len(src):,}")
print(f"  new size: {len(new_src):,}  (delta {len(new_src)-len(src):+d})")
