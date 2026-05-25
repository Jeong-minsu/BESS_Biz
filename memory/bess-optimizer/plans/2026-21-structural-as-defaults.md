# Plan: Structural AS Default Rules (ECRS, RRS, Non-Spin) — 2026-21

**Issue**: Two consecutive cycles (2026-05-22 and 2026-05-24) confirmed that bess-optimizer missed structural AS clearing windows:
- ECRS: cleared HE07-10 (morning ramp) both days — not recommended
- RRS: cleared HE19-24 (evening tail) both days — not recommended
- Non-Spin: GKS cleared $1,100-1,450 vs Smartbidder benchmark $2,558-2,683 (persistent -$1,100 gap)

These are structural patterns, not one-off events. The charge window mis-selection (overnight vs solar trough) was also corrected but not yet embedded in the recommendation template.

**Priority**: MAJOR

## Actions

- Encode three structural defaults into the bess-optimizer recommendation template for May-September:
  1. ECRS: offer 30-50 MW at HE07-10 (morning ramp) as default; remove ECRS from HE20-22 as primary slot.
  2. RRS: offer 20-40 MW at HE22-24 (evening tail, post-primary-discharge) when SoC is near-zero; this captures tail revenue at near-zero opportunity cost.
  3. Non-Spin: review MW sizing — current 50 MW offering may be below the clearing threshold that Smartbidder achieves. Evaluate whether 70-100 MW Non-Spin offer improves capture rate.
- For the charge window, establish a conditional rule: if solar DA price trough (HE09-14) is more than $6/MWh below overnight price (HE02-04), default to solar trough charge. Apply May 1 through September 30.
- Starting SoC: request pnl-manager provide end-of-day SoC estimate from Tenaska HSL data each settlement day; use this as the next-day starting SoC input.
