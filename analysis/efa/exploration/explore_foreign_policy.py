#!/usr/bin/env python3
"""Exploration: do the foreign-policy multi-select batteries (Ukraine CC24_308a,
Israel/Gaza CC24_308b, use-of-force CC24_420) cohere into a latent dimension, and
does it run orthogonal to the 5 domestic factors / cut across the 10 parties?

Method appropriate to check-all-that-apply binary data (NOT polychoric, which is what
the original EFA correctly rejected): PCA on the 0/1 indicators + weighted correlations
with the domestic factor scores + per-party means. Judged by coherence and cross-cutting,
not by party ID.
"""
import numpy as np, pandas as pd
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent.parent
DTA=ROOT/"CCES24_Common_OUTPUT_vv_topost_final (2).dta"

ITEMS_25=['pew_churatd','CC24_302','CC24_303','CC24_341a','CC24_341c','CC24_341d','CC24_323a','CC24_323b','CC24_323d','CC24_321b','CC24_321d','CC24_321e','CC24_325','CC24_324b','CC24_340a','CC24_340b','CC24_340c','CC24_340e','CC24_340f','CC24_440b','CC24_440c','CC24_421_1','CC24_421_2','CC24_423','CC24_424']
ITEMS=[x for x in ITEMS_25 if x!='CC24_340a']
UK=[f'CC24_308a_{i}' for i in range(1,9)]
IL=[f'CC24_308b_{i}' for i in range(1,10)]
FORCE=[f'CC24_420_{i}' for i in range(1,8)]
FP=UK+IL+FORCE
LABEL={'CC24_308a_1':'UA stay out','CC24_308a_2':'UA humanitarian','CC24_308a_3':'UA sanctions','CC24_308a_4':'UA arms','CC24_308a_5':'UA advisors','CC24_308a_6':'UA send force','CC24_308a_7':'UA negotiate','CC24_308a_8':'UA rebuild',
 'CC24_308b_1':'IL stay out','CC24_308b_2':'IL humanitarian','CC24_308b_3':'IL arms Israel','CC24_308b_4':'IL arms Hamas','CC24_308b_5':'IL navy/troops','CC24_308b_6':'IL support Israel','CC24_308b_7':'IL support Gaza','CC24_308b_8':'IL negotiate','CC24_308b_9':'IL rebuild',
 'CC24_420_1':'F oil','CC24_420_2':'F terrorist','CC24_420_3':'F genocide','CC24_420_4':'F democracy','CC24_420_5':'F allies','CC24_420_6':'F UN/law','CC24_420_7':'F none'}
ISO={'CC24_308a_1','CC24_308b_1','CC24_420_7'}  # stay-out / none → isolationist pole

df=pd.read_stata(DTA, columns=ITEMS+FP+['commonpostweight'], convert_categoricals=False)
mask=df[ITEMS+['commonpostweight']].notna().all(axis=1)
dc=df[mask].reset_index(drop=True)
typo=pd.read_csv(ROOT/'data'/'processed'/'typology_cluster_assignments.csv')
fs=pd.read_csv(ROOT/'data'/'processed'/'efa_factor_scores.csv')
assert len(dc)==len(typo)==len(fs)
cl=typo['cluster'].values; w=dc['commonpostweight'].values.astype(float)
PARTY={0:'CON',1:'SD',2:'STY',3:'NAT',4:'LIB',5:'POP',6:'CUP',7:'C7',8:'DSA',9:'PRG'}

# binary 0/1 (selected=1, not=0); rows with all-NaN FP dropped from FP analysis
B=np.column_stack([np.where(dc[c].values==1,1.0,np.where(dc[c].values==2,0.0,np.nan)) for c in FP])
fpok=~np.isnan(B).any(axis=1)
print(f"N listwise={len(dc):,}; with complete FP battery={int(fpok.sum()):,}")
Bx=B[fpok]; wx=w[fpok]; clx=cl[fpok]
FScols=['FS_F1','FS_F2','FS_F3','FS_F4_resid','FS_F5_resid']
FSx=fs.loc[fpok, FScols].values

# ---- PCA on standardized binaries (unweighted structure) ----
mu=Bx.mean(0); sd=Bx.std(0); sd[sd<1e-9]=1; Z=(Bx-mu)/sd
U,S,Vt=np.linalg.svd(Z-Z.mean(0), full_matrices=False)
varexp=S**2/np.sum(S**2)
print("\nPCA variance explained:", " ".join(f"PC{i+1}={varexp[i]*100:.1f}%" for i in range(5)))
for pc in range(2):
    load=Vt[pc]
    # orient PC1 so engagement(+) > isolationist
    order=np.argsort(-np.abs(load))
    print(f"\nPC{pc+1} top loadings:")
    for i in order[:10]:
        print(f"   {LABEL[FP[i]]:<18} {load[i]:+.2f}")

# ---- simple interpretable indices ----
act=[i for i,c in enumerate(FP) if c not in ISO]      # engagement actions
iso=[i for i,c in enumerate(FP) if c in ISO]
engage=Bx[:,act].mean(1)        # share of engagement actions selected
isolation=Bx[:,iso].mean(1)     # share of stay-out/none selected
pc1=Z[:,:].dot(Vt[0])           # PC1 score
# orient pc1 so it correlates + with engagement
if np.corrcoef(pc1,engage)[0,1]<0: pc1=-pc1

def wcorr(a,b,wt):
    aw=a-np.average(a,weights=wt); bw=b-np.average(b,weights=wt)
    return float(np.sum(wt*aw*bw)/np.sqrt(np.sum(wt*aw**2)*np.sum(wt*bw**2)))
print("\nWeighted correlation of foreign-policy measures with the 5 DOMESTIC factors:")
fshort=[c.replace('FS_','').replace('_resid','') for c in FScols]
print("  "+f"{'measure':<12}"+''.join(f'{s:>8}' for s in fshort))
for name,vec in [('PC1(engage)',pc1),('engagement',engage),('isolation',isolation)]:
    print(f"  {name:<12}"+''.join(f'{wcorr(vec,FSx[:,j],wx):>8.2f}' for j in range(5)))

# ---- per-party means: does engagement cut across left-right (F5)? ----
print("\nPer-party (weighted): engagement, isolation, PC1 — vs domestic F5 (pop. conservatism) & F1 (security):")
print(f"  {'party':<5}{'engage':>8}{'isol':>7}{'PC1':>7}{'F5':>7}{'F1':>7}")
rows=[]
for k in range(10):
    m=clx==k; ww=wx[m]
    e=np.average(engage[m],weights=ww); iso_=np.average(isolation[m],weights=ww); p=np.average(pc1[m],weights=ww)
    f5=np.average(FSx[m,4],weights=ww); f1=np.average(FSx[m,0],weights=ww)
    rows.append((PARTY[k],e,iso_,p,f5,f1))
for r in sorted(rows,key=lambda x:-x[1]):
    print(f"  {r[0]:<5}{r[1]:>8.2f}{r[2]:>7.2f}{r[3]:>7.2f}{r[4]:>7.2f}{r[5]:>7.2f}")
print("\n(if engagement ranking ≠ F5/F1 ranking, foreign-policy engagement is cross-cutting)")
