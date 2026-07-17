#!/usr/bin/env python3
"""6-dimension rebuild: cluster on the 5 production factor scores PLUS a foreign-policy
engagement score, and compare to the production 9 parties (same lens as the k=4 study).

Setup (documented choices):
- Sample/space = production: efa_factor_scores.csv (N=45,707) FS_F1..F3, FS_F4_resid, FS_F5_resid,
  used RAW exactly as the production DPGMM did. Baseline = production cluster labels (typology file),
  so the ONLY change is adding the 6th dimension.
- 6th dim = PC1 of the 24 foreign-policy binaries (engagement↔isolationism), z-scored then scaled
  to the MEDIAN sd of the 5 factor columns (enters as a typical-strength dimension).
- DPGMM params identical to production (n_components=10, dirichlet_process, n_init=5, seed 42).
- 5-D assignment confidence comes from the production posteriors (typology file); 6-D from the re-fit.
"""
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.mixture import BayesianGaussianMixture
from sklearn.metrics import adjusted_rand_score
ROOT=Path(__file__).resolve().parent.parent.parent
DTA=ROOT/"CCES24_Common_OUTPUT_vv_topost_final (2).dta"
ITEMS_25=['pew_churatd','CC24_302','CC24_303','CC24_341a','CC24_341c','CC24_341d','CC24_323a','CC24_323b','CC24_323d','CC24_321b','CC24_321d','CC24_321e','CC24_325','CC24_324b','CC24_340a','CC24_340b','CC24_340c','CC24_340e','CC24_340f','CC24_440b','CC24_440c','CC24_421_1','CC24_421_2','CC24_423','CC24_424']
ITEMS=[x for x in ITEMS_25 if x!='CC24_340a']
FP=[f'CC24_308a_{i}' for i in range(1,9)]+[f'CC24_308b_{i}' for i in range(1,10)]+[f'CC24_420_{i}' for i in range(1,8)]
ISO={'CC24_308a_1','CC24_308b_1','CC24_420_7'}
PARTY={0:'CON',1:'SD',2:'STY',3:'NAT',4:'LIB',5:'POP',6:'CUP',7:'C7',8:'DSA',9:'PRG'}

df=pd.read_stata(DTA, columns=ITEMS+FP+['commonpostweight'], convert_categoricals=False)
mask=df[ITEMS+['commonpostweight']].notna().all(1)
dc=df[mask].reset_index(drop=True)
typo=pd.read_csv(ROOT/'data/processed/typology_cluster_assignments.csv')
fs=pd.read_csv(ROOT/'data/processed/efa_factor_scores.csv')
assert len(dc)==len(typo)==len(fs), (len(dc),len(typo),len(fs))
w=dc['commonpostweight'].values.astype(float)
FScols=['FS_F1','FS_F2','FS_F3','FS_F4_resid','FS_F5_resid']
FS=fs[FScols].values
prod=typo['cluster'].values.astype(int)
conf5=typo[[f'prob_cluster_{i}' for i in range(10)]].max(1).values

# foreign-policy engagement PC1
B=np.column_stack([np.where(dc[c].values==1,1.0,np.where(dc[c].values==2,0.0,np.nan)) for c in FP])
assert not np.isnan(B).any()
mu=B.mean(0); sd=B.std(0); sd[sd<1e-9]=1; Z=(B-mu)/sd; Z=Z-Z.mean(0)
U,S,Vt=np.linalg.svd(Z,full_matrices=False)
pc1=Z.dot(Vt[0])
engage=B[:,[i for i,c in enumerate(FP) if c not in ISO]].mean(1)
if np.corrcoef(pc1,engage)[0,1]<0: pc1=-pc1
fp_z=(pc1-pc1.mean())/pc1.std()
fp_scaled=fp_z*np.median(FS.std(0))   # typical-strength dimension
print(f"N={len(dc):,}  FP PC1 variance={S[0]**2/np.sum(S**2)*100:.1f}%  scale(sd)={np.median(FS.std(0)):.3f}", flush=True)

def dpgmm(X):
    m=BayesianGaussianMixture(n_components=10,covariance_type='full',
        weight_concentration_prior_type='dirichlet_process',n_init=5,max_iter=500,random_state=42)
    lab=m.fit_predict(X); return lab, m.predict_proba(X).max(1)

# verify our DPGMM reproduces production on the 5-D space
print("fitting 5-D (verify vs production)...", flush=True)
lab5,_=dpgmm(FS)
print(f"  ARI(5-D refit vs production) = {adjusted_rand_score(lab5,prod):.3f}", flush=True)
print("fitting 6-D...", flush=True)
X6=np.column_stack([FS, fp_scaled]); lab6,conf6=dpgmm(X6)
eff6=len(np.unique(lab6))
print(f"  6-D effective clusters = {eff6}/10", flush=True)
print(f"  ARI(6-D vs production) = {adjusted_rand_score(lab6,prod):.3f}", flush=True)
print(f"  mean confidence: 5-D(prod)={np.average(conf5,weights=w):.3f}  6-D={np.average(conf6,weights=w):.3f}", flush=True)

out=pd.DataFrame({'w':w,'prod_cluster':prod,'prod_party':[PARTY[c] for c in prod],
                  'sixdim':lab6,'conf5':conf5,'conf6':conf6,'fp_engage':fp_z})
out.to_csv(ROOT/'analysis/efa/sixdim_labels.csv',index=False)

# survival: where does each production party go in the 6-D solution?
print("\nSURVIVAL (production party -> 6-D clusters):", flush=True)
print(f"  {'party':<5}{'wt%':>6}  best6D  purity  cluShare  verdict   FPsplit?")
for cid,p in PARTY.items():
    mp=prod==cid; tot=w[mp].sum()
    if tot==0: continue
    dist={k: w[mp&(lab6==k)].sum()/tot for k in np.unique(lab6)}
    bc=max(dist,key=dist.get); pur=dist[bc]
    clushare=w[mp&(lab6==bc)].sum()/w[lab6==bc].sum()
    verdict='SURVIVES' if pur>=0.6 and clushare>=0.5 else ('splits' if pur<0.6 else 'absorbed-in')
    # FP split: among this party's members, do the 6-D clusters they fall into differ on FP engagement?
    subs={k:v for k,v in dist.items() if v>=0.15}
    fp_by={k: np.average(fp_z[mp&(lab6==k)],weights=w[mp&(lab6==k)]) for k in subs}
    fpspread=(max(fp_by.values())-min(fp_by.values())) if len(fp_by)>1 else 0
    print(f"  {p:<5}{tot/w.sum()*100:>6.1f}  {bc:>6} {pur:>6.0%} {clushare:>8.0%}   {verdict:<11} Δengage={fpspread:+.2f} across {len(subs)} clusters")
print("\nsaved analysis/efa/sixdim_labels.csv\nDONE", flush=True)
