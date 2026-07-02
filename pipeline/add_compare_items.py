#!/usr/bin/env python3
"""Add foreign-policy / defense items (and the missing border-wall item) to
data/outputs/profiles/cluster_stats.csv so they surface in Compare Policies.

These are check-all-that-apply / binary CES items that were not part of the EFA
input set. Per-cluster % is computed by aligning the listwise EFA sample (numeric
codes, notna on the 24 items + weight → N=45,707, same order as the typology file)
to typology_cluster_assignments.csv by row position. Idempotent: removes any prior
rows for these variables before appending.
"""
import numpy as np, pandas as pd
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
DTA=ROOT/"CCES24_Common_OUTPUT_vv_topost_final (2).dta"
STATS=ROOT/"data"/"outputs"/"profiles"/"cluster_stats.csv"
TYPO=ROOT/"data"/"processed"/"typology_cluster_assignments.csv"

ITEMS_25=['pew_churatd','CC24_302','CC24_303','CC24_341a','CC24_341c','CC24_341d','CC24_323a','CC24_323b','CC24_323d','CC24_321b','CC24_321d','CC24_321e','CC24_325','CC24_324b','CC24_340a','CC24_340b','CC24_340c','CC24_340e','CC24_340f','CC24_440b','CC24_440c','CC24_421_1','CC24_421_2','CC24_423','CC24_424']
ITEMS=[x for x in ITEMS_25 if x!='CC24_340a']

FP="Foreign Policy & Defense"
# (variable, domain, question, kind). kind 'bin' = select/support→1, not/oppose(2)→0, 8/9→NaN.
#                                       kind 'incr' = 5pt spending; greatly/slightly increase(1,2)→1, else→0.
NEW=[
 ('CC24_308a_1',FP,'Ukraine: stay out of the conflict'),
 ('CC24_308a_2',FP,'Ukraine: send humanitarian aid'),
 ('CC24_308a_3',FP,'Ukraine: impose economic sanctions on Russia'),
 ('CC24_308a_4',FP,'Ukraine: provide arms to Ukraine'),
 ('CC24_308a_5',FP,'Ukraine: send non-combat military advisors'),
 ('CC24_308a_6',FP,'Ukraine: send significant force to fight Russia'),
 ('CC24_308a_7',FP,'Ukraine: negotiate a Russia–Ukraine peace accord'),
 ('CC24_308a_8',FP,'Ukraine: fund post-war reconstruction'),
 ('CC24_308b_1',FP,'Israel/Gaza: stay out of the conflict'),
 ('CC24_308b_2',FP,'Israel/Gaza: send humanitarian aid'),
 ('CC24_308b_3',FP,'Israel/Gaza: provide arms to Israel'),
 ('CC24_308b_4',FP,'Israel/Gaza: provide arms to Hamas'),
 ('CC24_308b_5',FP,'Israel/Gaza: send US Navy & troops to contain the conflict'),
 ('CC24_308b_6',FP,'Israel/Gaza: send non-combat military support to Israel'),
 ('CC24_308b_7',FP,'Israel/Gaza: send non-combat military support to Gaza'),
 ('CC24_308b_8',FP,'Israel/Gaza: negotiate a peace settlement'),
 ('CC24_308b_9',FP,'Israel/Gaza: fund post-war reconstruction'),
 ('CC24_420_1',FP,'Use US troops: to ensure the oil supply'),
 ('CC24_420_2',FP,'Use US troops: to destroy a terrorist camp'),
 ('CC24_420_3',FP,'Use US troops: to stop genocide or civil war'),
 ('CC24_420_4',FP,'Use US troops: to spread democracy'),
 ('CC24_420_5',FP,'Use US troops: to protect allies under attack'),
 ('CC24_420_6',FP,'Use US troops: to help the UN uphold international law'),
 ('CC24_420_7',FP,'Use US troops: for none of these reasons'),
 ('CC24_323c','Immigration','Build a wall between the U.S. and Mexico'),
 # Abortion battery (we previously surfaced only CC24_324b)
 ('CC24_324a','Abortion','Always allow abortion as a matter of personal choice'),
 ('CC24_324c','Abortion','Make abortion illegal in all circumstances'),
 ('CC24_324d','Abortion','Expand abortion access and affordability'),
 ('CC24_340a','Abortion','Protect access to contraception (Congress bill)'),
]
# 5-point state-spending battery → "% who want to increase" (greatly/slightly increase)
GS="Government Spending"
NEW_INCR=[
 ('CC24_443_1',GS,'Increase state spending on welfare'),
 ('CC24_443_2',GS,'Increase state spending on health care'),
 ('CC24_443_3',GS,'Increase state spending on education'),
 ('CC24_443_4',GS,'Increase state spending on law enforcement'),
 ('CC24_443_5',GS,'Increase state spending on transportation & infrastructure'),
]
# Categorical→binary items keyed by synth name. kind: target codes →1, valid-but-not-target →0, else NaN.
# (raw_var, synth_key, domain, question, target_codes, valid_codes)
VW="Voting History"
V16={1,2,3,4,5,6,7}; V20={1,2,3,4,5,6}; APPR={1,2,3,4,5}
NEW_CAT=[
 ('presvote16post','vote16_clinton',VW,'2016: Hillary Clinton (D)',{1},V16),
 ('presvote16post','vote16_trump',  VW,'2016: Donald Trump (R)',   {2},V16),
 ('presvote16post','vote16_third',  VW,'2016: Third-party / other',{3,4,5,6},V16),
 ('presvote16post','vote16_dnv',    VW,'2016: Did not vote',       {7},V16),
 ('presvote20post','vote20_biden',  VW,'2020: Joe Biden (D)',      {1},V20),
 ('presvote20post','vote20_trump',  VW,'2020: Donald Trump (R)',   {2},V20),
 ('presvote20post','vote20_third',  VW,'2020: Third-party / other',{3,4,5},V20),
 ('presvote20post','vote20_dnv',    VW,'2020: Did not vote',       {6},V20),
 ('CC24_312a','appr_biden', VW,'2024: Approve of Joe Biden (job)',     {1,2},APPR),
 ('CC24_312i','appr_harris',VW,'2024: Approve of Kamala Harris (job)', {1,2},APPR),
]
# 2024 vote = turnout (CC24_401: 5=voted) + choice (CC24_410), over the full sample so the
# Harris/Trump/third/DNV shares sum to ~100% like the 2016/2020 recall items.
VOTE24=['vote24_harris','vote24_trump','vote24_third','vote24_dnv']
# Religion: importance (4-pt, view), prayer frequency (7-pt, demo), denomination (nominal, demo).
# Emitted as binary "% Supporting" so they surface as rows; the ordinal ones (importance,
# prayer) also get full distributions from compute_intensity.py, joined by variable code.
FAITH="Faith"
DENOM=[  # (synth_key, question, target religpew codes)
 ('relig_protestant','Protestant',{1}),
 ('relig_catholic','Roman Catholic',{2}),
 ('relig_jewish','Jewish',{5}),
 ('relig_muslim','Muslim',{6}),
 ('relig_none','Unaffiliated (none / atheist / agnostic)',{9,10,11}),
 ('relig_other','Other faith',{3,4,7,8,12}),
]
RELIG_LOAD=['pew_religimp','pew_prayer','religpew']
LOADVARS=sorted(set([v for v,_,_ in NEW]+[v for v,_,_ in NEW_INCR]+[v for v,_,_,_,_,_ in NEW_CAT]+RELIG_LOAD+['CC24_401','CC24_410']))
EMITVARS=[v for v,_,_ in NEW]+[v for v,_,_ in NEW_INCR]+[sk for _,sk,_,_,_,_ in NEW_CAT]+VOTE24+['pew_religimp','pew_prayer']+[d[0] for d in DENOM]

def main():
    df=pd.read_stata(DTA, columns=ITEMS+LOADVARS+['commonpostweight'], convert_categoricals=False)
    mask=df[ITEMS+['commonpostweight']].notna().all(axis=1)
    dc=df[mask].reset_index(drop=True)
    typo=pd.read_csv(TYPO)
    assert len(dc)==len(typo), f"row mismatch {len(dc)} vs {len(typo)}"
    cl=typo['cluster'].values; w=dc['commonpostweight'].values.astype(float)
    def wpct(binvals, m):
        v=binvals[m]; ww=w[m]; ok=~np.isnan(v)
        return round(float((ww[ok]*v[ok]).sum()/ww[ok].sum()*100),4) if ok.any() else np.nan
    def emit(name,dom,q,b):
        rec={'variable':name,'domain':dom,'type':'binary','stat_label':'% Supporting','question':q,
             'overall':wpct(b,np.ones(len(b),bool))}
        for k in range(10): rec[f'c{k}']=wpct(b, cl==k)
        return rec
    rows=[]
    for var,dom,q in NEW:
        raw=dc[var].values.astype(float)
        b=np.where(raw==1,1.0,np.where(raw==2,0.0,np.nan))  # select/support→1, not/oppose→0, 8/9→NaN
        rows.append(emit(var,dom,q,b))
    for var,dom,q in NEW_INCR:
        raw=dc[var].values.astype(float)
        b=np.where(np.isin(raw,[1,2]),1.0,np.where(np.isin(raw,[3,4,5]),0.0,np.nan))  # increase→1
        rows.append(emit(var,dom,q,b))
    for var,sk,dom,q,tgt,valid in NEW_CAT:
        raw=dc[var].values.astype(float)
        b=np.where(np.isin(raw,list(tgt)),1.0,np.where(np.isin(raw,list(valid)),0.0,np.nan))
        rows.append(emit(sk,dom,q,b))
    # 2024 vote over full sample: denom = valid turnout (CC24_401 in 1..5); non-voters → 0 for each candidate
    t=dc['CC24_401'].values.astype(float); ch=dc['CC24_410'].values.astype(float)
    validturn=np.isin(t,[1,2,3,4,5])
    def v24(cond):
        b=np.where(cond,1.0,0.0); b[~validturn]=np.nan; return b
    rows.append(emit('vote24_harris',VW,'2024: Kamala Harris (D)',   v24(ch==1)))
    rows.append(emit('vote24_trump', VW,'2024: Donald Trump (R)',    v24(ch==2)))
    rows.append(emit('vote24_third', VW,'2024: Third-party / other', v24(np.isin(ch,[3,4,5,6,8]))))
    rows.append(emit('vote24_dnv',   VW,'2024: Did not vote',        v24(t!=5)))
    # Religion importance (very/somewhat important → 1); a "view"
    ri=dc['pew_religimp'].values.astype(float)
    rows.append(emit('pew_religimp','Religion','Religion is important (very or somewhat)',
                     np.where(np.isin(ri,[1,2]),1.0,np.where(np.isin(ri,[3,4]),0.0,np.nan))))
    # Prayer frequency (weekly or more, codes 1–4 → 1); a religiosity view
    pr=dc['pew_prayer'].values.astype(float)
    rows.append(emit('pew_prayer','Religion','Prays weekly or more often',
                     np.where(np.isin(pr,[1,2,3,4]),1.0,np.where(np.isin(pr,[5,6,7]),0.0,np.nan))))
    # Denomination buckets (nominal); each a demographic share over valid respondents
    rp=dc['religpew'].values.astype(float); rp_valid=np.isin(rp,list(range(1,13)))
    for key,q,tgt in DENOM:
        rows.append(emit(key,FAITH,q,np.where(np.isin(rp,list(tgt)),1.0,np.where(rp_valid,0.0,np.nan))))
    newdf=pd.DataFrame(rows)
    stats=pd.read_csv(STATS)
    stats=stats[~stats['variable'].isin(EMITVARS)]  # idempotent
    out=pd.concat([stats,newdf],ignore_index=True)
    out.to_csv(STATS,index=False)
    print(f"appended {len(newdf)} items to {STATS.relative_to(ROOT)} (total rows {len(out)})")
    print(newdf[['variable','question','overall','c0','c8','c9']].to_string(index=False))

if __name__=='__main__':
    main()
