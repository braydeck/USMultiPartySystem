#!/usr/bin/env python3
"""Recover real cluster strength = DPGMM assignment confidence (mean max posterior),
the same metric as production, for the k=5 resid (baseline-repro) and k=5 no-resid fits.
Re-fits both (same seed/params as the cached run) to get predict_proba, and appends the
per-respondent max-posterior to cluster_labels_variants.csv. Validates the baseline-repro
confidence against the production numbers so the no-resid confidence is trustworthy."""
import warnings; warnings.filterwarnings('ignore'); import numpy as np, pandas as pd
from factor_analyzer.rotator import Rotator
from sklearn.mixture import BayesianGaussianMixture
ITEMS_25=['pew_churatd','CC24_302','CC24_303','CC24_341a','CC24_341c','CC24_341d','CC24_323a','CC24_323b','CC24_323d','CC24_321b','CC24_321d','CC24_321e','CC24_325','CC24_324b','CC24_340a','CC24_340b','CC24_340c','CC24_340e','CC24_340f','CC24_440b','CC24_440c','CC24_421_1','CC24_421_2','CC24_423','CC24_424']
ITEMS=[x for x in ITEMS_25 if x!='CC24_340a']
R=pd.read_csv('data/processed/polychoric_matrix.csv',index_col=0).loc[ITEMS,ITEMS].values.astype(float)
R=(R+R.T)/2; np.fill_diagonal(R,1.0); ev=np.linalg.eigvalsh(R)
if ev.min()<1e-6: R+=np.eye(len(ITEMS))*(1e-6-ev.min()); d=np.sqrt(np.diag(R)); R/=np.outer(d,d)
Rinv=np.linalg.inv(R)
df=pd.read_stata('CCES24_Common_OUTPUT_vv_topost_final (2).dta', columns=ITEMS+['commonpostweight'], convert_categoricals=True, convert_missing=False, convert_dates=False)
S,O='Support','Oppose'
ca={'Strongly agree':5,'Somewhat agree':4,'Neither agree nor disagree':3,'Somewhat disagree':2,'Strongly disagree':1}
el={'Strongly agree':1,'Somewhat agree':2,'Neither agree nor disagree':3,'Somewhat disagree':4,'Strongly disagree':5}
gv={'A great deal':1,'A fair amount':2,'Not very much':3,'None at all':4,'Not sure':2}
def c(col,m): return df[col].map(m).astype(float)
r={'pew_churatd':c('pew_churatd',{'Never':1,'Seldom':2,'A few times a year':3,'Once or twice a month':4,'Once a week':5,'More than once a week':6,"Don't know":np.nan}),
'CC24_302':c('CC24_302',{'Increased a lot':1,'Increased somewhat':2,'Stayed about the same':3,'Decreased somewhat':4,'Decreased a lot':5}),
'CC24_303':c('CC24_303',{'Decreased a lot':1,'Decreased somewhat':2,'Stayed about the same':3,'Increased somewhat':4,'Increased a lot':5}),
'CC24_341a':c('CC24_341a',{S:1,O:0}),'CC24_341c':c('CC24_341c',{S:0,O:1}),'CC24_341d':c('CC24_341d',{S:0,O:1}),
'CC24_323a':c('CC24_323a',{S:0,O:1}),'CC24_323b':c('CC24_323b',{S:1,O:0}),'CC24_323d':c('CC24_323d',{S:0,O:1}),
'CC24_321b':c('CC24_321b',{S:1,O:0}),'CC24_321d':c('CC24_321d',{S:1,O:0}),'CC24_321e':c('CC24_321e',{S:0,O:1}),
'CC24_325':40.0-pd.to_numeric(df['CC24_325'].astype(str),errors='coerce'),'CC24_324b':c('CC24_324b',{S:1,O:0}),
'CC24_340b':c('CC24_340b',{S:0,O:1}),'CC24_340c':c('CC24_340c',{S:0,O:1}),'CC24_340e':c('CC24_340e',{S:1,O:0}),'CC24_340f':c('CC24_340f',{S:1,O:0}),
'CC24_440b':c('CC24_440b',ca),'CC24_440c':c('CC24_440c',ca),'CC24_421_1':c('CC24_421_1',el),'CC24_421_2':c('CC24_421_2',el),
'CC24_423':c('CC24_423',gv),'CC24_424':c('CC24_424',gv)}
D=pd.DataFrame(r); D['w']=df['commonpostweight'].values.astype(float)
comp=D[ITEMS].notna().all(axis=1)&D['w'].notna(); D=D[comp].reset_index(drop=True)
X=D[ITEMS].values; w=D['w'].values; wn=w/w.sum()
mu=(wn[:,None]*X).sum(0); sig=np.sqrt((wn[:,None]*(X-mu)**2).sum(0)); sig[sig<1e-10]=1; Z=(X-mu)/sig
lab=pd.read_csv('analysis/efa/cluster_labels_variants.csv'); assert len(lab)==len(D)
def paf(R,k,it=1000,tol=1e-7):
    Ri=np.linalg.pinv(R); h2=np.clip(1-1/np.diag(Ri),0.005,0.999)
    for _ in range(it):
        Rr=R.copy(); np.fill_diagonal(Rr,h2); e,vv=np.linalg.eigh(Rr); ix=np.argsort(e)[::-1]
        L=vv[:,ix[:k]]*np.sqrt(np.maximum(e[ix[:k]],0)); h2n=np.clip((L**2).sum(1),0,0.999)
        if np.max(np.abs(h2n-h2))<tol: break
        h2=h2n
    return L
def wresid(y,x,w):
    Xd=np.column_stack([np.ones_like(x),x]); W=w/w.mean(); XtW=Xd.T*W; return y-Xd@np.linalg.solve(XtW@Xd,XtW@y)
rot=Rotator(method='oblimin'); L=rot.fit_transform(paf(R,5)); Phi=rot.phi_; F=Z@(Rinv@(L@Phi))
for j in range(5):
    if L[np.argmax(np.abs(L[:,j])),j]<0: F[:,j]*=-1
a=lambda it:int(np.argmax(np.abs(L[ITEMS.index(it),:]))); id5=dict(enf=a('CC24_323b'),rel=a('pew_churatd'),val=a('CC24_440b'))
def space(resid):
    Xc=F.copy()
    if resid:
        enf=F[:,id5['enf']]
        for key in ('rel','val'):
            if id5[key]!=id5['enf']: Xc[:,id5[key]]=wresid(F[:,id5[key]],enf,w)
    return Xc
def fit(Xc):
    m=BayesianGaussianMixture(n_components=10,covariance_type='full',weight_concentration_prior_type='dirichlet_process',n_init=5,max_iter=500,random_state=42)
    labels=m.fit_predict(Xc); mx=m.predict_proba(Xc).max(1); return labels,mx
print("fitting k5 resid...",flush=True); lab_r,mx_r=fit(space(True))
print("fitting k5 no-resid...",flush=True); lab_n,mx_n=fit(space(False))
from sklearn.metrics import adjusted_rand_score
print("ARI re-fit vs cached  resid:",round(adjusted_rand_score(lab_r,lab['baseline_party'].astype('category').cat.codes),3),
      " noresid:",round(adjusted_rand_score(lab_n,lab['k5_noresid']),3))
lab['conf_resid']=mx_r; lab['conf_noresid']=mx_n
lab.to_csv('analysis/efa/cluster_labels_variants.csv',index=False)
# per-cluster weighted mean confidence
def percluster(labels,mx):
    out={}
    for cl in pd.unique(labels):
        m=labels==cl; out[int(cl)]=round(float((w[m]*mx[m]).sum()/w[m].sum()),3)
    return out
print("\nbaseline-repro conf (by cached baseline party):")
for p in ['CUP','C7','CON','SD','LIB','PRG','POP','NAT','DSA','STY']:
    m=lab['baseline_party'].values==p
    if m.sum(): print(f"  {p:<4} {float((w[m]*mx_r[m]).sum()/w[m].sum()):.2f}")
print("\nno-resid conf by cluster:",percluster(lab['k5_noresid'].values,mx_n))
print("DONE",flush=True)
