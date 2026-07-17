#!/usr/bin/env python3
"""Do the production parties survive the k=4 / no-residualization variants?

Baseline = k=5 + residualization (production method), whose 10 clusters are labeled
by matching their factor centroids to the real production party centroids (from
typology_cluster_assignments.csv) via optimal assignment. Then each variant's
clusters are cross-tabbed against those party labels (same 45k sample) to measure,
per party, whether it stays one cluster (survives), splits, or merges.
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from factor_analyzer.rotator import Rotator
from sklearn.mixture import BayesianGaussianMixture
from sklearn.metrics import adjusted_rand_score
from scipy.optimize import linear_sum_assignment

DTA="CCES24_Common_OUTPUT_vv_topost_final (2).dta"
ITEMS_25=["pew_churatd","CC24_302","CC24_303","CC24_341a","CC24_341c","CC24_341d","CC24_323a",
 "CC24_323b","CC24_323d","CC24_321b","CC24_321d","CC24_321e","CC24_325","CC24_324b","CC24_340a",
 "CC24_340b","CC24_340c","CC24_340e","CC24_340f","CC24_440b","CC24_440c","CC24_421_1","CC24_421_2","CC24_423","CC24_424"]
DROP="CC24_340a"; ITEMS=[x for x in ITEMS_25 if x!=DROP]
PROD_PARTY={0:"CON",1:"SD",2:"STY",3:"NAT",4:"LIB",5:"POP",6:"CUP",7:"C7",8:"DSA",9:"PRG"}

# ---- production party centroids (residualized 5D space) ----
tp=pd.read_csv('data/processed/typology_cluster_assignments.csv')
PCOLS=["FS_F1","FS_F2","FS_F3","FS_F4_resid","FS_F5_resid"]
prod_cent={}
for cid,name in PROD_PARTY.items():
    g=tp[tp['cluster']==cid]; ww=g['commonpostweight'].values; wwn=ww/ww.sum()
    prod_cent[name]=np.array([(wwn*g[c].values).sum() for c in PCOLS])
prod_names=list(prod_cent); prod_mat=np.array([prod_cent[n] for n in prod_names])

# ---- polychoric + recode (direction-consistent) ----
R25=pd.read_csv('data/processed/polychoric_matrix.csv', index_col=0)
R=R25.loc[ITEMS,ITEMS].values.astype(float); R=(R+R.T)/2; np.fill_diagonal(R,1.0)
ev=np.linalg.eigvalsh(R)
if ev.min()<1e-6: R+=np.eye(len(ITEMS))*(1e-6-ev.min()); d=np.sqrt(np.diag(R)); R/=np.outer(d,d)
Rinv=np.linalg.inv(R)
print("loading dta...",flush=True)
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
print(f"N={len(D):,}",flush=True)

def paf(R,k,it=1000,tol=1e-7):
    Ri=np.linalg.pinv(R); h2=np.clip(1-1/np.diag(Ri),0.005,0.999)
    for _ in range(it):
        Rr=R.copy(); np.fill_diagonal(Rr,h2); ev,evec=np.linalg.eigh(Rr); idx=np.argsort(ev)[::-1]
        L=evec[:,idx[:k]]*np.sqrt(np.maximum(ev[idx[:k]],0)); h2n=np.clip((L**2).sum(1),0,0.999)
        if np.max(np.abs(h2n-h2))<tol: break
        h2=h2n
    return L
def wresid(y,x,w):
    Xd=np.column_stack([np.ones_like(x),x]); W=w/w.mean(); XtW=Xd.T*W; return y-Xd@np.linalg.solve(XtW@Xd,XtW@y)
def build(k):
    L=Rotator(method='oblimin').fit_transform(paf(R,k)); rot=Rotator(method='oblimin'); L=rot.fit_transform(paf(R,k))
    Phi=rot.phi_ if rot.phi_ is not None else np.eye(k); F=Z@(Rinv@(L@Phi))
    for j in range(k):
        if L[np.argmax(np.abs(L[:,j])),j]<0: F[:,j]*=-1; L[:,j]*=-1
    a=lambda it:int(np.argmax(np.abs(L[ITEMS.index(it),:])))
    return F,dict(enf=a("CC24_323b"),rel=a("pew_churatd"),val=a("CC24_440b"),eld=a("CC24_421_2"),gov=a("CC24_423"))
def space(F,ident,resid):
    Xc=F.copy()
    if resid:
        enf=F[:,ident['enf']]
        for key in ('rel','val'):
            if ident[key]!=ident['enf']: Xc[:,ident[key]]=wresid(F[:,ident[key]],enf,w)
    return Xc
def dpgmm(Xc):
    return BayesianGaussianMixture(n_components=10,covariance_type='full',
        weight_concentration_prior_type='dirichlet_process',n_init=5,max_iter=500,random_state=42).fit_predict(Xc)

# ---- baseline: k=5 residualized, label clusters by production party ----
F5,id5=build(5); Xb=space(F5,id5,True); base=dpgmm(Xb)
# baseline centroids in residualized 5D, ordered [enf, eld, gov, rel, val] to match PCOLS
order=[id5['enf'],id5['eld'],id5['gov'],id5['rel'],id5['val']]
bcent=np.array([[ (w[base==cl]/w[base==cl].sum()*Xb[base==cl][:,j]).sum() for j in order] for cl in range(10)])
# z-score both centroid sets per factor, then optimal 1:1 assignment by Euclidean
def zc(M): return (M-M.mean(0))/ (M.std(0)+1e-9)
bz=zc(bcent); pz=zc(prod_mat)
cost=np.linalg.norm(bz[:,None,:]-pz[None,:,:],axis=2)
ri,ci=linear_sum_assignment(cost)
clu2party={int(ri[i]): prod_names[ci[i]] for i in range(len(ri))}
labparty=np.array([clu2party[cl] for cl in base])
print("\nBaseline (k=5 resid) cluster → party label (match distance):")
for i in range(len(ri)):
    print(f"  cluster {ri[i]} → {prod_names[ci[i]]:<4}  (dist {cost[ri[i],ci[i]]:.2f})")

def survival(tag,lab):
    print(f"\n{'='*70}\n{tag}  vs baseline parties — does each party survive?\n{'='*70}")
    ct=pd.crosstab(pd.Series(labparty,name='party'), pd.Series(lab,name='clu'),
                   values=w, aggfunc='sum').fillna(0)
    # for each party (row), the variant cluster capturing most of it
    print(f"  {'party':<5} {'wt%':>5}  {'bestClu':>7} {'purity':>7} {'cluShare':>8}  verdict")
    for p in ['PRG','DSA','LIB','SD','STY','CUP','POP','CON','NAT','C7']:
        if p not in ct.index: continue
        row=ct.loc[p]; tot=row.sum(); bc=row.idxmax(); pur=row[bc]/tot
        clushare=row[bc]/ct[bc].sum()   # fraction of that variant cluster that is party p
        v = 'SURVIVES' if pur>=0.6 and clushare>=0.5 else ('splits' if pur<0.6 else 'merges-in')
        print(f"  {p:<5} {tot/w.sum()*100:>5.1f}  {bc:>7} {pur:>6.0%} {clushare:>7.0%}   {v}")
    return ct

variants={}
variants['k5_noresid']=dpgmm(space(F5,id5,False))
F4,id4=build(4)
variants['k4_resid']=dpgmm(space(F4,id4,True))
variants['k4_noresid']=dpgmm(space(F4,id4,False))
for tag,lab in variants.items():
    survival(tag,lab)
    print(f"  ARI vs baseline: {adjusted_rand_score(base,lab):.3f}")

# save labels for inspection
out=pd.DataFrame({'w':w,'baseline_party':labparty,**variants}); out.to_csv('analysis/efa/cluster_labels_variants.csv',index=False)
print("\nsaved analysis/efa/cluster_labels_variants.csv\nDONE",flush=True)
