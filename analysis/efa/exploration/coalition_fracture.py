#!/usr/bin/env python3
"""How the 6-D (foreign-policy) future re-sorts the cross-pressured middle, and how that
changes legislation. Compares the new 6-D coalitions (SD/STY, POP/STY, the isolationist
bloc, the internationalist-SD wing) against the current parties (SD, STY, POP) on factor
space + key bills, and runs a party-discipline pass model (9-party House vs 6-D House)."""
import json, numpy as np, pandas as pd
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent.parent
DTA=ROOT/"CCES24_Common_OUTPUT_vv_topost_final (2).dta"
ITEMS_25=['pew_churatd','CC24_302','CC24_303','CC24_341a','CC24_341c','CC24_341d','CC24_323a','CC24_323b','CC24_323d','CC24_321b','CC24_321d','CC24_321e','CC24_325','CC24_324b','CC24_340a','CC24_340b','CC24_340c','CC24_340e','CC24_340f','CC24_440b','CC24_440c','CC24_421_1','CC24_421_2','CC24_423','CC24_424']
ITEMS=[x for x in ITEMS_25 if x!='CC24_340a']
# bills: (key, label, kind)  kind: 'sup'=%Support(raw), 'sel'=%selected(multi), 'inc'=%want-increase(5pt)
BILLS=[('CC24_341c','Raise taxes on $400k+ earners','sup'),
 ('CC24_328e','Expand Medicaid','sup'),('CC24_443_1','Increase welfare spending','inc'),
 ('CC24_323a','Grant legal status to undocumented','sup'),('CC24_323d','Pathway for Dreamers','sup'),
 ('CC24_323b','Increase border patrols','sup'),('CC24_340f','Deny asylum at the border','sup'),
 ('CC24_321d','Increase police by 10%','sup'),('CC24_340c','Recognize same-sex marriage','sup'),
 ('CC24_308a_4','Arm Ukraine','sel'),('CC24_308a_3','Sanction Russia','sel'),
 ('CC24_308b_3','Arm Israel','sel'),('CC24_420_5','Use troops to protect allies','sel'),
 ('CC24_420_2','Use troops vs terrorism','sel'),('CC24_308a_1','Ukraine: stay out','sel')]
BILLVARS=[b[0] for b in BILLS]
lab=pd.read_csv(ROOT/'analysis/efa/sixdim_labels.csv'); fs=pd.read_csv(ROOT/'data/processed/efa_factor_scores.csv')
cols=list(dict.fromkeys(ITEMS+BILLVARS+['commonpostweight']))
df=pd.read_stata(DTA, columns=cols, convert_categoricals=False)
mask=df[ITEMS+['commonpostweight']].notna().all(1); dc=df[mask].reset_index(drop=True)
assert len(dc)==len(lab)==len(fs)
w=lab['w'].values; prod=lab['prod_party'].values; six=lab['sixdim'].values
FACS=['FS_F1','FS_F2','FS_F3','FS_F4_resid','FS_F5_resid']; FACN=['enforce','elecSkep','govDist','relig','values']
FS=fs[FACS].values; fpe=lab['fp_engage'].values
def billvec(key,kind):
    raw=dc[key].values.astype(float)
    if kind=='sup': return np.where(raw==1,1.0,np.where(raw==2,0.0,np.nan))
    if kind=='sel': return np.where(raw==1,1.0,np.where(raw==2,0.0,np.nan))
    if kind=='inc': return np.where(np.isin(raw,[1,2]),1.0,np.where(np.isin(raw,[3,4,5]),0.0,np.nan))
BV={k:billvec(k,t) for k,_,t in BILLS}
def wpct(v,m): ok=~np.isnan(v)&m; return round(float((w[ok]*v[ok]).sum()/w[ok].sum()*100),0) if ok.any() else None
def wmean(v,m): ok=~np.isnan(v)&m; return round(float((w[ok]*v[ok]).sum()/w[ok].sum()),2) if ok.any() else None
def profile(m):
    return {'wtPct':round(w[m].sum()/w.sum()*100,1),
            'factors':{**{FACN[j]:wmean(FS[:,j],m) for j in range(5)},'FPengage':wmean(fpe,m)},
            'bills':{k:wpct(BV[k],m) for k,_,_ in BILLS}}
# --- groups: current middle parties vs the new 6-D coalitions ---
groups={}
for p in ['SD','STY','POP','CON']: groups['cur:'+p]=profile(prod==p); groups['cur:'+p]['kind']='current'
# identify 6-D clusters by composition signature
def lead_comp(cl):
    m=six==cl; tot=w[m].sum(); comp={p:w[m&(prod==p)].sum()/tot*100 for p in np.unique(prod)}
    return {p:round(v) for p,v in sorted(comp.items(),key=lambda kv:-kv[1]) if v>=10}
sixprof={}
for cl in sorted(np.unique(six)):
    comp=lead_comp(cl); g=profile(six==cl); g['comp']=comp; g['id']=int(cl); g['kind']='sixdim'; sixprof[cl]=g
# pick the interesting new coalitions (the fractured-middle ones)
def find(sig):
    for cl,g in sixprof.items():
        ks=list(g['comp']);
        if set(sig).issubset(set(ks)) and len(ks)>=len(sig): return cl
    return None
ISO=min(sixprof, key=lambda cl: sixprof[cl]['factors']['FPengage'])  # most isolationist
labelmap={}
for cl,g in sixprof.items():
    ks=list(g['comp']);
    name='/'.join(ks[:3])
    labelmap[cl]='6D:'+name+(' (isolationist)' if cl==ISO else '')
for cl in sixprof: groups[labelmap[cl]]=sixprof[cl]

# --- legislation under party discipline: 9-party House vs 6-D House ---
def house(units):  # units: list of (mask, seat_weight)
    res={}
    total=sum(sw for _,sw in units)
    for k,lblk,_ in BILLS:
        yes=0.0
        for m,sw in units:
            s=wpct(BV[k],m)
            if s is not None and s>50: yes+=sw
        res[k]=round(yes/total*100,0)  # % of seats in YES-voting blocs (party discipline)
    return res
nine=[(prod==p, w[prod==p].sum()) for p in ['PRG','DSA','LIB','SD','STY','CUP','POP','CON','NAT']]
sixd=[(six==cl, w[six==cl].sum()) for cl in np.unique(six)]
h9=house(nine); h6=house(sixd)
legis=[]
for k,lbl,_ in BILLS:
    legis.append({'key':k,'label':lbl,'overall':wpct(BV[k],np.ones(len(w),bool)),
                  'house9':h9[k],'house6':h6[k],'pass9':bool(h9[k]>50),'pass6':bool(h6[k]>50),'flip':bool((h9[k]>50)!=(h6[k]>50))})
OUT={'groups':groups,'bills':[{'key':k,'label':l,'kind':t} for k,l,t in BILLS],'factor_names':FACN+['FPengage'],
     'legislation':legis}
json.dump(OUT, open(ROOT/'analysis/efa/coalition_fracture.json','w'), indent=1)
print("=== legislation: party-discipline pass (% seats in YES blocs) — 9-party vs 6-D House ===")
print(f"{'bill':<36}{'overall':>8}{'9-party':>9}{'6-D':>6}  flip?")
for L in legis:
    print(f"  {L['label']:<34}{L['overall']:>7.0f}%{L['house9']:>8.0f}%{L['house6']:>6.0f}%  {'** FLIP **' if L['flip'] else ''}")
print("\nflips:",sum(L['flip'] for L in legis))
print("wrote analysis/efa/coalition_fracture.json")
