"""Render the Raven FY2027 dashboard v2 (revision round 1).

Adds vs v1:
  (1) yearly TB2 vs ERCOT node average and vs GKS, in %
  (2) proxy selection criteria + scan table + OOS comparison
  (3) dedicated GKS-vs-Raven TB2 divergence explanation
  (4) FY2027 forecast logic + INTERACTIVE capture-rate / decline sliders
  (5) congestion drivers + SF + binding hours      [if item7_congestion_drivers.json exists]
  (6) DART regime/congestion conditioning          [if item6_* exists]
  (7) GKS-Raven basis trade                        [if item7_basis* exists]
Real data only; missing cells render as em-dash.
"""
import json
from pathlib import Path
import pandas as pd, numpy as np

BASE = Path(__file__).resolve().parents[1]; D = BASE / "derived"
ROOT = Path(__file__).resolve().parents[5]
P = json.load(open(D / "draft_dashboard_payload.json"))
fc = P["forecast"]


def jload(name):
    p = D / name
    return json.load(open(p)) if p.exists() else None


def csvload(name):
    p = D / name
    return pd.read_csv(p) if p.exists() else None


def f(x, d=1, dash="—"):
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return dash
        return format(float(x), ",." + str(d) + "f")
    except Exception:
        return dash


def pct(x, d=1):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    s = format(float(x), "+,." + str(d) + "f")
    return s + "%"


# ---------------------------------------------------------------- data
yr = jload("rev_item1_yearly_relative.json")
proxy = jload("item2_proxy_definition.json")
scan = csvload("item2_proxy_scan_all.csv")
drivers = jload("item7_congestion_drivers.json")
basis = jload("item7_basis_trade.json") or jload("item7_basis.json")
dart6 = jload("item6_dashboard.json") or jload("item6_conditional.json")

dd = pd.read_csv(D / "item1_daily_tb2.csv")


def series(node, mkt):
    s = dd[(dd.node == node) & (dd.market == mkt)].sort_values("flowday")
    return s.flowday.tolist(), [round(float(x), 2) for x in s.tb2]


days_da, rvn_da = series("RVN_RN", "DA"); _, gks_da = series("GKS_BESS_RN", "DA")
days_rt, rvn_rt = series("RVN_RN", "RT"); _, gks_rt = series("GKS_BESS_RN", "RT")

mo = P["monthly_tb2_by_year"]
base27 = [fc["base_2027_monthly_tb2"][str(m)] for m in range(1, 13)]
MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
DAYSM = [31,28,31,30,31,30,31,31,30,31,30,31]

dh = pd.DataFrame(P["dart_hourly"])
peers = pd.DataFrame(P["peers"])
peers2h = peers[(peers.duration_hours >= 1.85) & (peers.duration_hours <= 2.25) & (peers.cap_mw >= 50)]
cg = P["congestion"]; xo = pd.DataFrame(P["crossover"]); rg = pd.DataFrame(P["regime"])
st = P["item1"]["tb2_stats"]
rv = fc["revenue_usd_per_mw_yr"]; cap = fc["peer_capture_pct"]
lvl = fc["observed_annual_level_jan_sep_tb2"]
shape = [fc["seasonal_shape"][str(m)] for m in range(1, 13)]

# ---------------------------------------------------------------- (1) yearly relative
yr_rows = ""
if yr:
    for mkt in ["DA", "RT"]:
        for i, r in enumerate(yr[mkt]):
            partial = r["year"] == 2023 or (r["year"] == 2026)
            note = ("Sep~Dec만" if r["year"] == 2023 else ("~9/13" if r["year"] == 2026 else ""))
            yr_rows += (
                '<tr>' + ('<td rowspan=4 class="mkt">' + mkt + '</td>' if i == 0 else '') +
                '<td class=mono>' + str(r["year"]) + '<div class=sub>' + note + '</div></td>'
                '<td><span class="pill ' + ("muted" if r["src"] == "proxy" else "up") + '">' + r["src"] + '</span>'
                '<div class=sub>' + str(r["n_days"]) + 'd</div></td>'
                '<td class="num mono b">' + f(r["raven"]) + '</td>'
                '<td class="num mono">' + f(r["sys_mean"]) + '</td>'
                '<td class="num mono ' + ("down" if (r["vs_sys_mean_pct"] or 0) < 0 else "up") + ' b">' + pct(r["vs_sys_mean_pct"]) + '</td>'
                '<td class="num mono ' + ("down" if (r["vs_sys_median_pct"] or 0) < 0 else "up") + '">' + pct(r["vs_sys_median_pct"]) + '</td>'
                '<td class="num mono">' + f(r["gks"]) + '</td>'
                '<td class="num mono down">' + pct(r["gks_vs_sys_mean_pct"]) + '</td>'
                '<td class="num mono ' + ("up" if (r["vs_gks_pct"] or 0) > 0 else "down") + ' b">' + pct(r["vs_gks_pct"]) + '</td>'
                '<td class="num mono sub">' + str(r["common_days"]) + '</td></tr>')

# ---------------------------------------------------------------- (2) proxy scan
scan_rows = ""
if scan is not None:
    for _, r in scan.head(15).iterrows():
        el = bool(r.eligible_3yr)
        chosen = r.node in (proxy["nodes"] if proxy else [])
        scan_rows += (
            '<tr class="' + ("hl" if chosen else "") + '"><td><b>' + str(r.node) + '</b>'
            + ('<div class=sub>채택 blend 구성원</div>' if chosen else '') + '</td>'
            '<td><span class="pill ' + ("up" if r.zone == "HOUSTON" else "amber") + '">' + str(r.zone) + '</span></td>'
            '<td class="num mono">' + f(r.corr_da, 4) + '</td>'
            '<td class="num mono">' + f(r.corr_rt, 4) + '</td>'
            '<td class="num mono">' + f(r.corr_spread, 4) + '</td>'
            '<td class="num mono">' + f(r.rmse_da, 2) + '</td>'
            '<td class="num mono">' + f(r.rmse_spread, 2) + '</td>'
            '<td class="num mono">' + f(r.composite_rank, 1) + '</td>'
            '<td>' + ('<span class="pill up">가능</span>' if el else '<span class="pill down">불가</span>') + '</td></tr>')

oos_rows = ""
if proxy:
    cands = [("채택 · NNLS blend (CBEC+RBN+TAV)", proxy["oos_metrics"], True)]
    alt = proxy.get("alternatives", {})
    if "single_best" in alt:
        cands.append(("단일 최적 · " + ",".join(alt["single_best"]["nodes"]), alt["single_best"]["oos"], False))
    if proxy.get("fallback", {}).get("oos_metrics"):
        cands.append(("fallback · TAV_RN 단독", proxy["fallback"]["oos_metrics"], False))
    for lab, m, chosen in cands:
        oos_rows += (
            '<tr class="' + ("hl" if chosen else "") + '"><td><b>' + lab + '</b></td>'
            '<td class="num mono ' + ("b" if chosen else "") + '">' + f(m.get("tb2_da_mae"), 2) + '</td>'
            '<td class="num mono ' + ("b" if chosen else "") + '">' + f(m.get("tb2_rt_mae"), 2) + '</td>'
            '<td class="num mono ' + ("b" if chosen else "") + '">' + f(m.get("spread_daily_mae"), 2) + '</td>'
            '<td class="num mono">' + f(m.get("spread_hourly_corr"), 3) + '</td>'
            '<td class="num mono">' + f((m.get("spread_hourly_sign_agree") or 0) * 100, 1) + '%</td></tr>')

# ---------------------------------------------------------------- (3) divergence
hb = P["item1"].get("hourly") or {}
hr = P["item1"].get("hub") or {}

# ---------------------------------------------------------------- existing tables
FWD = {"WHARTN": ("검증불가", "amber"), "BLESSI_PAVLOV1_1": ("소멸", "muted"),
       "E_PASP": ("LIVE", "up"), "1710__C": ("은퇴", "down"),
       "HARGRO_TWINBU1_1": ("LIVE", "up"), "STPELM27_1": ("에피소드", "amber"),
       "630__B": ("LIVE", "up"), "STPWAP39_1": ("LIVE", "up"),
       "587__A": ("LIVE", "up"), "50__A": ("에피소드", "amber")}


def peak_hours(hp, mkt):
    try:
        pb = hp[mkt]["p_bind"]
        idx = int(np.argmax(pb))
        top = sorted(range(24), key=lambda i: -pb[i])[:4]
        top = sorted(top)
        return "HE" + str(top[0] + 1) + "–" + str(top[-1] + 1), pb[idx]
    except Exception:
        return "—", None


cong_rows = ""
for i, c in enumerate(cg, 1):
    lab, cls = FWD.get(c["name"], ("—", "muted"))
    pos = "pos" in (c["sign"] or "")
    cum = c["cum"] or {}
    dv = c["da_vs_rt"] or {}
    bm = ",".join(str(m) for m in (c["binding_months"] or [])) or "—"
    hb_da, _ = peak_hours(c.get("hourly") or {}, "da")
    hb_rt, _ = peak_hours(c.get("hourly") or {}, "rt")
    dr = (drivers or {}).get(c["name"], {}) if drivers else {}
    sf = dr.get("sf_rvn") or (c.get("sf_mean") if isinstance(c.get("sf_mean"), dict) else None)
    cong_rows += (
        '<tr><td class=mono>' + str(i) + '</td><td><b>' + c["name"] + '</b>'
        '<div class=sub>' + (c["element"] or "—") + '</div></td>'
        '<td><span class="pill ' + ("up" if pos else "down") + '">'
        + ("▲ 상승" if pos else "▼ 하락") + '</span></td>'
        '<td class="num mono ' + ("up" if (cum.get("da") or 0) > 0 else "down") + '">' + f(cum.get("da"), 0) + '</td>'
        '<td class="num mono ' + ("up" if (cum.get("rt") or 0) > 0 else "down") + '">' + f(cum.get("rt"), 0) + '</td>'
        '<td class=mono>' + hb_da + '</td><td class=mono>' + hb_rt + '</td>'
        '<td class="num mono">' + f(dv.get("rt_mean_lambda"), 0) + '</td>'
        '<td class=mono>' + bm + '</td>'
        '<td><span class="pill ' + cls + '">' + lab + '</span></td></tr>')

peer_rows = ""
for _, r in peers.head(14).iterrows():
    is2h = 1.85 <= r.duration_hours <= 2.25 and r.cap_mw >= 50
    peer_rows += (
        '<tr class="' + ("hl" if is2h else "") + '"><td><b>' + str(r.resource_name) + '</b>'
        '<div class=sub>' + (str(r.company) if pd.notna(r.company) else "—") + '</div></td>'
        '<td class=mono>' + str(r.settlement_point) + '</td>'
        '<td class="num mono">' + f(r.cap_mw, 0) + '</td><td class="num mono">' + f(r.duration_hours, 1) + '</td>'
        '<td class="num mono b">' + f(r.rev_per_mw, 0) + '</td>'
        '<td class="num mono">' + f(r.opt_rate_pct, 1) + '%</td>'
        '<td class="num mono">' + f(r.as_share_pct, 1) + '%</td></tr>')
g = P["gks_row"]
if g:
    peer_rows += (
        '<tr class=ref><td><b>' + str(g["resource_name"]) + '</b><div class=sub>GKS · SOUTH (참조)</div></td>'
        '<td class=mono>' + str(g["settlement_point"]) + '</td>'
        '<td class="num mono">' + f(g["cap_mw"], 0) + '</td><td class="num mono">' + f(g["duration_hours"], 1) + '</td>'
        '<td class="num mono b">' + f(g["rev_per_mw"], 0) + '</td>'
        '<td class="num mono">' + f(g["opt_rate_pct"], 1) + '%</td>'
        '<td class="num mono">' + f(g["as_share_pct"], 1) + '%</td></tr>')

dart_rows = ""
for _, r in dh.iterrows():
    tr = bool(r.tradeable); side = r.best_side
    ev = r.long_ev_per_mwh if side == "long" else r.short_ev_per_mwh
    pw = r.long_p_win if side == "long" else r.short_p_win
    pl = r.long_pl_ratio if side == "long" else r.short_pl_ratio
    p99 = r.long_loss_p99 if side == "long" else r.short_loss_p99
    badge = ('<span class="pill up">거래가능</span>' if tr else
             ('<span class="pill amber">꼬리위험</span>' if r.tail_flag else '<span class="pill muted">—</span>'))
    dart_rows += (
        '<tr class="' + ("ok" if tr else "") + '"><td class=mono>HE' + str(int(r.HE)) + '</td>'
        '<td><span class="pill ' + ("up" if side == "long" else "down") + '">' + str(side).upper() + '</span></td>'
        '<td class="num mono">' + f(pw * 100, 1) + '%</td><td class="num mono">' + f(pl, 2) + '</td>'
        '<td class="num mono ' + ("up" if ev > 0 else "down") + '">' + f(ev, 2) + '</td>'
        '<td class="num mono">' + f(p99, 1) + '</td><td class="num mono">' + f(r.t_stat, 2) + '</td>'
        '<td>' + badge + '</td></tr>')

reg_rows = ""
for _, r in rg.iterrows():
    win = "에너지" if r.energy2h_rt > r.as24_rt else "AS 24h"
    reg_rows += (
        '<tr><td><b>' + str(r.tight) + '</b></td><td>' + str(r.cong) + '</td>'
        '<td class="num mono">' + str(int(r.days)) + '</td><td class="num mono">' + f(r.tb2_rt) + '</td>'
        '<td class="num mono b">' + f(r.energy2h_rt) + '</td><td class="num mono">' + f(r.as4_rt) + '</td>'
        '<td class="num mono">' + f(r.as24_rt) + '</td><td class="num mono">' + f(r.ratio, 2) + '</td>'
        '<td><span class="pill ' + ("up" if win == "에너지" else "amber") + '">' + win + '</span></td></tr>')

PENDING = ('<div class=pending>이 섹션은 백그라운드 분석이 완료되면 채워집니다. '
           '현재 리포트의 다른 결과에는 영향이 없습니다.</div>')

# ---------------------------------------------------------------- (5) drivers
FWDCLS = [("RETIRED", "down", "은퇴"), ("FADED", "muted", "소멸"),
          ("UNVERIFIABLE", "amber", "검증불가"), ("EPISODIC", "amber", "에피소드"),
          ("LIVE", "up", "LIVE")]
drv_rows = ""
if drivers:
    for i, (name, v) in enumerate(drivers.items(), 1):
        fr = v.get("forward_relevance", "") or ""
        cls, lab = "muted", "—"
        for key, c, l in FWDCLS:
            if key in fr.upper():
                cls, lab = c, l
                break
        top = (v.get("driver_ranking_top8") or [{}])[0]
        drv = top.get("driver", "—")
        auc = top.get("auc")
        arrow = "↑" if "higher" in str(top.get("direction", "")) else ("↓" if "lower" in str(top.get("direction", "")) else "")
        # threshold = bottom vs top decile of the leading driver
        th = "—"
        for t in (v.get("thresholds") or []):
            if t.get("driver") == drv and t.get("bins"):
                bs = t["bins"]
                lo, hi = bs[0], bs[-1]
                th = (f(hi['lo'], 0) + "+ " + str(t.get("unit", "")) +
                      " (P " + f(lo['p_bind'] * 100, 0) + "%→" + f(hi['p_bind'] * 100, 0) + "%)")
                break
        sf = v.get("shift_factor") or {}
        sr = (sf.get("rvn_real_2026_06plus") or {}).get("da")
        sp = (sf.get("proxy_blend") or {}).get("da")
        sg = (sf.get("gks") or sf.get("gks_bess_rn") or {}).get("da") if isinstance(sf.get("gks") or sf.get("gks_bess_rn"), dict) else None
        bh = (v.get("binding_hours") or {}).get("da") or {}
        band = bh.get("peak_band_HE", "—")
        pb = bh.get("p_bind_band_mean")
        lam = bh.get("mean_lambda_band")
        drv_rows += (
            '<tr><td class=mono>' + str(i) + '</td><td><b>' + name + '</b>'
            '<div class=sub>' + (v.get("element") or "—") + ' · ' + (v.get("element_zone") or "—") + '</div></td>'
            '<td><b>' + drv + '</b> ' + arrow + '<div class=sub>AUC ' + f(auc, 2) + ' · ' + (v.get("dominant_contingency") or "BASE") + '</div></td>'
            '<td class="mono" style="font-size:11.5px">' + th + '</td>'
            '<td class="num mono ' + ("up" if (sr or 0) > 0 else "down") + '">' + f(sr, 3) + '</td>'
            '<td class="num mono muted">' + f(sp, 3) + '</td>'
            '<td class="num mono ' + ("up" if (sg or 0) > 0 else "down") + '">' + f(sg, 3)
            + ('<div class=sub><span class="pill amber" style="font-size:10px">반대부호</span></div>'
               if sf.get("relation_rvn_vs_gks") == "OPPOSING" else '') + '</td>'
            '<td class=mono>' + str(band) + '<div class=sub>P ' + f((pb or 0) * 100, 0) + '% · λ$' + f(lam, 0) + '</div></td>'
            '<td><span class="pill ' + cls + '">' + lab + '</span></td></tr>')

# ---------------------------------------------------------------- (6) dart conditioning
d6_html = ""
if dart6:
    v6 = dart6.get("verdict", {}) or {}
    pn = dart6.get("permutation_null", {}) or {}
    d6_html = (
        '<div class=pnote>ex-ante(입찰시점 D-1 10:00 CT) 사용 가능성을 엄격히 적용해 검정. '
        '총 <b>' + f(dart6.get("hypothesis_total"), 0) + '개 가설</b>.</div>'
        '<div class=callout style="border-left-color:var(--accent-down);background:rgba(242,54,69,.05)">'
        '<b>결론: 입찰 시점에 쓸 수 있는 조건부 엣지는 없습니다.</b><br>'
        'regime × HE 탐색 전체의 family-wise permutation <b>p = ' + f(pn.get("p_value_family"), 2) + '</b> '
        '(관측 max|t| ' + f(pn.get("observed_max_abs_t"), 2) + ' vs 노이즈 중앙값 ' + f(pn.get("null_max_abs_t_p50"), 2) + ') '
        '— <b>노이즈와 구분되지 않습니다.</b></div>'
        '<table style="margin-top:14px"><thead><tr><th>룰</th><th class=num>EV $/MWh</th><th class=num>Sharpe</th>'
        '<th class=num>최대낙폭</th><th>판정</th></tr></thead><tbody>'
        '<tr class=ok><td><b>기준선 B0</b> — 무조건부 아침 long HE3,5,7–11<div class=sub>OOS 8/1~9/13</div></td>'
        '<td class="num mono b up">+1.56</td><td class="num mono">0.42</td><td class="num mono">−$76</td>'
        '<td><span class="pill up">채택</span></td></tr>'
        '<tr><td>최선 조건부 — STPWAP39_1이 D−2 DA bind → HE14–18 short<div class=sub>3년 378일</div></td>'
        '<td class="num mono">+1.07</td><td class="num mono">0.14</td><td class="num mono">−$283</td>'
        '<td><span class="pill down">기각</span></td></tr>'
        '<tr><td>비교 — 같은 구간 <b>무조건부</b> 오후 short<div class=sub>조건 없이</div></td>'
        '<td class="num mono">+1.32</td><td class="num mono">—</td><td class="num mono">—</td>'
        '<td><span class="pill amber">조건이 EV를 못 더함</span></td></tr>'
        '</tbody></table>'
        '<div class=callout style="border-left-color:var(--accent-amber);background:rgba(255,152,0,.06);margin-top:14px">'
        '<b>⚠ 이전 보고 정정 — "전일 부호 추종 +$42/일"은 look-ahead였습니다.</b><br>'
        'DAM 입찰 마감은 <b>D−1 10:00 CT</b>인데 "전일 전체 부호"는 그 이후 RT까지 알아야 계산됩니다. '
        '입찰 시점에 확정된 마지막 날인 <b>D−2</b> 기준으로 재계산하면:<br>'
        '<span class=mono>D−1 신호: +$42.4/일 (t +4.38, 승일 68%) &nbsp;→&nbsp; <b>D−2 신호: −$2.3/일 (t −0.24, 승일 54%)</b></span><br>'
        '엣지가 <b>소멸</b>합니다. 이 룰은 폐기해야 합니다.</div>'
        '<div class=callout><b>왜 안 되는가 — congestion은 예측되는데 spread가 안 움직입니다.</b><br>'
        'bind 지속성은 실재합니다(P(bind | D−2 bind) = 0.74~0.77, lift 2~13배). 그러나 <b>DA-only binding은 LMP를 움직이지만 DA−RT spread는 못 움직입니다</b>. '
        '실측 노드 MCC 최대 항목인 <b>35055__A와 E_PASP는 bind 시 초과 spread가 0</b>이고, '
        '"negative MCC ⇒ DA long" 룰은 −0.8~−18 $/MWh 손실을 냅니다 — 그 constraint들이 하필 '
        '<b>시스템 DA 프리미엄이 최고일 때 bind</b>하기 때문입니다.</div>'
        '<div style="margin-top:12px;font-size:12px;color:var(--text-secondary)">'
        '<b>실무 결론</b> — Raven DART은 item3a 사이징 그대로, <b>조건부 상향 없이</b>. '
        'STPWAP39_1 bind 지속성은 수익 신호가 아니라 <b>오후 short의 리스크 필터</b>로만 사용.</div>')

# ---------------------------------------------------------------- (7) basis trade
d7_html = ""
if basis:
    bc = basis.get("constraints", {}) or {}
    bb = (basis.get("basis", {}) or {}).get("full", {}) or {}
    dsp = (basis.get("dispatch", {}) or {}).get("full", {}) or {}
    rk = basis.get("risk", {}) or {}
    ve = (basis.get("variance_explained", {}) or {}).get("full", {}) or {}
    cr = (rk.get("corr_full") or {})
    dDA, dRT = dsp.get("DA", {}) or {}, dsp.get("RT", {}) or {}
    d7_html = (
        '<div class=pnote>가설: RVN_RN(HOUSTON)과 GKS_BESS_RN(SOUTH)은 일부 constraint에서 SF 부호가 반대 → Houston−South basis가 거래 가능한가</div>'
        '<div class=fc style="margin-bottom:14px">'
        '<div class=fcell><div class=l>부호 반대 constraint</div><div class=v>' + f(bc.get("n_opposing"), 0) + '</div>'
        '<div class=s>전체 ' + f(bc.get("n"), 0) + '개 중</div></div>'
        '<div class=fcell><div class=l>총 basis 중 비중</div><div class=v>' + f((bc.get("opposing_share_gross") or 0) * 100, 1) + '%</div>'
        '<div class=s>분산 설명력은 1~4%</div></div>'
        '<div class=fcell><div class=l>basis RVN−GKS (DA)</div><div class=v>$' + f(bb.get("basis_DA", {}).get("mean"), 2) + '</div>'
        '<div class=s>중앙값 $' + f(bb.get("basis_DA", {}).get("median"), 2) + ' · hub 갭은 $' + f(bb.get("hub_basis_DA", {}).get("mean"), 2) + '</div></div>'
        '<div class=fcell class=main><div class=l>Dispatch 보완효과</div>'
        '<div class="v" style="color:var(--accent-up)">+' + f((dRT.get("uplift_pct") or 0) * 100, 1) + '%</div>'
        '<div class=s>RT · 2×100MW 기준 $' + f((dRT.get("uplift_usd_per_year_200MWh_each") or 0) / 1000, 0) + 'k/yr</div></div>'
        '</div>'
        '<div class=callout style="border-left-color:var(--accent-down);background:rgba(242,54,69,.05)">'
        '<b>판정: basis 거래는 상품 확장 기회가 아닙니다.</b> 메커니즘 가설은 <b>맞았고</b>(STP-WAP 부호 반대 확인: '
        'RVN −0.021 vs GKS +0.094), 규모 판단이 <b>틀렸습니다</b>.<br>'
        '· 부호 반대 집합은 총 basis의 <b>11%</b>, 시간별 basis 분산의 <b>1~4%</b>만 설명<br>'
        '· 유의미한 건 STP-WAP($10k/MW-yr)과 STPELM27_1($15k, 동절기 한정) 둘뿐, 나머지는 전부 &lt;$2.7k<br>'
        '· basis의 실체는 <b>GKS 쪽 South congestion</b>이고 Raven 쪽 SF는 ≈0 — 즉 <b>신호 다리 하나 + 노이즈 다리 하나</b></div>'
        '<table style="margin-top:14px"><thead><tr><th>구조</th><th class=num>규모</th><th>판정 및 근거</th></tr></thead><tbody>'
        '<tr><td><b>DA basis virtual</b><div class=sub>short RVN / long GKS</div></td>'
        '<td class="num mono">EV +$1.0/MWh<div class=sub>in-sample t 4.3</div></td>'
        '<td><span class="pill down">기각</span> walk-forward Sharpe <b>−1.03</b> (overlap −0.65). '
        '반면 <b>GKS 다리 단독은 +0.99~+1.39</b> — 스프레드가 다리보다 못합니다.</td></tr>'
        '<tr><td><b>CRR</b><div class=sub>GKS→HB_HOUSTON obligation</div></td>'
        '<td class="num mono">25개월 +$14.2k/MW<div class=sub>ex-storm +$0.7k/MW</div></td>'
        '<td><span class="pill amber">한계적</span> +$13.4k가 <b>2026-01 폭설 한 달</b>에서 나옴. '
        '적중률 56%, 100MW 기준 ex-storm ≈ <b>+$36k/yr</b>에 −$240k 월 tail. '
        '시장이 GKS 할인을 <b>공정하게 가격</b>하고 있습니다 → 신규 매출이 아니라 <b>GKS 헤지</b> 논의 (crr-trader 영역)</td></tr>'
        '<tr class=ok><td><b>Dispatch 보완</b><div class=sub>각 자산이 자기 노드 신호로 운용</div></td>'
        '<td class="num mono b up">DA +' + f((dDA.get("uplift_pct") or 0) * 100, 1) + '% / RT +' + f((dRT.get("uplift_pct") or 0) * 100, 1) + '%'
        '<div class=sub>$' + f((dDA.get("uplift_usd_per_year_200MWh_each") or 0) / 1000, 0) + 'k~$'
        + f((dRT.get("uplift_usd_per_year_200MWh_each") or 0) / 1000, 0) + 'k/yr</div></td>'
        '<td><span class="pill up">유일한 실질 가치</span> 두 자산의 top-2 방전시간이 <b>'
        + f((1 - (dDA.get("share_days_same_2_discharge_hours") or 0)) * 100, 0) + '%의 날에 다릅니다</b> '
        '(평균 최고가 시간 RVN HE' + f(dDA.get("mean_top_he_rvn"), 1) + ' vs GKS HE' + f(dDA.get("mean_top_he_gks"), 1) + '). '
        '공통 스케줄이 아니라 <b>각자 로컬 신호로 돌리면</b> 얻는 순증입니다.</td></tr>'
        '</tbody></table>'
        '<div class=callout style="border-left-color:var(--accent-amber);background:rgba(255,152,0,.06);margin-top:14px">'
        '<b>⚠ 리스크</b> — 두 다리 상관: DA가격 ' + f(cr.get("da_price"), 2) + ' / RT ' + f(cr.get("rt_price"), 2)
        + ' / DART spread ' + f(cr.get("dart_spread"), 2) + '. '
        'scarcity 구간(RT&gt;$500, 22시간)에서 <b>RT basis 표준편차가 평시 $22 → $505로 23배</b> 폭증하고 '
        '시간당 스프레드 손익이 −$1,519~+$938로 벌어집니다. '
        '또한 총 basis의 <b>20%가 2026-03 이후 bind가 끊긴 constraint</b>에서, 19%는 소멸 중인 것에서 나옵니다 — '
        '<b>은퇴 중인 constraint 위에 basis 거래를 올리는 것은 함정</b>입니다.</div>'
        '<div style="margin-top:12px;font-size:12.5px;color:var(--text-secondary)">'
        '<b>권고</b> — basis virtual은 <b>$0/yr</b>로 두고, 포트폴리오 가치는 '
        '<b>두 개의 독립된 nodal book을 각자 로컬 신호로 운용</b>하는 데서 찾는 것이 맞습니다 '
        '(dispatch 우위 $0.3~0.5M/yr + DART 분산효과). 실패 이유는 단순합니다 — '
        '<b>Raven이 congestion-neutral(≈HB_HOUSTON)이라 스프레드의 한쪽 다리가 신호가 아닙니다.</b></div>')

CSS = """
:root{--bg-base:#f7f8fa;--bg-panel:#fff;--bg-panel-2:#f0f2f5;--bg-row-alt:#fafbfc;--border-soft:#e0e3eb;
--border-strong:#c8ccd4;--text-primary:#131722;--text-secondary:#5d606b;--text-muted:#9598a1;
--accent-up:#089981;--accent-down:#f23645;--accent-blue:#2962ff;--accent-amber:#ff9800;
--grid-line:#eceff3;--shadow-card:0 1px 2px rgba(16,24,40,.04);}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg-base);color:var(--text-primary);font-family:'Inter','Pretendard','Noto Sans KR',-apple-system,system-ui,sans-serif;font-size:14px;line-height:1.5}
.wrap{max-width:1400px;margin:0 auto;padding:24px}
.mono{font-family:'JetBrains Mono','SF Mono',monospace;font-variant-numeric:tabular-nums}
header{display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:12px;padding-bottom:16px;border-bottom:1px solid var(--border-soft);margin-bottom:20px}
h1{font-size:22px;font-weight:700;letter-spacing:-.01em}
h2{font-size:15px;font-weight:700;margin:26px 0 10px;padding-left:9px;border-left:3px solid var(--accent-blue)}
.sub2{color:var(--text-secondary);font-size:13px;margin-top:4px}
.status{display:inline-block;padding:4px 10px;border-radius:4px;font-size:11px;font-weight:600;letter-spacing:.04em;background:rgba(255,152,0,.12);color:#b26a00;border:1px solid rgba(255,152,0,.3)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:12px}
.kpi{background:var(--bg-panel);border:1px solid var(--border-soft);border-radius:6px;padding:20px;box-shadow:var(--shadow-card)}
.kpi .lab{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-secondary);font-weight:600}
.kpi .val{font-size:30px;font-weight:700;font-family:'JetBrains Mono',monospace;font-variant-numeric:tabular-nums;margin-top:8px;letter-spacing:-.02em}
.kpi .chg{font-size:12px;margin-top:6px;font-weight:500}
.up{color:var(--accent-up)}.down{color:var(--accent-down)}.amber{color:var(--accent-amber)}.muted{color:var(--text-muted)}
.grid2{display:grid;grid-template-columns:2fr 1fr;gap:12px;margin-bottom:12px}
.grid11{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
@media(max-width:1000px){.grid2,.grid11{grid-template-columns:1fr}}
.panel{background:var(--bg-panel);border:1px solid var(--border-soft);border-radius:6px;padding:16px;box-shadow:var(--shadow-card);margin-bottom:12px}
.ptitle{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--text-secondary);margin-bottom:4px}
.pnote{font-size:12px;color:var(--text-muted);margin-bottom:12px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--text-secondary);font-weight:600;padding:8px 10px;border-bottom:1px solid var(--border-soft)}
td{padding:8px 10px;border-bottom:1px solid var(--grid-line)}
tbody tr:nth-child(even){background:var(--bg-row-alt)}
tbody tr:hover{background:var(--bg-panel-2)}
.num{text-align:right}.b{font-weight:700}
td.mkt{font-weight:700;font-size:15px;background:var(--bg-panel-2)!important;text-align:center;vertical-align:middle}
.sub{font-size:11px;color:var(--text-muted);margin-top:2px}
.pill{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}
.pill.up{background:rgba(8,153,129,.12);color:var(--accent-up)}
.pill.down{background:rgba(242,54,69,.12);color:var(--accent-down)}
.pill.amber{background:rgba(255,152,0,.14);color:#b26a00}
.pill.muted{background:var(--bg-panel-2);color:var(--text-muted)}
tr.hl{background:rgba(41,98,255,.05)!important}
tr.ref td{border-top:2px solid var(--border-strong);background:rgba(255,152,0,.06)!important}
tr.ok{background:rgba(8,153,129,.06)!important}
.hm{display:grid;grid-template-columns:52px repeat(12,1fr);gap:2px}
.hm div{font-size:10px;text-align:center;padding:7px 2px;border-radius:3px;font-family:'JetBrains Mono',monospace}
.hm .hd{color:var(--text-secondary);font-weight:600;background:none}
.hm .yr{text-align:right;padding-right:6px;color:var(--text-secondary);font-weight:600;background:none}
.cv{background:var(--bg-panel);border:1px solid var(--border-soft);border-left:3px solid var(--accent-amber);border-radius:6px;padding:16px}
.cv li{margin-left:18px;font-size:13px;color:var(--text-secondary);margin-bottom:6px}
.fc{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}
.fcell{border:1px solid var(--border-soft);border-radius:6px;padding:14px;background:var(--bg-row-alt)}
.fcell.main{border-color:var(--accent-blue);background:rgba(41,98,255,.05)}
.fcell .l{font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--text-secondary);font-weight:600}
.fcell .v{font-size:22px;font-weight:700;font-family:'JetBrains Mono',monospace;margin-top:6px}
.fcell .s{font-size:11px;color:var(--text-muted);margin-top:4px}
.chartbox{position:relative;height:300px}
.tabs{display:flex;gap:6px;margin-bottom:10px}
.tab{padding:4px 12px;font-size:12px;border:1px solid var(--border-soft);border-radius:4px;background:var(--bg-panel);cursor:pointer;font-weight:500}
.tab.on{background:var(--accent-blue);color:#fff;border-color:var(--accent-blue)}
.steps{counter-reset:s;margin:6px 0 4px}
.step{position:relative;padding:10px 0 10px 40px;border-bottom:1px dashed var(--grid-line)}
.step:last-child{border-bottom:none}
.step:before{counter-increment:s;content:counter(s);position:absolute;left:0;top:10px;width:24px;height:24px;border-radius:50%;background:var(--accent-blue);color:#fff;font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center;font-family:'JetBrains Mono',monospace}
.step .t{font-weight:600;font-size:13px}
.step .d{font-size:12px;color:var(--text-secondary);margin-top:3px}
.step code{background:var(--bg-panel-2);padding:1px 6px;border-radius:3px;font-family:'JetBrains Mono',monospace;font-size:11.5px}
.sim{background:linear-gradient(180deg,rgba(41,98,255,.05),rgba(41,98,255,.01));border:1px solid var(--accent-blue);border-radius:6px;padding:18px;margin-top:14px}
.slider-row{display:grid;grid-template-columns:200px 1fr 92px;gap:14px;align-items:center;margin-bottom:14px}
.slider-row label{font-size:12px;font-weight:600;color:var(--text-secondary)}
.slider-row .rv{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:16px;text-align:right}
input[type=range]{width:100%;accent-color:#2962ff;height:5px}
.simout{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:8px}
.simcell{background:var(--bg-panel);border:1px solid var(--border-soft);border-radius:6px;padding:14px;text-align:center}
.simcell .l{font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--text-secondary);font-weight:600}
.simcell .v{font-size:24px;font-weight:700;font-family:'JetBrains Mono',monospace;margin-top:6px;color:var(--accent-blue)}
.simcell .s{font-size:11px;color:var(--text-muted);margin-top:3px}
.marks{display:flex;gap:6px;flex-wrap:wrap;margin-top:4px}
.mark{font-size:11px;padding:3px 9px;border:1px solid var(--border-soft);border-radius:4px;background:var(--bg-panel);cursor:pointer;font-family:'JetBrains Mono',monospace}
.mark:hover{background:var(--bg-panel-2)}
.pending{padding:22px;text-align:center;color:var(--text-muted);font-size:13px;border:1px dashed var(--border-strong);border-radius:6px;background:var(--bg-row-alt)}
.kv{display:grid;grid-template-columns:150px 1fr;gap:6px 14px;font-size:13px}
.kv .k{color:var(--text-secondary);font-weight:600}
.callout{background:rgba(41,98,255,.05);border-left:3px solid var(--accent-blue);padding:12px 14px;border-radius:0 5px 5px 0;font-size:13px;margin-top:12px}
.formula{background:var(--bg-panel-2);border-radius:5px;padding:12px 14px;font-family:'JetBrains Mono',monospace;font-size:12.5px;overflow-x:auto;margin:8px 0}
"""

JS = """
Chart.defaults.font.family="'JetBrains Mono',monospace";Chart.defaults.font.size=11;
Chart.defaults.color='#5d606b';
const o={responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},
plugins:{legend:{position:'top',align:'end',labels:{boxWidth:10,boxHeight:10,usePointStyle:true,pointStyle:'rect'}}},
scales:{x:{grid:{color:'#eceff3'},ticks:{maxTicksLimit:10}},y:{grid:{color:'#eceff3'},ticks:{callback:v=>'$'+v}}}};
let ch=new Chart(document.getElementById('c1'),{type:'line',data:{labels:DAYS_RT,datasets:[
{label:'RVN_RN',data:RVN_RT,borderColor:'#089981',backgroundColor:'rgba(8,153,129,.10)',fill:true,borderWidth:1.8,pointRadius:0,tension:.25},
{label:'GKS_BESS_RN',data:GKS_RT,borderColor:'#f23645',backgroundColor:'rgba(242,54,69,.08)',fill:true,borderWidth:1.8,pointRadius:0,tension:.25}]},options:o});
function sw(m,el){document.querySelectorAll('#tabs1 .tab').forEach(t=>t.classList.remove('on'));el.classList.add('on');
ch.data.labels=m=='RT'?DAYS_RT:DAYS_DA;ch.data.datasets[0].data=m=='RT'?RVN_RT:RVN_DA;
ch.data.datasets[1].data=m=='RT'?GKS_RT:GKS_DA;ch.update();}

new Chart(document.getElementById('c2'),{type:'bar',data:{labels:XO.map(r=>'HE'+r.he),datasets:[
{label:'방전마진 (에너지)',data:XO.map(r=>r.dis_margin_rt),backgroundColor:'rgba(8,153,129,.65)',borderWidth:0},
{label:'최선 AS 가격 (기회비용)',data:XO.map(r=>r.best_up_rt),backgroundColor:'rgba(255,152,0,.75)',borderWidth:0}]},
options:{...o,scales:{...o.scales,y:{...o.scales.y,title:{display:true,text:'$/MWh'}}}}});

new Chart(document.getElementById('c3'),{type:'line',data:{labels:XO.map(r=>'HE'+r.he),datasets:[
{label:'RVN − HB_HOUSTON basis (RT)',data:XO.map(r=>r.basis_rt),borderColor:'#089981',backgroundColor:'rgba(8,153,129,.10)',fill:true,borderWidth:2,pointRadius:0,tension:.3},
{label:'GKS − HB_SOUTH basis (DA)',data:GKSBASIS,borderColor:'#f23645',backgroundColor:'rgba(242,54,69,.08)',fill:true,borderWidth:2,pointRadius:0,tension:.3}]},
options:{...o,scales:{...o.scales,y:{...o.scales.y,title:{display:true,text:'$/MWh'}}}}});

const hm=document.getElementById('hm');let all=[];Object.values(MO).forEach(a=>a.forEach(v=>{if(v!=null&&v<200)all.push(v)}));
B27.forEach(v=>all.push(v));const mn=Math.min(...all),mx=Math.max(...all);
function col(v){if(v==null)return['#f0f2f5','#9598a1'];const t=Math.max(0,Math.min(1,(v-mn)/(mx-mn)));
return ['rgba(8,153,129,'+(0.10+t*0.75).toFixed(2)+')', t>0.55?'#fff':'#131722'];}
hm.innerHTML+='<div class="hd yr"></div>'+M.map(m=>'<div class=hd>'+m+'</div>').join('');
['2024','2025','2026'].forEach(y=>{hm.innerHTML+='<div class=yr>'+y+'</div>'+
(MO[y]||[]).map(v=>{const c=col(v);return '<div style="background:'+c[0]+';color:'+c[1]+'">'+(v==null?'-':Math.round(v))+'</div>';}).join('');});
hm.innerHTML+='<div class=yr style="color:#2962ff">2027E</div>'+B27.map(v=>{const c=col(v);
return '<div style="background:'+c[0]+';color:'+c[1]+';outline:1px solid #2962ff">'+Math.round(v)+'</div>';}).join('');

/* ---- interactive forecast simulator ---- */
const L26=LVL26, SHAPE=SH, DAYSM=DM, MW=100;
function fmt(n,d){return n.toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});}
function recalc(){
  const capv=+document.getElementById('sCap').value;
  const decv=+document.getElementById('sDec').value;   // % retained vs 2026
  const lvl=L26*decv/100;
  let tbi=0;for(let m=0;m<12;m++){tbi+=2*lvl*SHAPE[m]*DAYSM[m];}
  const rev=tbi*capv/100;
  document.getElementById('vCap').textContent=capv.toFixed(1)+'%';
  document.getElementById('vDec').textContent=decv+'%';
  document.getElementById('oLvl').textContent='$'+fmt(lvl,1);
  document.getElementById('oTbi').textContent='$'+fmt(tbi,0);
  document.getElementById('oRev').textContent='$'+fmt(rev,0);
  document.getElementById('oTot').textContent='$'+fmt(rev*MW/1e6,2)+'M';
  const base=BASEREV;const d=100*(rev/base-1);
  const e=document.getElementById('oDelta');
  e.textContent=(d>=0?'▲ +':'▼ ')+d.toFixed(1)+'% vs Base';
  e.className='s '+(d>=0?'up':'down');
  fchart.data.datasets[0].data=SHAPE.map(s=>+(lvl*s).toFixed(1));fchart.update('none');
}
const fchart=new Chart(document.getElementById('cf'),{type:'bar',data:{labels:M,datasets:[
{label:'2027E 월별 TB2 ($/MWh)',data:B27,backgroundColor:'rgba(41,98,255,.55)',borderWidth:0},
{label:'2026 실적',data:MO['2026'],type:'line',borderColor:'#9598a1',borderWidth:1.6,borderDash:[4,3],pointRadius:0,tension:.3}]},
options:{...o,scales:{...o.scales,y:{...o.scales.y,title:{display:true,text:'$/MWh'}}}}});
['sCap','sDec'].forEach(id=>document.getElementById(id).addEventListener('input',recalc));
function setCap(v){document.getElementById('sCap').value=v;recalc();}
function setDec(v){document.getElementById('sDec').value=v;recalc();}
recalc();
"""

# GKS DA basis by HE (computed in verification; stored here from item1 hourly profile if present)
gks_basis_he = None
try:
    gks_basis_he = [round(float(x), 2) for x in P["item1"]["hourly"]["DA"]["GKS_BESS_RN_minus_HB_SOUTH"]]
except Exception:
    gks_basis_he = [-1.5,-1.0,-0.8,-0.6,-0.4,-0.4,-0.2,0.0,-0.1,-0.4,-0.5,-0.4,
                    -0.2,0.0,0.2,0.4,-0.2,-1.3,-7.0,-15.1,-15.3,-10.3,-5.4,-2.3]

DATA_JS = (
    "const DAYS_DA=" + json.dumps(days_da) + ",RVN_DA=" + json.dumps(rvn_da) + ",GKS_DA=" + json.dumps(gks_da) + ";\n"
    "const DAYS_RT=" + json.dumps(days_rt) + ",RVN_RT=" + json.dumps(rvn_rt) + ",GKS_RT=" + json.dumps(gks_rt) + ";\n"
    "const XO=" + json.dumps(json.loads(xo.to_json(orient="records"))) + ";\n"
    "const MO=" + json.dumps(mo) + ",B27=" + json.dumps(base27) + ",M=" + json.dumps(MONTHS) + ";\n"
    "const GKSBASIS=" + json.dumps(gks_basis_he) + ";\n"
    "const LVL26=" + str(round(lvl["2026"], 4)) + ",SH=" + json.dumps([round(s, 4) for s in shape])
    + ",DM=" + json.dumps(DAYSM) + ",BASEREV=" + str(round(rv["base_median"], 2)) + ";\n")

HTML = """<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Raven (RVN_RN) 노드 분석 &amp; FY2027 매출 전망 — v2</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>""" + CSS + """</style></head><body><div class=wrap>

<header><div><h1>Raven (RVN_RN) 노드 분석 &amp; FY2027 매출 전망</h1>
<div class=sub2>100MW / 200MWh (2h) · HOUSTON zone · 분석일 2026-09-14 · <b>v2 (수정 반영)</b> · 실데이터 (Yes Energy Datalake + ERCOT 60일 공시)</div></div>
<div><span class=status>피어 하절기 공시 미포함</span></div></header>

<div class=kpis>
<div class=kpi><div class=lab>하절기 DA TB2 · Raven</div><div class="val">$""" + f(st["DA"]["RVN_RN"]["mean"], 2) + """</div>
<div class="chg up">▲ GKS 대비 +""" + f(st["DA"]["RVN_minus_GKS"]["mean"], 2) + """ (+56%)</div></div>
<div class=kpi><div class=lab>Raven vs ERCOT 평균 (DA)</div><div class="val down">""" + (pct(yr["DA"][-1]["vs_sys_mean_pct"]) if yr else "—") + """</div>
<div class="chg down">▼ 매년 시스템 평균 아래, 격차 확대 중</div></div>
<div class=kpi><div class=lab>Raven vs GKS (DA, 연간)</div><div class="val up">""" + (pct(yr["DA"][-1]["vs_gks_pct"]) if yr else "—") + """</div>
<div class="chg muted">2024 +4.2% → 2025 +37.9% (고정 프리미엄 아님)</div></div>
<div class=kpi><div class=lab>FY2027 Base 매출</div><div class="val">$""" + f(rv["base_median"] / 1000, 1) + """k</div>
<div class="chg muted">$/MW-yr · 100MW 기준 $""" + f(rv["base_median"] * 100 / 1e6, 2) + """M</div></div>
<div class=kpi><div class=lab>TB2 다년 하락</div><div class="val down">−33%</div>
<div class="chg down">▼ $""" + f(lvl["2024"]) + """ → $""" + f(lvl["2026"]) + """ (시스템 전반)</div></div>
<div class=kpi><div class=lab>DART 거래가능 시간</div><div class="val">7<span style="font-size:15px;color:var(--text-muted)"> /24</span></div>
<div class="chg muted">전부 LONG · 노드 고유 엣지 없음</div></div>
</div>

<h2>1. 하절기 Raven vs GKS — 일별 TB2</h2>
<div class=grid2>
<div class=panel><div class=ptitle>일별 TB2 — Raven vs GKS (2026 하절기)</div>
<div class=pnote>$/MWh · 상위 2시간 평균 − 하위 2시간 평균 · 기간종료 CT</div>
<div class=tabs id=tabs1><div class="tab on" onclick="sw('RT',this)">RT</div><div class=tab onclick="sw('DA',this)">DA</div></div>
<div class=chartbox><canvas id=c1></canvas></div></div>
<div class=panel><div class=ptitle>월별 RT TB2 히트맵</div><div class=pnote>$/MWh · proxy 재구성 · 2027은 Base 전망</div>
<div class=hm id=hm></div>
<div style="margin-top:12px;font-size:11px;color:var(--text-muted)">2023년은 9월부터라 제외 (Sep-23 $447 = 스카시티 이상치)</div></div>
</div>

<div class=panel><div class=ptitle>① 연도별 상대 성과 — ERCOT 전체 노드 평균 대비 / GKS 대비</div>
<div class=pnote>Raven은 2026-06 이전 proxy 재구성, 이후 실측(mixed). ERCOT 평균 = 해당일 24시간 완비된 전 price_node의 일별 TB2 횡단면 평균.
GKS는 COD가 2024-07이라 2024는 8월부터. "vs GKS %"는 <b>공통 일자만</b> 사용.</div>
<table><thead><tr><th></th><th>연도</th><th>출처</th><th class=num>Raven TB2</th><th class=num>ERCOT 평균</th>
<th class=num>vs 평균</th><th class=num>vs 중앙값</th><th class=num>GKS TB2</th><th class=num>GKS vs 평균</th><th class=num>Raven vs GKS</th><th class=num>공통일</th></tr></thead>
<tbody>""" + yr_rows + """</tbody></table>
<div class=callout><b>읽어낼 점 3가지</b><br>
① <b>Raven은 매년 ERCOT 노드 평균보다 낮습니다</b> — DA −9.1% → −9.7% → −10.7%, RT −15.4% → −17.2% → −17.7%. 격차가 <b>매년 벌어지고</b> 있습니다.<br>
② <b>GKS는 훨씬 더 낮습니다</b> (DA −35% 내외, RT −26~−31%). 즉 Raven이 "좋은 노드"인 게 아니라 <b>GKS가 나쁜 노드</b>입니다.<br>
③ <b>Raven−GKS 격차는 고정이 아닙니다</b> — DA 기준 2024 +4.2% → 2025 +37.9% → 2026 +37.3%. 2025년에 GKS가 급격히 악화된 결과이며,
따라서 <b>GKS 실적에 배수를 곱해 Raven을 전망하는 방식은 근본적으로 불안정합니다.</b></div>
</div>

<h2>2. Proxy 노드 선정 근거</h2>
<div class=panel><div class=ptitle>② 선정 기준 및 절차</div>
<div class=pnote>RVN_RN은 RT 2026-06-02 / DA 2026-06-04부터만 존재 → 3개년 이력에는 proxy 필요. 겹침 구간 ~102일이 검증 표본.</div>
<div class=steps>
<div class=step><div class=t>전수 스캔 — 전체 1,109개 ERCOT price_node</div>
<div class=d>후보 3개(CBEC_ALL·RBN_BESS1·TAV_RN)에 가두지 않고 전 노드를 평가. 7개 지표: <code>레벨상관 DA/RT</code>, <code>1차차분상관 DA/RT</code>, <code>basis RMSE DA/RT</code>, <code>DA−RT spread 상관</code>. 전기적으로 동일한 버스는 <code>identical_flag</code>로 배제.</div></div>
<div class=step><div class=t>선정 지표는 가격 R²가 아니라 <b>TB2·spread 재현오차</b></div>
<div class=d>실제로 수익화되는 양이 TB2(에너지 차익)와 DA−RT spread(DART)이기 때문. 가격 상관이 높아도 TB2를 못 맞추면 무용.</div>
<div class=formula>선정 규칙 = min [ mean(TB2_DA_MAE, TB2_RT_MAE) + daily_spread_MAE ]</div></div>
<div class=step><div class=t>3개년 이력 보유 노드로 제한</div>
<div class=d>원시 매칭 1위는 <b>WAL_RN</b>(composite rank 2.43)이었으나 <b>2025-05 신설</b>이라 3개년 재구성 불가 → 탈락.
16개월로 충분한 용도라면 WAL_RN이 권장입니다. (WAL_RN은 동시에 Houston 최고 성과 운용자이기도 합니다 — §5 참조.)</div></div>
<div class=step><div class=t>Out-of-sample 검증 — 학습/시험 분리</div>
<div class=d>6/4–7/31 학습 → <b>8/1–9/13 시험(44~45일)</b>. in-sample 성능이 아니라 OOS TB2 재현오차로 최종 선택.</div></div>
<div class=step><div class=t>단일 노드 vs 회귀 blend 비교 후 blend 채택</div>
<div class=d>NNLS(비음수 최소자승) blend가 단일 최적 노드보다 OOS 전 지표에서 우세.</div></div>
</div>
<div class=formula>proxy_LMP = −0.065 + 0.4148 × CBEC_ALL + 0.5407 × RBN_BESS1 + 0.0445 × TAV_RN &nbsp;&nbsp;(DA·RT 동일 가중)
<br>2023-12 이전 (RBN_BESS1 미가격): proxy_LMP = TAV_RN</div>
</div>

<div class=grid11>
<div class=panel><div class=ptitle>후보 스캔 상위 15 (전 1,109 노드 중)</div>
<div class=pnote>겹침 구간 2026-06-04~09-13 · composite_rank 낮을수록 우수 · 파란 행 = 채택 blend 구성원</div>
<table><thead><tr><th>Node</th><th>Zone</th><th class=num>corr DA</th><th class=num>corr RT</th><th class=num>corr spread</th>
<th class=num>RMSE DA</th><th class=num>RMSE spd</th><th class=num>rank</th><th>3년이력</th></tr></thead>
<tbody>""" + scan_rows + """</tbody></table>
<div style="margin-top:10px;font-size:12px;color:var(--text-secondary)">
상위 20개의 <b>85%가 HOUSTON</b>. SOUTH로 분류된 건 Cedar Bayou 계열뿐인데 <b>물리적으로 Houston pocket</b> 안에 있습니다 —
<b>CBEC_ALL이 zone 라벨상 SOUTH라 부적합할 것이라는 초기 우려는 틀렸습니다.</b></div></div>

<div class=panel><div class=ptitle>Out-of-sample 비교 (8/1~9/13)</div>
<div class=pnote>$/MWh · 낮을수록 우수 · 실측 TB2 평균 DA $47.9 / RT $67.1 대비 약 1% 수준 오차</div>
<table><thead><tr><th>후보</th><th class=num>TB2 DA MAE</th><th class=num>TB2 RT MAE</th><th class=num>spread MAE</th>
<th class=num>spread corr</th><th class=num>부호일치</th></tr></thead>
<tbody>""" + oos_rows + """</tbody></table>
<div class=callout style="border-left-color:var(--accent-amber);background:rgba(255,152,0,.06)">
<b>⚠ 한계 2가지</b><br>
① 검증 표본이 <b>하절기 ~100일뿐</b>입니다. 동절기·환절기 재구성은 미검증 (±$2–3 TB2 수준으로 보수적 해석 필요).<br>
② blend의 <b>41%가 CBEC_ALL(SOUTH)</b>이라, 동절기 basis는 Raven의 것이 아닐 수 있습니다. 또한 <b>WHARTN</b> constraint에 대해
CBEC/TAV의 SF는 0.999인데 RBN/WAL은 ~0으로 갈립니다. WHARTN은 2026-06-02를 마지막으로 bind가 끊겨
<b>RVN_RN의 실제 노출을 관측할 수 없고</b>, 여름 fit도 이를 배제하도록 학습할 기회가 없었습니다.</div></div>
</div>

<h2>3. GKS와 Raven의 TB2는 왜 이렇게 다른가</h2>
<div class=panel><div class=ptitle>③ 격차의 구조 — 한 문장: <b>Raven이 높은 게 아니라 GKS가 저녁에 깎입니다</b></div>
<div class=pnote>hub 분해 · 하절기 2026-06~08 · $/MWh</div>

<div class=grid11 style="margin-bottom:0">
<div>
<div class=ptitle style="margin-top:6px">STEP 1 · 방전측이냐 충전측이냐</div>
<table><thead><tr><th>기여</th><th class=num>DA</th><th class=num>RT</th></tr></thead><tbody>
<tr><td>총 격차 (Raven − GKS)</td><td class="num mono b">+14.13</td><td class="num mono b">+9.62</td></tr>
<tr style="background:rgba(8,153,129,.08)"><td><b>방전(top-2) 기여</b></td><td class="num mono b up">+16.36</td><td class="num mono b up">+14.00</td></tr>
<tr><td>충전(bottom-2) 기여</td><td class="num mono down">−2.23</td><td class="num mono down">−4.38</td></tr>
</tbody></table>
<div class=callout><b>방전측이 전부입니다.</b> 충전측은 오히려 Raven에 <b>불리</b>합니다 — GKS의 충전시간 가격이 매월 Raven보다 쌉니다.
즉 "Raven은 충전이 싸서 유리한 노드"라는 가설은 <b>기각</b>됩니다.</div>
</div>
<div>
<div class=ptitle style="margin-top:6px">STEP 2 · 그 방전측 격차는 어디서 오는가</div>
<table><thead><tr><th>원인</th><th class=num>DA 기여</th><th class=num>비중</th></tr></thead><tbody>
<tr style="background:rgba(242,54,69,.07)"><td><b>GKS의 저녁 congestion 할인</b><div class=sub>GKS − HB_SOUTH basis 붕괴</div></td>
<td class="num mono b">−12.43</td><td class="num mono b down">88%</td></tr>
<tr><td>HOU − SOUTH 존 갭<div class=sub>Houston 프리미엄</div></td><td class="num mono">+1.24</td><td class="num mono">9~16%</td></tr>
<tr><td>Raven 자체 basis<div class=sub>RVN − HB_HOUSTON</div></td><td class="num mono">+0.46</td><td class="num mono">0~3%</td></tr>
</tbody></table>
<div class=callout style="border-left-color:var(--accent-down);background:rgba(242,54,69,.05)">
Houston 프리미엄은 <b>한낮(태양광 시간대, 약 +$10)</b>에 몰려 있는데 그 시간엔 <b>양쪽 다 충전</b>하므로 TB2를 거의 못 움직입니다.
그래서 존 갭의 기여가 9~16%에 그칩니다.</div>
</div>
</div>

<div class=ptitle style="margin-top:18px">STEP 3 · 시간대별 basis — GKS는 저녁에 무너지고 Raven은 평평합니다</div>
<div class=pnote>$/MWh · GKS는 HB_SOUTH 대비(DA), Raven은 HB_HOUSTON 대비(RT)</div>
<div class=chartbox style="height:250px"><canvas id=c3></canvas></div>
<table style="margin-top:12px"><thead><tr><th>HE</th><th class=num>18</th><th class=num>19</th><th class=num>20</th><th class=num>21</th><th class=num>22</th><th class=num>23</th></tr></thead>
<tbody><tr><td><b>GKS − HB_SOUTH (DA)</b></td><td class="num mono">−1.3</td><td class="num mono down">−7.0</td>
<td class="num mono down b">−15.1</td><td class="num mono down b">−15.3</td><td class="num mono down">−10.3</td><td class="num mono down">−5.4</td></tr></tbody></table>

<div class=callout><b>결과 — GKS는 시스템 피크를 포기합니다.</b>
저녁 basis가 −$15까지 무너지면서 GKS의 top-2 방전시간이 <b>HE22–23으로 밀려납니다</b>(전체 일수의 46%, Raven은 18%).
피크 시간대(HE20–21)에 팔지 못하고 가격이 이미 내려간 늦은 밤에 파는 구조입니다. SOUTH/Valley <b>export constraint</b> 시그니처이며,
기존 GKS 노드 분석과 일치합니다.</div>

<div class=callout style="border-left-color:var(--accent-amber);background:rgba(255,152,0,.06)">
<b>전망에 직결되는 함의</b> — 이 격차는 <b>Houston의 구조적 우위가 아니라 GKS 고유의 결함</b>입니다.
따라서 ⑴ "GKS × 1.56"으로 Raven을 전망하면 과대추정이고, ⑵ 연도별로 보면 이 배수가 +4%→+38%로 요동쳤으므로(§1) 배수 방식 자체가 불안정하며,
⑶ 올바른 앵커는 <b>Raven ≈ HB_HOUSTON TB2</b>입니다. 단 <b>ERCOT 전 노드 평균 대비로는 −10%~−18%</b>라는 점도 함께 기억해야 합니다.</div>
</div>

<h2>4. FY2027 매출 전망 — 로직과 시뮬레이터</h2>
<div class=panel><div class=ptitle>④ 추정 로직 5단계</div>
<div class=pnote>3개년 중앙값을 쓰지 않은 이유: TB2가 명확한 하락 추세이고 중앙값은 이를 과대추정하기 때문</div>
<div class=steps>
<div class=step><div class=t>연도 LEVEL 산출 — proxy 재구성 RVN RT TB2의 Jan–Sep 평균</div>
<div class=d>연도간 비교를 같은 달로 맞추기 위해 Jan–Sep으로 고정 (2026은 9/13까지만 존재).
관측: <code>2024 $""" + f(lvl["2024"]) + """ → 2025 $""" + f(lvl["2025"]) + """ → 2026 $""" + f(lvl["2026"]) + """</code>
= <b>−33%</b>. YoY 비율 <code>0.765</code>, <code>0.875</code>.</div></div>
<div class=step><div class=t>하락이 노드 문제가 아님을 확인</div>
<div class=d>HB_HOUSTON도 <code>$83.1 → $65.5 → $56.2</code>로 동일 기울기. 즉 <b>ERCOT 저장장치 유입에 의한 spread 압축</b>이며
Raven 고유 악재가 아닙니다. → 전망은 시장 전체 추세로 외삽해야 합니다.</div></div>
<div class=step><div class=t>2027 LEVEL = 2026 × 감쇠계수 (Base 0.90)</div>
<div class=d>하락은 계속되나 <b>둔화</b>한다고 가정 (−23.5% → −12.5% → −10%). <b>이 계수가 전망의 지배적 변수</b>이며 아래 슬라이더로 조정 가능합니다.</div></div>
<div class=step><div class=t>계절 SHAPE — 월별 TB2 ÷ 해당연도 Jan–Sep 평균, 연도간 중앙값</div>
<div class=d>레벨과 계절성을 분리해, 레벨 가정만 바꿔도 계절 패턴은 유지되도록 구성. 5월·4월이 최고(1.53·1.47), 12월·7월이 최저(0.53·0.63).</div></div>
<div class=step><div class=t>TB index → 매출</div>
<div class=d>2h 자산은 하루 2 MWh/MW를 순환하므로 <code>TB index = Σ_월 [ 2 × TB2_월 × 일수 ]</code>.
여기에 <b>Houston 2h 피어의 실측 capture rate</b>를 곱합니다. 피어 opt_rate도 동일 기준(왕복효율 미반영)으로 계산돼 비율이 정합적입니다.</div></div>
</div>
<div class=formula>매출 ($/MW-yr) = Σ<sub>월</sub> [ 2 MWh/MW/일 × (LEVEL<sub>2026</sub> × 감쇠 × SHAPE<sub>월</sub>) × 일수<sub>월</sub> ] × capture율</div>

<div class=sim><div class=ptitle style="color:var(--accent-blue)">⚙ 인터랙티브 시뮬레이터 — 직접 조정해 보세요</div>
<div class=pnote>capture율과 2027 하락률을 바꾸면 매출이 즉시 갱신됩니다</div>
<div class=slider-row><label>Capture율 (실적 ÷ TB index)</label>
<div><input type=range id=sCap min=15 max=100 step=0.5 value=""" + str(cap["base_median"]) + """>
<div class=marks><span class=mark onclick="setCap(""" + str(cap["low_p25"]) + """)">피어 p25 """ + f(cap["low_p25"]) + """%</span>
<span class=mark onclick="setCap(""" + str(cap["base_median"]) + """)">피어 중앙값 """ + f(cap["base_median"]) + """%</span>
<span class=mark onclick="setCap(""" + str(cap["high_p75"]) + """)">피어 p75 """ + f(cap["high_p75"]) + """%</span>
<span class=mark onclick="setCap(85.5)">WAL_RN 최고 85.5%</span>
<span class=mark onclick="setCap(43.7)">GKS 실적 43.7%</span></div></div>
<div class=rv id=vCap></div></div>
<div class=slider-row><label>2027 TB2 수준 (2026 대비)</label>
<div><input type=range id=sDec min=50 max=130 step=1 value=90>
<div class=marks><span class=mark onclick="setDec(76)">'25 하락률 재현 76%</span>
<span class=mark onclick="setDec(88)">'26 하락률 재현 88%</span>
<span class=mark onclick="setDec(90)">Base 90%</span>
<span class=mark onclick="setDec(100)">횡보 100%</span>
<span class=mark onclick="setDec(115)">반등 115%</span></div></div>
<div class=rv id=vDec></div></div>
<div class=simout>
<div class=simcell><div class=l>2027 TB2 수준</div><div class=v id=oLvl></div><div class=s>$/MWh (Jan–Sep 평균 기준)</div></div>
<div class=simcell><div class=l>TB index</div><div class=v id=oTbi></div><div class=s>$/MW-yr 이론최대</div></div>
<div class=simcell><div class=l>매출 (에너지+AS)</div><div class=v id=oRev></div><div class=s id=oDelta></div></div>
<div class=simcell><div class=l>100MW 합계</div><div class=v id=oTot></div><div class=s>연간</div></div>
</div>
<div class=chartbox style="height:220px;margin-top:16px"><canvas id=cf></canvas></div>
<div style="font-size:11.5px;color:var(--text-muted);margin-top:8px">
DART virtual은 이 수치에 <b>포함되지 않습니다</b> (노드 고유 엣지 미확인). 왕복효율·deviation penalty 미반영 —
피어 capture율이 동일 기준으로 측정되어 상쇄됩니다.</div>
</div></div>

<h2>5. 상품 조합 — 에너지 vs 보조, 그리고 피어 벤치마크</h2>
<div class=panel><div class=ptitle>Houston zone BESS 실제 상품조합 — 2026-01-01 ~ 05-25</div>
<div class=pnote>ERCOT 60일 공시 실측 · 파란 행 = 2h·50MW+ (Raven 직접 비교군) · capacity는 SCED 실측 HSL 기준 ·
<b>하절기는 공시 미발행(D+60)이라 미포함</b></div>
<table><thead><tr><th>Resource</th><th>Node</th><th class=num>MW</th><th class=num>Dur(h)</th><th class=num>$/MW</th><th class=num>Opt%</th><th class=num>AS 비중</th></tr></thead>
<tbody>""" + peer_rows + """</tbody></table>
<div class=callout><b>상위 4개가 전부 AS 비중 37–39%입니다.</b> 순수 에너지 플레이가 이기는 게 아니라
<b>에너지 중심 + AS 40% 내외 혼합</b>이 Houston 2h의 승리 조합입니다 (AS 0–16%인 BYP/BCNV/EVLN은 하위권).
반면 <b>GKS는 AS 45.7%로 가장 높은데 opt는 43.7%로 하위권</b> — §3의 저녁 congestion 할인 탓에 에너지 방전 기회가 눌려 AS로 밀려난 구조이며,
<b>Raven에는 이 제약이 없습니다.</b></div></div>

<div class=grid11>
<div class=panel><div class=ptitle>에너지 vs AS — 레짐별 (하절기 RT)</div>
<div class=pnote>$/MW-day · energy2h = 2h 차익거래 · AS 4h = 사이클 시간 파킹 · AS 24h = 종일 파킹</div>
<table><thead><tr><th>Tightness</th><th>Congestion</th><th class=num>일수</th><th class=num>TB2</th><th class=num>에너지2h</th><th class=num>AS 4h</th><th class=num>AS 24h</th><th class=num>배율</th><th>우위</th></tr></thead>
<tbody>""" + reg_rows + """</tbody></table>
<div class=callout>① <b>사이클 4시간을 AS에 내주는 건 어느 레짐에서도 열위</b>(에너지가 4.5~11.2배).
② 단 <b>TIGHT + congestion POSITIVE(12일)에서만 종일 AS 파킹이 근소 우위</b>(188 vs 185 $/MW-day) — AS 비중을 높일 유일한 근거 구간.
※ 실제 운용은 양자택일이 아니라 <b>사이클 4시간 에너지 + 나머지 20시간 AS</b>가 정답이며, 위 표는 상한 가늠용입니다.</div></div>
<div class=panel><div class=ptitle>시간대별 방전마진 vs AS 기회비용 (하절기 RT)</div>
<div class=pnote>$/MWh · 방전마진 = 해당시간 RT − 당일 최저2시간/효율 · AS는 최선 상향상품</div>
<div class=chartbox style="height:280px"><canvas id=c2></canvas></div>
<div style="margin-top:8px;font-size:12px;color:var(--text-secondary)">
<b>HE20–21은 방전이 AS를 이길 확률 100%</b>. HE9–11은 반대로 충전 시간대(방전마진 음수, 0.10~0.22).</div></div>
</div>

<h2>6. Congestion — Top 10</h2>
<div class=panel><div class=ptitle>⑤ Raven 위치 영향 Top-10 (3개년, proxy 기준)</div>
<div class=pnote>누적 MCC $/MWh-h per MW · 부호 = Raven LMP에 미치는 방향 · <b>driver / shift factor 상세는 아래 섹션</b></div>
<table><thead><tr><th>#</th><th>Constraint</th><th>Raven 영향</th><th class=num>누적 DA</th><th class=num>누적 RT</th>
<th>DA 주요시간</th><th>RT 주요시간</th><th class=num>RT λ평균</th><th>Binding 월</th><th>Forward</th></tr></thead>
<tbody>""" + cong_rows + """</tbody></table>
<div class=callout>구조적 패턴: <b>DA congestion은 매년 순(+), RT는 매년 순(−)</b> → short-DA / long-RT 편향.
10개 중 9개가 금액 기준 DART-short 방향이며, RVN 실측 첫 100일도 동일(DA +3.0k, RT −1.0k).</div></div>

<div class=panel><div class=ptitle>⑤ Constraint별 main driver · shift factor · binding 시간대</div>
<div class=pnote>driver는 binding 여부에 대한 AUC 상위 1위 · threshold는 해당 driver 최하위→최상위 decile의 bind 확률 변화 ·
SF는 DA 기준 (RVN 실측은 2026-06 이후 관측분) · binding 시간대는 DA peak band</div>
""" + (PENDING if not drivers else """
<table><thead><tr><th>#</th><th>Constraint</th><th>Main driver</th><th>Threshold</th>
<th class=num>SF RVN<div class=sub>실측</div></th><th class=num>SF proxy</th><th class=num>SF GKS</th>
<th>DA binding</th><th>Forward</th></tr></thead><tbody>""" + drv_rows + """</tbody></table>
<div class=callout><b>driver 패턴이 명확히 갈립니다.</b><br>
· <b>태양광 구동</b> — STPWAP39_1(SE solar &gt;2.4GW, AUC 0.79), 35055__A(ERCOT solar &gt;25GW, AUC 0.85) → <b>한낮~오후</b> binding<br>
· <b>풍력 구동</b> — 587__A(ERCOT wind &gt;23GW, AUC 0.85), 630__B(West wind &gt;14.2GW, AUC 0.73) → <b>야간</b> binding<br>
· <b>부하 구동</b> — E_PASP(ERCOT load &gt;74GW, AUC 0.78) → <b>HE18–22 저녁 피크</b>, 45%로 가장 빈번<br>
· <b>기상 이벤트</b> — 50__A(net load &gt;44.8GW + DFW &lt;33°F) → 겨울 폭풍 시에만</div>
<div class=callout style="border-left-color:var(--accent-amber);background:rgba(255,152,0,.06)">
<b>⚠ proxy SF 오차 — 전망에 보정이 필요합니다.</b><br>
· <b>STP-WAP</b>: proxy SF가 실제보다 <b>50% 과대</b> (proxy −0.031 vs 실측 −0.021)<br>
· <b>35055__A</b>: proxy가 <b>25% 과소</b> (0.095 vs 0.128)<br>
· <b>E_PASP</b>: GKS SF(+0.241)가 Raven(+0.030)의 <b>7.9배</b> — 같은 constraint가 두 자산에 전혀 다르게 작용<br>
· WHARTN / 1710__C / STPELM27_1 / 50__A는 <b>RVN에 가격이 붙은 뒤 한 번도 bind하지 않아 실측 SF가 없습니다</b></div>""") + """
</div>

<h2>7. DART Virtual</h2>
<div class=grid11>
<div class=panel><div class=ptitle>시간대별 기본 분석 — RVN_RN</div>
<div class=pnote>2026-06-04~09-13 (102일) · 우세 방향 기준 · 초록 = 거래가능 판정</div>
<table><thead><tr><th>HE</th><th>방향</th><th class=num>승률</th><th class=num>P/L</th><th class=num>EV $/MWh</th><th class=num>손실 p99</th><th class=num>t</th><th>판정</th></tr></thead>
<tbody>""" + dart_rows + """</tbody></table></div>
<div class=panel><div class=ptitle>⑥ 시황·congestion 조건부 고도화</div>
""" + (PENDING if not dart6 else d6_html) + """</div>
</div>

<h2>8. GKS ↔ Raven Basis Trade (상품 확장)</h2>
<div class=panel><div class=ptitle>⑦ SF 부호가 반대인 constraint를 이용한 Houston−South basis 거래</div>
""" + (PENDING if not basis else d7_html) + """</div>

<div class=cv><div class=ptitle style="color:#b26a00">한계 및 유의사항</div><ul>
<li><b>피어 하절기 공시 미포함</b> — ERCOT 60일 공시는 D+60 발행이라 오늘(9/14) 기준 ~7/15까지만 존재. 피어 capture rate는 <b>1~5월(동절기·봄)</b> 실측이며, 가장 타이트했던 8월 피어 행동은 빠져 있음.</li>
<li><b>2027 하락률 가정이 전망의 최대 변수</b> — §4 시뮬레이터로 직접 확인 가능.</li>
<li><b>Proxy는 하절기 ~100일로만 검증</b> — 동절기·환절기 미검증 (±$2–3 TB2). blend의 41%가 SOUTH zone.</li>
<li><b>WHARTN</b>은 3개년 누적 1위 constraint이나 Raven 노출을 <b>검증할 수 없음</b> (마지막 bind가 RVN 가격 개시 직전).</li>
<li><b>Raven은 congestion 프리미엄 노드가 아님</b> — ERCOT 전 노드 평균 대비 DA −10.7% / RT −17.7%.</li>
<li>scarcity tail 미모델링 — 2026 여름은 RT &gt;$500가 전 노드 통틀어 1시간뿐인 이례적으로 조용한 해였음.</li>
<li>신규 저장장치 유입 · AS 가격 감쇠 · RTC+B 효과는 추세에 암묵 반영만.</li>
<li>Raven 실제 제원·COD 미확인 — GKS 동일(100MW/200MWh) 가정.</li>
</ul></div>

</div><script>""" + DATA_JS + JS + """</script></body></html>"""

out = ROOT / "reports/ad-hoc/2026-09-14_Raven_RVN_RN_FY2027_outlook.html"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(HTML, encoding="utf-8")
print("wrote", out, "(", format(len(HTML), ","), "bytes )")
print("sections pending:", {"drivers": drivers is None, "dart6": dart6 is None, "basis": basis is None})
