"""
GKS AS strategy recap & analysis: 2026-01-01 .. 2026-05-10 (data avail; user asked thru 05-13)
Products: NSPIN, RRS, ECRS only.
Answers:
  1. per-product avg DA award qty, RT buyback qty, RT sale qty
  2. per-product avg DA price, RT price
  3. NSPIN "full DA sell + full RT buyback" = DA-RT spread P&L
  4. optimal DA/RT AS strategy
"""
import pandas as pd, numpy as np, json

df = pd.read_parquet('shared/data/adhoc/2026-05-07_AS-strategy/derived/master_hourly.parquet')
H = len(df)
PROD = {
    'NSPIN': ('GKS_Gen_NS_Qty',  'GKS_DA_NS_Amt',  'AS_MCPC_NSPIN', 'RT_AS_MCPC_NSPIN', 'AS_SPREAD_NSPIN'),
    'RRS':   ('GKS_Gen_RRS_Qty', 'GKS_DA_RRS_Amt', 'AS_MCPC_RRS',   'RT_AS_MCPC_RRS',   'AS_SPREAD_RRS'),
    'ECRS':  ('GKS_Gen_ECRS_Qty','GKS_DA_ECRS_Amt','AS_MCPC_ECRS',  'RT_AS_MCPC_ECRS',  'AS_SPREAD_ECRS'),
}
CAP = 100.0  # GKS MW

print(f"=== GKS AS RECAP  {df['date'].min()} .. {df['date'].max()}  ({H} hours, {df['date'].nunique()} days) ===\n")

rows = []
for p,(q,amt,dap,rtp,spr) in PROD.items():
    qty = df[q].fillna(0.0)
    offered = qty > 0
    da_rev = df[amt].sum()
    # GKS actual RT AS positions: RT_Ancillary_Imbalance_Amt is 0 across all 130 days -> no RT buyback / RT sale
    rows.append(dict(
        product=p,
        hrs_offered=int(offered.sum()),
        pct_hrs=offered.mean()*100,
        avg_DA_qty_all=qty.mean(),
        avg_DA_qty_offered=qty[offered].mean(),
        avg_RT_buyback_qty=0.0,           # actual
        avg_RT_sale_qty=0.0,              # actual
        avg_DA_price_all=df[dap].mean(),
        avg_DA_price_offered=df.loc[offered,dap].mean(),
        avg_RT_price_all=df[rtp].mean(),
        avg_RT_price_offered=df.loc[offered,rtp].mean(),
        DA_total_rev=da_rev,
    ))
rec = pd.DataFrame(rows).set_index('product')
pd.set_option('display.width',220); pd.set_option('display.float_format',lambda x:f'{x:,.2f}')
print("--- Q1+Q2: per-product actuals ---")
print(rec.to_string())
print()

# --- Q3: NSPIN full-DA-sell + full-RT-buyback = pure DA-RT spread ---
print("--- Q3: NSPIN  'sell 100MW DA every hour, buy 100MW back in RT'  (P&L = 100*(DA-RT)) ---")
for p in PROD:
    dap, rtp = PROD[p][2], PROD[p][3]
    s = df[dap] - df[rtp]                      # DA - RT spread, $/MW/h
    pnl = s * CAP
    win = (s > 0).mean()*100
    print(f"  {p:6s}  spread mean={s.mean():6.2f}  median={s.median():5.2f}  p5={s.quantile(.05):7.2f}  p95={s.quantile(.95):6.2f}"
          f"  | win%={win:5.1f}  total P&L (100MW,all hrs)=${pnl.sum():12,.0f}  worst hr=${pnl.min():,.0f}")
print()

# strategy comparison for NSPIN (and all 3) -- per-MW-of-capacity, all hours
print("--- Q4: strategy comparison  (revenue if you committed 100MW of capacity to this product, all hours) ---")
print(f"{'product':8s}{'S1 buyback($)':>16s}{'S2 hold/deliver($)':>20s}{'RT>DA hrs':>12s}{'cond. S3($)':>14s}")
for p in PROD:
    dap, rtp = PROD[p][2], PROD[p][3]
    da, rt = df[dap], df[rtp]
    s1 = ((da-rt)*CAP).sum()                          # sell DA, buy back all RT
    s2 = (da*CAP).sum()                               # sell DA, deliver (hold) -> keep full DA payment
    # S3 conditional: buy back when DA>RT (capture spread + free battery), deliver when RT>=DA
    s3 = (np.where(da>rt, (da-rt), 0.0)*CAP).sum() + (np.where(da<=rt, da, 0.0)*CAP).sum()
    print(f"{p:8s}{s1:16,.0f}{s2:20,.0f}{(rt>da).sum():12d}{s3:14,.0f}")
print()
print("note: S2 'hold' commits the 100MW (no RT energy arb); S1/S3 free the battery for RT energy.")

rec.reset_index().to_json('shared/data/adhoc/2026-05-07_AS-strategy/derived/gks_as_recap_jan_may.json', orient='records', indent=1)
