#!/usr/bin/env python3
"""Extend the foreign-policy exploration: (1) apply the same lens to the state-spending
battery (CC24_443), (2) quantify how much the existing 9 clusters already separate
people on these orthogonal dimensions — between- vs within-party variance (η²) — which
indicates whether adding them to the clustering would cleanly SPLIT parties or just
fragment them. η² here is w.r.t. the actual clusters, not party ID."""
import numpy as np, pandas as pd
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent.parent
DTA=ROOT/"CCES24_Common_OUTPUT_vv_topost_final (2).dta"
ITEMS_25=['pew_churatd','CC24_302','CC24_303','CC24_341a','CC24_341c','CC24_341d','CC24_323a','CC24_323b','CC24_323d','CC24_321b','CC24_321d','CC24_321e','CC24_325','CC24_324b','CC24_340a','CC24_340b','CC24_340c','CC24_340e','CC24_340f','CC24_440b','CC24_440c','CC24_421_1','CC24_421_2','CC24_423','CC24_424']
ITEMS=[x for x in ITEMS_25 if x!='CC24_340a']
FP=[f'CC24_308a_{i}' for i in range(1,9)]+[f'CC24_308b_{i}' for i in range(1,10)]+[f'CC24_420_{i}' for i in range(1,8)]
ISO={'CC24_308a_1','CC24_308b_1','CC24_420_7'}
SPEND=[f'CC24_443_{i}' for i in range(1,6)]
SPLAB=['welfare','health','education','law enforcement','transportation']

df=pd.read_stata(DTA, columns=ITEMS+FP+SPEND+['commonpostweight'], convert_categoricals=False)
mask=df[ITEMS+['commonpostweight']].notna().all(axis=1)
dc=df[mask].reset_index(drop=True)
typo=pd.read_csv(ROOT/'data'/'processed'/'typology_cluster_assignments.csv')
fs=pd.read_csv(ROOT/'data'/'processed'/'efa_factor_scores.csv')
cl=typo['cluster'].values; w=dc['commonpostweight'].values.astype(float)
FScols=['FS_F1','FS_F2','FS_F3','FS_F4_resid','FS_F5_resid']; FS=fs[FScols].values
PARTY={0:'CON',1:'SD',2:'STY',3:'NAT',4:'LIB',5:'POP',6:'CUP',7:'C7',8:'DSA',9:'PRG'}

def wcorr(a,b,wt):
    aw=a-np.average(a,weights=wt); bw=b-np.average(b,weights=wt)
    return float(np.sum(wt*aw*bw)/np.sqrt(np.sum(wt*aw**2)*np.sum(wt*bw**2)))
def eta2(x,labels,wt):
    gm=np.average(x,weights=wt); sst=np.sum(wt*(x-gm)**2); ssb=0.0
    for k in np.unique(labels):
        m=labels==k; Wc=wt[m].sum(); ssb+=Wc*(np.average(x[m],weights=wt[m])-gm)**2
    return ssb/sst
def pca1(M):
    mu=M.mean(0); sd=M.std(0); sd[sd<1e-9]=1; Z=(M-mu)/sd; Z=Z-Z.mean(0)
    U,S,Vt=np.linalg.svd(Z,full_matrices=False); return Z, S**2/np.sum(S**2), Vt

# ---- foreign-policy engagement ----
B=np.column_stack([np.where(dc[c].values==1,1.0,np.where(dc[c].values==2,0.0,np.nan)) for c in FP])
ok=~np.isnan(B).any(1); Bx=B[ok]; wx=w[ok]; clx=cl[ok]; FSx=FS[ok]
act=[i for i,c in enumerate(FP) if c not in ISO]
engage=Bx[:,act].mean(1)
Zfp,vfp,Vfp=pca1(Bx); pc1fp=Zfp.dot(Vfp[0])
if np.corrcoef(pc1fp,engage)[0,1]<0: pc1fp=-pc1fp

# ---- state spending (5pt: 1 greatly incr .. 5 greatly decr → reverse so high=more spending) ----
Sp=np.column_stack([np.where(np.isin(dc[c].values,[1,2,3,4,5]),6-dc[c].values,np.nan) for c in SPEND])
oks=~np.isnan(Sp).any(1); Spx=Sp[oks]; ws=w[oks]; cls=cl[oks]; FSs=FS[oks]
Zsp,vsp,Vsp=pca1(Spx); pc1sp=Zsp.dot(Vsp[0])
if np.average(pc1sp,weights=ws)*0==0 and wcorr(pc1sp, Spx.mean(1), ws)<0: pc1sp=-pc1sp
spend_idx=Spx.mean(1)  # overall pro-spending

print("=== STATE SPENDING (CC24_443) ===")
print("PCA var:", " ".join(f"PC{i+1}={vsp[i]*100:.0f}%" for i in range(3)))
print("PC1 loadings:", " ".join(f"{SPLAB[i]}{Vsp[0][i]:+.2f}" for i in range(5)))
print("corr(spend PC1, domestic factors):", " ".join(f"{c.replace('FS_','').replace('_resid','')}={wcorr(pc1sp,FSs[:,j],ws):+.2f}" for j,c in enumerate(FScols)))

print("\n=== ORTHOGONAL-DIMENSION SEPARATION ACROSS THE 9 CLUSTERS (η² w.r.t. clusters) ===")
print("how much the existing parties already separate people on each dimension:")
print(f"  foreign-policy engagement : η²={eta2(engage,clx,wx):.3f}   (PC1 {eta2(pc1fp,clx,wx):.3f})")
print(f"  state-spending index      : η²={eta2(spend_idx,cls,ws):.3f}   (PC1 {eta2(pc1sp,cls,ws):.3f})")
print("  --- baselines (domestic factors the clusters were BUILT on) ---")
for j,c in enumerate(FScols):
    print(f"  {c:<25} : η²={eta2(FS[:,j],cl,w):.3f}")

print("\n=== per-party spending index (high = more pro-spending) vs F5 ===")
rows=[]
for k in range(10):
    m=cls==k; rows.append((PARTY[k], np.average(spend_idx[m],weights=ws[m]), np.average(FSs[m,4],weights=ws[m])))
for r in sorted(rows,key=lambda x:-x[1]): print(f"  {r[0]:<5} spend={r[1]:+.2f}  F5={r[2]:+.2f}")
