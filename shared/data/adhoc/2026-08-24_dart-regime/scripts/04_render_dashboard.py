# -*- coding: utf-8 -*-
"""
DART regime analysis #04 — render single-file HTML dashboard (no external JS;
CSS-only charts so it also works inside the Artifact CSP).

Output: reports/ad-hoc/dart_regime_2026-07-08.html
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]
ADHOC = Path(__file__).resolve().parents[1]
OUT = PROJECT_ROOT / "reports" / "ad-hoc" / "dart_regime_2026-07-08.html"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

d = json.loads((ADHOC / "derived" / "regime_stats.json").read_text(encoding="utf-8"))
AS_PATH = ADHOC / "derived" / "as_stats.json"
das = json.loads(AS_PATH.read_text(encoding="utf-8")) if AS_PATH.exists() else None

REG_LABEL = {
    "normal": ("Normal", "peak net-load FC ≤ 68 GW"),
    "scarcity_lambda": ("Scarcity · λ-following", "> 68 GW, HE20 wind FC south 또는 coastal < 2 GW"),
    "scarcity_bearish": ("Scarcity · Bearish congestion", "> 68 GW, HE20 wind FC south ≥ 2 GW & coastal ≥ 2 GW"),
}
REG_ORDER = ["normal", "scarcity_lambda", "scarcity_bearish"]


def fmt(v, pct=False, money=False, nd="—"):
    if v is None:
        return nd
    if pct:
        return f"{v*100:.0f}%"
    if money:
        return f"${v:,.0f}"
    return f"{v}"


def he_get(reg, he):
    bh = d["regimes"][reg]["by_he"]
    return bh.get(str(he)) or bh.get(he)


def bar_chart(reg):
    """24-column CSS chart: market avg spread (top) + our PnL (bottom)."""
    cells = []
    vals_sp = []
    vals_pnl = []
    for he in range(1, 25):
        v = he_get(reg, he)
        sp = v["market"]["avg_spread"] if v else None
        pnl = v["ours"]["total_pnl_usd"] if v else None
        vals_sp.append(sp or 0)
        vals_pnl.append(pnl or 0)
    max_sp = max(abs(x) for x in vals_sp) or 1
    max_pnl = max(abs(x) for x in vals_pnl) or 1
    for i, he in enumerate(range(1, 25)):
        sp, pnl = vals_sp[i], vals_pnl[i]
        h_sp = abs(sp) / max_sp * 46
        h_pnl = abs(pnl) / max_pnl * 46
        cls_sp = "up" if sp > 0 else "dn"
        cls_pnl = "up" if pnl > 0 else "dn"
        v = he_get(reg, he)
        wr = v["market"]["short_winrate"] if v else None
        owr = v["ours"]["winrate"] if v else None
        n = v["ours"]["n_hours_with_pos"] if v else 0
        tip = (f"HE{he} · spread {sp:+.1f} $/MWh · mkt short WR {fmt(wr,pct=True)}"
               f" · 우리 PnL {pnl:+,.0f}$ (WR {fmt(owr,pct=True)}, n={n})")
        cells.append(
            f'<div class="col" title="{tip}">'
            f'<div class="half top"><div class="bar {cls_sp}" style="height:{h_sp:.0f}px"></div></div>'
            f'<div class="half bot"><div class="bar {cls_pnl}" style="height:{h_pnl:.0f}px"></div></div>'
            f'<div class="he">{he}</div></div>'
        )
    return (f'<div class="hechart"><div class="axis"><span>spread<br>$/MWh</span>'
            f'<span>우리<br>PnL</span></div><div class="cols">{"".join(cells)}</div></div>'
            f'<div class="legend"><span><i class="sw up"></i>DA&gt;RT (short 우위)</span>'
            f'<span><i class="sw dn"></i>DA&lt;RT (long 우위)</span>'
            f'<span class="mut">위: 시장 평균 spread · 아래: 우리 시간대 누적 PnL · hover 시 상세</span></div>')


STAT_HEADER = ("<th class='num'>시장(GKS) short WR</th><th class='num'>시장(GKS) short P/L</th>"
               "<th class='num'>평균 spread</th>"
               "<th class='num'>우리 WR</th><th class='num'>우리 P/L</th>"
               "<th class='num'>참여 hrs</th><th class='num'>short hrs</th><th class='num'>long hrs</th>"
               "<th class='num'>short 평균 MW</th><th class='num'>long 평균 MW</th>"
               "<th class='num'>우리 PnL</th>")


def stat_cells(v):
    mk, us = v["market"], v["ours"]
    pnl = us["total_pnl_usd"]
    pnl_cls = "pos" if pnl > 0 else ("neg" if pnl < 0 else "")
    return (f"<td class='num'>{fmt(mk['short_winrate'],pct=True)}</td>"
            f"<td class='num'>{fmt(mk['short_pl_ratio'])}</td>"
            f"<td class='num'>{fmt(mk['avg_spread'])}</td>"
            f"<td class='num'>{fmt(us['winrate'],pct=True)}</td>"
            f"<td class='num'>{fmt(us['pl_ratio'])}</td>"
            f"<td class='num'>{us['n_hours_with_pos']}</td>"
            f"<td class='num'>{us['n_short_hours']}</td>"
            f"<td class='num'>{us['n_long_hours']}</td>"
            f"<td class='num'>{fmt(us['short_mwh_avg'])}</td>"
            f"<td class='num'>{fmt(us['long_mwh_avg'])}</td>"
            f"<td class='num {pnl_cls}'>{fmt(pnl,money=True)}</td>")


def block_table(reg):
    rows = [f"<tr><td>{b}</td>{stat_cells(v)}</tr>"
            for b, v in d["regimes"][reg]["by_block"].items()]
    return (f"<table><thead><tr><th>시간 블록</th>{STAT_HEADER}</tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>")


def he_table(reg):
    rows = []
    for he in range(1, 25):
        v = he_get(reg, he)
        if v is None:
            continue
        rows.append(f"<tr><td>HE{he}</td>{stat_cells(v)}</tr>")
    return (f"<details><summary>시간대별 상세 (HE1–24)</summary>"
            f"<table><thead><tr><th>HE</th>{STAT_HEADER}</tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></details>")


def regime_section(reg):
    label, crit = REG_LABEL[reg]
    r = d["regimes"][reg]
    mk, us = r["overall"]["market"], r["overall"]["ours"]
    warn = ('<span class="pill warn">표본 6일 — 단일 스파이크 데이(8/23)가 손익비 지배</span>'
            if reg == "scarcity_bearish" else "")
    return f"""
<section class="panel">
  <div class="sechead"><h2>{label} <span class="days">{r['n_days']}일</span></h2>
  <span class="crit">{crit}</span>{warn}</div>
  <div class="mini-kpis">
    <div><span class="lbl">시장(GKS) short WR</span><b>{fmt(mk['short_winrate'],pct=True)}</b></div>
    <div><span class="lbl">시장(GKS) short P/L</span><b>{fmt(mk['short_pl_ratio'])}</b></div>
    <div><span class="lbl">평균 spread</span><b>{fmt(mk['avg_spread'])} $/MWh</b></div>
    <div><span class="lbl">우리 WR</span><b>{fmt(us['winrate'],pct=True)}</b></div>
    <div><span class="lbl">우리 P/L</span><b>{fmt(us['pl_ratio'])}</b></div>
    <div><span class="lbl">우리 PnL</span><b class="{ 'pos' if us['total_pnl_usd']>0 else 'neg'}">{fmt(us['total_pnl_usd'],money=True)}</b></div>
  </div>
  {bar_chart(reg)}
  {block_table(reg)}
  {he_table(reg)}
</section>"""


AS_STAT_COLS = ("<th class='num'>short WR</th><th class='num'>short P/L</th>"
                "<th class='num'>평균 spread</th>")


def as_cells(v):
    sp = v["avg_spread"]
    sp_cls = "pos" if (sp or 0) > 0 else ("neg" if (sp or 0) < 0 else "")
    return (f"<td class='num'>{fmt(v['short_winrate'],pct=True)}</td>"
            f"<td class='num'>{fmt(v['short_pl_ratio'])}</td>"
            f"<td class='num {sp_cls}'>{fmt(sp)}</td>")


def as_product_section(p):
    pr = das["products"][p]
    nb, sb = pr["normal"], pr["scarcity"]
    blocks = "".join(
        f"<tr><td>{b}</td>{as_cells(nb['by_block'][b])}{as_cells(sb['by_block'][b])}</tr>"
        for b in nb["by_block"])
    overall = (f"<tr style='font-weight:600'><td>전체</td>"
               f"{as_cells(nb['overall'])}{as_cells(sb['overall'])}</tr>")
    hes = []
    for he in range(1, 25):
        vn = nb["by_he"].get(str(he)) or nb["by_he"].get(he)
        vs = sb["by_he"].get(str(he)) or sb["by_he"].get(he)
        if vn is None or vs is None:
            continue
        hes.append(f"<tr><td>HE{he}</td>{as_cells(vn)}{as_cells(vs)}</tr>")
    return f"""
  <h3 style="margin-top:14px">{p} <span class="crit">DA 평균 ${nb['avg_da']} / RT 평균 ${nb['avg_rt']} (normal) · ${sb['avg_da']} / ${sb['avg_rt']} (scarcity)</span></h3>
  <table><thead>
    <tr><th></th><th colspan="3" style="border-bottom:none">Normal ({das['day_counts']['normal']}일)</th><th colspan="3" style="border-bottom:none">Scarcity ({das['day_counts']['scarcity']}일)</th></tr>
    <tr><th>시간 블록</th>{AS_STAT_COLS}{AS_STAT_COLS}</tr>
  </thead><tbody>{overall}{blocks}</tbody></table>
  <details><summary>{p} 시간대별 상세 (HE1–24)</summary>
  <table><thead><tr><th>HE</th>{AS_STAT_COLS}{AS_STAT_COLS}</tr></thead><tbody>{"".join(hes)}</tbody></table></details>"""


as_section = ""
if das:
    as_section = f"""
<section class="panel">
  <div class="sechead"><h2>보조서비스 DA−RT MCPC — Normal vs Scarcity</h2>
  <span class="crit">spread = DA MCPC − RT MCPC (hourly mean) · short win = DA &gt; RT · AS 가격은 ERCOT 시스템 단일가 (nodal 아님 — congestion 무관)</span></div>
  {"".join(as_product_section(p) for p in ["RRS", "ECRS", "NSPIN"])}
</section>"""

tot_pnl = sum(d["regimes"][r]["overall"]["ours"]["total_pnl_usd"] for r in REG_ORDER)
norm = d["regimes"]["normal"]["overall"]
scl = d["regimes"]["scarcity_lambda"]["overall"]
scb = d["regimes"]["scarcity_bearish"]["overall"]
rlz = d.get("regimes_realized", {})
rlz_b = rlz.get("scarcity_bearish_rlz", {}).get("overall", {})

sections = "".join(regime_section(r) for r in REG_ORDER)

html = f"""<title>DART Regime Playbook — GKS</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&family=Noto+Sans+KR:wght@400;500;700&display=swap">
<style>
:root {{
  --bg-base:#f7f8fa; --bg-panel:#ffffff; --bg-panel-2:#f0f2f5; --bg-row-alt:#fafbfc;
  --border-soft:#e0e3eb; --text-primary:#131722; --text-secondary:#5d606b; --text-muted:#9598a1;
  --accent-up:#089981; --accent-down:#f23645; --accent-blue:#2962ff; --accent-amber:#b26a00;
  --grid-line:#eceff3; --shadow-card:0 1px 2px rgba(16,24,40,.04);
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg-base:#0d1117; --bg-panel:#131722; --bg-panel-2:#1c2030; --bg-row-alt:#161b27;
  --border-soft:#2a2e39; --text-primary:#d1d4dc; --text-secondary:#787b86; --text-muted:#5d606b;
  --accent-up:#26a69a; --accent-down:#ef5350; --accent-amber:#ff9800;
  --grid-line:#1e222d; --shadow-card:none;
}} }}
:root[data-theme="dark"] {{
  --bg-base:#0d1117; --bg-panel:#131722; --bg-panel-2:#1c2030; --bg-row-alt:#161b27;
  --border-soft:#2a2e39; --text-primary:#d1d4dc; --text-secondary:#787b86; --text-muted:#5d606b;
  --accent-up:#26a69a; --accent-down:#ef5350; --accent-amber:#ff9800;
  --grid-line:#1e222d; --shadow-card:none;
}}
* {{ box-sizing:border-box; margin:0; }}
body {{ background:var(--bg-base); color:var(--text-primary);
  font-family:'Inter','Noto Sans KR',-apple-system,system-ui,sans-serif; font-size:14px;
  padding:24px; }}
.wrap {{ max-width:1200px; margin:0 auto; display:flex; flex-direction:column; gap:12px; }}
header.panel {{ display:flex; justify-content:space-between; align-items:baseline; flex-wrap:wrap; gap:8px; }}
h1 {{ font-size:20px; font-weight:700; }}
.sub {{ color:var(--text-secondary); font-size:12px; }}
.panel {{ background:var(--bg-panel); border:1px solid var(--border-soft); border-radius:6px;
  padding:20px; box-shadow:var(--shadow-card); }}
.kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; }}
.kpi {{ background:var(--bg-panel); border:1px solid var(--border-soft); border-radius:6px; padding:14px 16px; box-shadow:var(--shadow-card); }}
.kpi .lbl, .mini-kpis .lbl {{ display:block; font-size:10px; letter-spacing:.08em; text-transform:uppercase; color:var(--text-secondary); margin-bottom:4px; }}
.kpi b {{ font-family:'JetBrains Mono',monospace; font-size:26px; font-weight:600; font-variant-numeric:tabular-nums; }}
.kpi .note {{ font-size:11px; color:var(--text-muted); margin-top:2px; }}
.pos {{ color:var(--accent-up); }} .neg {{ color:var(--accent-down); }}
.sechead {{ display:flex; align-items:baseline; gap:12px; flex-wrap:wrap; margin-bottom:12px; }}
h2 {{ font-size:15px; font-weight:600; }}
.days {{ font-family:'JetBrains Mono',monospace; font-size:12px; color:var(--accent-blue); }}
.crit {{ font-size:11px; color:var(--text-muted); }}
.pill {{ font-size:10px; padding:2px 8px; border-radius:999px; border:1px solid currentColor; }}
.pill.warn {{ color:var(--accent-amber); }}
.mini-kpis {{ display:flex; gap:24px; flex-wrap:wrap; margin-bottom:14px; }}
.mini-kpis b {{ font-family:'JetBrains Mono',monospace; font-size:15px; font-variant-numeric:tabular-nums; }}
.hechart {{ display:flex; gap:8px; margin:6px 0 2px; }}
.axis {{ display:flex; flex-direction:column; justify-content:space-around; font-size:9px;
  letter-spacing:.05em; text-transform:uppercase; color:var(--text-muted); text-align:right; padding-bottom:14px; }}
.cols {{ flex:1; display:flex; gap:2px; align-items:stretch; overflow-x:auto; }}
.col {{ flex:1; min-width:14px; display:flex; flex-direction:column; cursor:default; }}
.half {{ height:48px; display:flex; }}
.half.top {{ align-items:flex-end; border-bottom:1px solid var(--grid-line); }}
.half.bot {{ align-items:flex-start; }}
.bar {{ width:100%; border-radius:2px 2px 0 0; }}
.half.bot .bar {{ border-radius:0 0 2px 2px; }}
.bar.up {{ background:var(--accent-up); }} .bar.dn {{ background:var(--accent-down); }}
.col:hover {{ background:var(--bg-panel-2); }}
.he {{ font-size:9px; text-align:center; color:var(--text-muted); font-family:'JetBrains Mono',monospace; padding-top:2px; }}
.legend {{ display:flex; gap:16px; font-size:11px; color:var(--text-secondary); margin:8px 0 16px; flex-wrap:wrap; }}
.legend .sw {{ display:inline-block; width:9px; height:9px; border-radius:2px; margin-right:5px; }}
.sw.up {{ background:var(--accent-up); }} .sw.dn {{ background:var(--accent-down); }}
.legend .mut {{ color:var(--text-muted); }}
.tblwrap, section {{ overflow-x:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th {{ font-size:10px; letter-spacing:.06em; text-transform:uppercase; color:var(--text-secondary);
  text-align:left; padding:8px 10px; border-bottom:1px solid var(--border-soft); white-space:nowrap; }}
td {{ padding:7px 10px; border-bottom:1px solid var(--grid-line); white-space:nowrap; }}
tbody tr:nth-child(even) {{ background:var(--bg-row-alt); }}
tbody tr:hover {{ background:var(--bg-panel-2); }}
.num {{ text-align:right; font-family:'JetBrains Mono',monospace; font-variant-numeric:tabular-nums; }}
.playbook li {{ margin:8px 0 8px 18px; line-height:1.55; }}
.playbook b {{ font-weight:600; }}
.notes {{ font-size:12px; color:var(--text-secondary); line-height:1.6; }}
.notes li {{ margin:4px 0 4px 16px; }}
h3 {{ font-size:13px; font-weight:600; margin-bottom:8px; }}
details {{ margin-top:12px; }}
details summary {{ cursor:pointer; font-size:12px; color:var(--accent-blue); padding:6px 0; user-select:none; }}
details summary:hover {{ color:var(--text-primary); }}
details[open] summary {{ margin-bottom:6px; }}
</style>
<div class="wrap">
<header class="panel">
  <div><h1>GKS DART Virtual — Regime Playbook</h1>
  <div class="sub">2026-07-01 ~ 2026-08-23 · GKS_BESS_RN · 시장(DA−RT spread) vs 우리 실적(Tenaska award 기준)</div></div>
  <div class="sub">spread = DA − RT · short win = DA &gt; RT</div>
</header>

<div class="kpis">
  <div class="kpi"><span class="lbl">기간 총 우리 DART PnL</span><b class="{'pos' if tot_pnl>0 else 'neg'}">${tot_pnl:+,.0f}</b><div class="note">54일 · virtual 노출분만</div></div>
  <div class="kpi"><span class="lbl">Normal (42일)</span><b class="pos">${norm['ours']['total_pnl_usd']:+,.0f}</b><div class="note">WR {fmt(norm['ours']['winrate'],pct=True)} · P/L {norm['ours']['pl_ratio']}</div></div>
  <div class="kpi"><span class="lbl">Scarcity λ ({d['regimes']['scarcity_lambda']['n_days']}일)</span><b class="{'pos' if scl['ours']['total_pnl_usd']>0 else 'neg'}">${scl['ours']['total_pnl_usd']:+,.0f}</b><div class="note">WR {fmt(scl['ours']['winrate'],pct=True)} · P/L {scl['ours']['pl_ratio']}</div></div>
  <div class="kpi"><span class="lbl">Scarcity bearish ({d['regimes']['scarcity_bearish']['n_days']}일)</span><b class="{'pos' if scb['ours']['total_pnl_usd']>0 else 'neg'}">${scb['ours']['total_pnl_usd']:+,.0f}</b><div class="note">WR {fmt(scb['ours']['winrate'],pct=True)} · P/L {scb['ours']['pl_ratio']}</div></div>
  <div class="kpi"><span class="lbl">시장(GKS) short WR (전체 시간)</span><b>{fmt(d['regimes']['normal']['overall']['market']['short_winrate'],pct=True)} / {fmt(scl['market']['short_winrate'],pct=True)}</b><div class="note">normal / scarcity-λ</div></div>
</div>

{sections}
{as_section}
<section class="panel playbook">
  <h2>Regime별 DART 전략 제언</h2>
  <ul>
  <li><b>Normal (≤68 GW):</b> 저녁 HE18–22 short DA가 시장·우리 모두 확실한 엣지 (시장 WR 63%/P/L 1.39, 우리 WR 70%/P/L 1.64, +$22.7k). <b>유지·증량 후보.</b> 반면 midday HE12–15는 우리 −$6.8k (시장 spread는 +인데 side 선택 실패) — 물량 축소 또는 모델 재점검.</li>
  <li><b>Scarcity · bearish congestion (6일):</b> 저녁 GKS spread는 6일 중 4일 소폭 + (+$4~16)로 short가 자주 이기지만, 8/23 시스템 스파이크 하루가 −$121/MWh로 전부 반납시킴 (저녁 P/L 0.23). <b>congestion은 short의 부분 헤지</b> — 8/17엔 hub 저녁 spread −$52일 때 GKS는 +$16으로 basis 눌림(−$111)이 short를 방어. 결론: bearish 신호 시 <b>소사이즈 저녁 short는 가능하되 tail(시스템 스파이크) 감안한 사이징 필수, late HE23–24 short 금지</b> (우리 손실 −$3.8k 발생 구간).</li>
  <li><b>Scarcity · λ-following (6일):</b> 유일하게 작동한 건 HE15–17 ramp short (우리 +$2.3k, P/L 4.09). 저녁은 spread ~flat, late HE23–24는 평균 −$38로 <b>short 절대 금지</b>. 이 regime에서 우리는 +$1.5k로 선방 — 현행 기조 유지하되 late 노출 제거.</li>
  <li><b>분류 기준 (v2, 민수 제안 반영):</b> HE20 south ≥2 GW & coastal ≥2 GW (bid-close STWPF). 실현 bearish 7일 중 5일 포착, 오탐 1일 (8/21, 실현 basis −$7). 놓친 2일 (7/21 south 1.6, 8/18 south 1.9 GW)은 threshold 살짝 아래의 near-miss — south 기준을 1.9 GW로 낮추면 7/7 포착. congestion-analyst constraint binding prob 결합 시 정밀도 개선 여지.</li>
  </ul>
</section>

<section class="panel playbook">
  <h2>제안 의사결정 프레임 — HE20–22 DART (bid-close 예측치만 사용)</h2>
  <p class="crit" style="margin-bottom:10px">검증: 2026-06-01~08-23 84일, GKS node spread 기준. wind FC = WIND_STWPF_BIDCLOSE GR_SOUTH·GR_COASTAL HE20–21 평균 (지역별 각각). west_ratio = west FC ÷ (south+coastal FC).</p>
  <ol>
  <li style="margin:8px 0 8px 18px; line-height:1.55"><b>Gate (tail 차단):</b> peak net-load FC &gt; 68 GW <b>이고</b> south 또는 coastal &lt; 2 GW → <b>short 금지, long RT 기본.</b> 이 버킷이 유일한 재앙 소스 (E[spread] −$24.7, worst −$189).</li>
  <li style="margin:8px 0 8px 18px; line-height:1.55"><b>Short day:</b> south·coastal <b>각각 ≥ 2.5 GW</b> → short DA 기본. 84일 중 29일 해당, day-WR 66%, E +$2.1, worst −$13 (tail이 얕음 — congestion이 hub 스파이크를 부분 헤지, 8/17 사례: hub −$52 vs GKS +$16). 2.0~2.5 GW 구간은 half-size.</li>
  <li style="margin:8px 0 8px 18px; line-height:1.55"><b>Size-up:</b> short day 중 west_ratio가 낮으면 (west FC &lt; south+coastal 합) basis 눌림이 2배 이상 깊어짐 (−18.9 vs −8.1) → 증량. wind FC는 basis 예측력 상위 (west_ratio corr +0.40), net-load FC는 반대 방향 상위 (−0.42).</li>
  <li style="margin:8px 0 8px 18px; line-height:1.55"><b>시간 컷:</b> scarcity day는 HE22 이후 short 보유 금지 — 7~8월 우리 HE23–24 손실 −$4.9k 전부 야간 RT 스파이크 지속 구간에서 발생.</li>
  <li style="margin:8px 0 8px 18px; line-height:1.55"><b>그 외 (normal &amp; wind 미달):</b> E ≈ 0 — 미참여 또는 소액.</li>
  </ol>
  <table style="margin-top:10px"><thead><tr><th>버킷 (84일)</th><th class='num'>일수</th><th class='num'>short day-WR</th><th class='num'>E[spread]</th><th class='num'>worst day</th><th class='num'>evening basis</th><th>액션</th></tr></thead><tbody>
  <tr><td>wind 각 ≥2.5 GW</td><td class='num'>29</td><td class='num'>66%</td><td class='num pos'>+2.1</td><td class='num'>−13.1</td><td class='num'>−13.7</td><td>short 기본</td></tr>
  <tr><td>normal &amp; wind 각 ≥2.0 GW</td><td class='num'>52</td><td class='num'>65%</td><td class='num pos'>+1.2</td><td class='num'>−21.0</td><td class='num'>−12.0</td><td>short half-size</td></tr>
  <tr><td>normal &amp; wind &lt;2.0 GW</td><td class='num'>20</td><td class='num'>50%</td><td class='num'>−0.6</td><td class='num'>−29.3</td><td class='num'>−2.2</td><td>중립/미참여</td></tr>
  <tr><td>scarcity &amp; wind &lt;2.0 GW</td><td class='num'>7</td><td class='num'>43%</td><td class='num neg'>−24.7</td><td class='num neg'>−189.4</td><td class='num'>−35.9</td><td><b>short 금지 · long RT</b></td></tr>
  </tbody></table>
  <p class="crit" style="margin-top:8px">주의: 여름 단일 시즌 표본 — 겨울·봄엔 wind 레벨이 달라 threshold 재보정 필요. E[spread]가 크지 않으므로 사이징·tail 관리가 수익의 대부분을 결정. 향후 outage FC, AG2↔COP HSL wind 괴리, Smartbidder P(DA&lt;RT), congestion-analyst binding prob 결합 검토.</p>
</section>

<section class="panel notes">
  <h3>방법론 · 주의</h3>
  <ul>
  <li>시장 통계: Yes Energy DALMP/RTLMP (hourly), GKS_BESS_RN. short win = spread &gt; 0, P/L = mean(win spread)/mean(loss spread). long은 미러 (WR = 1 − short WR).</li>
  <li>우리 실적: Tenaska PTP Battery Settlement — short MWh = max(DA_Sales − RT_Gen, 0), long MWh = max(DA_Purchases − RT_Cons, 0), PnL = short×spread − long×spread. 물리 dispatch와 겹치는 financial 노출만 집계 (1 MWh 미만 시간 제외). 순수 virtual bid 상품과는 정의가 다를 수 있음.</li>
  <li>Regime 분류는 D−1 bid-close vintage만 사용 (leakage-free): NET_LOAD_FORECAST_BID_CLOSE:ERCOT peak, WIND_STWPF_BIDCLOSE GR_SOUTH·GR_COASTAL의 HE20 스냅샷 (각 지역 ≥ 2 GW → bearish). v1 (두 지역 평균 ≥2.5 GW, 2일만 포착)은 폐기.</li>
  <li>basis = RT LMP(GKS_BESS_RN) − RT LMP(HB_BUSAVG). HB_BUSAVG는 ERCOT 전체 bus 평균 RT 가격으로 시스템 λ의 proxy — basis가 음수면 GKS가 congestion (MCC)으로 시스템 대비 눌린 것. evening basis는 HE18–22 평균.</li>
  <li>참여 hrs = short 또는 long ≥ 1 MWh인 시간 수. short/long hrs는 각 leg ≥ 1 MWh 기준 (한 시간에 양 leg 동시 보유 가능 → short+long ≥ 참여). short/long 평균 MW = 해당 leg 참여 시간의 시간당 평균 awarded virtual 물량.</li>
  <li>"시장(GKS)" 통계는 모두 GKS_BESS_RN 노드의 DALMP−RTLMP 기준 (시스템 λ 아님). HB_BUSAVG는 basis 산출에만 사용.</li>
  <li>AS spread: DA MCPC는 NP4-188 (DAM Clearing Prices for Capacity), RT MCPC는 NP6-331 (15분 정산, ~2026-07-30 발행 중단) + NP6-332 (SCED 5분, 이후 구간)를 hourly 평균. RTC+B 체제의 RT AS 시장 기준. Scarcity 분류는 DART와 동일 (peak net-load FC &gt; 68 GW).</li>
  <li>데이터: 실제 fetch (mock 아님), 2026-08-24 수집.</li>
  </ul>
</section>
</div>
"""

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(html, encoding="utf-8")
print(f"wrote {OUT} ({len(html):,} bytes)")
