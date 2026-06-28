#!/usr/bin/env python3
"""Characterize every cluster in each variant (no DPGMM — uses cached labels).
Recomputes factor scores (fast) + a few marquee item positions, attaches the
cached per-respondent labels, and prints each cluster's: weight, production-party
makeup, factor profile, and signature policy positions.
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from factor_analyzer.rotator import Rotator

DTA="CCES24_Common_OUTPUT_vv_topost_final (2).dta"
ITEMS_25=["pew_churatd","CC24_302","CC24_303","CC24_341a","CC24_341c","CC24_341d","CC24_323a",
 "CC24_323b","CC24_323d","CC24_321b","CC24_321d","CC24_321e","CC24_325","CC24_324b","CC24_340a",
 "CC24_340b","CC24_340c","CC24_340e","CC24_340f","CC24_440b","CC24_440c","CC24_421_1","CC24_421_2","CC24_423","CC24_424"]
DROP="CC24_340a"; ITEMS=[x for x in ITEMS_25 if x!=DROP]

R25=pd.read_csv('data/processed/polychoric_matrix.csv', index_col=0)
R=R25.loc[ITEMS,ITEMS].values.astype(float); R=(R+R.T)/2; np.fill_diagonal(R,1.0)
ev=np.linalg.eigvalsh(R)
if ev.min()<1e-6: R+=np.eye(len(ITEMS))*(1e-6-ev.min()); d=np.sqrt(np.diag(R)); R/=np.outer(d,d)
Rinv=np.linalg.inv(R)
df=pd.read_stata(DTA, columns=ITEMS+['commonpostweight'], convert_categoricals=True, convert_missing=False, convert_dates=False)
S,O='Support','Oppose'
ca={'Strongly agree':5,'Somewhat agree':4,'Neither agree nor disagree':3,'Somewhat disagree':2,'Strongly disagree':1}
el={'Strongly agree':1,'Somewhat agree':2,'Neither agree nor disagree':3,'Somewhat disagree':4,'Strongly disagree':5}
gv={'A great deal':1,'A fair amount':2,'Not very much':3,'None at all':4,'Not sure':2}
def c(col,m): return df[col].map(m).astype(float)
r={}
r['pew_churatd']=c('pew_churatd',{'Never':1,'Seldom':2,'A few times a year':3,'Once or twice a month':4,'Once a week':5,'More than once a week':6,"Don't know":np.nan})
r['CC24_302']=c('CC24_302',{'Increased a lot':1,'Increased somewhat':2,'Stayed about the same':3,'Decreased somewhat':4,'Decreased a lot':5})
r['CC24_303']=c('CC24_303',{'Decreased a lot':1,'Decreased somewhat':2,'Stayed about the same':3,'Increased somewhat':4,'Increased a lot':5})
r['CC24_341a']=c('CC24_341a',{S:1,O:0}); r['CC24_341c']=c('CC24_341c',{S:0,O:1}); r['CC24_341d']=c('CC24_341d',{S:0,O:1})
r['CC24_323a']=c('CC24_323a',{S:0,O:1}); r['CC24_323b']=c('CC24_323b',{S:1,O:0}); r['CC24_323d']=c('CC24_323d',{S:0,O:1})
r['CC24_321b']=c('CC24_321b',{S:1,O:0}); r['CC24_321d']=c('CC24_321d',{S:1,O:0}); r['CC24_321e']=c('CC24_321e',{S:0,O:1})
r['CC24_325']=40.0-pd.to_numeric(df['CC24_325'].astype(str),errors='coerce'); r['CC24_324b']=c('CC24_324b',{S:1,O:0})
r['CC24_340b']=c('CC24_340b',{S:0,O:1}); r['CC24_340c']=c('CC24_340c',{S:0,O:1})
r['CC24_340e']=c('CC24_340e',{S:1,O:0}); r['CC24_340f']=c('CC24_340f',{S:1,O:0})
r['CC24_440b']=c('CC24_440b',ca); r['CC24_440c']=c('CC24_440c',ca)
r['CC24_421_1']=c('CC24_421_1',el); r['CC24_421_2']=c('CC24_421_2',el)
r['CC24_423']=c('CC24_423',gv); r['CC24_424']=c('CC24_424',gv)
D=pd.DataFrame(r); D['w']=df['commonpostweight'].values.astype(float)
comp=D[ITEMS].notna().all(axis=1)&D['w'].notna(); D=D[comp].reset_index(drop=True)
X=D[ITEMS].values; w=D['w'].values; wn=w/w.sum()
mu=(wn[:,None]*X).sum(0); sig=np.sqrt((wn[:,None]*(X-mu)**2).sum(0)); sig[sig<1e-10]=1; Z=(X-mu)/sig

lab=pd.read_csv('analysis/efa/cluster_labels_variants.csv')
assert len(lab)==len(D), f"row mismatch {len(lab)} vs {len(D)}"
print(f"N={len(D):,}  (labels aligned)\n", flush=True)

def paf(R,k,it=1000,tol=1e-7):
    Ri=np.linalg.pinv(R); h2=np.clip(1-1/np.diag(Ri),0.005,0.999)
    for _ in range(it):
        Rr=R.copy(); np.fill_diagonal(Rr,h2); ev,evec=np.linalg.eigh(Rr); idx=np.argsort(ev)[::-1]
        L=evec[:,idx[:k]]*np.sqrt(np.maximum(ev[idx[:k]],0)); h2n=np.clip((L**2).sum(1),0,0.999)
        if np.max(np.abs(h2n-h2))<tol: break
        h2=h2n
    return L
def build(k):
    rot=Rotator(method='oblimin'); L=rot.fit_transform(paf(R,k))
    Phi=rot.phi_ if rot.phi_ is not None else np.eye(k); F=Z@(Rinv@(L@Phi))
    for j in range(k):
        if L[np.argmax(np.abs(L[:,j])),j]<0: F[:,j]*=-1; L[:,j]*=-1
    a=lambda it:int(np.argmax(np.abs(L[ITEMS.index(it),:])))
    ident=dict(enf=a("CC24_323b"),rel=a("pew_churatd"),val=a("CC24_440b"),eld=a("CC24_421_2"),gov=a("CC24_423"))
    return F,ident
F5,id5=build(5); F4,id4=build(4)

def fac_labels(k,ident):
    base={ident['enf']:'enforce', ident['eld']:'elecSkep', ident['gov']:'govDist', ident['rel']:'relig', ident['val']:'values'}
    return [base.get(j, f'F{j+1}') for j in range(k)]

def wmean(v,m): ww=w[m]; return (ww*v[m]).sum()/ww.sum()
IDX={it:ITEMS.index(it) for it in ITEMS}
def sig_items(m):
    pol=wmean(X[:,IDX['CC24_321d']],m)*100      # % support police +10%
    fair=wmean(X[:,IDX['CC24_421_1']],m)         # 1=elec fair .. 5=distrust
    ch=wmean(X[:,IDX['pew_churatd']],m)          # 1..6 church attendance
    tax=wmean(X[:,IDX['CC24_341a']],m)*100       # % support extend tax cuts
    rac=wmean(X[:,IDX['CC24_440b']],m)           # 1..5 agree racial problems rare
    return f"police+ {pol:>3.0f}%  taxcut {tax:>3.0f}%  elecDistrust {fair:.1f}/5  church {ch:.1f}/6  racialRare {rac:.1f}/5"

def profile(tag,col,F,ident,k):
    flab=fac_labels(k,ident)
    print(f"\n{'='*94}\n{tag}\n{'='*94}")
    L=lab[col].values
    rows=[]
    for cl in sorted(np.unique(L)):
        m=L==cl; wpct=w[m].sum()/w.sum()*100
        comp=lab.loc[m].groupby('baseline_party').apply(lambda g: w[g.index].sum())
        comp=(comp/comp.sum()*100).sort_values(ascending=False)
        mk=" ".join(f"{p}{int(v)}%" for p,v in comp.head(3).items() if v>=12)
        prof=" ".join(f"{flab[j]}{wmean(F[:,j],m):+.1f}" for j in range(k))
        rows.append((wpct,cl,mk,prof,sig_items(m)))
    rows.sort(key=lambda t:-t[0])
    for wpct,cl,mk,prof,si in rows:
        print(f"  [{wpct:>4.1f}%] makeup: {mk:<26}")
        print(f"          factors: {prof}")
        print(f"          {si}")

profile("k=5 NO-RESID — 10 clusters","k5_noresid",F5,id5,5)
profile("k=4 RESID — 10 clusters","k4_resid",F4,id4,4)
profile("k=4 NO-RESID — 10 clusters","k4_noresid",F4,id4,4)
print("\nDONE",flush=True)
