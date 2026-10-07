"""ITEM 6 - consolidate the regime / congestion / rules outputs into one dashboard-shaped JSON
(derived/item6_dashboard.json) and print the numbers quoted in item6_FINDINGS.md."""
import json, numpy as np, pandas as pd
from item6_common import D

reg = json.load(open(D / "item6_regime_stats.json")); cg = json.load(open(D / "item6_congestion_stats.json"))
rb = json.load(open(D / "item6_rules_backtest.json")); perm = json.load(open(D / "item6_permutation_null.json"))
bt = pd.DataFrame(rb["backtest"]); by = pd.DataFrame(rb["by_year_season"])
ex = pd.DataFrame(cg["exante_rules"]); pers = pd.DataFrame(cg["persistence"]); expost = pd.DataFrame(cg["expost"])
sep = pd.DataFrame(reg["feature_separation"])

# hypothesis tally (rules backtest counted once per window, not per part)
tally = {**reg["hypothesis_tally"], **{k: v for k, v in cg["hypothesis_tally"].items() if not k.startswith("exante_rule_test")}}
tally["rules_backtest_predeclared"] = dict(n_tests=int(bt[bt.part == "test"].shape[0]))
total = int(sum(v["n_tests"] for v in tally.values()))
bh_total = int(sum(v.get("n_bh_q10", 0) for v in tally.values()))

cols = ["rule", "n_hours", "n_days", "ev_per_mwh", "per_day_per_mw", "hit_rate_hours", "hit_rate_days", "sharpe_daily", "sharpe_annualised", "max_drawdown_per_mw", "worst_hour", "t_stat", "ev_sys_part", "ev_basis_part"]
oos = {w: bt[(bt.window == w) & (bt.part == "test")].sort_values("ev_per_mwh", ascending=False)[cols].to_dict(orient="records") for w in ("REAL", "FULL")}
tvt = pd.DataFrame(rb["train_vs_test"])

def rows(w, names):
    x = bt[(bt.window == w) & bt.rule.isin(names)].pivot_table(index="rule", columns="part", values="ev_per_mwh")
    return x.round(3).reset_index().to_dict(orient="records")

# leakage decomposition of the persistence rule
p1 = bt[(bt.window == "FULL") & (bt.part == "all") & (bt.rule == "P_follow_yesterday_sign_perHE_lag1_leaky")].ev_per_mwh.iloc[0]
p2 = bt[(bt.window == "FULL") & (bt.part == "all") & (bt.rule == "P_follow_yesterday_sign_perHE_lag2_strict")].ev_per_mwh.iloc[0]
leak = dict(full_lag1_leaky_ev=p1, full_lag2_strict_ev=p2, share_of_lag1_edge_from_leakage=round(1 - p2 / p1, 2),
            real_lag1=bt[(bt.window == "REAL") & (bt.part == "all") & (bt.rule == "P_follow_yesterday_sign_perHE_lag1_leaky")].ev_per_mwh.iloc[0],
            real_lag2=bt[(bt.window == "REAL") & (bt.part == "all") & (bt.rule == "P_follow_yesterday_sign_perHE_lag2_strict")].ev_per_mwh.iloc[0])

# regime shrinkage (REAL, conditional long-morning rules vs static morning long)
rr = tvt[(tvt.window == "REAL") & tvt.rule.str.startswith("R_")]
shrink = dict(mean_train_ev=round(float(rr.train.mean()), 2), mean_test_ev=round(float(rr.test.mean()), 2), mean_shrink=round(float(1 - rr.test.mean() / rr.train.mean()), 2),
              static_morning_long_test_ev=float(tvt[(tvt.window == "REAL") & (tvt.rule == "B_long_HE7-11_static")].test.iloc[0]),
              baseline_B0_test_ev=float(tvt[(tvt.window == "REAL") & (tvt.rule == "B0_item3a_long_HE3,5,7-11")].test.iloc[0]))

# congestion: persistence headline + ex-ante survivors on both windows
pers_full = pers[pers.window == "FULL"][["constraint", "p_bind_day", "p_bind_given_bind_lag1", "lift_lag1", "p_bind_given_bind_lag2", "lift_lag2", "p_bind_he_given_bind_same_he_lag1", "p_bind_he_base"]]
pers_real = pers[pers.window == "REAL"][["constraint", "p_bind_day", "p_bind_given_bind_lag1", "lift_lag1", "p_bind_given_bind_lag2", "lift_lag2", "p_bind_he_given_bind_same_he_lag1", "p_bind_he_base"]]
exc = ["window", "constraint", "lag", "side", "typical_HEs", "n_signal_days", "n_hours", "ev_per_mwh", "t_stat", "hit_rate_hours", "sharpe_daily", "worst_hour", "max_drawdown_per_mw", "ev_uncond_same_hours", "p_vs_uncond", "ev_sys_part", "ev_basis_part", "ev_train", "ev_test", "n_test", "t_test", "bh_exante_rule_ev", "bh_exante_rule_test_window"]
ex_surv = ex[(ex.ev_per_mwh > 0) & ex.bh_exante_rule_ev & (ex.ev_test > 0) & ex.bh_exante_rule_test_window][exc]
stpwap_by = by[(by.window == "FULL") & (by.rule == "C_short_HE14-18_if_STPWAP39_1_bound_lag2")].pivot_table(index="season", columns="year", values="ev_per_mwh").round(2)
stpwap_n = by[(by.window == "FULL") & (by.rule == "C_short_HE14-18_if_STPWAP39_1_bound_lag2")].pivot_table(index="season", columns="year", values="n_hours")

out = dict(
    meta=dict(item="item6", question="Is there a regime- or congestion-conditional DART edge at RVN_RN beyond the item3a $1.23/MWh baseline?",
              convention="spread = DA - RT; short PnL = +spread; 1 MW per traded hour; no clearing model / fees", windows=rb["meta"]["windows"],
              data="real Yes Energy datalake prices (RVN_RN own from 2026-06-04, item2 NNLS proxy before) + item2 congestion panel + datalake system load/wind/solar actuals; no mock"),
    verdict=dict(conditional_edge_exists="marginal at best; nothing beats the unconditional hour-of-day rule out-of-sample on EV/MWh",
                 best_strict_ex_ante_rule="C_short_HE14-18_if_STPWAP39_1_bound_lag2 (FULL test EV 1.07 $/MWh, t 2.7, hit 63%, Sharpe 0.14/day) - but static short HE14-18 gives 1.32 on the same test window; the condition only improves hit rate/drawdown",
                 baseline_item3a_real_test_ev=shrink["baseline_B0_test_ev"], total_hypotheses_tested=total, bh_q10_rejections_total=bh_total,
                 regime_family_permutation_p=perm["p_value_family"]),
    hypothesis_tally=tally, hypothesis_total=total, permutation_null=perm,
    regime=dict(feature_separation=sep.to_dict(orient="records"), shrinkage_real=shrink, leakage_persistence=leak,
                rt_vol_regime_sign_flip=by[(by.window == "FULL") & (by.rule == "R_long_HE7-11_if_rt_vol_lag2_high")].pivot_table(index="season", columns="year", values="ev_per_mwh").round(2).reset_index().to_dict(orient="records")),
    congestion=dict(persistence_full=pers_full.to_dict(orient="records"), persistence_real=pers_real.to_dict(orient="records"),
                    exante_rules_all=ex[exc].to_dict(orient="records"), exante_rules_surviving_both_bh=ex_surv.to_dict(orient="records"),
                    expost_real=expost[expost.window == "REAL"].sort_values("p").to_dict(orient="records"),
                    basis_share=cg["basis_share"], stpwap_by_year_season=dict(ev=stpwap_by.reset_index().to_dict(orient="records"), n_hours=stpwap_n.reset_index().to_dict(orient="records"))),
    rules=dict(oos_test=oos, train_vs_test=tvt.round(3).to_dict(orient="records"), by_year_season=by.to_dict(orient="records")),
)
json.dump(out, open(D / "item6_dashboard.json", "w"), indent=1, default=str)
pd.set_option("display.width", 300); pd.set_option("display.max_rows", 200)
print("TOTAL hypotheses:", total, "| BH q10 rejections:", bh_total); print(json.dumps(tally, indent=1))
print("\nleakage:", leak); print("\nshrink:", shrink)
print("\nSTPWAP lag2 by season x year EV:\n", stpwap_by, "\n n:\n", stpwap_n)
print("\nex-ante survivors both BH:\n", ex_surv.to_string())
print("\nsep FULL HE grain:\n", sep[(sep.grain == "HE") & (sep.window == "FULL")][["feature", "avail", "n_bh_sig", "median_p"]].to_string())
print("\nsep REAL HE grain:\n", sep[(sep.grain == "HE") & (sep.window == "REAL")][["feature", "avail", "n_bh_sig", "median_p"]].to_string())
