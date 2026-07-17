#!/usr/bin/env python3
"""Robustness check: re-run the polychoric EFA with the 4 dropped partisan/identity
proxies added back (self-placed ideology, Biden approval, Harris approval, economy
retrospective). Question: do the cross-cutting factors (Electoral Skepticism,
Government Distrust, Religious Traditionalism) survive, or do the proxies form a
partisanship factor that absorbs the structure?

Same method as the original pipeline: weighted polychoric matrix + oblimin rotation.
"""
import warnings; warnings.filterwarnings('ignore')
import time
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from scipy.stats import norm
from scipy.stats import multivariate_normal as mvn
from factor_analyzer import FactorAnalyzer

DTA = "CCES24_Common_OUTPUT_vv_topost_final (2).dta"
BIG = 8.0

# 24 final EFA items (from efa_loadings_k5_final.csv) + 4 proxies that were dropped.
FINAL = ['pew_churatd','CC24_302','CC24_303','CC24_341a','CC24_341c','CC24_341d',
         'CC24_323a','CC24_323b','CC24_323d','CC24_321b','CC24_321d','CC24_321e',
         'CC24_325','CC24_324b','CC24_340b','CC24_340c','CC24_340e','CC24_340f',
         'CC24_440b','CC24_440c','CC24_421_1','CC24_421_2','CC24_423','CC24_424']
PROXIES = ['CC24_330a','CC24_301','CC24_312a','CC24_312i']   # ideology, economy, Biden, Harris
ALL = FINAL + PROXIES

LABELS = {'pew_churatd':'Church attend','CC24_302':'HH income chg','CC24_303':'Price chg',
    'CC24_341a':'Extend tax cuts','CC24_341c':'$400k tax[r]','CC24_341d':'Infra spend[r]',
    'CC24_323a':'Legal status[r]','CC24_323b':'Border patrols','CC24_323d':'Dreamers[r]',
    'CC24_321b':'Conceal carry','CC24_321d':'Police +10%','CC24_321e':'Decr police[r]',
    'CC24_325':'Abortion limit','CC24_324b':'Abortion rape/incest','CC24_340b':'Abortion restr[r]',
    'CC24_340c':'Same-sex[r]','CC24_340e':'Surveillance','CC24_340f':'Deny asylum',
    'CC24_440b':'Racial probs rare','CC24_440c':'Women seek power','CC24_421_1':'US elec fair[d]',
    'CC24_421_2':'State elec fair[d]','CC24_423':'Fed distrust','CC24_424':'State distrust',
    'CC24_330a':'*IDEOLOGY self','CC24_301':'*Economy retro','CC24_312a':'*Biden approve','CC24_312i':'*Harris approve'}

def cat(s, m): return s.map(m).astype(float)

print("Loading .dta (selected columns)...", flush=True)
cols = ALL + ['commonpostweight']
df = pd.read_stata(DTA, columns=cols, convert_categoricals=True,
                   convert_missing=False, convert_dates=False)
print(f"  {len(df):,} rows", flush=True)

S, O = 'Support', 'Oppose'
con_agree = {'Strongly agree':5,'Somewhat agree':4,'Neither agree nor disagree':3,'Somewhat disagree':2,'Strongly disagree':1}
elec = {'Strongly agree':1,'Somewhat agree':2,'Neither agree nor disagree':3,'Somewhat disagree':4,'Strongly disagree':5}
govt = {'A great deal':1,'A fair amount':2,'Not very much':3,'None at all':4}
appr = {'Strongly approve':1,'Somewhat approve':2,'Somewhat disapprove':3,'Strongly disapprove':4,'Not sure':np.nan}

r = {}
r['pew_churatd']=cat(df['pew_churatd'],{'Never':1,'Seldom':2,'A few times a year':3,'Once or twice a month':4,'Once a week':5,'More than once a week':6,"Don't know":np.nan})
r['CC24_302']=cat(df['CC24_302'],{'Increased a lot':1,'Increased somewhat':2,'Stayed about the same':3,'Decreased somewhat':4,'Decreased a lot':5})
r['CC24_303']=cat(df['CC24_303'],{'Decreased a lot':1,'Decreased somewhat':2,'Stayed about the same':3,'Increased somewhat':4,'Increased a lot':5})
r['CC24_341a']=cat(df['CC24_341a'],{S:1,O:0}); r['CC24_341c']=cat(df['CC24_341c'],{S:0,O:1}); r['CC24_341d']=cat(df['CC24_341d'],{S:0,O:1})
r['CC24_323a']=cat(df['CC24_323a'],{S:0,O:1}); r['CC24_323b']=cat(df['CC24_323b'],{S:1,O:0}); r['CC24_323d']=cat(df['CC24_323d'],{S:0,O:1})
r['CC24_321b']=cat(df['CC24_321b'],{S:1,O:0}); r['CC24_321d']=cat(df['CC24_321d'],{S:1,O:0}); r['CC24_321e']=cat(df['CC24_321e'],{S:0,O:1})
r['CC24_325']=40.0-pd.to_numeric(df['CC24_325'].astype(str),errors='coerce'); r['CC24_324b']=cat(df['CC24_324b'],{S:1,O:0})
r['CC24_340b']=cat(df['CC24_340b'],{S:0,O:1}); r['CC24_340c']=cat(df['CC24_340c'],{S:0,O:1})
r['CC24_340e']=cat(df['CC24_340e'],{S:1,O:0}); r['CC24_340f']=cat(df['CC24_340f'],{S:1,O:0})
r['CC24_440b']=cat(df['CC24_440b'],con_agree); r['CC24_440c']=cat(df['CC24_440c'],con_agree)
r['CC24_421_1']=cat(df['CC24_421_1'],elec); r['CC24_421_2']=cat(df['CC24_421_2'],elec)
r['CC24_423']=cat(df['CC24_423'],govt); r['CC24_424']=cat(df['CC24_424'],govt)
# proxies
r['CC24_330a']=cat(df['CC24_330a'],{'Very Liberal':1,'Liberal':2,'Somewhat Liberal':3,'Middle of the Road':4,'Somewhat Conservative':5,'Conservative':6,'Very Conservative':7,'Not sure':np.nan})
r['CC24_301']=cat(df['CC24_301'],{'Gotten much better':1,'Gotten somewhat better':2,'Stayed about the same':3,'Gotten somewhat worse':4,'Gotten much worse':5,'Not sure':np.nan})
r['CC24_312a']=cat(df['CC24_312a'],appr); r['CC24_312i']=cat(df['CC24_312i'],appr)

data = pd.DataFrame(r); data['w']=df['commonpostweight'].values.astype(float)
complete = data[ALL].notna().all(axis=1)
d = data[complete].reset_index(drop=True); w = d['w'].values
print(f"  Listwise N = {complete.sum():,}  weighted N = {w.sum():,.0f}", flush=True)

def wpoly(x,y,wts):
    m=~(np.isnan(x)|np.isnan(y)); x_,y_,w_=x[m],y[m],wts[m]
    xc=np.sort(np.unique(x_)); yc=np.sort(np.unique(y_)); nx,ny=len(xc),len(yc)
    if nx<2 or ny<2: return np.nan
    xi=np.searchsorted(xc,x_); yi=np.searchsorted(yc,y_); w_=w_/w_.sum()
    ct=np.zeros((nx,ny))
    for a,b,c in zip(xi,yi,w_): ct[a,b]+=c
    xm=ct.sum(1); ym=ct.sum(0)
    tx=np.concatenate([[-BIG],norm.ppf(np.clip(np.cumsum(xm)[:-1],1e-7,1-1e-7)),[BIG]])
    ty=np.concatenate([[-BIG],norm.ppf(np.clip(np.cumsum(ym)[:-1],1e-7,1-1e-7)),[BIG]])
    def nll(rho):
        H,K=np.meshgrid(tx,ty,indexing='ij'); pts=np.column_stack([H.ravel(),K.ravel()])
        cdf=mvn(mean=[0,0],cov=[[1,rho],[rho,1]]).cdf(pts).reshape(nx+1,ny+1)
        P=np.maximum(np.diff(np.diff(cdf,axis=0),axis=1),1e-12); return -np.sum(ct*np.log(P))
    return float(minimize_scalar(nll,bounds=(-.9999,.9999),method='bounded',options={'xatol':1e-5}).x)

n=len(ALL); R=np.eye(n); pairs=[(i,j) for i in range(n) for j in range(i+1,n)]
print(f"Computing {len(pairs)} polychoric pairs...", flush=True); t0=time.time()
for k,(i,j) in enumerate(pairs):
    R[i,j]=R[j,i]=wpoly(d[ALL[i]].values,d[ALL[j]].values,w)
    if (k+1)%50==0: print(f"  {k+1}/{len(pairs)} ({time.time()-t0:.0f}s)", flush=True)

# fix non-PSD
ev,_=np.linalg.eigh(R)
if ev.min()<0:
    vals,vecs=np.linalg.eigh(R); vals=np.clip(vals,1e-6,None)
    R=vecs@np.diag(vals)@vecs.T; dsq=np.sqrt(np.diag(R)); R=R/np.outer(dsq,dsq)
    print(f"  (repaired non-PSD; min eig was {ev.min():.4f})", flush=True)

Rdf=pd.DataFrame(R,index=ALL,columns=ALL)
Rdf.to_csv('analysis/efa/polychoric_matrix_with_proxies.csv')

for K in (5,6):
    fa=FactorAnalyzer(n_factors=K, rotation='oblimin', method='principal', is_corr_matrix=True)
    fa.fit(Rdf.values)
    L=pd.DataFrame(fa.loadings_, index=[LABELS[v] for v in ALL], columns=[f'F{i+1}' for i in range(K)])
    var=fa.get_factor_variance()
    print(f"\n{'='*70}\nk={K}  rotated loadings (oblimin)  — * = re-added proxy\n{'='*70}", flush=True)
    for name,row in L.iterrows():
        dom=int(np.argmax(np.abs(row.values)))
        print(f"{name:<22} F{dom+1}  "+"  ".join(f"{x:+.2f}" for x in row.values), flush=True)
    print("  %var: "+"  ".join(f"F{i+1}={v*100:.1f}" for i,v in enumerate(var[1])), flush=True)
print("\nDONE", flush=True)
