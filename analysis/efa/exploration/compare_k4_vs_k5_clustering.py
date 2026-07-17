#!/usr/bin/env python3
"""Compare DPGMM typologies on a 4-factor vs 5-factor EFA, with and without the
F1-residualization of the culture factors. Characterizes each cluster by its
factor profile so we can see which "potential parties" emerge and whether the
cross-cutting clusters (off the dominant enforcement axis) survive.

Pipeline (per k): polychoric R24 -> PAF(k) -> oblimin -> Thomson regression scores
-> partisan sign-flips. Then DPGMM(n_components=10, dirichlet_process) on either the
raw scores or the scores with culture factors residualized on enforcement.
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from factor_analyzer.rotator import Rotator
from sklearn.mixture import BayesianGaussianMixture
from sklearn.metrics import adjusted_rand_score

DTA = "CCES24_Common_OUTPUT_vv_topost_final (2).dta"
ITEMS_25 = ["pew_churatd","CC24_302","CC24_303","CC24_341a","CC24_341c","CC24_341d",
    "CC24_323a","CC24_323b","CC24_323d","CC24_321b","CC24_321d","CC24_321e","CC24_325",
    "CC24_324b","CC24_340a","CC24_340b","CC24_340c","CC24_340e","CC24_340f","CC24_440b",
    "CC24_440c","CC24_421_1","CC24_421_2","CC24_423","CC24_424"]
DROP="CC24_340a"; ITEMS=[x for x in ITEMS_25 if x!=DROP]
SHORT={'pew_churatd':'church','CC24_302':'income','CC24_303':'inflation','CC24_341a':'taxcut',
    'CC24_341c':'400k','CC24_341d':'infra','CC24_323a':'legalstatus','CC24_323b':'border',
    'CC24_323d':'dreamers','CC24_321b':'carry','CC24_321d':'police+','CC24_321e':'police-',
    'CC24_325':'abortlim','CC24_324b':'abortonly','CC24_340b':'abortrestr','CC24_340c':'samesex',
    'CC24_340e':'surveil','CC24_340f':'asylum','CC24_440b':'racialrare','CC24_440c':'womenpower',
    'CC24_421_1':'elecfair','CC24_421_2':'stelecfair','CC24_423':'fedtrust','CC24_424':'sttrust'}

R25=pd.read_csv('data/processed/polychoric_matrix.csv', index_col=0)
R=R25.loc[ITEMS,ITEMS].values.astype(float); R=(R+R.T)/2; np.fill_diagonal(R,1.0)
ev=np.linalg.eigvalsh(R)
if ev.min()<1e-6:
    R+=np.eye(len(ITEMS))*(1e-6-ev.min()); d=np.sqrt(np.diag(R)); R/=np.outer(d,d)
Rinv=np.linalg.inv(R)

print("loading dta...", flush=True)
df=pd.read_stata(DTA, columns=ITEMS+['commonpostweight'], convert_categoricals=True,
                 convert_missing=False, convert_dates=False)
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
comp=D[ITEMS].notna().all(axis=1) & D['w'].notna()
D=D[comp].reset_index(drop=True); print(f"listwise N = {len(D):,}", flush=True)
X=D[ITEMS].values; w=D['w'].values; wn=w/w.sum()
mu=(wn[:,None]*X).sum(0); sig=np.sqrt((wn[:,None]*(X-mu)**2).sum(0)); sig[sig<1e-10]=1
Z=(X-mu)/sig

def paf(R,k,it=1000,tol=1e-7):
    Ri=np.linalg.pinv(R); h2=np.clip(1-1/np.diag(Ri),0.005,0.999)
    for _ in range(it):
        Rr=R.copy(); np.fill_diagonal(Rr,h2)
        ev,evec=np.linalg.eigh(Rr); idx=np.argsort(ev)[::-1]
        L=evec[:,idx[:k]]*np.sqrt(np.maximum(ev[idx[:k]],0))
        h2n=np.clip((L**2).sum(1),0,0.999)
        if np.max(np.abs(h2n-h2))<tol: break
        h2=h2n
    return L
def wresid(y,x,w):
    Xd=np.column_stack([np.ones_like(x),x]); W=w/w.mean(); XtW=Xd.T*W
    return y-Xd@np.linalg.solve(XtW@Xd, XtW@y)

def build(k):
    L0=paf(R,k); rot=Rotator(method='oblimin'); L=rot.fit_transform(L0)
    Phi=rot.phi_ if rot.phi_ is not None else np.eye(k)
    F=Z@(Rinv@(L@Phi))
    a=lambda it: int(np.argmax(np.abs(L[ITEMS.index(it),:])))
    enf=a("CC24_323b"); rel=a("pew_churatd"); val=a("CC24_440b"); eld=a("CC24_421_2"); gov=a("CC24_423")
    # orient every factor so its top item points "conservative/skeptic" (high = more)
    for j in range(k):
        if L[np.argmax(np.abs(L[:,j])), j] < 0: F[:,j]*=-1; L[:,j]*=-1
    # factor labels by top-3 items
    labels=[]
    for j in range(k):
        top=np.argsort(-np.abs(L[:,j]))[:3]
        labels.append("/".join(SHORT[ITEMS[t]] for t in top))
    return F,L,labels,dict(enf=enf,rel=rel,val=val,eld=eld,gov=gov)

def dpgmm(Xc):
    m=BayesianGaussianMixture(n_components=10, covariance_type='full',
        weight_concentration_prior_type='dirichlet_process', n_init=5,
        max_iter=500, random_state=42)
    return m.fit_predict(Xc)

def report(tag,F,labels,ident,resid):
    Xc=F.copy()
    if resid:
        enf=F[:,ident['enf']]
        for key in ('rel','val'):
            if ident[key]!=ident['enf']: Xc[:,ident[key]]=wresid(F[:,ident[key]],enf,w)
    lab=dpgmm(Xc)
    eff=len(np.unique(lab)); k=F.shape[1]
    print(f"\n{'#'*72}\n{tag}  ({k}-D, residualized={resid})  — effective clusters: {eff}/10\n{'#'*72}")
    print("  factors: "+" | ".join(f"F{j+1}:{labels[j]}" for j in range(k)))
    hdr="  clu   wt%  "+"  ".join(f"F{j+1}" for j in range(k))+"     profile"
    print(hdr)
    rows=[]
    for cl in sorted(np.unique(lab)):
        msk=lab==cl; ww=w[msk]; wwn=ww/ww.sum()
        wpct=ww.sum()/w.sum()*100
        means=[(wwn*F[msk,j]).sum() for j in range(k)]  # report RAW factor means (interpretable)
        rows.append((cl,wpct,means))
    rows.sort(key=lambda t:-t[1])
    for cl,wpct,means in rows:
        prof=", ".join(f"{labels[j].split('/')[0]}{means[j]:+.1f}" for j in range(k) if abs(means[j])>=0.4)
        cells="  ".join(f"{m:>+4.1f}" for m in means)
        print(f"  {cl:>3} {wpct:>5.1f}  {cells}     {prof}")
    return lab

results={}
for k in (5,4):
    F,L,labels,ident=build(k)
    a=ident
    print(f"\n=== k={k} anchors: enf=F{a['enf']+1} rel=F{a['rel']+1} val=F{a['val']+1} eld=F{a['eld']+1} gov=F{a['gov']+1} ===")
    results[(k,True)]=report(f"k={k} RESIDUALIZED (production style)",F,labels,ident,True)
    results[(k,False)]=report(f"k={k} RAW (no residualization)",F,labels,ident,False)

print(f"\n{'='*60}\nADJUSTED RAND INDEX between solutions\n{'='*60}")
keys=list(results)
for i in range(len(keys)):
    for j in range(i+1,len(keys)):
        a,b=keys[i],keys[j]
        print(f"  {str(a):<16} vs {str(b):<16}: ARI={adjusted_rand_score(results[a],results[b]):.3f}")
print("\nDONE", flush=True)
