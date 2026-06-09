# -*- coding: utf-8 -*-
"""Korean / DART-framed narratives + datapack updater for the 5 LIVE POS constraints.
Called by dart_spread.py --write. Rewrites KR text fields (DART short/long framing,
removing the old charge/discharge wording) and injects section8_dart_spread.
Numbers/identifiers/codes left as-is; only narrative wording is Korean DART framing.
"""
from __future__ import annotations
import json
from pathlib import Path

# Per-id Korean DART narratives. Numbers reference the computed metrics (full-window 23mo).
NARR = {
    "HAINE__LA_PAL1_1": {
        "mechanism": "GKS 주입이 로컬 Valley 138(LA PALMA–HAINE DR) 부하를 경감(SF≈−0.03<0) → 바인딩 시 GKS_BESS_RN MCC 기여 양수(LMP↑). 봄 RGV solar+wind 과다로 DA·RT 모두 거의 동일 강도로 만성 바인딩 → DA MCC(+$10,874)≈RT MCC(+$10,931) → DA-RT spread 기여가 서로 상쇄(net −$57, 사실상 flat). DART 관점: 평상시 DA 만성분은 short, RT 스파이크분은 long으로 갈리는 양면 신호.",
        "s4": "봄(Feb–May) 오후 HE12–19, 특히 HE17–19 + South load>4GW + 로컬 RGV solar>1.1GW 또는 GR_SOUTH wind>2.2GW ⇒ DA·RT 동시 만성 바인딩. 평상시 DA가 약간 비싸 short 우위 시간 75.8%(DA-only 3,722h, +$3,226 short). 단 RT 스파이크(LA_PALMA outage 등) 시 RT 급등 → 스파이크 시간의 96.5%가 long(worst −$58/h). 누적 spread −$57로 거의 flat ⇒ net 방향성 미약(mixed). short=평상시 DA-binding, long=RT 이벤트.",
        "s7": "DART read: HAINE의 GKS 노드 DA-RT congestion basis 기여는 net ≈ 제로(누적 −$57, mixed). 가장 빈번(active 5,600+h)하지만 DA MCC와 RT MCC가 거의 동일해 상쇄. 평상시(DA 만성 바인딩·RT 미바인딩) short, RT 스파이크(봄 outage·고RGV solar로 RT $1000+) 시 long. 일방 베팅보다 'RT 스파이크=long' 이벤트 트리거로만 활용. da_dominant=balanced.",
        "seasonality": "봄(Feb–May; Mar/Apr 최대), 저점 Aug–Oct. 시간 HE12–19, P(bind)·λ 모두 HE17–19 피크. spread 기여도 같은 창에서 최대 — 평상시 short, 봄 outage RT 스파이크 시 long.",
        "rot": "평상시(봄 오후 DA 만성 바인딩, RT 미스파이크) → 약한 short. RT λ 스파이크(LA_PALMA outage·고RGV solar 시 RT $1000+) → long. 누적 net≈0이므로 일방 베팅보다 'RT 스파이크=long' 이벤트 트리거 위주.",
        "net_lean_text": "Net mixed(누적 −$57, minority share 0.50): DA MCC(+$10,874)와 RT MCC(+$10,931)가 거의 정확히 상쇄. 시간 기준 short 75.8% 우세이나 $ 기준 net 무시할 수준.",
        "nuance_text": "평소 short(DA 만성 바인딩, DA-only 3,722h +$3,226), RT 스파이크 시 long(top-decile RT 시간의 96.5% long). POS 제약 직관 일치: 만성 DA-binding=DA 비쌈→short, RT-spike=RT 비쌈→long.",
        "caveats": [
            "RT λ source = market_shift_factors MARKET='RT' @ GKS pricenode (1710__C 샘플로 검증); SCED resource-level cross-check 권장.",
            "Window = 노드 존재기간 2024-07-03..2026-06-08(~23mo).",
            "Threshold는 단일 대표월(2025-03, base 0.65) 기반 — full-window stats와 방향 일치하나 full-window 적합은 아님.",
            "Outage watchlist는 day-level 비정보(base 0.72).",
            "net spread≈0(DA·RT 상쇄)이라 일방 DART 시그널로는 약함 — short/long은 RT 스파이크 유무로 갈림.",
        ],
        "drivers": [
            "South load bind 3944 vs nonbind 3559 MW; P(bind) 0.44(저)→0.80(고), λ̄ $37→$127.",
            "South solar bind 897 vs 493(P(bind)→0.88); GR_SOUTH wind bind 1841 vs 1272(P(bind)→0.88 top-decile). 로컬 Valley solar+wind이 138 과부하.",
            "LA_PALMA 138/345 + LA_PALMA–KNGFSHER 345 계획 outage(Feb–Mar 2026)가 RT λ를 $3500까지 증폭 → 이때 spread가 강한 long; 단 base 바인딩률 0.72라 일별 빈도 lift는 없음(severity-only).",
            "load proxy만 존재, 직접 temp series 없음(봄 오후 패턴은 냉방/일사와 정합).",
            "irradiance/wind은 renewable lens로 포착, 별도 weather feature 없음.",
        ],
    },
    "421__A": {
        "mechanism": "GKS 발전 주입이 deep South의 North→South 수입을 BCESW–SNDSW 345 seam에서 대체(SF≈−0.19, |SF| 최대 0.32) → 바인딩 시 GKS MCC 기여 양수(LMP↑). DA(|SF|≈0.32)가 RT(0.18)보다 강해 DA MCC(+$5,681)>RT MCC(+$4,239) → DA-RT spread net +$1,442 short. RT 스파이크 시 long 공존(mixed). Sandow/BCESW 345 병렬경로 outage가 onset gate.",
        "s4": "Sandow/BCESW 345 병렬경로(431_B/455_A/3425_B) outage일 때만 의미 있게 바인딩. 그 조건 봄(Apr)·늦가을/겨울(Oct–Dec) 오후 HE13–16 + 낮은 South wind ⇒ DA MCC가 RT보다 커 short 우위(short 시간 69.2%, DA-only 520h +$1,864 short). RT 스파이크(top-decile) 84.5% long(worst −$140/h). net +$1,442 short-leaning(mixed). |SF| 최대 0.32로 per-MW 레버리지 1위, 2026 유일 성장 제약.",
        "s7": "DART read: net short-leaning(누적 +$1,442, mixed). DA MCC(+$5,681)>RT MCC(+$4,239) → 평상시 short. Sandow/BCESW 345 병렬회랑 outage 시(현 regime) 봄(Apr)·늦가을/겨울 오후 HE13–16 short. RT 스파이크 시 long 공존. 2026 유일 성장 제약이라 short 기여 확대 추세. da_dominant=balanced(r=1.34); Stage-2에 병렬-345 outage-state feature 권장.",
        "seasonality": "봄(Apr 최대) + 늦가을/겨울(Nov/Dec/Oct); 오후 HE10–18, P(bind) HE13–16 피크, λ HE17–18 피크. 2025-onset & 성장(병렬-345 outage gated). short 기여도 동일 창에 집중.",
        "rot": "병렬-345 outage regime + 봄(Apr)/늦가을·겨울 오후 HE13–16 + 낮은 South wind → short(DA 비쌈). RT 급등 시(스파이크 시간 84.5% long) long. 평소 short, 이벤트 long.",
        "net_lean_text": "Net short-leaning(누적 +$1,442, minority share 0.378→mixed): DA MCC가 RT보다 +$1,442 크다. short 시간 69.2%, gross short $3,664 vs gross long $2,222.",
        "nuance_text": "평소 short(병렬-345 outage regime의 DA 만성분, DA-only +$1,864), RT 스파이크 시 long(top-decile 84.5% long, worst −$140/h). 만성 DA-binding=short / RT-spike=long 직관 일치.",
        "caveats": [
            "2025-onset/성장 제약 — window-average section2 P(bind)는 현재(2026) 수준을 과소평가; outage regime window = 2025-01-01+.",
            "Driver threshold는 얇은 월(2025-04, 바인딩 15h, base 2%) 기반 → load/wind/solar 신뢰도 낮음; 1차 switch는 outage-state gate.",
            "RT λ source = market_shift_factors MARKET='RT' @ GKS pricenode.",
            "병렬-345 outage 지속 ⇒ 일별 lift가 아니라 regime base-rate 점프로 나타남.",
            "net short이나 mixed(long minority 38%) — RT 스파이크 빈발 시 일중 long 전환 가능.",
        ],
        "drivers": [
            "병렬 345 BGRSW–BCESW 431_B / BGRSW–SNDSW 455_A / BCESW–YARSW 3425_B가 2025-04~05부터 Forced-out; 바인딩 2024:160→2025:2983→2026:3023 rows. 지속 outage=regime onset(일별 lift 아님).",
            "SouthCentral load bind 9022 vs nonbind 8222 MW; 얇은 2025-04 샘플(base 2%) — North→South-import 방향 정합하나 검정력 부족.",
            "GR_SOUTH wind bind 993 vs nonbind 1908 MW — 낮은 South wind ⇒ 남향 수입↑ ⇒ 바인딩(1710__C와 동일 import 스토리, 샘플 얇음).",
            "직접 temp series 없음; 샘플이 얇아 load와 분리 불가.",
            "inverse-wind 가설로만 포착, 별도 weather feature 없음.",
        ],
    },
    "BLESSING_1382": {
        "mechanism": "GKS 주입이 deep South TX의 coastal 수출(Blessing 345/138 변압기) 부하를 경감(SF<0) → 바인딩 시 GKS MCC 기여 양수(LMP↑). DA 만성 바인딩(N-1) 빈도가 높아 DA MCC(+$3,857)>RT MCC(+$2,913) → DA-RT spread net +$944 short. RT 스파이크 시 long 공존.",
        "s4": "겨울+봄 overnight/morning HE3–10 + 높은 coastal+south wind + 낮은 ERCOT load ⇒ Blessing 345 변압기 DA 만성 바인딩. DA가 비싸 short 우위(short 시간 90.7%, DA-only 3,540h +$2,913 short). RT 스파이크(top-decile) 96.7% long(worst −$135/h). net +$944 short-leaning(mixed). 단발 아닌 누적형 short tailwind.",
        "s7": "DART read: net short-leaning(누적 +$944, mixed). 빈도형 — DA 만성 바인딩(4,171 DA bind-hrs)으로 평상시 short(short 시간 90.7%), per-hour λ는 낮음. 겨울/봄 overnight-morning HE3–10 고coastal-wind·저load일에 short. RT 스파이크 시 long(96.7%). 누적형이라 단일 이벤트 아님. da_dominant=balanced(r=1.32).",
        "seasonality": "겨울+봄, overnight/morning. DA 피크 Apr/Jan/Feb/Dec/May/Nov(여름 아님). 시간 HE4–10 피크, HE12–17 저점. short 기여도 동일 창.",
        "rot": "겨울/봄 overnight-morning HE3–10 + 고coastal+south wind + 저load → short(DA 만성, DA 비쌈). RT 급등 시(스파이크 96.7% long) long. 평소 short, 이벤트 long.",
        "net_lean_text": "Net short-leaning(누적 +$944, minority share 0.416→mixed): DA MCC(+$3,857)>RT MCC(+$2,913). short 시간 90.7%, gross short $3,291 vs gross long $2,347.",
        "nuance_text": "평소 short(DA 만성 N-1 바인딩, DA-only 3,540h +$2,913), RT 스파이크 시 long(top-decile 96.7% long, worst −$135/h). 만성 DA-binding=short / RT-spike=long 직관 일치.",
        "caveats": [
            "Post-contingency N-1 only(base-case 0%).",
            "Wind/outage driver는 co-occurrence + seasonality이지 episode별 회귀 적합 아님.",
            "Section2/3 P(bind) 분모 = full window 2024-07-03..2026-06-08; section3는 active season+hours 조건부.",
            "RT λ는 market_shift_factors MARKET=RT(GKS pricenode-level); STPELM rt/와 cross-check.",
            "net short이나 mixed(long minority 42%) — overnight-wind 가설은 데이터상 미지지(고wind일수록 P(bind) 감소). RT 스파이크 시 long 전환.",
        ],
        "drivers": [
            "off-peak(HE3-10 바인딩, HE12-17 저점) ⇒ 낮은 overnight load이 coastal export pocket을 가능케 함; 고load 드라이버 아님.",
            "패널(Nov-May HE3-10): coastal+south wind↑일수록 P(bind) 감소(65.7%@<1.5GW→26.8%@>2.5GW, AJO out 조건부에서도) — overnight-wind-export 가설 미지지; 잔잔한 overnight에 더 빈번.",
            "STP/Elm-Creek/coastal outlet N-1 순수 post-contingency(DELMTEX5/MANSSTP5/DSTPREF5); base-case 0%. 병렬-345 outage 판별력 약함(REFORZAR 회랑 lift ~1.6, 높은 base rate).",
            "별도 분리 안 됨; off-peak 패턴은 temperature/load-peak 드라이버와 상충.",
            "DA cum top Apr706/Jan559/Feb556/Dec492/May408/Nov395; 여름 거의 0(Aug32). RT top Feb733/Apr515/Jul452/Dec372/Nov361.",
        ],
    },
    "STPELM27_1": {
        "mechanism": "STP-ELMCREEK가 STP+coastal 발전을 Matagorda pocket 밖으로 북송; GKS는 STP 남측이라 GKS 주입이 coastal-pocket 수출을 대체(SF<0) → 바인딩 시 GKS MCC 기여 양수(LMP↑). 빈도는 DA 우위지만 RT 심도가 압도($795 mean, $4500 max) → RT MCC(+$4,457)>DA MCC(+$2,750) → DA-RT spread net −$1,707 long, RT-dominant. GKS POS 제약 중 최고 심도.",
        "s4": "AJO-REFORZAR 345 병렬 OUT이 1차 gate(P(bind) 0.4%→18.8%, lift x47). 그 위 겨울밤(Dec>Jan>Nov) HE5–9·HE17–20 ⇒ RT severe binding($1000–$4500). 평상시(DA 바인딩·RT 미스파이크) short 시간은 많으나(short 83.9%, DA-only 431h +$1,108 short) 드문 RT 스파이크가 $를 지배(RT 스파이크 100% long, worst −$202/h) → net long −$1,707, RT-dominant(r=0.61). 고wind은 frequency 아닌 severity↑.",
        "s7": "DART read: net LONG(누적 −$1,707, RT-dominant). 빈도상 DA-binding short 시간이 많지만(83.9%), 겨울밤 RT severe 스파이크($795 mean/$4500 max)가 $를 지배 → long이 net을 결정. AJO/South-TX 345 회랑 OUT + 겨울밤(Dec>Jan>Nov) HE5–9/HE17–20 + 고coastal+south wind = strong long 트리거. 정상 corridor면 거의 무바인딩.",
        "seasonality": "겨울(Dec>Jan>Nov), overnight/morning HE5–9 + 저녁 HE17–20. Onset 2025(2024 데이터 없음). RT 스파이크(=long)도 동일 창.",
        "rot": "AJO-REFORZAR 345 OUT + 겨울밤(Dec>Jan>Nov) HE5–9/HE17–20 + 고coastal+south wind → strong long(RT severe 스파이크, RT 비쌈). 평상시 약한 short(DA 바인딩)이나 $ 기준 RT long이 지배. 정상 corridor면 시그널 거의 없음.",
        "net_lean_text": "Net LONG(누적 −$1,707, RT-dominant r=0.61): RT MCC(+$4,457)>DA MCC(+$2,750). 시간 기준은 short 83.9%이나 드문 RT 스파이크가 $를 지배 → net long. gross long $3,233 vs gross short $1,526.",
        "nuance_text": "평소 약한 short(DA 바인딩, DA-only 431h +$1,108), RT 스파이크 시 강한 long(top-decile 100% long, worst −$202/h, $4500 episode). 빈도(short)와 심도(long)가 반대 → 심도가 net 결정. 만성 DA-binding=short / RT-spike=long 직관 일치, 단 RT-spike $ 지배.",
        "caveats": [
            "Onset 2025: full-window P(bind) 분모가 희석(2024-07..2025 비활성) — 겨울밤 셀만 비영(지문).",
            "CONTINGENCY text가 rt/에서 공란 → DA CONTINGENCYID=DELMSTP5로 디코드.",
            "RT $4500 episode는 rt/2026012522.csv.gz(PRICE=4500, VALUEMW 713>LIMITMW 611)에서 cross-check.",
            "Outage lift는 겨울 시즌 내 co-occurrence이지 contingency-membership/causation 아님.",
            "net long이 시간이 아니라 $ 기준임에 유의 — 시간 기준은 short 다수. RT 스파이크 부재 시 약한 short.",
        ],
        "drivers": [
            "낮은 겨울-overnight load이 export-pocket을 가능케 하는 조건이지 고load 드라이버 아님.",
            "단일 피크 $4500 밤(2026-01-25)은 ~3.7GW coastal+south wind였으나, 패널(AJO out 조건부)은 P(bind)가 <2GW(28.5%)에서 최고, >3GW(13.1%)에서 낮음 — 고wind은 드문 이벤트의 SEVERITY를 키우지 frequency 아님; 깨끗한 양의 트리거 아님.",
            "AJO-REFORZAR 345 OUT(2025-09~)이 gate: P(bind|HE4-9,17-20)=18.8% out vs 0.4% in(lift x47); 겨울-day lift x14.6. coastal/STP flow를 STP-ELMCREEK로 집중 → DELMSTP5 N-1 과부하(limit ~611MW). 2025-26 겨울 내 co-occurrence이지 인과 증명 아님.",
            "DA cum Dec1789/Jan806/Nov106; RT Dec3025/Jan1172/Nov261; Nov-Jan 밖 ~0. 겨울 overnight = 고wind + 저load.",
            "onset 2025(2024 바인딩 없음); regime-change 제약, onset/active-outage feature로 다룰 것.",
        ],
    },
    "WESTEX": {
        "mechanism": "高West-basin wind이 North로 수출되며 West Texas Export GTC 바인딩. RT 대표요소(RILEY→KRWSW) SF=−0.15 → MCC_RT 양수(+$3,099, GKS LMP↑). DA 대표요소(CLEARCRO→WILLOW CREEK) SF=+0.048 → MCC_DA 음수(−$908, GKS LMP↓). 두 효과 모두 'RT가 DA보다 비싸지는' 방향으로 합류 → DA-RT spread 항상 음수 → long 100%, net −$4,007, RT-dominant. DART 관점 가장 깨끗한 long(단 magnitude 작음).",
        "s4": "West-basin wind(GR_WEST+GR_PANHANDLE) > ~14GW(최강 16–17GW) + 봄(Mar–May) + GTC limit 10.6GW 낮은 설정 ⇒ RT P(bind) ~0%(<14GW)→12–19%(>14GW). DA SF는 부호 반대(+0.048)라 MCC_DA가 음(−), MCC_RT가 양(+) → spread 항상 음 → long 100%(short 0%). 여름엔 wind trough로 급감. net −$4,007 순수 long이나 시간당 magnitude 작음(worst long −$13/h).",
        "s7": "DART read: 순수 LONG, RT-dominant(누적 −$4,007, short 0%/long 100%). DA·RT가 서로 다른 대표요소를 봐 부호가 갈리는데(DA SF +0.048→MCC −$908, RT SF −0.15→MCC +$3,099) 둘 다 'RT가 DA보다 비싸다'로 합류 → 일관된 long. 봄(Mar–May) overnight HE23–HE2·midday, West-basin wind>14GW, GTC 10.6GW 낮은 설정에서 long. magnitude 작아 저우선·RT 기회성.",
        "seasonality": "봄 집중(Mar–May ~180 bind-hr/mo), 연중 꾸준, 여름 저점(Jul–Sep ~10–40hr/mo). 시간: overnight 피크 HE23–HE2(HE24) + midday 보조; 아침 저점 HE4–7. long 기여도 동일 창.",
        "rot": "West-basin wind>14GW(최강 16–17GW) + 봄(Mar–May) overnight HE23–HE2/midday + GTC limit 10.6GW 낮은 설정 → long(RT가 DA보다 비쌈). DA SF 부호 반대라 short 시그널은 없음. 여름·저wind이면 거의 무신호. magnitude 작아 저우선.",
        "net_lean_text": "Net LONG, 순수(누적 −$4,007, short 0%/long 100%, minority share 0): DA SF(+0.048)와 RT SF(−0.15)의 부호 차이로 MCC_DA(−$908)와 MCC_RT(+$3,099)가 spread를 항상 음으로 만듦. RT-dominant(r=0.29).",
        "nuance_text": "여기선 만성/스파이크 양분이 아니라 구조적 일방 long: DA-only 시간도 long(−$266), RT 활성 시간도 long. DA 대표요소가 GKS LMP를 낮추고(MCC_DA<0) RT 대표요소가 올려서(MCC_RT>0) 항상 RT가 DA보다 비쌈 → long. magnitude는 작음(worst −$13/h).",
        "caveats": [
            "GTC LIMIT은 시변(계절): WESTEX 10,630→11,810 MW; 낮은 봄/가을 설정이 피크 바인딩과 일치. 고정 rating 아닌 시변 feature로 취급.",
            "DA·RT가 같은 GTC의 서로 다른 대표요소를 모니터 → GKS SF 부호가 다름: DA SF=+0.048(MCC −$908) vs RT SF=−0.15(MCC +$3,099). spread는 항상 음 → 순수 long; net +$2,191(절대 MCC)이나 DART spread는 −$4,007 long.",
            "BASE CASE(pre-contingency steady-state stability)에서 바인딩, N-1 아님.",
            "GTC element membership 부재 → outage watch-list를 GTC-limit regime으로 대체(section5).",
            "Magnitude 작음(RT λ median $15, P90 $28, P99 $50, max $169) — long 시그널이나 시간당 영향은 소.",
        ],
        "drivers": [
            "Overnight 저load + 고wind 공존(바인딩 피크 HE23–HE2)이나 system-only load로는 wind 신호와 분리 불가.",
            "West-basin wind bind-median 16.7–17.2 GW vs nonbind 7.2–7.7 GW; DA corr(λ, basin-wind)=+0.29; P(bind) ~14GW 미만 ~0, 초과 시 12–19%로 점프. 전형적 고West-wind 수출.",
            "GTC element membership이 datalake에 없음. GTC LIMIT history(10,630–11,810 MW)로 net operator effect 포착; 낮은 봄/가을 설정이 피크 바인딩과 일치.",
            "zonal load/temp 분리 없음; wind/season 신호에 포함.",
            "봄 고wind 피크, 여름(Jul–Sep) wind trough가 바인딩 계절성 견인; West-basin wind이 근위 weather 드라이버.",
        ],
    },
}


def update_datapacks(metrics: dict, derived: Path, convention: str, caveats_common: list[str]):
    for cid, m in metrics.items():
        n = NARR[cid]
        fp = derived / f"datapack_{cid}.json"
        d = json.loads(fp.read_text(encoding="utf-8"))

        d["mechanism"] = n["mechanism"]
        d["section4_rule_of_thumb"] = n["s4"]
        d["section7_gks_read"] = n["s7"]
        d["seasonality_text"] = n["seasonality"]
        d["caveats"] = n["caveats"]

        ev = n["drivers"]
        for i, row in enumerate(d.get("section6_drivers", [])):
            if i < len(ev):
                row["evidence"] = ev[i]

        nz = m["nuance"]
        d["section8_dart_spread"] = {
            "convention": convention,
            "net_lean": m["net_lean"],
            "net_lean_text": n["net_lean_text"],
            "minority_share": m["minority_share"],
            "cum_spread_usd_per_mw": m["cum_spread"],
            "da_cum_usd_per_mw": m["cum_da"],
            "rt_cum_usd_per_mw": m["cum_rt"],
            "da_dominant_or_rt": m["da_dominant_or_rt"],
            "r_da_abs_over_rt_abs": m["r_da_over_rt"],
            "pct_hours_short": m["pct_hours_short"],
            "pct_hours_long": m["pct_hours_long"],
            "mean_spread_when_active": m["mean_spread_when_active"],
            "gross_short_usd_per_mw": m["gross_short_usd_per_mw"],
            "gross_long_usd_per_mw": m["gross_long_usd_per_mw"],
            "nuance": nz,
            "nuance_text": n["nuance_text"],
            "dart_rule_of_thumb": n["rot"],
            "month_hour_spread": m["month_hour_spread"],
            "month_hour_axis_note": "rows=month 1..12; cols index0=HE1 .. index23=HE24 (hour-beginning, col index = hour-of-day). 값=기대 spread 기여 $/MWh-h (0=미바인딩 시간 포함). short=양수, long=음수.",
            "caveats": caveats_common,
        }

        fp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"updated datapack_{cid}.json  net_lean={m['net_lean']} {m['da_dominant_or_rt']}")
