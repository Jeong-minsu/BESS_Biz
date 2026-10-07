"""Render the Raven FY2027 dashboard — EXECUTIVE edition.

Same data as rev_render_html.py, restructured for a CEO briefing:
  - answer-first: every section opens with the conclusion in plain Korean
  - no analyst jargon (basis / leg / Sharpe / TB2 / shift factor ... all spelled out)
  - glossary at the end
  - interactive revenue simulator retained
Real data only; missing values render as em-dash.
"""
import json
from pathlib import Path
import pandas as pd, numpy as np

BASE = Path(__file__).resolve().parents[1]; D = BASE / "derived"
ROOT = Path(__file__).resolve().parents[5]
P = json.load(open(D / "draft_dashboard_payload.json"))
fc = P["forecast"]


def jload(n):
    p = D / n
    return json.load(open(p, encoding="utf-8")) if p.exists() else None


def csvload(n):
    p = D / n
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
    return format(float(x), "+,." + str(d) + "f") + "%"


yr = jload("rev_item1_yearly_relative.json")
proxy = jload("item2_proxy_definition.json")
scan = csvload("item2_proxy_scan_all.csv")
drivers = jload("item7_congestion_drivers.json")
basis = jload("item7_basis_trade.json")
dart6 = jload("item6_dashboard.json")
zcap = jload("zone_capacity.json")
zload = jload("zone_load.json")
zprice = jload("zone_price.json")
q3 = jload("q3_supply_demand.json")
q3r = jload("q3_robustness.json")
q2 = jload("q2_dart_spread_levels.json")

# ------------------------------------------------------------------ Houston zone overview
ZKO = {"COAST": "Houston (연안)", "NORTH_CENTRAL": "북중부 (DFW)", "SOUTH_CENTRAL": "남중부 (Austin·SA)",
       "SOUTH": "남부 (GKS)", "FAR_WEST": "극서부 (Permian)", "WEST": "서부", "EAST": "동부", "NORTH": "북부",
       "ERCOT": "ERCOT 전체"}
zone_rows = ""
if zcap and zload:
    comp = {r["zone"]: r for r in zcap["zone_comparison"]}
    for z in ["COAST", "SOUTH", "NORTH_CENTRAL", "SOUTH_CENTRAL", "FAR_WEST", "WEST"]:
        r = comp.get(z, {})
        hl = ' class=hl' if z == "COAST" else ''
        zone_rows += (
            '<tr' + hl + '><td><b>' + ZKO[z] + '</b></td>'
            '<td class="num mono">' + f(zload["avg_jan_aug_mw"][z]["2026"] / 1000, 1) + '</td>'
            '<td class="num mono ' + ("b" if z == "COAST" else "") + '">' + pct(zload["cagr_2023_2026_pct"][z]) + '</td>'
            '<td class="num mono">' + f(r.get("share_Gas"), 0) + '%</td>'
            '<td class="num mono">' + f(r.get("share_Solar"), 0) + '%</td>'
            '<td class="num mono">' + f(r.get("share_Wind"), 0) + '%</td>'
            '<td class="num mono">' + f(r.get("share_ESS"), 0) + '%</td>'
            '<td class="num mono ' + ("b up" if z == "COAST" else "") + '">+' + f((r.get("add_ESS_2023_2026") or 0) / 1000, 1) + '</td>'
            '<td class="num mono ' + ("b" if z == "COAST" else "") + '">+' + f((r.get("planned_2027_ess") or 0) / 1000, 1) + '</td></tr>')

hub_rows = ""
if zprice:
    HKO = {"HB_HOUSTON": "Houston", "HB_SOUTH": "남부", "HB_NORTH": "북부", "HB_WEST": "서부", "HB_PAN": "Panhandle"}
    for h in ["HB_HOUSTON", "HB_SOUTH", "HB_NORTH", "HB_WEST", "HB_PAN"]:
        r = [x for x in zprice["by_hub_year"] if x["hub"] == h and x["year"] == 2026]
        if not r:
            continue
        r = r[0]
        hl = ' class=hl' if h == "HB_HOUSTON" else ''
        hub_rows += (
            '<tr' + hl + '><td><b>' + HKO[h] + '</b></td>'
            '<td class="num mono ' + ("up" if r["premium_midday_HE10_15"] > 0 else "down") + '">' + format(r["premium_midday_HE10_15"], "+.1f") + '</td>'
            '<td class="num mono ' + ("up" if r["premium_evening_HE18_22"] > 0 else "down") + '">' + format(r["premium_evening_HE18_22"], "+.1f") + '</td>'
            '<td class="num mono b">' + f(r["rt_tb2"], 1) + '</td>'
            '<td class="num mono">' + f(r["hours_rt_lt_0"], 0) + '</td>'
            '<td class="num mono">' + f(r["hours_rt_gt_500"], 0) + '</td></tr>')

# ------------------------------------------------------------------ Q3 supply-demand upside check
lfl_rows = ""
BANDKO = {"(0, 45]": "45GW 이하 (여유)", "(45, 50]": "45~50GW", "(50, 55]": "50~55GW",
          "(55, 60]": "55~60GW", "(60, 65]": "60~65GW (타이트)", "(65, 100]": "65GW 초과 (매우 타이트)"}
if q3:
    lf = q3["like_for_like_tb2_median_by_band"]; dc = q3["days_per_cell"]
    for band, vals in lf.items():
        tight = band in ("(60, 65]", "(65, 100]")
        v24, v26 = vals.get("2024"), vals.get("2026")
        chg = (100 * (v26 / v24 - 1)) if (v24 and v26) else None
        lfl_rows += (
            '<tr' + (' style="background:rgba(242,54,69,.06)"' if tight else '') + '><td><b>' + BANDKO.get(band, band) + '</b></td>'
            '<td class="num mono">' + f(vals.get("2024"), 0) + '<div class=sub>' + str(dc[band].get("2024", 0)) + '일</div></td>'
            '<td class="num mono">' + f(vals.get("2025"), 0) + '<div class=sub>' + str(dc[band].get("2025", 0)) + '일</div></td>'
            '<td class="num mono">' + f(vals.get("2026"), 0) + '<div class=sub>' + str(dc[band].get("2026", 0)) + '일</div></td>'
            '<td class="num mono ' + ("b down" if tight else "") + '">' + pct(chg, 0) + '</td></tr>')

TB_IDX_100 = fc["tb_index_sensitivity"]["0% decline"]          # TB index at 2026 level (100%)
def rev_at(level_pct, capv=None):
    capv = fc["peer_capture_pct"]["base_median"] if capv is None else capv
    return TB_IDX_100 * level_pct / 100 * capv / 100 * 100 / 1e6   # $M for 100 MW

sc_rows = ""
SCKO = [("Downside", "하방", "배터리 계획 물량 전부 준공 · 수요 둔화", "2027 신규 배터리 9.6GW · 피크 순수요 +1GW"),
        ("Base", "기준", "통상적 준공 지연 · 추세 수요 성장", "2027 신규 배터리 6.5GW · 피크 순수요 +2.5GW"),
        ("Upside", "상방 (요청 가정)", "배터리 준공 대거 지연 + AI 데이터센터 수요 유입", "2027 신규 배터리 3.5GW · 피크 순수요 +5GW")]
if q3r:
    lin, lg = q3r["linear ESS"]["scenarios"], q3r["log ESS"]["scenarios"]
    for key, ko, story, inputs in SCKO:
        lo, hi = sorted([lin[key], lg[key]])
        cls = "up" if key == "Upside" else ("down" if key == "Downside" else "")
        sc_rows += (
            '<tr' + (' style="background:rgba(8,153,129,.07)"' if key == "Upside" else '') + '><td><b>' + ko + '</b><div class=sub>' + story + '</div></td>'
            '<td class=sub style="font-size:11.5px">' + inputs + '</td>'
            '<td class="num mono ' + cls + '">' + f(lo, 0) + '~' + f(hi, 0) + '%</td>'
            '<td class="num mono b ' + cls + '">$' + f(rev_at(lo), 2) + '~' + f(rev_at(hi), 2) + 'M</td></tr>')

dd = pd.read_csv(D / "item1_daily_tb2.csv")


def series(node, mkt):
    s = dd[(dd.node == node) & (dd.market == mkt)].sort_values("flowday")
    return s.flowday.tolist(), [round(float(x), 2) for x in s.tb2]


days_da, rvn_da = series("RVN_RN", "DA"); _, gks_da = series("GKS_BESS_RN", "DA")
days_rt, rvn_rt = series("RVN_RN", "RT"); _, gks_rt = series("GKS_BESS_RN", "RT")

mo = P["monthly_tb2_by_year"]
base27 = [fc["base_2027_monthly_tb2"][str(m)] for m in range(1, 13)]
MONTHS = ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"]
DAYSM = [31,28,31,30,31,30,31,31,30,31,30,31]

dh = pd.DataFrame(P["dart_hourly"])
peers = pd.DataFrame(P["peers"])
peers2h = peers[(peers.duration_hours >= 1.85) & (peers.duration_hours <= 2.25) & (peers.cap_mw >= 50)]
xo = pd.DataFrame(P["crossover"]); rg = pd.DataFrame(P["regime"])
st = P["item1"]["tb2_stats"]
rv = fc["revenue_usd_per_mw_yr"]; cap = fc["peer_capture_pct"]
lvl = fc["observed_annual_level_jan_sep_tb2"]
shape = [fc["seasonal_shape"][str(m)] for m in range(1, 13)]

gks_basis_he = [-1.5,-1.0,-0.8,-0.6,-0.4,-0.4,-0.2,0.0,-0.1,-0.4,-0.5,-0.4,
                -0.2,0.0,0.2,0.4,-0.2,-1.3,-7.0,-15.1,-15.3,-10.3,-5.4,-2.3]

# ------------------------------------------------------------------ DART 3-year (proxy) + forecast tightness
d3 = jload("dart3y_results.json")
d3r = json.load(open(D / "dart3y_robustness.json", encoding="utf-8")) if (D / "dart3y_robustness.json").exists() else None
SIDEKO = {"short": ("SHORT", "sh"), "long": ("LONG", "lg")}

d3_rows = ""
if d3:
    for r in d3["A_hourly_3y"]:
        side = r["best"]; lab, cls = SIDEKO[side]
        s = r[side]
        c, k = map(int, r["consistent_years"].split("/"))
        strong = abs(r["t"]) >= 2 and c == k and (r["mean_wins"] > 0) == (r["mean_spread"] > 0)
        tail = s["worst1pct_loss"] > 20 * max(r["ev_best"], 0.01)
        badge = ('<span class="pill up">유력</span>' if strong and not tail else
                 '<span class="pill amber">유력·손실위험</span>' if strong else
                 '<span class="pill down">급등 의존</span>' if (r["mean_wins"] > 0) != (r["mean_spread"] > 0) or abs(r["mean_wins"]) < 0.3 * abs(r["mean_spread"]) else
                 '<span class="pill muted">근거 약함</span>')
        yrs = "".join('<span class="yb ' + ("sh" if (v or 0) > 0 else "lg") + '">' + str(y)[2:] + '</span>'
                      if v is not None else '<span class="yb">—</span>' for y, v in r["years"].items())
        d3_rows += (
            '<tr class="' + ("ok" if strong and not tail else "") + '"><td class=mono>' + str(r["he"]) + '시</td>'
            '<td><span class="pill ' + cls + '">' + lab + '</span></td>'
            '<td class="num mono">' + format(r["mean_spread"], "+.2f") + '</td>'
            '<td class="num mono">' + f(s["p_win"] * 100, 0) + '%</td>'
            '<td class="num mono">' + f(s["pl_ratio"], 2) + '</td>'
            '<td class="num mono ' + ("down" if tail else "") + '">' + f(s["worst1pct_loss"], 0) + '</td>'
            '<td class="num mono">' + format(r["mean_wins"], "+.2f") + '</td>'
            '<td>' + yrs + '</td><td>' + badge + '</td></tr>')


def heat_grid(rows, rowkey, order, title_fn=lambda x: x):
    """Season/tightness x hour heat grid. + (SHORT) = blue, - (LONG) = orange. * = |t|>=2 and same sign every year."""
    vals = [abs(r["mean"]) for r in rows]
    vmax = max(4.0, np.percentile(vals, 90)) if vals else 4.0
    html = '<div class=hg><div class=hh></div>' + "".join('<div class=hh>' + str(hh) + '</div>' for hh in range(1, 25))
    for key in order:
        html += '<div class=hr>' + title_fn(key) + '</div>'
        for hh in range(1, 25):
            r = next((x for x in rows if x[rowkey] == key and x["he"] == hh), None)
            if r is None:
                html += '<div>—</div>'; continue
            a = min(1.0, abs(r["mean"]) / vmax)
            bg = ("rgba(41,98,255," if r["mean"] > 0 else "rgba(255,152,0,") + format(0.08 + 0.72 * a, ".2f") + ")"
            star = r["consistent"] == r["n_years"] and r["n_years"] >= 2 and abs(r["t"]) >= 2
            tip = (title_fn(key) + " " + str(hh) + "시 · 평균 " + format(r["mean"], "+.1f") + " $/MWh · t " + format(r["t"], "+.1f")
                   + " · " + str(r["consistent"]) + "/" + str(r["n_years"]) + "년 같은 방향")
            html += ('<div title="' + tip + '" style="background:' + bg + ';color:' + ("#fff" if a > 0.55 else "#131722")
                     + ';' + ("outline:2px solid #131722;outline-offset:-2px;font-weight:700" if star else "") + '">'
                     + format(r["mean"], "+.0f") + '</div>')
    return html + '</div>'


hg_season = heat_grid(d3["B_season_he"], "season", ["겨울", "봄", "여름", "가을"]) if d3 else ""
hg_tight = heat_grid(d3["C_tight_he"], "tight", ["여유", "보통", "타이트"], lambda x: "예측 " + x) if d3 else ""

d3_block_rows = ""
if d3:
    BL = ["새벽 1–6시", "아침 7–11시", "낮 12–16시", "저녁 17–21시", "밤 22–24시"]
    for s_ in ["겨울", "봄", "여름", "가을"]:
        for tg in ["여유", "보통", "타이트"]:
            cells = ""
            for b in BL:
                r = next((x for x in d3["D_season_tight_block"] if x["season"] == s_ and x["tight"] == tg and x["block"] == b), None)
                if r is None:
                    cells += '<td class="num mono muted">—</td>'; continue
                star = abs(r["t"]) >= 2 and r["consistent"] == r["n_years"] and r["n_years"] >= 2
                cls = ("sh" if r["mean"] > 0 else "lg") if star else "muted"
                cells += ('<td class="num mono"><span class="' + ("pill " + cls if star else "muted") + '">'
                          + ("SHORT " if star and r["mean"] > 0 else "LONG " if star else "")
                          + format(r["mean"], "+.1f") + '</span></td>')
            d3_block_rows += '<tr><td><b>' + s_ + '</b> · ' + tg + '</td>' + cells + '</tr>'

oos_rows_d3 = ""
if d3 and d3r:
    VERD = {"① 시간대만 (24칸)": ("up", "보통", "수익의 84%가 1월 한파 이틀"),
            "② 계절 × 시간대 (96칸)": ("up", "양호", "급등일 제외해도 흑자 유지"),
            "③ 타이트함 × 시간대 (72칸)": ("up", "최선", "실측 가격 검증 최고"),
            "④ 계절 × 타이트함 × 구간 (60칸)": ("down", "기각", "1월 외 흑자월 2개 · 과적합")}
    NAMES = {"① 시간대만 (24칸)": "① 시간대만", "② 계절 × 시간대 (96칸)": "② 계절 × 시간대",
             "③ 타이트함 × 시간대 (72칸)": "③ 예측 타이트함 × 시간대", "④ 계절 × 타이트함 × 구간 (60칸)": "④ 계절 × 타이트함 × 시간구간"}
    for fam, e in d3["E_oos"].items():
        rb = d3r[fam]; te = e["test"]; rc = rb["real_check_jun_sep"]
        vc, vl, vn = VERD[fam]
        oos_rows_d3 += (
            '<tr class="' + ("hl" if vl == "최선" else "") + '"><td><b>' + NAMES[fam] + '</b><div class=sub>' + str(e["tested"]) + '칸 중 ' + str(e["selected"]) + '칸 선택</div></td>'
            '<td class="num mono">' + format(float(e["train"]["ev_per_mwh"]), "+.2f") + '</td>'
            '<td class="num mono b">' + format(float(te["ev_per_mwh"]), "+.2f") + '</td>'
            '<td class="num mono">' + f(float(te["hit_rate"]) * 100, 0) + '%</td>'
            '<td class="num mono b">$' + format(rb["total"], ",.0f") + '</td>'
            '<td class="num mono">$' + format(rb["total_ex_best3_worst3"], ",.0f") + '</td>'
            '<td class="num mono">' + rb["months_positive"] + '</td>'
            '<td class="num mono down">$' + format(rb["max_drawdown"], ",.0f") + '</td>'
            '<td class="num mono ' + ("up" if (rc["real_ev"] or 0) > 0 else "down") + '">' + format(rc["real_ev"], "+.2f")
            + '<div class=sub>적중 ' + f(rc["real_hit"] * 100, 0) + '%</div></td>'
            '<td><span class="pill ' + vc + '">' + vl + '</span><div class=sub>' + vn + '</div></td></tr>')

# ------------------------------------------------------------------ Houston top-3 peers: table + hourly stack
pstack = jload("peer_hourly_stack.json")
top3_rows = ""
_pk = pd.DataFrame(P["peers"])
_sites = [("WAL", "Tesla", ["WAL_ESR1"]), ("CLO", "Jupiter Power", ["CLO_ESR1", "CLO_ESR2"]), ("LON", "Tokyo Gas America", ["LON_ESR1"])]
for i, (site, comp, units) in enumerate(_sites, 1):
    u = _pk[_pk.resource_name.isin(units)]
    if u.empty:
        continue
    capmw = float(u.cap_mw.sum()); rev = float(u.total_rev.sum())
    revmw = rev / capmw
    opt = float((u.opt_rate_pct * u.total_rev).sum() / rev)
    asr = float((u.as_share_pct * u.total_rev).sum() / rev)
    top3_rows += (
        '<tr><td class=mono>' + str(i) + '</td><td><b>' + site + '</b><div class=sub>' + comp + (' · 2기 합산' if len(units) > 1 else '') + '</div></td>'
        '<td class="num mono">' + f(capmw, 0) + '</td><td class="num mono b">$' + f(revmw, 0) + '</td>'
        '<td class="num mono">' + f(opt, 1) + '%</td><td class="num mono">' + f(asr, 1) + '%</td></tr>')
_ps = (pstack or {}).get("summary", {})

# ------------------------------------------------------------------ tables
yr_rows = ""
if yr:
    for mkt, lab in [("DA", "전일시장"), ("RT", "실시간시장")]:
        rows = [r for r in yr[mkt] if r["year"] >= 2024]
        for i, r in enumerate(rows):
            note = "~9/13" if r["year"] == 2026 else ""
            yr_rows += (
                '<tr>' + ('<td rowspan=3 class=mkt>' + lab + '</td>' if i == 0 else '') +
                '<td class=mono>' + str(r["year"]) + (('<div class=sub>' + note + '</div>') if note else '') + '</td>'
                '<td class="num mono b">' + f(r["raven"]) + '</td>'
                '<td class="num mono">' + f(r["sys_mean"]) + '</td>'
                '<td class="num mono down b">' + pct(r["vs_sys_mean_pct"]) + '</td>'
                '<td class="num mono">' + f(r["gks"]) + '</td>'
                '<td class="num mono down">' + pct(r["gks_vs_sys_mean_pct"]) + '</td>'
                '<td class="num mono up b">' + pct(r["vs_gks_pct"]) + '</td></tr>')

peer_rows = ""
for _, r in peers.head(12).iterrows():
    is2h = 1.85 <= r.duration_hours <= 2.25 and r.cap_mw >= 50
    peer_rows += (
        '<tr class="' + ("hl" if is2h else "") + '"><td><b>' + str(r.resource_name) + '</b>'
        '<div class=sub>' + (str(r.company) if pd.notna(r.company) else "—") + '</div></td>'
        '<td class="num mono">' + f(r.cap_mw, 0) + '</td><td class="num mono">' + f(r.duration_hours, 1) + '</td>'
        '<td class="num mono b">' + f(r.rev_per_mw, 0) + '</td>'
        '<td class="num mono">' + f(r.opt_rate_pct, 1) + '%</td>'
        '<td class="num mono">' + f(r.as_share_pct, 1) + '%</td></tr>')
g = P["gks_row"]
if g:
    peer_rows += (
        '<tr class=ref><td><b>GKS</b><div class=sub>당사 · 남부지역 (참고)</div></td>'
        '<td class="num mono">' + f(g["cap_mw"], 0) + '</td><td class="num mono">' + f(g["duration_hours"], 1) + '</td>'
        '<td class="num mono b">' + f(g["rev_per_mw"], 0) + '</td>'
        '<td class="num mono">' + f(g["opt_rate_pct"], 1) + '%</td>'
        '<td class="num mono">' + f(g["as_share_pct"], 1) + '%</td></tr>')

SIDE = {"long": ("매수", "up"), "short": ("매도", "down")}
dart_rows = ""
for _, r in dh.iterrows():
    tr = bool(r.tradeable); side = r.best_side
    lab, cls = SIDE.get(side, (side, "muted"))
    ev = r.long_ev_per_mwh if side == "long" else r.short_ev_per_mwh
    pw = r.long_p_win if side == "long" else r.short_p_win
    p99 = r.long_loss_p99 if side == "long" else r.short_loss_p99
    badge = ('<span class="pill up">거래 가능</span>' if tr else
             ('<span class="pill down">손실 위험 큼</span>' if r.tail_flag else '<span class="pill muted">근거 부족</span>'))
    dart_rows += (
        '<tr class="' + ("ok" if tr else "") + '"><td class=mono>' + str(int(r.HE)) + '시</td>'
        '<td><span class="pill ' + cls + '">' + lab + '</span></td>'
        '<td class="num mono">' + f(pw * 100, 1) + '%</td>'
        '<td class="num mono ' + ("up" if ev > 0 else "down") + '">' + f(ev, 2) + '</td>'
        '<td class="num mono ' + ("down" if p99 > 30 else "") + '">' + f(p99, 1) + '</td>'
        '<td>' + badge + '</td></tr>')

TIGHT = {"LOOSE": "여유", "TIGHT": "타이트"}
reg_rows = ""
for _, r in rg.iterrows():
    win = "에너지" if r.energy2h_rt > r.as24_rt else "보조 종일"
    cong = "유리" if "POS" in str(r.cong) else "불리"
    reg_rows += (
        '<tr><td><b>' + TIGHT.get(str(r.tight), str(r.tight)) + '</b></td><td>' + cong + '</td>'
        '<td class="num mono">' + str(int(r.days)) + '</td>'
        '<td class="num mono b">' + f(r.energy2h_rt) + '</td><td class="num mono">' + f(r.as4_rt) + '</td>'
        '<td class="num mono">' + f(r.as24_rt) + '</td>'
        '<td><span class="pill ' + ("up" if win == "에너지" else "amber") + '">' + win + '</span></td></tr>')

FWDMAP = [("RETIRED", "down", "은퇴 — 사용 불가"), ("FADED", "muted", "소멸 — 사용 불가"),
          ("UNVERIFIABLE", "amber", "검증 불가"), ("EPISODIC", "amber", "특정 시기만"),
          ("LIVE", "up", "유효")]
DRVKO = {"solar_ercot": "전체 태양광 ↑", "solar_southeast": "남동부 태양광 ↑",
         "wind_ercot": "전체 풍력 ↑", "wind_west_panhandle": "서부 풍력",
         "load_ercot": "전력수요 ↑", "load_southern": "남부 수요 ↑",
         "load_farwest": "서부 수요 ↑", "net_load_ercot": "순수요 ↑",
         "wind_coastal": "연안 풍력 ↑"}
def pi_cell(raw_sf):
    """Price-impact coefficient = -SF (+ bullish / - bearish), as an opening <td>."""
    if raw_sf is None:
        return '<td class="num mono muted">—'
    v = -raw_sf
    if abs(v) < 0.0005:
        return '<td class="num mono muted">0.000'
    return '<td class="num mono ' + ("up" if v > 0 else "down") + '">' + format(v, "+.3f")


drv_rows = ""
if drivers:
    for i, (name, v) in enumerate(drivers.items(), 1):
        fr = (v.get("forward_relevance") or "").upper()
        cls, lab = "muted", "—"
        for k, c, l in FWDMAP:
            if k in fr:
                cls, lab = c, l
                break
        top = (v.get("driver_ranking_top8") or [{}])[0]
        drv = DRVKO.get(top.get("driver", ""), top.get("driver", "—"))
        th = "—"
        for t in (v.get("thresholds") or []):
            if t.get("driver") == top.get("driver") and t.get("bins"):
                b = t["bins"]
                th = (f(b[-1]["lo"] / 1000, 1) + "GW 초과 시 "
                      + f(b[0]["p_bind"] * 100, 0) + "%→" + f(b[-1]["p_bind"] * 100, 0) + "%")
                break
        sf = v.get("shift_factor") or {}
        sr = (sf.get("rvn_real_2026_06plus") or {}).get("da")
        sg = (sf.get("gks_bess_rn") or {}).get("da")
        bh = (v.get("binding_hours") or {}).get("da") or {}
        band = str(bh.get("peak_band_HE", "—")).replace("HE", "").replace("-", "~")
        pb = bh.get("p_bind_band_mean")
        pos = "pos" in (v.get("sign_at_raven") or "")
        drv_rows += (
            '<tr><td class=mono>' + str(i) + '</td><td><b>' + name + '</b></td>'
            '<td>' + drv + '</td><td class="mono" style="font-size:11.5px">' + th + '</td>'
            '<td><span class="pill ' + ("up" if pos else "down") + '">'
            + ("가격 ▲" if pos else "가격 ▼") + '</span></td>'
            + pi_cell(sr)
            + ('<div class=sub><span class="pill amber" style="font-size:10px">GKS와 반대</span></div>'
               if sf.get("relation_rvn_vs_gks") == "OPPOSING" else '') + '</td>'
            + pi_cell(sg) + '</td>'
            '<td class=mono>' + band + '시<div class=sub>발생률 ' + f((pb or 0) * 100, 0) + '%</div></td>'
            '<td><span class="pill ' + cls + '">' + lab + '</span></td></tr>')

oos_rows = ""
if proxy:
    cands = [("<b>채택</b> — 3개 노드 가중 합성", proxy["oos_metrics"], True)]
    alt = proxy.get("alternatives", {})
    if "single_best" in alt:
        cands.append(("단일 최적 노드 (" + ",".join(alt["single_best"]["nodes"]) + ")", alt["single_best"]["oos"], False))
    for lab, m, ch in cands:
        oos_rows += (
            '<tr class="' + ("hl" if ch else "") + '"><td>' + lab + '</td>'
            '<td class="num mono">$' + f(m.get("tb2_da_mae"), 2) + '</td>'
            '<td class="num mono">$' + f(m.get("tb2_rt_mae"), 2) + '</td>'
            '<td class="num mono">' + f((m.get("spread_hourly_sign_agree") or 0) * 100, 1) + '%</td></tr>')

# basis / dispatch numbers
bc = (basis or {}).get("constraints", {}) or {}
bb = ((basis or {}).get("basis", {}) or {}).get("full", {}) or {}
dsp = ((basis or {}).get("dispatch", {}) or {}).get("full", {}) or {}
rk = (basis or {}).get("risk", {}) or {}
cr = rk.get("corr_full") or {}
dDA, dRT = dsp.get("DA", {}) or {}, dsp.get("RT", {}) or {}

CSS = """
:root{--bg:#f7f8fa;--pnl:#fff;--pnl2:#f0f2f5;--alt:#fafbfc;--bd:#e0e3eb;--bd2:#c8ccd4;
--tx:#131722;--tx2:#5d606b;--tx3:#9598a1;--up:#089981;--dn:#f23645;--bl:#2962ff;--am:#ff9800;
--gl:#eceff3;--sh:0 1px 2px rgba(16,24,40,.04);}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--tx);font-family:'Inter','Pretendard','Noto Sans KR',-apple-system,system-ui,sans-serif;font-size:14px;line-height:1.55}
.wrap{max-width:1360px;margin:0 auto;padding:26px}
.mono{font-family:'JetBrains Mono','SF Mono',monospace;font-variant-numeric:tabular-nums}
header{display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:12px;padding-bottom:16px;border-bottom:2px solid var(--tx);margin-bottom:24px}
h1{font-size:24px;font-weight:700;letter-spacing:-.02em}
.sub2{color:var(--tx2);font-size:12.5px;margin-top:6px}
.tag{display:inline-block;padding:4px 10px;border-radius:4px;font-size:11px;font-weight:600;background:rgba(255,152,0,.12);color:#b26a00;border:1px solid rgba(255,152,0,.3)}
h2{font-size:17px;font-weight:700;margin:34px 0 12px;display:flex;align-items:center;gap:10px}
h2 .n{width:26px;height:26px;border-radius:5px;background:var(--tx);color:#fff;font-size:13px;display:flex;align-items:center;justify-content:center;font-family:'JetBrains Mono',monospace;flex:none}
.ans{background:linear-gradient(180deg,rgba(41,98,255,.07),rgba(41,98,255,.02));border:1px solid var(--bl);border-left:4px solid var(--bl);border-radius:6px;padding:15px 18px;margin-bottom:14px}
.ans .k{font-size:10px;font-weight:700;letter-spacing:.1em;color:var(--bl);margin-bottom:5px}
.ans .v{font-size:16px;font-weight:700;line-height:1.5}
.ans ul{margin:9px 0 0 18px}.ans li{font-size:13px;color:var(--tx2);margin-bottom:4px}
.ans li b{color:var(--tx)}
.panel{background:var(--pnl);border:1px solid var(--bd);border-radius:6px;padding:16px;box-shadow:var(--sh);margin-bottom:12px}
.pt{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:var(--tx2);margin-bottom:4px}
.pn{font-size:12px;color:var(--tx3);margin-bottom:12px}
.g2{display:grid;grid-template-columns:2fr 1fr;gap:12px;margin-bottom:12px}
.g11{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
@media(max-width:1000px){.g2,.g11{grid-template-columns:1fr}}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:var(--tx2);font-weight:600;padding:8px 9px;border-bottom:1px solid var(--bd)}
td{padding:8px 9px;border-bottom:1px solid var(--gl)}
tbody tr:nth-child(even){background:var(--alt)}
tbody tr:hover{background:var(--pnl2)}
.num{text-align:right}.b{font-weight:700}
td.mkt{font-weight:700;background:var(--pnl2)!important;text-align:center;vertical-align:middle;font-size:13px}
.sub{font-size:11px;color:var(--tx3);margin-top:2px}
.up{color:var(--up)}.down{color:var(--dn)}.amber{color:var(--am)}.muted{color:var(--tx3)}
.pill{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;white-space:nowrap}
.pill.up{background:rgba(8,153,129,.12);color:var(--up)}
.pill.down{background:rgba(242,54,69,.12);color:var(--dn)}
.pill.amber{background:rgba(255,152,0,.14);color:#b26a00}
.pill.muted{background:var(--pnl2);color:var(--tx3)}
tr.hl{background:rgba(41,98,255,.05)!important}
tr.ref td{border-top:2px solid var(--bd2);background:rgba(255,152,0,.06)!important}
tr.ok{background:rgba(8,153,129,.06)!important}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(275px,1fr));gap:12px;margin-bottom:14px}
.card{background:var(--pnl);border:1px solid var(--bd);border-radius:6px;padding:18px;box-shadow:var(--sh);border-top:3px solid var(--bl)}
.card.warn{border-top-color:var(--am)}.card.good{border-top-color:var(--up)}.card.bad{border-top-color:var(--dn)}
.card .n{font-size:10px;font-weight:700;letter-spacing:.09em;color:var(--tx3)}
.card .h{font-size:15px;font-weight:700;margin:7px 0 9px;line-height:1.45}
.card .d{font-size:12.5px;color:var(--tx2)}
.card .big{font-size:27px;font-weight:700;font-family:'JetBrains Mono',monospace;margin:4px 0}
.hm{display:grid;grid-template-columns:56px repeat(12,1fr);gap:2px}
.hm div{font-size:10px;text-align:center;padding:7px 2px;border-radius:3px;font-family:'JetBrains Mono',monospace}
.hm .hd{color:var(--tx2);font-weight:600}.hm .yr{text-align:right;padding-right:6px;color:var(--tx2);font-weight:600}
.note{background:var(--alt);border-left:3px solid var(--bd2);padding:11px 14px;border-radius:0 5px 5px 0;font-size:12.5px;color:var(--tx2);margin-top:12px}
.note.w{background:rgba(255,152,0,.06);border-left-color:var(--am)}
.note.g{background:rgba(8,153,129,.06);border-left-color:var(--up)}
.note.r{background:rgba(242,54,69,.05);border-left-color:var(--dn)}
.note b{color:var(--tx)}
.chartbox{position:relative;height:290px}
.tabs{display:flex;gap:6px;margin-bottom:10px}
.tab{padding:4px 13px;font-size:12px;border:1px solid var(--bd);border-radius:4px;background:var(--pnl);cursor:pointer;font-weight:500}
.tab.on{background:var(--bl);color:#fff;border-color:var(--bl)}
.steps{counter-reset:s}
.step{position:relative;padding:11px 0 11px 40px;border-bottom:1px dashed var(--gl)}
.step:last-child{border-bottom:none}
.step:before{counter-increment:s;content:counter(s);position:absolute;left:0;top:11px;width:25px;height:25px;border-radius:50%;background:var(--bl);color:#fff;font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center;font-family:'JetBrains Mono',monospace}
.step .t{font-weight:600;font-size:13.5px}.step .d{font-size:12.5px;color:var(--tx2);margin-top:3px}
.step code{background:var(--pnl2);padding:1px 6px;border-radius:3px;font-family:'JetBrains Mono',monospace;font-size:11.5px}
.sim{background:linear-gradient(180deg,rgba(41,98,255,.06),rgba(41,98,255,.01));border:1.5px solid var(--bl);border-radius:6px;padding:20px;margin-top:14px}
.srow{display:grid;grid-template-columns:210px 1fr 96px;gap:14px;align-items:center;margin-bottom:15px}
.srow label{font-size:12.5px;font-weight:600;color:var(--tx2)}
.srow .rv{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:17px;text-align:right}
input[type=range]{width:100%;accent-color:#2962ff;height:5px}
.simout{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:6px}
.sc{background:var(--pnl);border:1px solid var(--bd);border-radius:6px;padding:14px;text-align:center}
.sc .l{font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--tx2);font-weight:600}
.sc .v{font-size:25px;font-weight:700;font-family:'JetBrains Mono',monospace;margin-top:6px;color:var(--bl)}
.sc .s{font-size:11px;color:var(--tx3);margin-top:3px}
.marks{display:flex;gap:6px;flex-wrap:wrap;margin-top:5px}
.mark{font-size:11px;padding:3px 9px;border:1px solid var(--bd);border-radius:4px;background:var(--pnl);cursor:pointer;font-family:'JetBrains Mono',monospace}
.mark:hover{background:var(--pnl2);border-color:var(--bl)}
.dec td:first-child{font-weight:700}
.gl{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:0 26px}
.gl .r{display:grid;grid-template-columns:120px 1fr;gap:10px;padding:7px 0;border-bottom:1px solid var(--gl);font-size:12.5px}
.gl .r b{color:var(--tx)}.gl .r span{color:var(--tx2)}
.pill.sh{background:rgba(41,98,255,.13);color:#2962ff}
.pill.lg{background:rgba(255,152,0,.16);color:#b26a00}
.yb{display:inline-block;width:26px;text-align:center;font-size:10.5px;font-family:'JetBrains Mono',monospace;border-radius:3px;margin-right:2px;padding:1px 0;background:var(--pnl2);color:var(--tx3)}
.yb.sh{background:rgba(41,98,255,.15);color:#2962ff;font-weight:600}.yb.lg{background:rgba(255,152,0,.18);color:#b26a00;font-weight:600}
.hg{display:grid;grid-template-columns:78px repeat(24,minmax(22px,1fr));gap:2px;overflow-x:auto;margin-bottom:6px}
.hg div{font-size:10px;text-align:center;padding:6px 0;border-radius:2px;font-family:'JetBrains Mono',monospace}
.hg .hh{color:var(--tx2);font-weight:600;background:none;padding:2px 0}
.hg .hr{text-align:right;padding-right:6px;color:var(--tx2);font-weight:600;background:none;font-family:inherit;font-size:11px;white-space:nowrap}

"""

JS = """
Chart.defaults.font.family="'Inter','Noto Sans KR',sans-serif";Chart.defaults.font.size=11;
Chart.defaults.color='#5d606b';
const o={responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},
plugins:{legend:{position:'top',align:'end',labels:{boxWidth:10,boxHeight:10,usePointStyle:true,pointStyle:'rect'}}},
scales:{x:{grid:{color:'#eceff3'},ticks:{maxTicksLimit:9}},y:{grid:{color:'#eceff3'},ticks:{callback:v=>'$'+v}}}};
let ch=new Chart(document.getElementById('c1'),{type:'line',data:{labels:DAYS_RT,datasets:[
{label:'Raven',data:RVN_RT,borderColor:'#089981',backgroundColor:'rgba(8,153,129,.10)',fill:true,borderWidth:1.9,pointRadius:0,tension:.25},
{label:'GKS',data:GKS_RT,borderColor:'#f23645',backgroundColor:'rgba(242,54,69,.08)',fill:true,borderWidth:1.9,pointRadius:0,tension:.25}]},options:o});
function sw(m,el){document.querySelectorAll('#t1 .tab').forEach(t=>t.classList.remove('on'));el.classList.add('on');
ch.data.labels=m=='RT'?DAYS_RT:DAYS_DA;ch.data.datasets[0].data=m=='RT'?RVN_RT:RVN_DA;
ch.data.datasets[1].data=m=='RT'?GKS_RT:GKS_DA;ch.update();}

new Chart(document.getElementById('c3'),{type:'bar',data:{labels:[...Array(24)].map((_,i)=>(i+1)+'시'),datasets:[
{label:'GKS 가격 − 남부 기준가격',data:GKSBASIS,backgroundColor:GKSBASIS.map(v=>v<-5?'rgba(242,54,69,.85)':'rgba(149,152,161,.5)'),borderWidth:0}]},
options:{...o,plugins:{...o.plugins,legend:{display:false}},scales:{...o.scales,y:{...o.scales.y,title:{display:true,text:'$/MWh'}}}}});



if(document.getElementById('czc') && Object.keys(ZC).length){
  const yrs=Object.keys(ZC), FU=[['Gas','가스','#9598a1'],['Nuclear','원자력','#b39ddb'],['Solar','태양광','#ffb74d'],['Wind','풍력','#4fc3f7'],['ESS','배터리','#089981']];
  new Chart(document.getElementById('czc'),{type:'bar',data:{labels:yrs.map(y=>y==='2026'?'2026.7':y),
    datasets:FU.map(([k,l,c])=>({label:l,data:yrs.map(y=>+(ZC[y][k]/1000).toFixed(2)),backgroundColor:c,borderWidth:0}))},
    options:{...o,scales:{x:{stacked:true,grid:{display:false}},y:{stacked:true,grid:{color:'#eceff3'},ticks:{callback:v=>v+'GW'}}}}});
}
if(document.getElementById('czp') && Object.keys(ZP).length){
  const hs=Object.keys(ZP).map(Number).sort((a,b)=>a-b), vs=hs.map(h=>ZP[h]);
  new Chart(document.getElementById('czp'),{type:'bar',data:{labels:hs.map(h=>h+'시'),datasets:[
    {label:'Houston − 시스템 평균',data:vs,backgroundColor:hs.map((h,i)=>((h>=12&&h<=17&&vs[i]>0)||(h>=19&&h<=23&&vs[i]<0))?'rgba(242,54,69,.8)':'rgba(149,152,161,.5)'),borderWidth:0}]},
    options:{...o,plugins:{...o.plugins,legend:{display:false}},scales:{...o.scales,y:{...o.scales.y,title:{display:true,text:'$/MWh'}}}}});
}

const PSC=[['dis','방전','#089981'],['chg','충전','#9ed9cf'],['regup','RegUp','#2962ff'],['regdn','RegDown','#7aa2ff'],
 ['rrs','RRS','#6d4c9f'],['ecrs','ECRS','#ff9800'],['nonspin','NonSpin','#ffcc80']];
let PST={site:'PEER_AVG',mkt:'rt',season:'all'};
function pdata(){
  const src=PST.season==='all'?PS.profiles:(PS.profiles_season[PST.season]||PS.profiles);
  const p=src[PST.site]||src['PEER_AVG']; const m=PST.mkt;
  const key=k=>k==='dis'?m+'_dis':k==='chg'?m+'_chg':m+'_'+k+'_mw';
  return PSC.map(([k,l,c])=>({label:l,data:(p?p[key(k)]:[]).map(v=>+(+v).toFixed(1)),backgroundColor:c,borderWidth:0,stack:'s'}));
}
const pchart=new Chart(document.getElementById('cps'),{type:'bar',data:{labels:[...Array(24)].map((_,i)=>(i+1)+'시'),datasets:pdata()},
 options:{...o,plugins:{...o.plugins,tooltip:{callbacks:{label:c=>c.dataset.label+': '+c.parsed.y.toFixed(1)+'%'}}},
 scales:{x:{stacked:true,grid:{display:false}},y:{stacked:true,grid:{color:'#eceff3'},ticks:{callback:v=>v+'%'},title:{display:true,text:'설비 용량 대비 %'}}}}});
function pnote(){
  const n=document.getElementById('psnote'); const s=PST.season!=='all';
  n.textContent=(PST.site==='PEER_AVG'?'3사 동일가중 평균':PST.site+' 단독')+' · '+(PST.mkt==='rt'?'실시간 실제 출력과 실시간 보조서비스 배정':'전일시장 에너지 낙찰과 보조서비스 낙찰')+' · '+(s?PST.season:'전체 기간')+(PST.site!=='PEER_AVG'&&s?' (계절 분리는 3사 평균만 제공)':'');
}
function psel(k,v,el,grp){
  PST[k]=v;
  const box=document.getElementById(grp==='pt3'?'pt2':grp);
  box.querySelectorAll('.tab').forEach(t=>{
    const isSeason=['전체','겨울·봄','여름'].includes(t.textContent);
    if((grp==='pt3')===isSeason) t.classList.remove('on');
  });
  el.classList.add('on');
  if(k==='site'&&v!=='PEER_AVG'&&PST.season!=='all'){PST.season='all';box.parentNode.querySelectorAll('#pt2 .tab').forEach(t=>{if(['겨울·봄','여름'].includes(t.textContent))t.classList.remove('on')});document.getElementById('ps_all').classList.add('on');}
  pchart.data.datasets=pdata(); pchart.update(); pnote();
}
pnote();
const hm=document.getElementById('hm');let all=[];Object.values(MO).forEach(a=>a.forEach(v=>{if(v!=null&&v<200)all.push(v)}));
B27.forEach(v=>all.push(v));const mn=Math.min(...all),mx=Math.max(...all);
function col(v){if(v==null)return['#f0f2f5','#9598a1'];const t=Math.max(0,Math.min(1,(v-mn)/(mx-mn)));
return ['rgba(8,153,129,'+(0.10+t*0.75).toFixed(2)+')', t>0.55?'#fff':'#131722'];}
hm.innerHTML+='<div class=hd></div>'+M.map(m=>'<div class=hd>'+m.replace('월','')+'</div>').join('');
['2024','2025','2026'].forEach(y=>{hm.innerHTML+='<div class=yr>'+y+'</div>'+
(MO[y]||[]).map(v=>{const c=col(v);return '<div style="background:'+c[0]+';color:'+c[1]+'">'+(v==null?'-':Math.round(v))+'</div>';}).join('');});
hm.innerHTML+='<div class=yr style="color:#2962ff">2027E</div>'+B27.map(v=>{const c=col(v);
return '<div style="background:'+c[0]+';color:'+c[1]+';outline:1.5px solid #2962ff">'+Math.round(v)+'</div>';}).join('');

const L26=LVL26,SHAPE=SH,DM2=DM,MW=100;
function fmt(n,d){return n.toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});}
function recalc(){
  const c=+document.getElementById('sCap').value, d=+document.getElementById('sDec').value;
  const lvl=L26*d/100; let tbi=0; for(let m=0;m<12;m++)tbi+=2*lvl*SHAPE[m]*DM2[m];
  const rev=tbi*c/100;
  document.getElementById('vCap').textContent=c.toFixed(1)+'%';
  document.getElementById('vDec').textContent=d+'%';
  document.getElementById('oTbi').textContent='$'+fmt(tbi,0);
  document.getElementById('oRev').textContent='$'+fmt(rev,0);
  document.getElementById('oTot').textContent='$'+fmt(rev*MW/1e6,2)+'M';
  const dd=100*(rev/BASEREV-1), e=document.getElementById('oDelta');
  e.textContent=(dd>=0?'▲ +':'▼ ')+dd.toFixed(1)+'% (기준안 대비)';
  e.className='s '+(dd>=0?'up':'down');
  fchart.data.datasets[0].data=SHAPE.map(s=>+(lvl*s).toFixed(1));fchart.update('none');
}
const fchart=new Chart(document.getElementById('cf'),{type:'bar',data:{labels:M,datasets:[
{label:'2027년 전망',data:B27,backgroundColor:'rgba(41,98,255,.55)',borderWidth:0},
{label:'2026년 실적',data:MO['2026'],type:'line',borderColor:'#9598a1',borderWidth:1.7,borderDash:[4,3],pointRadius:0,tension:.3}]},
options:{...o,scales:{...o.scales,y:{...o.scales.y,title:{display:true,text:'$/MWh'}}}}});
['sCap','sDec'].forEach(i=>document.getElementById(i).addEventListener('input',recalc));
function setCap(v){document.getElementById('sCap').value=v;recalc();}
function setDec(v){document.getElementById('sDec').value=v;recalc();}
recalc();
"""

DATA_JS = (
    "const DAYS_DA=" + json.dumps(days_da) + ",RVN_DA=" + json.dumps(rvn_da) + ",GKS_DA=" + json.dumps(gks_da) + ";\n"
    "const DAYS_RT=" + json.dumps(days_rt) + ",RVN_RT=" + json.dumps(rvn_rt) + ",GKS_RT=" + json.dumps(gks_rt) + ";\n"
    "const XO=" + json.dumps(json.loads(xo.to_json(orient="records"))) + ";\n"
    "const MO=" + json.dumps(mo) + ",B27=" + json.dumps(base27) + ",M=" + json.dumps(MONTHS) + ";\n"
    "const GKSBASIS=" + json.dumps(gks_basis_he) + ";\n"
    "const PS=" + json.dumps(pstack or {}, ensure_ascii=False) + ";\n"
    "const ZC=" + json.dumps((zcap or {}).get("coast_by_fuel", {})) + ";\n"
    "const ZP=" + json.dumps(((zprice or {}).get("rt_premium_profile_2025_26", {}) or {}).get("HB_HOUSTON", {})) + ";\n"
    "const LVL26=" + str(round(lvl["2026"], 4)) + ",SH=" + json.dumps([round(s, 4) for s in shape])
    + ",DM=" + json.dumps(DAYSM) + ",BASEREV=" + str(round(rv["base_median"], 2)) + ";\n")

y26 = yr["DA"][-1] if yr else {}
y24 = [r for r in yr["DA"] if r["year"] == 2024][0] if yr else {}

HTML = ("""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Raven BESS 노드 분석 및 FY2027 매출 전망</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>""" + CSS + """</style></head><body><div class=wrap>

<header><div><h1>Raven BESS 노드 분석 및 FY2027 매출 전망</h1>
<div class=sub2>100MW / 200MWh (2시간) · Houston 지역 · 보고일 2026-09-15<br>
데이터: Yes Energy 3개년 전 노드 가격·송전제약 + ERCOT 60일 공시 — 전부 실측</div></div>
<div><span class=tag>인근 발전소 하절기 실적 미포함</span></div></header>

<!-- ============ 핵심 결론 ============ -->
<h2><span class=n>Ⅰ</span>핵심 결론</h2>
<div class=cards>
<div class="card good"><div class=n>결론 1 · 매출 전망</div>
<div class=h>FY2027 매출은 100MW 기준 약 $2.1M</div>
<div class="big up">$""" + f(rv["base_median"] * 100 / 1e6, 2) + """M</div>
<div class=d>운용 역량별 $""" + f(rv["low_p25"] * 100 / 1e6, 2) + """M ~ $""" + f(rv["high_p75"] * 100 / 1e6, 2) + """M<br>
<b>수급 상방</b>(배터리 준공 지연 + 데이터센터 수요) 시 <b>최대 $3.0M</b><br>
에너지 + 보조서비스 합계 (가상거래 제외)</div></div>

<div class="card warn"><div class=n>결론 2 · 노드 평가</div>
<div class=h>"Raven이 GKS보다 좋다"는 절반만 맞음</div>
<div class=d>GKS 대비 우위는 사실이나, 그 차이의 <b>88%는 Houston의 강점이 아니라 GKS의 약점</b>에서 나옴.<br>
Raven은 <b>ERCOT 전체 평균보다 10~18% 낮은</b> 평범 이하의 노드.</div></div>

<div class="card warn"><div class=n>결론 3 · 신규 수익원</div>
<div class=h>가격차 거래는 기회 없음 · 가상거래는 소규모 시범 가치</div>
<div class=d>· 지역간 가격차 거래 — 메커니즘은 실재하나 <b>규모가 전체의 11%</b><br>
· 가상거래 — Raven 고유 수익은 없으나, <b>예측상 타이트한 날 오후·저녁 SHORT</b>가 3년 데이터·2026년 사후검증에서 유효. 실측 기준 MW당 연 <b>$1.3~2.5천</b></div></div>

<div class="card good"><div class=n>결론 4 · 예상 밖 시너지</div>
<div class=h>두 발전소 독립 운용 시 연 $0.3~0.5M 순증</div>
<div class="big up">+$""" + f((dRT.get("uplift_usd_per_year_200MWh_each") or 0) / 1000, 0) + """k</div>
<div class=d>최적 방전 시간대가 <b>76%의 날에 서로 다름</b>.<br>
신규 투자 없이 <b>운용 방식 변경만으로</b> 실현 가능</div></div>
</div>



<!-- ============ Houston 지역 개요 ============ -->
<h2><span class=n>Ⅱ</span>Houston 지역 개요 — Raven이 들어가는 시장</h2>
<div class=ans><div class=v>Houston은 가스 중심의 "조용한" 시장이며, 배터리 경쟁은 ERCOT에서 가장 치열</div>
<ul>
<li><b>수요</b>: 석유화학 등 산업 부하 중심으로 성장이 느림 — 연 <b>2.6%</b> (ERCOT 평균 4.3%). ERCOT 수요 성장은 서부(Permian 유전)와 북부가 주도</li>
<li><b>공급</b>: 가스 비중 <b>69%로 전 지역 최고</b>, 그중 24%가 공장 자가용 열병합. 태양광·풍력 비중은 낮음</li>
<li><b>배터리</b>: 최근 3년 <b>+3.3GW로 전 지역 최대 증가</b>, 2027년 계획도 +1.9GW로 최대 — 지역 내 경쟁이 가장 빠르게 늘고 있음</li>
<li><b>가격</b>: 한낮엔 비싸고(+$4.5) 저녁엔 오히려 저렴(−$1.3). <b>이론 차익은 전 허브 중 최저</b>, 음(−)가격 시간도 최저 → 배터리에 구조적으로 불리한 모양</li>
</ul></div>

<div class=g11>
<div class=panel><div class=pt>Houston 연료원별 설비 추이</div>
<div class=pn>설치용량 GW · EIA-860M(2026년 7월판) · 2026년은 7월 기준</div>
<div class=chartbox style="height:260px"><canvas id=czc></canvas></div>
<div class=note>배터리 <b>0.3GW(2023) → 3.6GW(2026.7)</b>, 3년간 약 12배. 같은 기간 가스는 21.2 → 22.4GW로 거의 정체.
원자력은 South Texas Project 2.7GW.</div></div>

<div class=panel><div class=pt>지역 비교</div>
<div class=pn>수요 = 1~8월 평균 부하(GW)와 3년 연평균 성장률 · 설비 비중 = 2026년 7월 설치용량 기준</div>
<table><thead><tr><th>지역</th><th class=num>수요</th><th class=num>수요성장</th><th class=num>가스</th><th class=num>태양광</th><th class=num>풍력</th><th class=num>배터리</th><th class=num>배터리 증가<div class=sub>'23→'26, GW</div></th><th class=num>2027 계획<div class=sub>배터리, GW</div></th></tr></thead>
<tbody>""" + zone_rows + """</tbody></table>
<div class="note w">EIA-860M은 ERCOT 자체 집계보다 재생·배터리를 10~15% 적게 잡음(2025년말 배터리 EIA 13.9GW vs ERCOT 15.6GW).
지역 간 <b>상대 비교용</b>으로 해석해야 함.</div></div>
</div>

<div class=g11>
<div class=panel><div class=pt>시간대별 Houston 가격 프리미엄 (시스템 평균 대비)</div>
<div class=pn>$/MWh · 실시간시장 · 2025~2026년 평균 · <b style="color:#f23645">붉은 막대</b> = 배터리에 불리한 시간 (충전 시간에 비쌈 / 방전 시간에 쌈)</div>
<div class=chartbox style="height:240px"><canvas id=czp></canvas></div>
<div class="note r"><b>배터리에 불리한 모양.</b> 한낮(13~16시)엔 +$5 비싸서 <b>충전 비용이 높고</b>,
저녁(20~22시)엔 −$1~2 싸서 <b>방전 수익이 낮음</b>. 태양광이 적은 수입 지역이라 한낮에 외부에서 전기를 받아오기 때문.</div></div>

<div class=panel><div class=pt>허브별 가격 특성 (2026년)</div>
<div class=pn>프리미엄 = 시스템 평균 대비 $/MWh · 이론 차익 = 실시간시장 일평균 · 시간 수 = 1~9월</div>
<table><thead><tr><th>허브</th><th class=num>한낮 프리미엄<div class=sub>10~15시</div></th><th class=num>저녁 프리미엄<div class=sub>18~22시</div></th><th class=num>이론 차익</th><th class=num>음(−)가격 시간</th><th class=num>$500 초과 시간</th></tr></thead>
<tbody>""" + hub_rows + """</tbody></table>
<div class=note><b>Houston은 전 허브 중 가장 안정적인 시장</b> — 이론 차익·음가격 빈도·가격 변동성 모두 최저.
서부·Panhandle은 풍력 과잉으로 음가격이 연 900~1,200시간 발생해 충전이 매우 싸지만, Houston은 113시간뿐.</div>
<div class="note g"><b>Raven 관점의 함의</b> — Houston 입지 자체는 배터리에 유리하지 않음.
Raven의 이론 차익이 시장 평균보다 낮은 것(Ⅲ장)은 노드 문제가 아니라 <b>지역 구조</b>에서 비롯됨.
또한 지역 내 배터리 증가가 가장 빠르므로, 향후 경쟁 심화 리스크도 가장 큼.</div></div>
</div>

<!-- ============ Ⅱ 노드 실체 ============ -->
<h2><span class=n>Ⅲ</span>Raven 노드의 실체</h2>
<div class=ans><div class=v>Raven은 GKS보다 낫지만, 시장 평균에는 못 미침</div>
<ul>
<li>하절기 이론 차익이 GKS 대비 <b>전일시장 +56% / 실시간시장 +26%</b> — 91%의 날에 우위</li>
<li>그러나 ERCOT 전체 노드 평균과 비교하면 <b>매년 10~18% 낮고, 격차가 벌어지고 있음</b></li>
<li>GKS와의 격차는 고정이 아님 — <b>2024년 +4% → 2025년 +38%</b>. 배수 방식 전망은 성립하지 않음</li>
</ul></div>

<div class=g2>
<div class=panel><div class=pt>일별 이론 차익 — Raven vs GKS (2026년 하절기)</div>
<div class=pn>하루 중 가장 싼 2시간에 충전, 가장 비싼 2시간에 방전했을 때의 MWh당 가격차</div>
<div class=tabs id=t1><div class="tab on" onclick="sw('RT',this)">실시간시장</div><div class=tab onclick="sw('DA',this)">전일시장</div></div>
<div class=chartbox><canvas id=c1></canvas></div>
<div class=note>평균 <b>전일시장 Raven $""" + f(st["DA"]["RVN_RN"]["mean"], 2) + """ vs GKS $""" + f(st["DA"]["GKS_BESS_RN"]["mean"], 2) + """</b>.
월이 갈수록 격차 확대 — 6월 +$5.2 → 7월 +$15.8 → <b>8월 +$20.2</b></div></div>

<div class=panel><div class=pt>월별 이론 차익 추이</div><div class=pn>$/MWh · 2027년은 전망치</div>
<div class=hm id=hm></div>
<div class="note w">3년간 <b>시장 전체 수익성이 33% 하락</b>함.<br>
연평균 $83.8 → $64.1 → <b>$56.1</b> — 배터리 신규 진입에 따른 가격차 축소로,
Houston 기준가격도 동일하게 하락함. <b>Raven만의 문제가 아님.</b></div></div>
</div>

<div class=panel><div class=pt>연도별 상대 성과</div>
<div class=pn>비교 기준 = ERCOT 전체 발전 노드(약 1,100개)의 일별 이론 차익 평균 · 단위 $/MWh</div>
<table><thead><tr><th></th><th>연도</th><th class=num>Raven</th><th class=num>시장 평균</th>
<th class=num>Raven vs 시장</th><th class=num>GKS</th><th class=num>GKS vs 시장</th><th class=num>Raven vs GKS</th></tr></thead>
<tbody>""" + yr_rows + """</tbody></table>
<div class="note r"><b>핵심 3가지</b><br>
① Raven은 <b>매년 시장 평균 아래</b>이고 격차가 벌어짐 (전일 −9.1%→−10.7%, 실시간 −15.4%→−17.7%)<br>
② GKS는 훨씬 더 낮음 (−35% 수준) → <b>Raven이 좋은 것이 아니라 GKS가 나쁜 것</b><br>
③ Raven−GKS 격차가 <b>2024년 +4.2%에서 2025년 +37.9%로 급변</b> → 배수 방식 전망은 사용할 수 없음</div></div>

<!-- ============ Ⅲ 왜 차이나는가 ============ -->
<h2><span class=n>Ⅳ</span>왜 GKS와 차이가 나는가</h2>
<div class=ans><div class=v>Raven이 비싸게 파는 것이 아니라, GKS가 저녁 피크에 제 값을 못 받음</div>
<ul>
<li>차이는 전적으로 <b>"파는 쪽"</b>에서 발생함 — 충전 측면은 오히려 GKS가 유리</li>
<li>GKS는 저녁 피크(20~21시)에 지역 기준가격보다 <b>$15 낮게</b> 받음</li>
<li>그 결과 <b>방전을 22~23시로 미루게 되어 하루 중 가장 비싼 시간을 놓침</b> (전체 일수의 46%)</li>
<li>원인은 <b>남부 지역의 송전 용량 부족</b> — 발전력을 외부로 내보내지 못함</li>
</ul></div>

<div class=g11>
<div class=panel><div class=pt>1단계 · 차이는 "파는 쪽"에서 나옴</div>
<table><thead><tr><th>차이의 출처</th><th class=num>전일시장</th><th class=num>실시간시장</th></tr></thead><tbody>
<tr><td>전체 차이</td><td class="num mono b">+14.13</td><td class="num mono b">+9.62</td></tr>
<tr style="background:rgba(8,153,129,.09)"><td><b>방전(파는) 가격 차이</b></td><td class="num mono b up">+16.36</td><td class="num mono b up">+14.00</td></tr>
<tr><td>충전(사는) 가격 차이</td><td class="num mono down">−2.23</td><td class="num mono down">−4.38</td></tr>
</tbody></table>
<div class=note><b>충전 측면은 오히려 Raven이 불리.</b> GKS의 충전 시간대 전기값이 매월 더 저렴.
→ "Raven은 싸게 충전할 수 있어 유리하다"는 가설은 <b>성립하지 않음.</b></div>

<div class=pt style="margin-top:20px">2단계 · 그 차이의 88%는 GKS의 송전 혼잡</div>
<table><thead><tr><th>원인</th><th class=num>기여</th><th class=num>비중</th></tr></thead><tbody>
<tr style="background:rgba(242,54,69,.08)"><td><b>GKS의 저녁 시간대 가격 할인</b></td><td class="num mono b">−12.43</td><td class="num mono b down">88%</td></tr>
<tr><td>Houston 지역 프리미엄</td><td class="num mono">+1.24</td><td class="num mono">9~16%</td></tr>
<tr><td>Raven 노드 고유 요인</td><td class="num mono">+0.46</td><td class="num mono">0~3%</td></tr>
</tbody></table>
<div class=note>Houston 프리미엄은 <b>한낮(태양광 시간대)에 집중</b>되는데, 그 시간은 두 발전소 모두 <b>충전하는 시간</b>이라
수익에 거의 기여하지 못함.</div></div>

<div class=panel><div class=pt>3단계 · GKS는 저녁 피크에 $15 손해를 판단</div>
<div class=pn>GKS 노드 가격 − 남부지역 기준가격 ($/MWh, 전일시장) · 붉은 막대 = $5 이상 할인</div>
<div class=chartbox style="height:250px"><canvas id=c3></canvas></div>
<div class="note r"><b>결과 — GKS는 하루 중 가장 비싼 시간을 놓침.</b><br>
저녁 피크에 가격이 $15 깎이니 GKS는 방전을 <b>22~23시로 미룸</b>.
전체 일수의 <b>46%</b>에서 이런 현상이 발생함 (Raven은 18%).
이미 가격이 내려간 늦은 밤에 파는 구조.</div>
<div class="note w"><b>경영 함의</b><br>
· 잘못된 전제: "Houston이 구조적으로 좋은 지역이다" → 실제: <b>GKS 노드가 구조적으로 불리</b><br>
· 잘못된 전제: "Raven = GKS × 1.56" → 실제: <b>배수가 불안정, 절대 수준으로 직접 전망해야 함</b></div></div>
</div>

<!-- ============ Ⅳ 전망 ============ -->
<h2><span class=n>Ⅴ</span>FY2027 매출 전망</h2>
<div class=ans><div class=v>100MW 기준 $2.08M. 최대 변수는 Raven이 아니라 시장 전체의 수익성 하락</div>
<ul>
<li>시장 수익성이 3년간 <b>33% 하락</b>했고, 이는 Houston 기준가격도 동일 — <b>배터리 신규 진입에 따른 구조적 현상</b></li>
<li>2027년은 하락이 <b>지속되되 둔화</b>한다고 가정 (2026년 대비 90%)</li>
<li>실제 달성률은 <b>인근 2시간 배터리의 실측치 59.5%</b>를 적용</li>
<li><b>"예비율이 떨어지면 상방 아닌가"</b>를 수급 모형으로 검증 — 논리는 맞으나 2027년엔 조건 충족이 어렵고, <b>상방 시 최대 $3.0M</b> (이 장 하단)</li>
</ul></div>

<div class=panel><div class=pt>추정 5단계</div>
<div class=steps>
<div class=step><div class=t>현재 수준 확정</div><div class=d>2026년 실적 <code>$""" + f(lvl["2026"]) + """/MWh</code> (1~9월 평균, 연도간 동일 기준으로 비교)</div></div>
<div class=step><div class=t>하락이 시장 전체 현상임을 확인</div>
<div class=d>Raven <code>$""" + f(lvl["2024"]) + """ → $""" + f(lvl["2025"]) + """ → $""" + f(lvl["2026"]) + """</code> ·
Houston 기준가격 <code>$83.1 → $65.5 → $56.2</code> — <b>동일한 기울기</b></div></div>
<div class=step><div class=t>2027년 수준 가정</div>
<div class=d>$""" + f(lvl["2026"]) + """ × <b>0.90</b> = <b>$""" + f(fc["base_2027_level_tb2"]) + """/MWh</b>.
연간 하락률이 2025년 −23.5% → 2026년 −12.5%로 <b>둔화 중</b>인 점 반영</div></div>
<div class=step><div class=t>계절성 반영</div><div class=d>월별 편차를 3개년 중앙값으로 적용 (5월 최고 1.53배, 12월 최저 0.53배)</div></div>
<div class=step><div class=t>이론 최대 매출 → 실제 매출</div>
<div class=d>2시간 배터리는 하루 2MWh/MW 순환 → 이론 최대 <code>$""" + f(fc["tb_index_2027_usd_per_mw_yr"], 0) + """/MW-년</code>.
여기에 인근 발전소 <b>실측 달성률</b>을 곱함</div></div>
</div></div>

<div class=panel><div class=pt>매출 시뮬레이터 — 가정을 직접 조정해 보십시오</div>
<div class=pn>두 가정을 바꾸면 매출이 즉시 재계산</div>
<div class=sim>
<div class=srow><label>달성률<div class=sub style="font-weight:400">실제 매출 ÷ 이론 최대</div></label>
<div><input type=range id=sCap min=15 max=100 step=0.5 value=""" + str(cap["base_median"]) + """>
<div class=marks>
<span class=mark onclick="setCap(""" + str(cap["low_p25"]) + """)">인근 하위25% """ + f(cap["low_p25"]) + """%</span>
<span class=mark onclick="setCap(""" + str(cap["base_median"]) + """)">인근 중간 """ + f(cap["base_median"]) + """%</span>
<span class=mark onclick="setCap(""" + str(cap["high_p75"]) + """)">인근 상위25% """ + f(cap["high_p75"]) + """%</span>
<span class=mark onclick="setCap(85.5)">최고 운용사 85.5%</span>
<span class=mark onclick="setCap(43.7)">현재 GKS 43.7%</span></div></div>
<div class=rv id=vCap></div></div>

<div class=srow><label>2027년 시장 수준<div class=sub style="font-weight:400">2026년 대비</div></label>
<div><input type=range id=sDec min=50 max=130 step=1 value=90>
<div class=marks><span class=mark onclick="setDec(61)">수급 하방 61%</span>
<span class=mark onclick="setDec(77)">수급 기준(선형) 77%</span>
<span class=mark onclick="setDec(90)">기준안 90%</span>
<span class=mark onclick="setDec(100)">횡보 100%</span>
<span class=mark onclick="setDec(109)">수급 상방 109%</span>
<span class=mark onclick="setDec(132)">수급 상방(포화) 132%</span></div></div>
<div class=rv id=vDec></div></div>

<div class=simout>
<div class=sc><div class=l>이론 최대 매출</div><div class=v id=oTbi></div><div class=s>$/MW-년</div></div>
<div class=sc><div class=l>실제 매출</div><div class=v id=oRev></div><div class=s id=oDelta></div></div>
<div class=sc><div class=l>100MW 연간 합계</div><div class=v id=oTot></div><div class=s>에너지 + 보조서비스</div></div>
</div>
<div class=chartbox style="height:215px;margin-top:16px"><canvas id=cf></canvas></div>
<div class=note>가상거래(DART) 수익은 <b>포함되지 미반영</b> — Raven 고유 수익이 아니고 규모가 작음 (10~20MW 시범 시 연 약 $1.3~5만, Ⅶ장).
극단적 가격 급등 수익도 미반영 — 2026년 여름은 실시간 가격 $500 초과가 전 노드 통틀어 1시간뿐인 이례적으로 조용한 해.</div>
</div></div>

<div class=panel><div class=pt>검토 요청 — 예비율이 더 떨어지면 2027년은 올해보다 좋아지는가?</div>
<div class=pn>가정: 2027년 신규 공급(특히 배터리)은 적고, AI 데이터센터 등 신규 수요는 크다 → 예비율 하락 → 가격차 확대</div>

<div class=ans style="margin-top:4px"><div class=v>논리는 맞음. 그러나 2027년에는 조건이 충족되기 어렵고, 상방은 2028년 이후에 더 현실적</div>
<ul>
<li><b>메커니즘은 데이터로 확인됨</b> — 피크 순수요 +1GW당 이론 차익 <b>+5.0%</b>, 배터리 +1GW당 <b>−4.9%</b>. 예비율 하락과 배터리 둔화의 <b>이중 수혜</b>는 실재함</li>
<li><b>그러나 2024→2026년에도 계통은 이미 타이트해졌음</b> — 피크 순수요 +3.5GW, 사상 최대 부하 91GW. 그런데도 이론 차익은 하락함. <b>배터리가 +13GW로 수요 증가를 압도</b>했기 때문</li>
<li><b>"2027년 신규 배터리가 적다"는 전제는 데이터와 다름</b> — 2027년 배터리 증설 전망은 <b>+5.5GW(ERCOT 최신)~8.2GW(CDR)~9.6GW(EIA 계획)</b>로 <b>2025년 실적(+6.4GW)과 비슷하거나 더 큼</b>. 2025년 하반기 신규 신청 급감(−58%)은 준공까지 2~3년이 걸려 <b>2028년 이후</b>에 반영됨</li>
<li><b>이미 확정된 역풍도 있음</b> — 2026년 하반기에 준공된 배터리 약 6.6GW의 효과가 2026년 평균에는 아직 절반만 반영돼, 2027년에 추가로 작용함</li>
</ul></div>

<div class=g11 style="margin-bottom:0">
<div>
<div class=pt style="margin-top:8px">① 같은 타이트함에서 비교하면 — 배터리가 "비싼 날"의 수익을 잠식함</div>
<div class=pn>시스템 평균 이론 차익 중앙값 ($/MWh) · 하루 피크 순수요(수요 − 풍력 − 태양광) 구간별 · 1~9월</div>
<table><thead><tr><th>계통 타이트함</th><th class=num>2024</th><th class=num>2025</th><th class=num>2026</th><th class=num>'24→'26</th></tr></thead>
<tbody>""" + lfl_rows + """</tbody></table>
<div class="note r"><b>여유로운 날에는 거의 변화가 없지만, 타이트한 날의 수익은 반토막</b> (65GW 초과: $141 → $60).
배터리가 바로 그 <b>희소성 프리미엄</b>을 잠식한 것. 2026년은 65GW 초과일이 <b>32일로 2024년(12일)의 2.7배</b>였는데도 수익은 더 낮았음.</div>
</div>

<div>
<div class=pt style="margin-top:8px">② 2024→2026년 변화 요인 분해</div>
<div class=pn>시스템 평균 이론 차익(일별, 로그) 회귀 · 계절 통제 · 1,018일</div>
<table><thead><tr><th>요인</th><th class=num>2024 → 2026</th><th class=num>이론 차익 영향</th></tr></thead><tbody>
<tr><td>계통 타이트함 (피크 순수요)</td><td class="num mono">46.9 → 50.4 GW</td><td class="num mono up">+18%</td></tr>
<tr><td>극단 타이트함 (60GW 초과분)</td><td class="num mono">—</td><td class="num mono up">+5%</td></tr>
<tr><td>저녁 수요 급증폭 (태양광 일몰)</td><td class="num mono">17.0 → 26.9 GW</td><td class="num mono up">+25%</td></tr>
<tr><td>가스 가격</td><td class="num mono">$1.80 → $2.72</td><td class="num mono up">+13%</td></tr>
<tr style="background:rgba(242,54,69,.08)"><td><b>배터리 설치 증가</b></td><td class="num mono b">6.0 → 19.2 GW</td><td class="num mono b down">−49%</td></tr>
</tbody></table>
<div class=note><b>배터리를 제외한 모든 요인이 수익을 끌어올림.</b> 수요 증가, 저녁 급증폭 확대, 가스가격 상승 모두 상방 요인이었으나
배터리 증가 하나가 이를 전부 상쇄함. → <b>하락은 날씨 같은 일시적 요인이 아니라 구조적</b>임.</div>
<div class="note w">배터리 효과에는 2025년 12월 실시간 통합최적화(RTC+B) 시행 효과도 섞여 있음. 둘 다 시기가 겹치는 구조적 변화라 완전히 분리하기 어려움 —
어느 쪽이든 <b>되돌아가지 않는 변화</b>라는 결론은 동일.</div>
</div>
</div>

<div class=pt style="margin-top:20px">③ 수급 기반 2027년 시나리오</div>
<div class=pn>배터리 효과를 선형으로 볼지 체감(포화)으로 볼지에 따라 결과가 달라져 두 모형의 범위로 제시 · 매출 = 100MW, 달성률 59.5% 기준</div>
<table><thead><tr><th>시나리오</th><th>입력 가정</th><th class=num>이론 차익<div class=sub>2026년 대비</div></th><th class=num>매출</th></tr></thead>
<tbody>""" + sc_rows + """</tbody></table>
<div class=note>현재 기준안(2026년 대비 90%, $2.08M)은 수급 모형의 기준 시나리오 범위(77~100%) 안에 있음 — <b>기준안은 유지</b>하되,
이제 추세 연장이 아니라 <b>수급 근거</b>로 뒷받침됨.</div>

<div class="note g"><b>상방이 성립하려면 두 조건이 동시에 필요</b><br>
① 2027년 신규 배터리가 <b>약 6GW 이하</b>로 억제 (현 계획 8~10GW 대비 대거 지연) &nbsp;+&nbsp;
② 피크 순수요가 <b>+5GW 이상</b> 증가 (추세의 약 2배, 데이터센터 실제 연계 필요)<br>
둘 중 하나만으로는 올해 수준 유지가 어려움. 다만 두 조건이 맞으면 <b>2026년 대비 +9~32%, 매출 $2.5~3.0M</b>까지 가능.</div>

<div class="note w"><b>시사점 — 상방 논리는 FY2028 이후에 더 강하게 작동함</b><br>
배터리 신규 신청이 2025년 하반기에 <b>−58% 급감</b>(반기 26GW → 14GW)했고 2026년 상반기에도 감소가 지속됨.
준공까지 2~3년이 걸리므로 <b>2028~2029년 신규 공급이 실제로 줄어드는 시점</b>에 데이터센터 수요가 겹치면,
Raven 운영 2~3년차에 의미 있는 상방이 나타날 수 있음. <b>장기 수익 모델에는 이 반등 시나리오를 반영할 것을 권고함.</b></div>
</div>

<!-- ============ Ⅴ 에너지 vs 보조 ============ -->
<h2><span class=n>Ⅵ</span>운용 전략 ① — 에너지 vs 보조서비스</h2>
<div class=ans><div class=v>에너지와 보조서비스는 양자택일이 아니라 "시간대별로 겹쳐 쌓는" 문제.
Houston 상위 3사는 설비의 약 60%를 늘 보조서비스에 걸어두면서, 실시간시장에서 하루 약 0.7회(2시간 배터리 기준) 방전함</div>
<ul>
<li><b>보조서비스를 상시 기본층으로</b> — 시간대와 무관하게 설비의 <b>55~60%</b>가 보조서비스에 배정됨 (RRS가 바닥층, ECRS·NonSpin이 그 위)</li>
<li><b>충전하는 한낮에 상향 예비력을 가장 많이 판매</b> — 충전 중인 출력은 줄이면 곧 공급이 되므로, 충전과 ECRS·NonSpin 판매가 동시에 가능</li>
<li><b>에너지는 실시간시장 중심</b> — 방전량의 약 70%를 실시간에서 처리, DA 에너지 매각은 30% 수준 (CLO는 거의 0)</li>
<li><b>여름엔 "한낮 충전 → 17~19시 예비력 대기 → 20~22시 집중 방전"</b>, 겨울·봄엔 <b>아침·저녁 2회 방전</b></li>
<li>보조서비스 가격은 <b>ERCOT 전 지역 단일 가격</b>이라 위치와 무관 — Raven도 Houston 상위사와 같은 조합이 가능</li>
</ul></div>

<div class=g11>
<div class=panel><div class=pt>Houston 상위 3개 발전소 (2026년 1~5월 실측)</div>
<div class=pn>Raven 직접 비교군(2시간·50MW 이상) 중 MW당 매출 상위 3개 사이트 · 용량은 실제 운전 기록 기준 · CLO는 동일 사이트 2기 합산</div>
<table><thead><tr><th>#</th><th>발전소</th><th class=num>MW</th><th class=num>MW당 매출</th><th class=num>달성률</th><th class=num>보조 매출 비중</th></tr></thead>
<tbody>""" + top3_rows + """</tbody></table>
<div class=note>최고 성과 발전소 <b>WAL</b>이 위치한 노드는 분석 과정에서 <b>Raven과 가격이 가장 유사한 노드</b>로 확인되었음 — 가장 직접적인 벤치마크 대상임.
3사 모두 <b>보조서비스가 매출의 38~39%</b>를 차지함.</div>

<div class=pt style="margin-top:18px">시장 상황별 최적 조합</div>
<div class=pn>MW당 일수익 $ · 실시간시장 기준 · 2026년 여름</div>
<table><thead><tr><th>수급</th><th>혼잡</th><th class=num>일수</th><th class=num>에너지 2h</th><th class=num>보조 4h</th><th class=num>보조 24h</th><th>우위</th></tr></thead>
<tbody>""" + reg_rows + """</tbody></table>
<div class=note>충방전 4시간을 보조서비스로 돌리는 것은 어떤 상황에서도 손해(에너지가 4.5~11.2배).
<b>시장이 타이트하고 혼잡이 유리한 날에만</b> 종일 보조서비스 대기가 근소 우위.</div></div>

<div class=panel><div class=pt>상위 3사의 시간대별 상품 배치</div>
<div class=pn>설비 용량 대비 % · 막대 위쪽 = 방전과 보조서비스, 아래쪽 = 충전 · ERCOT 60일 공시 2025-12-05 ~ 2026-07-17 (220일)</div>
<div class=tabs id=pt1>
<div class="tab on" onclick="psel('site','PEER_AVG',this,'pt1')">3사 평균</div>
<div class=tab onclick="psel('site','WAL',this,'pt1')">WAL</div>
<div class=tab onclick="psel('site','CLO',this,'pt1')">CLO</div>
<div class=tab onclick="psel('site','LON',this,'pt1')">LON</div></div>
<div class=tabs id=pt2>
<div class="tab on" onclick="psel('mkt','rt',this,'pt2')">실시간 실제 배치</div>
<div class=tab onclick="psel('mkt','da',this,'pt2')">전일시장 배정</div>
<span style="width:14px"></span>
<div class="tab on" id=ps_all onclick="psel('season','all',this,'pt3')">전체</div>
<div class=tab onclick="psel('season','겨울·봄(12~5월)',this,'pt3')">겨울·봄</div>
<div class=tab onclick="psel('season','여름(6~7월)',this,'pt3')">여름</div></div>
<div class=chartbox style="height:340px"><canvas id=cps></canvas></div>
<div class=sub id=psnote style="margin-top:6px"></div>
</div>
</div>

<div class=g11>
<div class=panel><div class=pt>시사점 — 상위 3사 운용 방식</div>
<table><thead><tr><th style="width:130px">시간대</th><th>무엇을 하는가 (3사 평균, 실시간 기준)</th></tr></thead><tbody>
<tr><td><b>새벽 1~5시</b></td><td>소량 충전(6~12%) + <b>NonSpin·RRS 대기</b>(합계 25~33%) — 싼 야간 전력으로 일부 채워 둠</td></tr>
<tr><td><b>아침 7~8시</b></td><td><b>1차 방전</b>(10~12%, 겨울·봄 중심) + RegUp 증가 — 아침 수요 급증 대응</td></tr>
<tr style="background:rgba(41,98,255,.06)"><td><b>한낮 9~16시</b></td><td><b>본 충전</b>(최대 18%) + <b>ECRS 20~27% · NonSpin 15~23% 동시 판매</b> — 충전 출력은 줄이면 곧 공급이므로 상향 예비력 판매와 겹칠 수 있음</td></tr>
<tr style="background:rgba(41,98,255,.06)"><td><b>오후 17~19시</b></td><td>방전 준비 — <b>ECRS·NonSpin을 최대로 유지</b>(여름 ECRS 35~38%), 에너지는 아직 소량</td></tr>
<tr style="background:rgba(8,153,129,.08)"><td><b>저녁 20~22시</b></td><td><b>본 방전</b>(최대 25%, 여름 21시 36%) — 이때 보조서비스는 가장 낮게(ECRS 8~12%)</td></tr>
</tbody></table>
<div class="note g"><b>Raven 운용에 주는 시사점</b><br>
① <b>보조서비스를 "남는 시간에 파는 것"이 아니라 상시 기본층</b>으로 설계함 — 설비의 절반 이상<br>
② <b>충전 시간을 비워두지 않음</b> — 한낮 충전과 ECRS·NonSpin 판매를 동시에<br>
③ <b>에너지는 실시간 중심</b>으로 가격 급등 기회를 남겨 둠 — DA 에너지 매각은 일부만<br>
④ <b>계절 전환</b>: 여름은 저녁 1회 집중 방전, 겨울·봄은 아침·저녁 2회</div></div>

<div class=panel><div class=pt>참고 — 우리 GKS와 비교</div>
<div class=pn>같은 기간 · 설비 용량 대비</div>
<table><thead><tr><th>항목</th><th class=num>상위 3사 평균</th><th class=num>GKS</th></tr></thead><tbody>
<tr><td>실시간 방전량 (하루, 설비 가득 방전 시간 환산)</td><td class="num mono b">""" + f(_ps.get("PEER_AVG", {}).get("rt_discharge_hours_equiv"), 2) + """시간</td><td class="num mono down b">""" + f(_ps.get("GKS", {}).get("rt_discharge_hours_equiv"), 2) + """시간</td></tr>
<tr><td>실시간 보조서비스 배정 (평균)</td><td class="num mono b">""" + f(_ps.get("PEER_AVG", {}).get("avg_as_pct_rt"), 0) + """%</td><td class="num mono down b">""" + f(_ps.get("GKS", {}).get("avg_as_pct_rt"), 0) + """%</td></tr>
<tr><td>전일시장 보조서비스 배정 (평균)</td><td class="num mono">""" + f(_ps.get("PEER_AVG", {}).get("avg_as_pct_da"), 0) + """%</td><td class="num mono">""" + f(_ps.get("GKS", {}).get("avg_as_pct_da"), 0) + """%</td></tr>
<tr><td>방전 중 DA 에너지 매각 비중</td><td class="num mono">""" + f((_ps.get("PEER_AVG", {}).get("da_energy_share_of_rt_discharge") or 0) * 100, 0) + """%</td><td class="num mono">0%</td></tr>
</tbody></table>
<div class="note w"><b>GKS는 방전량이 상위 3사의 약 56%에 그치고, 실시간 보조서비스 배정도 3분의 1 수준</b>임.
대신 전일시장에서 NonSpin을 새벽에 설비의 60%까지 팔고 실시간에서는 대부분 되사는 구조.
저녁 혼잡(Ⅳ장) 영향도 있지만, <b>운용 방식 자체의 차이</b>가 GKS 달성률(43.7%)이 상위사(60~86%)보다 낮은 이유 중 하나로 추정.</div>
<div class=note>※ 전일시장 보조서비스 배정은 금융적 약정, 실시간 배정은 실제 대기 책임임. 두 값이 다르면 그 차이만큼 실시간 가격으로 정산됨.</div>
<div class="note w" style="margin-top:10px">공시 데이터는 60일 지연 발행이라 <b>7월 중순까지</b>만 반영됨. 2025-12-05(실시간 통합최적화 시행 첫날) 실시간 RegUp·RegDown 기록은 오류값(음수)이라 제외함.</div></div>
</div>

<!-- ============ Ⅵ DART ============ -->
<h2><span class=n>Ⅶ</span>운용 전략 ② — 가상거래(DART)</h2>

<div class="panel" style="border-left:4px solid var(--tx);padding:14px 18px">
<div class=pt>용어 — 이 장의 방향 표기</div>
<table style="margin-top:6px"><thead><tr><th style="width:120px">표기</th><th>거래</th><th>수익이 나는 경우</th></tr></thead><tbody>
<tr><td><span class="pill sh">SHORT</span></td><td><b>전일시장(DA)에서 팔고 → 실시간시장(RT)에서 되사는 거래</b></td><td>DA 가격 &gt; RT 가격 (가격차 = DA − RT 가 <b>+</b>)</td></tr>
<tr><td><span class="pill lg">LONG</span></td><td><b>전일시장(DA)에서 사고 → 실시간시장(RT)에서 되파는 거래</b></td><td>RT 가격 &gt; DA 가격 (가격차 = DA − RT 가 <b>−</b>)</td></tr>
</tbody></table>
<div class=sub style="margin-top:6px">가상거래는 실물 발전 없이 두 시장의 가격차만 취하는 금융 거래. 아래 모든 표·그림에서 <b style="color:#2962ff">파랑 = SHORT 유리</b>, <b style="color:#e68900">주황 = LONG 유리</b>.</div>
</div>

<div class=ans><div class=v>Raven 고유의 수익원은 없지만, 3년 데이터에서 "오후·저녁 SHORT"라는 시장 전체의 패턴이 확인됨.
예측상 계통이 타이트한 날 가장 강하며, 2026년 사후검증에서도 수익 발생 — 다만 규모는 작음</div>
<ul>
<li><b>3년(2023.12~2026.9) 기준, 오후·저녁 14~19시 SHORT</b>가 3개 연도 모두 같은 방향이며 통계적으로 뚜렷 (DA가 RT보다 비싸게 형성되는 경향)</li>
<li><b>입찰 전 발표된 예측</b>(수요·풍력·태양광)상 <b>타이트한 날</b>에는 15~19시 SHORT가 평균 <b>+$3~10/MWh</b> — 여유로운 날의 몇 배</li>
<li>계절별로는 <b>겨울 낮 12~16시</b>, <b>봄·여름 저녁 17~19시</b> SHORT가 강하고, <b>여름 아침 7~8시만 LONG</b>이 작지만 3년 일관</li>
<li><b>2024~2025년 데이터로 고른 규칙을 2026년에 그대로 적용</b>한 결과 흑자. 단 1월 한파 이틀이 수익의 큰 몫이고, 실측 Raven 가격으로는 대리노드 대비 수익이 35~60% 낮음</li>
<li><b>최선안(예측 타이트함 × 시간대)</b>: 실측 가격 기준 평균 <b>+$1.00/MWh</b>, 적중 60% → MW당 연 약 <b>$1.3~2.5천</b>. <b>소규모(10~20MW) 시범 운용</b> 수준이 적정</li>
</ul></div>

<div class="note g" style="margin:0 0 14px;padding:14px 16px;font-size:13.5px">
<b>핵심 메시지 — Raven DART는 "Houston·ERCOT 시장 전체의 DART"를 보는 것과 사실상 동일</b><br>
Raven 가격차(DA − RT)의 <b>98%는 Houston 허브, 93%는 ERCOT 시스템 가격차</b>로 설명됨 — 노드 고유 혼잡의 몫은 한 자릿수%다.
따라서 방향 판단은 <b>ERCOT 전체 수급 예측(타이트함)·풍력 예측 불확실성·DA 프리미엄 수준·극단 기상</b> 같은 시장 요인으로 하고,
<b>Houston 지역 요인(연안 풍력·Houston 수요)과 노드 혼잡(예: STP-WAP)은 포지션 규모를 조절하는 리스크 필터</b>로 관리하는 것이 적절.
</div>

<div class=panel><div class=pt>① 3년 시간대별 기본 분석 — 대리 노드 기준</div>
<div class=pn>2023-12-01 ~ 2026-09-13 (1,017일) · 가격차 = DA − RT ($/MWh) · 승률·손익비·손실은 우세 방향 기준 · "급등 제외 평균" = 상하위 1% 시간을 잘라낸 평균 (소수 급등일 의존 여부 확인)</div>
<table><thead><tr><th>시간</th><th>우세 방향</th><th class=num>평균 가격차</th><th class=num>승률</th><th class=num>손익비<div class=sub>평균이익÷평균손실</div></th>
<th class=num>최악 1% 손실</th><th class=num>급등 제외 평균</th><th>연도별 방향<div class=sub>'24 '25 '26</div></th><th>판단</th></tr></thead>
<tbody>""" + d3_rows + """</tbody></table>
<div class=note><b>3년 전체로 보면 하루 24시간 모두 평균적으로 SHORT가 유리</b>. 그중 <b>9~12시, 14~15시, 17~19시</b>는 3년 모두 같은 방향이고 급등일을 빼도 유지됨.
반면 <b>6~8시의 큰 평균값은 겨울 한파 며칠이 만든 것</b>이라 급등 제외 시 크게 줄어듦. 20~21시는 평균은 크지만 최악 1% 손실이 $137~199로 위험이 큼.</div>
<div class="note w"><b>앞선 분석(2026년 여름 102일)과 다른 이유</b> — 여름 102일만 보면 "아침 LONG"이 유리했지만, 3년으로 넓히면 <b>SHORT가 기본값</b>임.
2026년 여름은 가격차가 이례적으로 음(−)이었던 시기였음 (여름 평균: 2024 +1.54, 2025 +2.54, <b>2026 −0.36</b>).</div>
</div>

<div class=g11>
<div class=panel><div class=pt>② 계절 × 시간대</div>
<div class=pn>평균 가격차 $/MWh · <b>굵은 테두리</b> = 통계적으로 뚜렷하고(t≥2) 모든 연도에서 같은 방향 · 칸에 마우스를 올리면 상세</div>
""" + hg_season + """
<div class=note><b>유효한 패턴 (굵은 테두리)</b><br>
· <b>겨울</b>: 9~16시 SHORT — 난방 수요 예측이 DA에 과하게 반영<br>
· <b>봄</b>: 12시, 17~18시 SHORT<br>
· <b>여름</b>: 14시·16~19시 SHORT (19시 +$7.8) / <b>7~8시 LONG</b> (작지만 3년 일관)<br>
· <b>가을</b>: 뚜렷한 패턴 없음</div></div>

<div class=panel><div class=pt>③ 예측 기준 계통 타이트함 × 시간대</div>
<div class=pn>타이트함 = 입찰 전(전날 오전 7~9시) 발표된 ERCOT 예측으로 계산한 <b>다음날 피크 순수요</b>(수요 − 풍력 − 태양광)를 직전 60일과 비교해 상·중·하 3등분 · 계절 영향이 자동 보정됨</div>
""" + hg_tight + """
<div class=note><b>타이트할수록 SHORT가 강해짐.</b> 예측상 타이트한 날 15~19시는 <b>+$3.0~9.5</b>로 뚜렷하고,
여유로운 날은 대부분 ±$1 수준으로 방향성 약함. → <b>시장이 타이트할 것으로 예상되면 DA에 희소성 프리미엄이 과하게 붙고,
실제 RT에서는 그만큼 실현되지 않는 경우가 많음</b>는 뜻임.</div>
<div class=sub style="margin-top:8px">예측 정확도 검증: 예측 피크 순수요와 실제의 상관 0.976, 평균 오차 2.1GW · 1,018일 모두 입찰 마감 전 발표분 사용(사후정보 0건)</div></div>
</div>

<div class=panel><div class=pt>④ 계절 × 예측 타이트함 × 시간 구간</div>
<div class=pn>평균 가격차 $/MWh · 색 표시 = 통계적으로 뚜렷하고 모든 연도 같은 방향인 칸만</div>
<table><thead><tr><th>계절 · 예측 타이트함</th><th class=num>새벽 1–6시</th><th class=num>아침 7–11시</th><th class=num>낮 12–16시</th><th class=num>저녁 17–21시</th><th class=num>밤 22–24시</th></tr></thead>
<tbody>""" + d3_block_rows + """</tbody></table>
<div class="note w">칸을 잘게 나눌수록 표본이 줄어 <b>우연히 좋아 보이는 칸</b>이 섞임. 아래 ⑤ 사후검증에서 이 방식(④)은 2026년에 1월 외 흑자월이 2개뿐이라 <b>기각</b>함.
예: 겨울·타이트·아침 +$28은 한파 며칠이 만든 값임.</div></div>

<div class=panel><div class=pt>⑤ 사후검증 — 과거로 고른 규칙이 미래에도 통하는가</div>
<div class=pn><b>2023.12~2025년 데이터만으로</b> 규칙을 고르고(t≥2, 2024·2025 모두 같은 방향, 급등 제외해도 같은 방향), <b>2026년 1~9월에 그대로 적용</b> · 수익은 MW당 누적 $ · 실측 검증 = 같은 규칙을 6/4~9/13 <b>실제 Raven 가격</b>에 적용</div>
<table><thead><tr><th>규칙 방식</th><th class=num>학습기간<div class=sub>평균수익</div></th><th class=num>2026<div class=sub>평균수익</div></th><th class=num>2026<div class=sub>적중</div></th>
<th class=num>2026 누적<div class=sub>$/MW</div></th><th class=num>급등 3일·최악 3일<div class=sub>제외 시</div></th><th class=num>흑자월</th><th class=num>최대 누적손실</th>
<th class=num>실측 Raven<div class=sub>평균수익</div></th><th>판정</th></tr></thead>
<tbody>""" + oos_rows_d3 + """</tbody></table>
<div class="note g"><b>최선안 ③ — 운용 규칙 (입찰 전 예측만으로 판단 가능)</b><br>
· <b>예측상 타이트한 날</b>: 15~19시 SHORT (학습기간 평균 +$3.4~9.7/MWh)<br>
· <b>보통인 날</b>: 새벽 1시, 9~10시, 12~13시, 15시 SHORT (소폭)<br>
· <b>여유로운 날</b>: 11~14시 SHORT (소폭)<br>
→ 2026년 적용 시 9개월 중 7개월 흑자, 최대 누적손실 MW당 $539, 실측 Raven 가격 기준 평균 +$1.00/MWh, 적중 60%</div>
<div class="note w"><b>⚠ 유의사항</b><br>
· <b>2026년 수익의 상당 부분이 1월 한파(1/25~26)</b>에서 발생 — 한파 전 DA가 과열됐다가 RT에서 식은 전형적 사례. 반복되는 패턴이지만 연 1~2회라 변동이 큼<br>
· <b>실측 가격으로는 대리 노드보다 수익이 35~60% 낮음</b> (③: 대리 $811 vs 실측 $526, 6~9월) — 실제 기대치는 실측 기준으로 잡아야 함<br>
· <b>Raven 고유의 수익이 아님</b> — Raven 가격차의 95%가 시장 전체에서 오므로, 같은 규칙을 허브에서 해도 결과는 유사. GKS와 합산해 리스크 한도를 관리해야 함<br>
· 수수료·체결 실패·입찰 가격 설정은 반영하지 않은 이론치</div>
<div class=note><b>이전 검토(4,394개 전략, "기회 없음")와의 차이</b> — 이전 검토는 입찰 시점에 쓸 수 있는 정보를 <b>지난 가격·지난 혼잡</b>으로 한정했고, 그 신호들은 효과가 없었음.
이번에는 <b>입찰 전 발표된 수요·풍력·태양광 예측</b>을 새로 확보해 구분 기준으로 썼고, 3년 표본으로 확대. 그 결과 <b>예측 타이트함이 실제로 유효한 신호</b>임이 확인됨.</div>
</div>

<div class=panel><div class=pt>검토 요청 — Raven의 평균 가격차가 GKS보다 낮아서 메리트가 없는 것인가?</div>
<div class=ans style="margin-top:6px"><div class=v>아님 — Raven의 평균 가격차는 오히려 GKS의 2.6배. 메리트가 제한적인 이유는 "크기"가 아니라 "차별성"임</div></div>
<div class=g11 style="margin-bottom:0">
<div><table><thead><tr><th>평균 가격차 (DA − RT)<div class=sub>$/MWh · + = SHORT 유리</div></th><th class=num>Raven</th><th class=num>GKS</th><th class=num>시스템</th></tr></thead><tbody>
""" + ("".join(
    '<tr><td>' + str(r["year"]) + '</td>'
    '<td class="num mono b">' + (format(r["RAVEN"]["mean"], "+.2f") if r.get("RAVEN") else "—") + '</td>'
    '<td class="num mono">' + (format(r["GKS"]["mean"], "+.2f") if r.get("GKS") else "—") + '</td>'
    '<td class="num mono">' + (format(r["HUB_SYS"]["mean"], "+.2f") if r.get("HUB_SYS") else "—") + '</td></tr>'
    for r in (q2 or {}).get("by_year", []) if r["year"] >= 2024)) + """
<tr style="background:rgba(41,98,255,.06)"><td><b>3년 전체</b></td><td class="num mono b">+1.44</td><td class="num mono b">+0.55</td><td class="num mono">+1.13</td></tr>
</tbody></table></div>
<div><table><thead><tr><th>가격차 변동 중 노드 고유 요인</th><th class=num>Raven</th><th class=num>GKS</th></tr></thead><tbody>
<tr><td>노드 고유 요인 비중</td><td class="num mono b">4.9%</td><td class="num mono b">98.9%</td></tr>
<tr><td>노드 고유 요인의 평균 기여</td><td class="num mono">+0.32</td><td class="num mono down">−0.61</td></tr>
</tbody></table></div>
</div>
<div class=note><b>Raven의 +1.44는 사실상 시장 전체의 가격차</b> (Houston 기준가격 +1.37과 거의 동일). GKS가 낮은 이유는 시장 가격차(+1.13)를 <b>자기 노드 혼잡(−0.61)이 상쇄</b>했기 때문.
→ Raven 가상거래는 <b>허브나 다른 노드에서 해도 결과가 같으므로</b>, GKS와 별개의 수익원으로 계상하면 <b>같은 시장 리스크를 두 번 세는 것</b>임.</div>
<div class="note w"><b>⚠ 중간보고 정정</b> — "전날 방향을 따라가는 규칙이 하루 $42 수익"은 <b>미래 정보를 사용한 오류</b>였음.
입찰 마감(전날 10시) 시점에 확정된 정보만 쓰면 <span class=mono>+$42.4/일 → <b>−$2.3/일</b></span>. 해당 규칙은 폐기함.</div>
</div>

<!-- ============ Ⅶ 가격차 거래 ============ -->
<h2><span class=n>Ⅷ</span>운용 전략 ③ — 지역간 가격차 거래 (검토 요청 사항)</h2>
<div class=ans><div class=v>메커니즘은 실재하나 규모는 미미. 신상품 추진은 권고하지 않음<br>
<span style="font-weight:500;font-size:14px;color:var(--tx2)">대신 두 발전소 독립 운용으로 연 $0.3~0.5M을 확보할 수 있음</span></div>
<ul>
<li><b>검토 배경</b>: Raven(Houston)과 GKS(남부)는 일부 송전 제약에서 영향을 정반대로 받음.
그렇다면 두 지역 가격 차이 자체를 상품화할 수 있는가?</li>
<li><b>가설 확인</b>: STP-WAP 제약에서 정반대 확인 — Raven <b>+0.021 (가격 상승)</b> vs GKS <b>−0.094 (가격 하락)</b></li>
<li><b>그러나</b>: 방향이 반대인 제약은 <b>1,575개 중 64개, 가격차의 11%</b>에 불과</li>
</ul></div>

<div class=g11>
<div class=panel><div class=pt>왜 안 되는가</div>
<table><thead><tr><th>항목</th><th class=num>수치</th></tr></thead><tbody>
<tr><td>방향이 정반대인 송전 제약</td><td class="num mono b">64개 / 1,575개</td></tr>
<tr><td>두 노드 가격차에서 차지하는 비중</td><td class="num mono b down">11%</td></tr>
<tr><td>시간대별 가격차 변동 설명력</td><td class="num mono down">1~4%</td></tr>
<tr><td>의미 있는 규모의 제약</td><td class="num mono">2개뿐</td></tr>
</tbody></table>
<div class="note r"><b>근본 문제</b> — 두 노드의 가격 차이는 대부분 <b>GKS 쪽 남부 혼잡</b> 때문에 생기고
Raven 쪽은 거의 영향받지 않음. 즉 <b>한쪽에만 신호가 있고 다른 쪽은 잡음</b>인 구조.
이런 거래는 신호가 있는 쪽만 단독으로 거래하는 것보다 나을 수 없음.</div>

<div class=pt style="margin-top:20px">검토한 3개 상품</div>
<table><thead><tr><th>상품</th><th>결과</th></tr></thead><tbody>
<tr><td><b>전일시장 가격차 거래</b><div class=sub>Raven SHORT + GKS LONG 동시 실행</div></td>
<td><span class="pill down">기각</span><div class=sub style="margin-top:4px">과거 데이터로는 수익이나
<b>과거로 학습해 미래로 검증하니 손실 전환</b>. GKS 단독 거래가 더 유리</div></td></tr>
<tr><td><b>송전권(CRR) 매입</b><div class=sub>GKS→Houston 구간 가격차 수취권</div></td>
<td><span class="pill amber">한계적</span><div class=sub style="margin-top:4px">25개월 +$14.2k/MW인데
<b>수익의 94%가 2026년 1월 한파 한 달</b>. 이를 빼면 연 $36k에 월 −$240k 손실 위험.
<b>시장이 이미 정확히 가격을 매기고 있음</b></div></td></tr>
<tr style="background:rgba(8,153,129,.07)"><td><b>독립 운용 전환</b><div class=sub>각 발전소가 자기 지역 신호대로</div></td>
<td><span class="pill up">채택 권고</span><div class=sub style="margin-top:4px">연 <b>$303k~$523k</b> 순증</div></td></tr>
</tbody></table></div>

<div class=panel><div class=pt>채택 권고 — 두 발전소 독립 운용</div>
<div class="note g" style="margin-top:0"><b>발견: 두 발전소의 최적 방전 시간대가 서로 다름</b></div>
<table style="margin-top:12px"><thead><tr><th>항목</th><th class=num>수치</th></tr></thead><tbody>
<tr><td>최적 방전 2시간이 <b>서로 다른 날</b></td><td class="num mono b up">"""
+ f((1 - (dDA.get("share_days_same_2_discharge_hours") or 0)) * 100, 0) + """%</td></tr>
<tr><td>평균 최고가 시간대</td><td class="num mono">Raven """ + f(dDA.get("mean_top_he_rvn"), 1) + """시 vs GKS """ + f(dDA.get("mean_top_he_gks"), 1) + """시</td></tr>
<tr><td>통합 스케줄 대비 수익 증가</td><td class="num mono b up">전일 +"""
+ f((dDA.get("uplift_pct") or 0) * 100, 1) + """% / 실시간 +""" + f((dRT.get("uplift_pct") or 0) * 100, 1) + """%</td></tr>
<tr style="background:rgba(8,153,129,.09)"><td><b>2×100MW 연간 순증</b></td>
<td class="num mono b up">$""" + f((dDA.get("uplift_usd_per_year_200MWh_each") or 0) / 1000, 0) + """k ~ $"""
+ f((dRT.get("uplift_usd_per_year_200MWh_each") or 0) / 1000, 0) + """k</td></tr>
</tbody></table>
<div class="note g">원인은 Ⅳ장의 <b>GKS 저녁 혼잡</b>임. GKS는 22~23시로 방전이 밀리고 Raven은 20~21시에 방전함.
<b>동일한 혼잡 현상이 GKS에게는 손실이지만, 포트폴리오 차원에서는 시간 분산 효과</b>가 됨.
신규 투자나 신규 상품 없이 <b>운용 체계 변경만으로 실현</b> 가능.</div>
<div class="note w"><b>⚠ 가격차 거래가 특히 위험한 이유</b><br>
· <b>극단 상황에서 변동 폭발</b> — 실시간 가격이 $500를 넘은 22시간 동안 두 노드 가격차의
변동성이 <b>평상시의 23배</b>로 확대, 시간당 손익이 −$1,519 ~ +$938로 벌어짐<br>
· <b>기반 제약의 소멸</b> — 가격차의 20%가 <b>2026년 3월 이후 발생하지 않는 제약</b>에서,
19%가 소멸 중인 제약에서 나옴. 사라지는 제약 위에 상품 설계는 위험<br>
· <b>두 포지션이 함께 움직임</b> — 두 노드 가격은 0.83(전일)·0.74(실시간) 수준으로 동조하므로
서로 상쇄될 것이라 기대하기 어려움</div></div>
</div>

<!-- ============ Ⅷ 송전 제약 ============ -->
<h2><span class=n>Ⅸ</span>Raven 영향 주요 송전 제약 10선</h2>
<div class=ans><div class=v>절반은 2027년 전망에 사용할 수 없음. 유효한 것은 6개</div>
<ul>
<li><b>송전 제약이란</b>: 특정 송전선의 용량 한계. 이를 넘으면 발전 배분이 조정되어 지역별 가격이 벌어짐</li>
<li><b>가격 영향계수</b>: 제약이 발생했을 때 해당 노드 가격이 움직이는 방향과 크기. <b>+ = 가격 상승(유리)</b>, <b>− = 가격 하락(불리)</b>. 예: GKS의 E_PASP −0.241 → 제약 가격 $100당 GKS 가격 $24 하락</li>
<li>원인이 명확히 갈림 — <b>태양광형은 오후</b>, <b>풍력형은 야간</b>, <b>수요형은 저녁 피크</b>에 발생</li>
<li><b>35055__A는 2026년 신규 발생</b> 제약으로 Raven 최대 고유 노출 — 최우선 감시 대상</li>
</ul></div>
<div class=panel>
<table><thead><tr><th>#</th><th>제약</th><th>발생 원인</th><th>발생 조건</th><th>Raven 영향</th>
<th class=num>Raven 가격 영향<div class=sub>+상승 / −하락</div></th><th class=num>GKS 가격 영향<div class=sub>+상승 / −하락</div></th><th>주요 시간대</th><th>2027 적용</th></tr></thead>
<tbody>""" + drv_rows + """</tbody></table>
<div class="note w"><b>⚠ 전망 보정 필요</b> — Raven은 신규 노드라 과거 3년은 대리 노드로 추정했는데,
실측과 대조하니 오차가 있다: <b>STP-WAP은 50% 과대, 35055__A는 25% 과소</b> 추정되었음.
또한 <b>E_PASP 제약은 두 노드 모두 가격을 끌어내리지만 GKS(−0.241)가 Raven(−0.030)보다 8배 크게</b> 받음 — 같은 제약이 두 자산에 전혀 다른 강도로 작용함.<br>
4개 제약(WHARTN, 1710__C, STPELM27_1, 50__A)은 <b>Raven 가격 개시 이후 한 번도 발생하지 않아 실측값이 없음.</b></div></div>

<!-- ============ Ⅸ 방법론 ============ -->
<h2><span class=n>Ⅹ</span>분석 방법론 — 대리 노드 선정</h2>
<div class=ans><div class=v>3개 노드의 가중 합성을 채택. 검증 오차 약 1%</div>
<ul>
<li><b>배경</b>: Raven 노드는 2026년 6월 신설로 가격 이력이 3개월뿐 — 3개년 분석을 위해 대리 노드가 필요함</li>
<li><b>핵심 판단</b>: 단순 가격 유사도가 아니라 <b>실제 수익이 결정되는 이론 차익의 재현 정확도</b>로 선정</li>
<li>후보를 제한하지 않고 <b>ERCOT 전체 1,109개 노드</b>를 평가</li>
</ul></div>
<div class=g11>
<div class=panel><div class=pt>선정 절차</div>
<div class=steps>
<div class=step><div class=t>전수 조사</div><div class=d>후보 3개에 한정하지 않고 <b>전체 1,109개 노드</b> 평가</div></div>
<div class=step><div class=t>평가 기준 설정</div><div class=d>가격 상관도가 <b>아니라</b> 이론 차익과 전일-실시간 가격차의 재현 정확도.
가격이 비슷해도 수익 구조를 못 맞추면 무용하기 때문</div></div>
<div class=step><div class=t>이력 요건 적용</div><div class=d>원래 1위였던 <b>WAL_RN은 2025년 5월 신설</b>이라 3개년 재구성 불가 → 제외
(16개월로 충분한 용도라면 WAL_RN 권장)</div></div>
<div class=step><div class=t>별도 구간 검증</div><div class=d>6~7월로 산식 도출 → <b>8~9월(45일)로 독립 검증</b></div></div>
<div class=step><div class=t>최종 선택</div><div class=d>단일 노드 대비 가중 합성이 모든 검증 지표에서 우수</div></div>
</div></div>
<div class=panel><div class=pt>검증 결과 (8/1~9/13, 독립 구간)</div>
<div class=pn>실측 이론차익 평균이 전일 $47.9 / 실시간 $67.1이므로 오차율 약 1% 수준</div>
<table><thead><tr><th>후보</th><th class=num>전일 오차</th><th class=num>실시간 오차</th><th class=num>방향 일치율</th></tr></thead>
<tbody>""" + oos_rows + """</tbody></table>
<div class=note><b>채택 산식</b><br>
<span class=mono style="font-size:11.5px">Raven 추정가격 = −0.065 + 0.4148×CBEC_ALL + 0.5407×RBN_BESS1 + 0.0445×TAV_RN</span></div>
<div class="note w"><b>⚠ 한계 3가지</b><br>
① 검증 구간이 <b>하절기 100일뿐</b> — 동절기·환절기 미검증 (±$2~3 오차 가능)<br>
② 합성의 <b>41%가 남부 지역 노드</b> — 동절기 특성이 Raven과 다를 수 있음<br>
③ <b>WHARTN 제약 문제</b> — 3개년 누적 영향 1위 제약이나 마지막 발생일이
Raven 가격 개시 <b>직전</b>이라 실제 영향 여부를 확인할 수 없음</div></div>
</div>

<!-- ============ 한계 ============ -->
<h2><span class=n>Ⅺ</span>분석 한계 및 후속 과제</h2>
<div class=g11>
<div class=panel><div class=pt>한계</div>
<table><thead><tr><th>항목</th><th>영향</th></tr></thead><tbody>
<tr><td><b>인근 발전소 하절기 실적 미확보</b><div class=sub>ERCOT 공시 60일 지연</div></td><td>달성률이 동절기·봄 기준, 8월 미포함</td></tr>
<tr><td><b>2027년 시장 하락률 가정</b></td><td>매출 전망 ±$0.2M</td></tr>
<tr><td>대리 노드가 하절기만 검증됨</td><td>동절기 분석 신뢰도</td></tr>
<tr><td>WHARTN 제약 영향 확인 불가</td><td>혼잡 분석</td></tr>
<tr><td>대리 노드 영향계수 오차</td><td>STP-WAP 50% 과대, 35055__A 25% 과소</td></tr>
<tr><td>극단 가격 급등 수익 미반영</td><td>상방 잠재력</td></tr>
<tr><td><b>Raven 실제 제원·가동 시점 미확인</b></td><td>GKS와 동일 가정</td></tr>
</tbody></table></div>
<div class=panel><div class=pt>후속 과제</div>
<table><thead><tr><th>우선</th><th>과제</th><th>시점</th></tr></thead><tbody>
<tr><td><span class="pill down">높음</span></td><td>하절기 인근 실적 확보 후 달성률 재산출</td><td>10월 말</td></tr>
<tr><td><span class="pill down">높음</span></td><td>DART 시범 규칙(예측 타이트일 SHORT) 실시간 모의 운용 — 실측 Raven 가격으로 누적 검증</td><td>즉시</td></tr>
<tr><td><span class="pill down">높음</span></td><td>2025년 하절기 실적을 계절 대용으로 추가</td><td><b>즉시 가능</b></td></tr>
<tr><td><span class="pill down">높음</span></td><td>35055__A 제약 감시 체계 편입</td><td>즉시</td></tr>
<tr><td><span class="pill amber">중간</span></td><td>WHARTN 제외 시나리오 민감도 검토</td><td>—</td></tr>
<tr><td><span class="pill amber">중간</span></td><td>대리 노드 영향계수 보정 반영</td><td>—</td></tr>
<tr><td><span class="pill amber">중간</span></td><td>Raven 동절기 실측 축적 후 재검증</td><td>2027년 1분기</td></tr>
<tr><td><span class="pill muted">낮음</span></td><td>송전권(CRR) GKS 헤지 검토 이관</td><td>—</td></tr>
</tbody></table></div>
</div>

<!-- ============ 용어 ============ -->
<div class=panel style="margin-top:22px"><div class=pt>용어 설명</div>
<div class=gl>
<div class=r><b>이론 차익</b><span>하루 중 가장 싼 2시간에 충전, 가장 비싼 2시간에 방전했을 때의 MWh당 가격차. 2시간 배터리의 수익 상한</span></div>
<div class=r><b>달성률</b><span>실제 매출 ÷ 이론 최대 매출. 운용 역량 지표</span></div>
<div class=r><b>전일시장</b><span>전날 입찰로 가격이 결정되는 시장 (마감 전날 오전 10시)</span></div>
<div class=r><b>실시간시장</b><span>당일 5분 단위로 가격이 결정되는 시장</span></div>
<div class=r><b>가격차</b><span>전일가격 − 실시간가격. 양수면 SHORT, 음수면 LONG이 유리</span></div>
<div class=r><b>SHORT</b><span>전일시장(DA)에서 팔고 실시간시장(RT)에서 되사는 가상거래. DA가 더 비쌀 때 수익</span></div>
<div class=r><b>LONG</b><span>전일시장(DA)에서 사고 실시간시장(RT)에서 되파는 가상거래. RT가 더 비쌀 때 수익</span></div>
<div class=r><b>예측 타이트함</b><span>입찰 전 발표된 수요·풍력·태양광 예측으로 계산한 다음날 피크 순수요를 직전 60일과 비교한 상대 수준</span></div>
<div class=r><b>가상거래(DART)</b><span>실물 발전 없이 전일-실시간 가격차만 취하는 금융 거래</span></div>
<div class=r><b>노드</b><span>발전소별 정산 지점. ERCOT는 지점마다 가격이 다름</span></div>
<div class=r><b>기준가격</b><span>여러 노드를 대표하는 지역 평균 가격</span></div>
<div class=r><b>송전 제약</b><span>특정 송전선의 용량 한계. 초과 시 발전 배분이 조정되어 지역 가격이 벌어짐</span></div>
<div class=r><b>가격 영향계수</b><span>제약 발생 시 해당 노드 가격이 움직이는 방향과 크기. +는 가격 상승, −는 하락. 제약 가격(원) × 계수 = 노드 가격 변화. ERCOT 원자료(shift factor)와 부호가 반대로 표기됨</span></div>
<div class=r><b>보조서비스</b><span>주파수 조정·예비력 등. ERCOT는 전 지역 단일 가격</span></div>
<div class=r><b>송전권(CRR)</b><span>두 지점 간 가격차를 수취하는 금융 권리. 경매로 취득</span></div>
<div class=r><b>최악 1% 손실</b><span>100번 중 가장 나쁜 1번에서 잃는 금액. 극단 상황 손실 규모</span></div>
</div></div>

</div><script>""" + DATA_JS + JS + """</script></body></html>""")

out = ROOT / "reports/ad-hoc/2026-09-14_Raven_RVN_RN_FY2027_outlook.html"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(HTML, encoding="utf-8")
print("wrote", out, "(", format(len(HTML), ","), "bytes )")
print("data present:", {"yearly": yr is not None, "drivers": drivers is not None,
                        "basis": basis is not None, "dart6": dart6 is not None})
