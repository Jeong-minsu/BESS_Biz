# -*- coding: utf-8 -*-
"""NEG-side runner: DART spread (DA-RT congestion basis) for the 5 LIVE NEG constraints
(E_PASP, VALEXP, BRUNI_69_1, LOYOLA_69_1, LASCRU_MILO1_1) at GKS_BESS_RN.

REUSES the shared POS machinery (dart_spread.load / per_constraint / CONVENTION / CAVEATS_COMMON)
so the section8_dart_spread schema is IDENTICAL to the POS datapacks (main thread renders uniformly).
Rewrites KR / DART-framed text fields (removing the old charge/discharge wording) + injects section8.

NEG sign note (INVERSE of POS): MCC = -SF*lambda is NEGATIVE (LMP down). Chronic DA binding pushes
DA MCC more negative => DA cheaper => spread = MCC_DA - MCC_RT < 0 => LONG. RT cap-out spike pushes
RT more negative => RT cheaper => spread > 0 => SHORT. (verified: da_only_lean=long, rt_spike=short for all 5)

Run:  python build_dart_section8.py
"""
from __future__ import annotations
import json
from pathlib import Path

import dart_spread as D  # shared POS module (load, per_constraint, CONVENTION, CAVEATS_COMMON)

NEG_TARGETS = ["E_PASP", "VALEXP", "BRUNI_69_1", "LOYOLA_69_1", "LASCRU_MILO1_1"]

NARR = {
    "E_PASP": {
        "mechanism": "GKS의 Valley/South-TX 수출 조류가 PAWNEE→CALAVERAS 345(SA-import interface)를 북상 적재(양의 SF +0.244) → 혼잡 악화 → GKS_BESS_RN MCC 기여 음수(LMP↓). NEG 클러스터 최대 SF. 만성 DA 바인딩(4,539h)이 DA MCC를 RT보다 깊게 눌러(DA −$56,360 vs RT −$22,983) DA가 더 쌈 → DA-RT spread<0 → net LONG. 드문 RT 캡아웃 스파이크 땐 RT가 더 눌려 spread>0 → 그 시간만 short. DART 관점: 평상시 long, RT 스파이크 시 short인 양면 신호이나 $·시간 모두 long 우세.",
        "s4": "저녁 HE17-21 + South/coastal wind >1.5GW + South load >5GW ⇒ P(bind)~45-56%. 만성 DA 우위로 DA가 더 싸 long 우위(long 시간 85.3%, DA-only 3,517h 누적 −$28,357 long). RT 캡아웃 스파이크(top-decile 122h)의 82%만 short(겨울 다일 수출·scarcity, λ→$1k+, max short +$1,923/h). 누적 net LONG −$33,377/MW. long=평상 DA 바인딩, short=RT 스파이크.",
        "s7": "DART read: net LONG(누적 −$33,377/MW, DA-dominant r=2.45). 만성 DA 혼잡이 DA를 RT보다 깊게 눌러(DA −$56,360 vs RT −$22,983) DA가 싸짐 → long 시간 85.3%. 저녁 HE17-21 고South/coastal-wind·고SA부하일 LONG. RT 캡아웃 스파이크(122h 중 82% short)에만 단기 short 전환. 2026-06-08까지 연속 바인딩 = 견고한 forward long 시그널. NEG 클러스터 최대 SF·최대 누적.",
        "seasonality": "월별: 2026-01 에피소드 지배, 이후 8/7월(여름 풍력+부하); ex-episode 여름 집중. RT: 5/1/8/7월. 시간: 저녁 피크 HE17-21(P(bind) 45-56%), 야간 저조(13-17%). long 기여도 동일 창; RT 스파이크(=short)는 겨울 다일 이벤트에 집중.",
        "rot": "평상시(저녁 HE17-21 DA 만성 바인딩, RT 미스파이크; DA-only 3,517h −$28,357) → LONG(DA가 더 쌈). RT 캡아웃 스파이크(겨울 다일 수출·scarcity, λ→$1k+) → 그 시간만 SHORT. 누적·시간 모두 long 우세 → 기본 long, RT 스파이크 이벤트 short.",
        "net_lean_text": "Net LONG(누적 spread −$33,377/MW, minority share 0.213): 만성 DA 혼잡이 DA MCC를 −$56,360까지 눌러 RT MCC(−$22,983)보다 깊음 → DA가 더 싸 spread<0. 시간 85.3% long, gross long $45,717 vs gross short $12,340. DA-dominant(r=2.45).",
        "nuance_text": "만성 DA-dominant(DA 4,539h vs RT 776h) → DA가 더 눌려 DA-only 3,517h 전부 long(−$28,357). RT 캡아웃 시 RT가 더 세게 눌려 top-decile RT 122h 중 82% short(max short +$1,923/h). NEG 부호 직관(만성 DA→long, RT-spike→short)·데이터 일치. task의 'E_PASP DA-dominant→net long' 예상과 일치(검증).",
        "caveats": [
            "2026-01 −$17.5k 3일 에피소드(1/24-26) = DA 누적의 31%; ex-episode DA −$38.9k. 이 에피소드가 RT-spike(short) 기여의 상당부분.",
            "RTI BASE-CASE interface(GTC-like), 단일 감시선 N-1 아님 — binding 물리 다름; interface-vs-N1을 feature로 임베드.",
            "단일 $15,341 RT msf 값은 미확인 outlier; rt-corroborated severity(~$3,665 peak) 사용.",
            "section5 outage lift: 대부분 일자 바인딩 → frequency-lift 거의 무변별, severity-lift 사용. co-occurrence ≠ causation, NMMS 멤버십 아님.",
            "패널 λ는 DA-scale(median bind/evening 25.8); section3 lambda_cond은 DA median(RT 아님).",
            "R&R: 본 datapack의 spread/lean은 congestion-driven basis 시그널 특성만(congestion-analyst). 포지션 사이징·승률·손익비·입찰은 dart-virtual-trader 몫 — position 추천 아님.",
        ],
        "drivers": [
            "P(bind) 10%→47%, South 부하 3→7GW 상승 시; corr +0.29. 수출-대-부하 interface: 저녁 San-Antonio/South 고부하가 South-TX 발전을 PAWNEE→CALAVERAS로 북상시킴.",
            "주 드라이버. P(bind) 7%→40%, South wind 0→2500MW; coastal-wind corr +0.45(단일 최고), south-wind +0.26. >3000MW South wind 시 P(bind) 하락(전역 surplus). Solar corr +0.06 = 불충분.",
            "2026-01-24~26 = 3일 24/24h 바인딩, λ med $206/$1061/$314, max $4,566(=DA 누적의 31%). base-case interface → SA-import corridor의 STANDING 평행-345 derate signature(N-1 아님). section5 episode 목록 참조; 미확정(co-occurrence).",
            "부하가 채널(San-Antonio 여름/겨울 피크); 본 패널에서 부하와 별도 분리 안 됨.",
            "Coastal+South 풍력 주입(공급 채널)이 지배적 weather 드라이버; coastal-wind corr +0.45. Solar 미미(+0.06).",
        ],
    },
    "VALEXP": {
        "mechanism": "GKS Valley 방출/순수출이 매우 낮은 Valley Export 안정도 interface를 적재(양의 SF ~+1.0) → interface 혼잡 상승이 GKS LMP를 끌어내림(MCC 음수). solar off·Valley 순부하 낮을 때 가장 강함. base-case GTC라 DA·RT 모두 바인딩하지만 RT 혼잡(RT MCC −$13,004)이 DA(−$4,930)를 압도 → RT가 더 싸 DA-RT spread>0 → dollar net SHORT. 단 시간 기준 67%는 완만한 long(DA 우위) — 큰 $는 RT scarcity 스파이크에서 발생. 부호는 가정 아닌 데이터로 확정.",
        "s4": "Nov-May 비여름 + 야간/저녁(HE1-7, HE18-22, solar off) + Valley(GR_SOUTH) wind 0.5-1.5GW + 낮은 GTC limit(≤900MW) ⇒ RT P(bind)~10-18%. 데이터상 dollar net SHORT(RT-dominant, 누적 spread +$8,075/MW): RT λ 스파이크(→$4304, top-decile 58h 100% short, max +$2,008/h)가 DA보다 깊어 RT가 쌈. 단 일반 시간대 67%는 완만한 LONG(DA-only 946h −$3,405). 여름·한낮(HE10-16) solar가 interface RELIEVE → 거의 무신호.",
        "s7": "DART read: net SHORT(누적 +$8,075/MW, RT-dominant r=0.38). base-case GTC라 DA·RT 동시 바인딩이나 spread 부호는 데이터로 확정 → RT 누적(−$13,004) > DA(−$4,930) 깊이라 RT가 쌈. RT scarcity 스파이크(겨울/봄 solar-off 야간, GTC tight)가 $를 지배. 단 hour-count 67%는 LONG(완만 DA 우위) — 평상 약 long, RT 스파이크 강 SHORT. 여름·한낮 무신호. GKS 최대 SF(~+1.0 DA, +0.98 RT).",
        "seasonality": "겨울+봄 지배(12/1/11월 + 4월 RT 스파이크); 여름 ~0. 시간: 야간 HE2-6(피크 HE5) + 저녁 HE17-20(HE18) bimodal; 한낮 HE10-16 저조. short($) 기여는 RT 스파이크(겨울/봄 야간)에 집중.",
        "rot": "평상 시간대(완만 DA 우위; DA-only 946h −$3,405) → 약 LONG. RT scarcity 스파이크(겨울/봄 solar-off 야간, GTC tight; top-decile RT 58h 100% short, λ→$4304) → 강한 SHORT. dollar net은 RT-dominant라 SHORT(+$8,075/MW). 여름·한낮 무신호.",
        "net_lean_text": "Net SHORT(누적 +$8,075/MW, RT-dominant r=0.38, minority share 0.241): RT 혼잡·λ 스파이크(RT MCC −$13,004)가 DA(−$4,930)를 압도 → RT가 더 싸 spread>0. gross short $11,820 vs gross long $3,745. 단 시간 기준은 67% long(완만 DA 우위). 부호는 가정 아닌 데이터로 확정.",
        "nuance_text": "base-case GTC라 DA·RT 둘 다 바인딩 — spread 부호 데이터로 확정. RT-dominant → dollar net SHORT(+$8,075). 그러나 hour-count 67% long(평상 완만 DA 우위, DA-only 946h −$3,405). 큰 $는 RT scarcity 스파이크(top-decile 58h 100% short, max +$2,008/h)에서. '평소 약 long, RT 스파이크 강 short', $는 short 지배. NEG 부호 직관(만성 DA→long, RT-spike→short) 일치.",
        "caveats": [
            "GTC LIMIT은 시변(운영자/ERCOT Quarterly Stability): 625→1,140MW(23mo, 2026-02-04 Greater Valley 업데이트 상향). fixed rating 아닌 시변 feature; binding 빈도/타이밍이 각 GTC 업데이트마다 단계 변화.",
            "BASE CASE(pre-contingency 정상상태 안정도) 바인딩, N-1 아님 — Houston N-1 corridor와 구분.",
            "DA·RT 동일 GTC 강제: DA SF=+1.000(pseudo-line '- 0KV VALEXP'), RT SF~+0.98 — 둘 다 GKS LMP를 끌어내림(MCC 동일 음부호, WESTEX와 달리 DA/RT SF 부호 충돌 없음). spread 부호는 DA/RT 심도 차에서 옴.",
            "datalake zonal 부하 부재(system-only) → demand lens는 diurnal/계절로 추론.",
            "GTC element 멤버십 부재 → outage watch-list 대신 GTC-limit regime(section5).",
            "R&R: 본 datapack의 spread/lean은 congestion-driven basis 시그널 특성만(congestion-analyst). 포지션 사이징·승률·손익비·입찰은 dart-virtual-trader 몫 — position 추천 아님.",
        ],
        "drivers": [
            "낮은 Valley 순부하에서 바인딩(겨울-야간 저부하 계절성); datalake zonal 부하 부재로 diurnal/계절 binding 패턴 추론(HE2-6 + HE18-20 피크, 한낮 저조).",
            "SouthEast solar bind-median 0 vs nonbind 32-77MW; 한낮 solar가 국소 흡수·interface RELIEVE. GR_SOUTH wind 중-저(bind-median ~1023MW); Valley wind 상승 시 P(bind) 감소(역방향, surge 아님).",
            "GTC element 멤버십 datalake 부재. 운영자 net 효과는 GTC LIMIT 이력(625→935→690→920→1075→1140MW)으로 포착; 2026-02-04 Greater Valley GTC 업데이트가 limit 단계 상향.",
            "겨울-야간 저부하 집중(12/1/11월 + 4월)이 저온 저순부하 regime와 일치; system-only 부하로 직접 귀속 제한.",
            "Solar diurnal cycle가 강하게 변조(한낮 relief); 겨울+봄 regime 지배, 여름 ~0.",
        ],
    },
    "BRUNI_69_1": {
        "mechanism": "GKS deep-South 주입이 BRUNI 138/69 autotransformer 통한 South-TX 수출에 가산; 양의 SF(~0.013) → post-contingency 과부하 악화 → 자기 LMP 하락(MCC 음수). 만성 DA 바인딩(4,022h)이 DA MCC를 RT보다 깊게 눌러(DA −$10,343 vs RT −$7,274) DA가 더 쌈 → DA-RT spread<0 → net long-leaning. SF 작아 per-event 작지만 RT 캡아웃(→$3500) 스파이크 시 그 시간만 short. balanced(DA 약우위)이라 net은 mixed(long-leaning).",
        "s4": "야간 HE22-07 + GR_SOUTH wind >2GW + FO-AV-LO Laredo 컨틴전시 활성 ⇒ P(bind)~44-57%. 만성 DA 우위로 DA가 더 싸 long 시간 83%(DA-only 2,657h 누적 −$6,032 long). RT autotransformer 캡아웃 스파이크(top-decile 81h 중 97.5% short, λ→$3500, max short +$46/h)만 short. 누적 spread −$3,070/MW(net mixed, long-leaning). long=평상 DA 바인딩, short=RT 스파이크.",
        "s7": "DART read: net MIXED, long-leaning(누적 −$3,070/MW, minority 0.364, balanced r=1.42). 만성 DA 바인딩(4,022 DA h)이 DA를 RT보다 깊게 눌러(DA −$10,343 vs RT −$7,274) 평상시 long 시간 83%. 야간 고South풍력일 LONG, RT autotransformer 캡아웃 스파이크(81h 97.5% short)에만 short. SF 작아 per-event 작음 — 빈도형 long tailwind + 드문 short 스파이크. 클러스터 D 최고 RT-severity(RT mean λ $978).",
        "seasonality": "봄(4월 최대 −$3.96k DA) + 12/1월 보조. 야간 HE22-07 지배; 한낮 저조. long 기여 동일 창; RT 스파이크(=short)는 겨울/봄 캡아웃 이벤트.",
        "rot": "야간 고South풍력 평상시(DA-only 2,657h −$6,032) → LONG(DA가 더 쌈). RT autotransformer 캡아웃 스파이크(top-decile 81h 97.5% short, λ→$3500) → 그 시간만 SHORT. net mixed이나 long-leaning(−$3,070/MW) → 기본 약 long, RT 스파이크 short.",
        "net_lean_text": "Net MIXED, long-leaning(누적 −$3,070/MW, minority share 0.364): DA MCC(−$10,343)가 RT(−$7,274)보다 깊어 DA가 더 쌈 → long쪽. 시간 83% long, gross long $7,188 vs gross short $4,119. balanced(r=1.42, DA 약우위)이라 minority 36%로 mixed.",
        "nuance_text": "평소 long(만성 N-1 DA 바인딩, DA-only 2,657h −$6,032), RT autotransformer 캡아웃 스파이크 시 short(top-decile 81h 97.5% short, λ→$3500). DA가 약우위라 누적 long-leaning이나 minority 36%로 net mixed. NEG 부호 직관(만성 DA→long, RT-spike→short) 일치.",
        "caveats": [
            "section2 컬럼 = HE1..HE24(index0=HE1).",
            "SF 미소(~0.013) → per-MWh per-event 작음; 수천 DA시간 바인딩으로만 material.",
            "BRUNI & LASCRU_MILO은 DFOAVLO5 컨틴전시 공유 → 동일 FO-AV-LO outage 주변 전기적 결합.",
            "관측 RT transmission cap = $3500.",
            "R&R: 본 datapack의 spread/lean은 congestion-driven basis 시그널 특성만(congestion-analyst). 포지션 사이징·승률·손익비·입찰은 dart-virtual-trader 몫 — position 추천 아님.",
        ],
        "drivers": [
            "GR_SOUTH wind 2266 vs 1486MW binding/non(2025-04, 1.52x); 야간 P(bind) 2%→57%, wind <0.5GW→>2.5GW.",
            "100% post-contingency(FO-AV-LO 그룹); base-case 바인딩 없음. 특정 outage 귀속 불가(CRR Network Model 부재); 실-outage lift 비변별(sec5).",
            "야간 피크가 야간 South-wind surge와 분리 안 됨.",
            "4/12/1월 피크; 2026-01 겨울 이벤트 동시발생이나 temp가 wind와 분리 안 됨.",
            "봄/쿨시즌 고풍력 저-solar 윈도우; wind와 별도 검증 안 됨.",
        ],
    },
    "LOYOLA_69_1": {
        "mechanism": "GKS 주입이 LOYOLA 138/69 변압기 통한 South-TX 수출 적재; 양의 SF(~0.012-0.015) → post-contingency 과부하 악화 → 자기 LMP 하락(MCC 음수). DA·RT 혼잡 심도 균형(DA MCC −$6,770 ≈ RT −$7,343) → dollar net 사실상 MIXED(+$573/MW). 시간 기준 77%는 long(만성 DA가 더 쌈), RT 캡아웃(→$3500) 스파이크가 $를 short쪽으로 상쇄해 방향성 약함.",
        "s4": "저녁 HE18-21 + GR_SOUTH wind >1.5-2GW + Loyola 단일요소 N-1(SN_SLON5/SKLELOY8) ⇒ P(bind)~34-44%. spread MIXED(누적 +$573/MW, minority 0.47): 시간 77% LONG(DA가 더 쌈, DA-only 2,441h −$3,536), RT 캡아웃 스파이크(top-decile 112h 중 98.2% short, λ→$3500, max +$97/h)가 $를 거의 상쇄 → 방향성 약함. 평상 약 LONG, RT 스파이크 SHORT.",
        "s7": "DART read: net MIXED(누적 +$573/MW, balanced r=0.92, minority 0.47) — DA/RT 심도 균형. 클러스터 D 최다 DA binder(4,435 DA h)라 시간 77% long이나 RT 캡아웃 스파이크가 $를 short으로 상쇄해 net 방향성 약함. 단방향 베팅보다 조건부(RT-spike=short, 평상=long) 접근. SF 작아 per-event 작음.",
        "seasonality": "봄(5월 최대 −$1.59k DA / −$1.79k RT, 4월) + 11월. 저녁 HE18-21 지배. long(평상)·short(RT 스파이크) 모두 동일 창.",
        "rot": "평상 저녁 고South풍력(DA-only 2,441h −$3,536) → 약 LONG(DA가 더 쌈). RT 변압기 캡아웃 스파이크(top-decile 112h 98.2% short, λ→$3500) → SHORT. dollar net MIXED(+$573/MW)라 단방향성 약함 — 조건부 시그널로만.",
        "net_lean_text": "Net MIXED(누적 +$573/MW, minority share 0.47): DA MCC(−$6,770)≈RT MCC(−$7,343) 균형 → 방향성 미약. 시간 77% long, gross short $5,006 ≈ gross long $4,434. balanced(r=0.92).",
        "nuance_text": "평소 long(만성 DA 바인딩, DA-only 2,441h −$3,536), RT 변압기 캡아웃 스파이크 시 short(top-decile 112h 98.2% short, λ→$3500). DA·RT 거의 균형 → net 방향성 약함(mixed). 단방향 베팅보다 'RT 스파이크=short, 평상=long' 조건부. NEG 부호 직관 일치.",
        "caveats": [
            "section2 컬럼 = HE1..HE24(index0=HE1).",
            "rt LIMITMW ~38MW(소요소) → 빠른 포화 → RT λ가 $3500 cap 충돌.",
            "SF 미소(~0.012-0.015); 가치는 바인딩 빈도, per-event 크기 아님.",
            "Loyola 컨틴전시(SN_SLON5/SKLELOY8)는 BRUNI/LASCRU FO-AV-LO 그룹과 별개.",
            "R&R: 본 datapack의 spread/lean은 congestion-driven basis 시그널 특성만(congestion-analyst). 포지션 사이징·승률·손익비·입찰은 dart-virtual-trader 몫 — position 추천 아님.",
        ],
        "drivers": [
            "GR_SOUTH wind 1854 vs 977MW binding/non(2025-05, 1.90x); 저녁 P(bind) 11%→44%, wind bins.",
            "100% post-contingency(SN_SLON5/SKLELOY8 단일요소 N-1); 실-outage lift 비변별(sec5).",
            "저녁 HE18-21이 국소 부하 피크와 정렬되나 저녁 wind 램프와 동시; 분리 안 됨.",
            "5/4/11월 피크; temp가 wind/계절성과 분리 안 됨.",
            "shoulder-시즌 고풍력 윈도우; 별도 검증 안 됨.",
        ],
    },
    "LASCRU_MILO1_1": {
        "mechanism": "GKS 주입이 LASCRUCE-MILO 138kV 선로 경로의 South-TX 수출에 가산; 큰 양의 SF(~0.09, 변압기들의 ~7배) → post-contingency 과부하 악화 → 자기 LMP 하락(MCC 음수). DA·RT 심도 균형(DA MCC −$5,052 ≈ RT −$5,470) → dollar net MIXED(+$419/MW). 시간 79%는 long(만성 DA가 더 쌈), RT 선로 캡아웃 스파이크가 $를 short쪽으로 상쇄. Mar-Sep 휴면.",
        "s4": "쿨시즌(10-1월) 저녁/야간 + GR_SOUTH wind >1.5-2GW + DFOAVLO5 활성 ⇒ 바인딩(클러스터 D 최대 per-event SF ~0.09). spread MIXED(누적 +$419/MW, minority 0.468): 시간 79% LONG(DA가 더 쌈, DA-only 1,019h −$2,577), RT 캡아웃 스파이크(top-decile 45h 100% short, max +$206/h)가 $를 상쇄. South wind <~0.9GW 또는 온난월(3-9월) ~0(휴면). 평상 약 LONG, RT 스파이크 SHORT.",
        "s7": "DART read: net MIXED(누적 +$419/MW, balanced r=0.92, minority 0.468) — DA/RT 심도 균형. 클러스터 D 최대 per-event SF(~0.09). 쿨시즌 저녁/야간 고South풍력 평상시 약 LONG(시간 79%), RT 선로 캡아웃 스파이크 시 SHORT. 온난월 무신호(휴면). 단방향성 약함 → 조건부 시그널.",
        "seasonality": "가을/겨울만(11월 최대 −$2.31k DA, 1/10월); 2026-01 최대 RT월(−$2.37k). 저녁/야간 HE19-23. 3-9월 사실상 휴면. long(평상)·short(RT 스파이크) 모두 쿨시즌 한정.",
        "rot": "쿨시즌 저녁/야간 고South풍력 평상(DA-only 1,019h −$2,577) → 약 LONG(DA가 더 쌈). RT 선로 캡아웃 스파이크(top-decile 45h 100% short, max +$206/h) → SHORT. dollar net MIXED(+$419/MW, minority 0.468). 온난월(3-9월) 무신호.",
        "net_lean_text": "Net MIXED(누적 +$419/MW, minority share 0.468): DA MCC(−$5,052)≈RT MCC(−$5,470) 균형. 시간 79% long, gross short $3,516 ≈ gross long $3,097. balanced(r=0.92). 쿨시즌 한정(3-9월 휴면).",
        "nuance_text": "평소 long(쿨시즌 만성 DA 바인딩, DA-only 1,019h −$2,577), RT 선로 캡아웃 스파이크 시 short(top-decile 45h 100% short, max +$206/h). DA·RT 균형 → net mixed. 3-9월 휴면. '평소 약 long, RT 스파이크 강 short'. NEG 부호 직관 일치.",
        "caveats": [
            "section2 컬럼 = HE1..HE24(index0=HE1); 3-9월은 진짜 0(휴면), null 아님.",
            "BRUNI & LASCRU_MILO은 DFOAVLO5 컨틴전시 공유 → 전기적 결합.",
            "클러스터 최대 SF(~0.09)이나 바인딩 시간 최소; RT 가치 episodic(1/11월 쿨시즌 이벤트).",
            "저녁-윈도우 wind 임계는 쿨시즌 조건부; 쿨시즌 야간이 진짜 트리거.",
            "R&R: 본 datapack의 spread/lean은 congestion-driven basis 시그널 특성만(congestion-analyst). 포지션 사이징·승률·손익비·입찰은 dart-virtual-trader 몫 — position 추천 아님.",
        ],
        "drivers": [
            "GR_SOUTH wind 1815 vs 769MW binding/non(2026-01, 2.36x = 클러스터 최고 wind 민감도); 3-9월 바인딩 소멸.",
            "100% post-contingency, DFOAVLO5 지배(BRUNI와 동일 FO-AV-LO outage). 특정 outage 비변별(sec5).",
            "가을/겨울 지배(11/1/10월), 최대 RT월 2026-01(−$2.37k) 겨울 이벤트; cold-load가 고풍력과 분리 안 됨.",
            "저녁 HE19-23 피크가 국소 부하와 정렬되나 wind 램프와 동시.",
            "한낮 binding 저조가 South-solar 수출 relief와 일치; 직접 검증 안 됨.",
        ],
    },
}


def update_datapacks(metrics, derived, convention, caveats_common):
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
            "nuance": m["nuance"],
            "nuance_text": n["nuance_text"],
            "dart_rule_of_thumb": n["rot"],
            "month_hour_spread": m["month_hour_spread"],
            "month_hour_axis_note": "rows=month 1..12; cols index0=HE1 .. index23=HE24 (hour-beginning, col index = hour-of-day). 값=기대 spread 기여 $/MWh-h (0=미바인딩 시간 포함). short=양수, long=음수.",
            "caveats": caveats_common,
        }

        fp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"updated datapack_{cid}.json  net_lean={m['net_lean']} {m['da_dominant_or_rt']} cum_spread={m['cum_spread']}")


def main():
    df = D.load()
    metrics = {t: D.per_constraint(df, t) for t in NEG_TARGETS}
    (D.DERIVED / "dart_spread_metrics_neg.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    update_datapacks(metrics, D.DERIVED, D.CONVENTION, D.CAVEATS_COMMON)


if __name__ == "__main__":
    main()
