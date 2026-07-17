#!/usr/bin/env python3
"""Build the data JSON for the cluster-robustness infographic (no DPGMM — uses cached labels).
Per model (baseline k5+resid, k5 no-resid, k4 resid, k4 no-resid) computes each cluster's:
policy-item support %, demographics, factor profile, 24-item standardized centroid; then matches
variant clusters to baseline parties in the common 24-item space (preserved / merged / split / novel).
"""
import warnings; warnings.filterwarnings('ignore')
import json, numpy as np, pandas as pd
from factor_analyzer.rotator import Rotator

DTA="CCES24_Common_OUTPUT_vv_topost_final (2).dta"
ITEMS_25=["pew_churatd","CC24_302","CC24_303","CC24_341a","CC24_341c","CC24_341d","CC24_323a",
 "CC24_323b","CC24_323d","CC24_321b","CC24_321d","CC24_321e","CC24_325","CC24_324b","CC24_340a",
 "CC24_340b","CC24_340c","CC24_340e","CC24_340f","CC24_440b","CC24_440c","CC24_421_1","CC24_421_2","CC24_423","CC24_424"]
DROP="CC24_340a"; ITEMS=[x for x in ITEMS_25 if x!=DROP]
DEMO=['birthyr','gender4','educ','race','hispanic','faminc_new','urbancity','pid3','ideo5','pew_bornagain','child18','ownhome']

# marquee policy items: (key, label, how to compute %)  type: 'bin'=mean*100, 'ge4'/'ge3'=threshold
POL=[('CC24_341a','Extend 2017 tax cuts','bin'),('CC24_341c','Oppose raising $400k+ rates','bin'),
 ('CC24_341d','Oppose $150B infrastructure','bin'),('CC24_323b','Increase border patrols','bin'),
 ('CC24_323a','Oppose legal status for undoc.','bin'),('CC24_323d','Oppose Dreamer pathway','bin'),
 ('CC24_340f','Deny asylum at border','bin'),('CC24_321d','Increase police 10%','bin'),
 ('CC24_321e','Oppose cutting police','bin'),('CC24_321b','Easier concealed carry','bin'),
 ('CC24_324b','Abortion only rape/incest/life','bin'),('CC24_340b','Allow abortion restrictions','bin'),
 ('CC24_340c','Oppose same-sex marriage mandate','bin'),('CC24_340e','Renew surveillance programs','bin'),
 ('CC24_440b','Agree: racial problems are rare','ge4'),('CC24_440c','Agree: women seek power over men','ge4'),
 ('CC24_421_1','Distrust: US elections fair','ge4'),('CC24_421_2','Distrust: 2024 local election','ge4'),
 ('CC24_423','Low trust in federal govt','ge3'),('CC24_424','Low trust in state govt','ge3'),
 ('pew_churatd','Attend church monthly+','ge4cap')]

R25=pd.read_csv('data/processed/polychoric_matrix.csv', index_col=0)
R=R25.loc[ITEMS,ITEMS].values.astype(float); R=(R+R.T)/2; np.fill_diagonal(R,1.0)
ev=np.linalg.eigvalsh(R)
if ev.min()<1e-6: R+=np.eye(len(ITEMS))*(1e-6-ev.min()); d=np.sqrt(np.diag(R)); R/=np.outer(d,d)
Rinv=np.linalg.inv(R)
print("loading dta...",flush=True)
df=pd.read_stata(DTA, columns=ITEMS+['commonpostweight']+DEMO, convert_categoricals=True, convert_missing=False, convert_dates=False)
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
RAW={k:c(k,ca) for k in []}  # placeholder
# raw agree/distrust values for POL thresholds (1-5 / 1-4 / 1-6)
polval={'CC24_440b':r['CC24_440b'],'CC24_440c':r['CC24_440c'],'CC24_421_1':r['CC24_421_1'],
        'CC24_421_2':r['CC24_421_2'],'CC24_423':r['CC24_423'],'CC24_424':r['CC24_424'],'pew_churatd':r['pew_churatd']}
D=pd.DataFrame(r); D['w']=df['commonpostweight'].values.astype(float)
# demographics → numeric features
age=2024-pd.to_numeric(df['birthyr'],errors='coerce')
g=df['gender4']; female=(g=='Woman').astype(float); female[~g.isin(['Man','Woman','Non-binary','Other'])]=np.nan
edu=df['educ']; college=edu.isin(['4-year','Post-grad']).astype(float); college[~edu.isin(['No HS','High school graduate','Some college','2-year','4-year','Post-grad'])]=np.nan
race=df['race']
white=(race=='White').astype(float); black=(race=='Black').astype(float); hisp=(race=='Hispanic').astype(float); asian=(race=='Asian').astype(float)
for s in (white,black,hisp,asian): s[race.isin(['skipped','not asked'])]=np.nan
fincorder=['Less than $10,000','$10,000 - $19,999','$20,000 - $29,999','$30,000 - $39,999','$40,000 - $49,999','$50,000 - $59,999','$60,000 - $69,999','$70,000 - $79,999','$80,000 - $99,999','$100,000 - $119,999','$120,000 - $149,999','$150,000 - $199,999','$200,000 - $249,999','$250,000 - $349,999','$350,000 - $499,999','$500,000 or more']
fmap={v:i+1 for i,v in enumerate(fincorder)}
faminc=df['faminc_new'].map(fmap)
lowinc=(faminc<=5).astype(float); lowinc[faminc.isna()]=np.nan
urb=df['urbancity']; city=(urb=='City').astype(float); rural=(urb=='Rural area').astype(float)
for s in (city,rural): s[~urb.isin(['City','Suburb','Town','Rural area','Other'])]=np.nan
born=df['pew_bornagain']; bornagain=(born=='Yes').astype(float); bornagain[~born.isin(['Yes','No'])]=np.nan
pid=df['pid3']; dem=(pid=='Democrat').astype(float); rep=(pid=='Republican').astype(float); ind=(pid=='Independent').astype(float)
for s in (dem,rep,ind): s[~pid.isin(['Democrat','Republican','Independent','Other','Not sure'])]=np.nan
ideo=df['ideo5'].map({'Very liberal':1,'Liberal':2,'Moderate':3,'Conservative':4,'Very conservative':5})
DEMOF={'age':age,'female':female,'college':college,'white':white,'black':black,'hisp':hisp,'asian':asian,
       'lowinc':lowinc,'city':city,'rural':rural,'bornagain':bornagain,'dem':dem,'rep':rep,'ind':ind,'ideo':ideo}

comp=D[ITEMS].notna().all(axis=1)&D['w'].notna()
idx=np.where(comp.values)[0]
D=D[comp].reset_index(drop=True); X=D[ITEMS].values; w=D['w'].values; wn=w/w.sum()
for k in polval: polval[k]=polval[k].values[idx]
for k in DEMOF: DEMOF[k]=DEMOF[k].values[idx]
mu=(wn[:,None]*X).sum(0); sig=np.sqrt((wn[:,None]*(X-mu)**2).sum(0)); sig[sig<1e-10]=1; Z=(X-mu)/sig
lab=pd.read_csv('analysis/efa/cluster_labels_variants.csv'); assert len(lab)==len(D)
print(f"N={len(D):,}",flush=True)

def paf(R,k,it=1000,tol=1e-7):
    Ri=np.linalg.pinv(R); h2=np.clip(1-1/np.diag(Ri),0.005,0.999)
    for _ in range(it):
        Rr=R.copy(); np.fill_diagonal(Rr,h2); ev,evec=np.linalg.eigh(Rr); ix=np.argsort(ev)[::-1]
        L=evec[:,ix[:k]]*np.sqrt(np.maximum(ev[ix[:k]],0)); h2n=np.clip((L**2).sum(1),0,0.999)
        if np.max(np.abs(h2n-h2))<tol: break
        h2=h2n
    return L
def build(k):
    rot=Rotator(method='oblimin'); L=rot.fit_transform(paf(R,k)); Phi=rot.phi_ if rot.phi_ is not None else np.eye(k); F=Z@(Rinv@(L@Phi))
    for j in range(k):
        if L[np.argmax(np.abs(L[:,j])),j]<0: F[:,j]*=-1; L[:,j]*=-1
    a=lambda it:int(np.argmax(np.abs(L[ITEMS.index(it),:])))
    return F,dict(enf=a("CC24_323b"),rel=a("pew_churatd"),val=a("CC24_440b"),eld=a("CC24_421_2"),gov=a("CC24_423"))
F5,id5=build(5); F4,id4=build(4)
def facname(k,ident):
    if k==5:
        nm={ident['enf']:'enforce',ident['eld']:'elecSkep',ident['gov']:'govDist',ident['rel']:'relig',ident['val']:'values'}
    else:
        nm={ident['enf']:'enforce',ident['eld']:'trust',ident['rel']:'relig+values'}
        for j in range(k):
            if j not in nm: nm[j]='residual (surveil)'  # under-extraction leftover; top item = post-9/11 surveillance
    return [nm[j] for j in range(k)]

def wmean(v,m):
    vv=v[m]; ww=w[m]; ok=~np.isnan(vv)
    return float((ww[ok]*vv[ok]).sum()/ww[ok].sum()) if ok.any() else None
def pol_pct(key,m):
    if key in ('CC24_440b','CC24_440c','CC24_421_1','CC24_421_2'): return 100*wmean((polval[key]>=4).astype(float),m)
    if key in ('CC24_423','CC24_424'): return 100*wmean((polval[key]>=3).astype(float),m)
    if key=='pew_churatd': return 100*wmean((polval['pew_churatd']>=4).astype(float),m)
    return 100*wmean(X[:,ITEMS.index(key)],m)

def cluster_records(labels, F, ident, k):
    facs=facname(k,ident); recs=[]
    for cl in sorted(pd.unique(labels)):
        m=labels==cl
        rec={'id':int(cl),'wtPct':round(w[m].sum()/w.sum()*100,1),
             'centroid':[wmean(Z[:,j],m) for j in range(Z.shape[1])],
             'factors':{facs[j]:round(wmean(F[:,j],m),2) for j in range(k)},
             'pol':{key:round(pol_pct(key,m),0) for key,_,_ in POL},
             'demo':{d:(round(wmean(DEMOF[d],m)*(1 if d in ('age','ideo') else 100),1)) for d in DEMOF}}
        recs.append(rec)
    return recs

# baseline: group by party label
bp=lab['baseline_party'].values
base_recs=[]
facs5=facname(5,id5)
for p in ['PRG','DSA','LIB','SD','STY','CUP','POP','CON','NAT','C7']:
    m=bp==p
    if m.sum()==0: continue
    base_recs.append({'id':p,'party':p,'wtPct':round(w[m].sum()/w.sum()*100,1),
        'centroid':[wmean(Z[:,j],m) for j in range(Z.shape[1])],
        'factors':{facs5[j]:round(wmean(F5[:,j],m),2) for j in range(5)},
        'pol':{key:round(pol_pct(key,m),0) for key,_,_ in POL},
        'demo':{d:(round(wmean(DEMOF[d],m)*(1 if d in ('age','ideo') else 100),1)) for d in DEMOF}})
base_cent={r['party']:np.array(r['centroid']) for r in base_recs}

# ---- cluster strength = DPGMM assignment confidence (mean max posterior), the real GMM measure ----
# production confidence (gold; from real posteriors) for baseline parties
tp=pd.read_csv('data/processed/typology_cluster_assignments.csv'); PARTYID={0:'CON',1:'SD',2:'STY',3:'NAT',4:'LIB',5:'POP',6:'CUP',7:'C7',8:'DSA',9:'PRG'}
pc=[f'prob_cluster_{i}' for i in range(10)]; tp['mx']=tp[pc].max(axis=1)
prod_conf={}
for cid,p in PARTYID.items():
    g=tp[tp['cluster']==cid]; prod_conf[p]=round(float((g['commonpostweight']*g['mx']).sum()/g['commonpostweight'].sum()),2)
# reproduction confidence from the re-fit (cluster_confidence_k5.py adds conf_resid / conf_noresid per respondent)
HAS_CONF='conf_noresid' in lab.columns
def wconf(col,m): return round(float((w[m]*lab[col].values[m]).sum()/w[m].sum()),2) if HAS_CONF else None
for r in base_recs:
    r['conf']=prod_conf.get(r['party'])
    r['confRepro']=wconf('conf_resid', bp==r['party'])  # reproduction conf, validates against prod

def cos(a,b): a=np.array(a); b=np.array(b); return float(a@b/(np.linalg.norm(a)*np.linalg.norm(b)+1e-12))

def correspond(recs, labels):
    # composition: for each variant cluster, % weight from each baseline party
    for rec in recs:
        m=labels==rec['id']; tot=w[m].sum()
        ctab={}
        for p in base_cent:
            ctab[p]=round(w[m & (bp==p)].sum()/tot*100,0)
        comp={p:v for p,v in sorted(ctab.items(),key=lambda kv:-kv[1]) if v>=8}
        rec['composition']=comp
        sims={p:cos(rec['centroid'],c) for p,c in base_cent.items()}
        rec['sims']={p:round(s,3) for p,s in sorted(sims.items(),key=lambda kv:-kv[1])[:4]}
        top=list(comp.items())
        rec['matchParty']=top[0][0] if top else None
        rec['matchShare']=top[0][1] if top else 0
    # party-level: where does each baseline party's weight go (row-normalized)
    party_dispersion={}
    for p in base_cent:
        mp=bp==p; tot=w[mp].sum(); dist={}
        for rec in recs:
            ov=w[mp & (labels==rec['id'])].sum()/tot*100
            if ov>=8: dist[rec['id']]=round(ov,0)
        party_dispersion[p]=dict(sorted(dist.items(),key=lambda kv:-kv[1]))
    return party_dispersion

variants={}
for tag,col,F,ident,k in [('k5_noresid','k5_noresid',F5,id5,5),('k4_resid','k4_resid',F4,id4,4),('k4_noresid','k4_noresid',F4,id4,4)]:
    labels=lab[col].values
    recs=cluster_records(labels,F,ident,k)
    if tag=='k5_noresid' and HAS_CONF:
        for rec in recs: rec['conf']=wconf('conf_noresid', labels==rec['id'])
    disp=correspond(recs,labels)
    # classify each baseline party: survives (one variant cluster has >=60% of it) / splits / merges
    survival={}
    for p in base_cent:
        d=disp[p]
        if not d: survival[p]='absent'; continue
        topclu=max(d,key=d.get); topshare=d[topclu]
        # is that cluster dominated by p? (composition)
        cluComp=next(rr for rr in recs if rr['id']==topclu)['matchShare'] if any(rr['id']==topclu for rr in recs) else 0
        rec_top=next(rr for rr in recs if rr['id']==topclu)
        p_in_clu=rec_top['composition'].get(p,0)
        if topshare>=60 and p_in_clu>=50: survival[p]='preserved'
        elif topshare>=60 and p_in_clu<50: survival[p]='absorbed'  # p mostly into a cluster dominated by another
        else: survival[p]='split'
    variants[tag]={'k':k,'resid':('resid' in tag),'clusters':recs,'dispersion':disp,'survival':survival}

# govDist eta2 under each clustering (govDist scores are identical; only clusters differ)
def eta2(x,labels):
    gm=(w*x).sum()/w.sum(); sst=(w*(x-gm)**2).sum(); ssb=0.0
    for cl in pd.unique(labels):
        m=labels==cl; Wc=w[m].sum(); mc=(w[m]*x[m]).sum()/Wc; ssb+=Wc*(mc-gm)**2
    return round(ssb/sst,3)
gov=F5[:,id5['gov']]
gov_eta={'resid':eta2(gov,bp),'noResid':eta2(gov,lab['k5_noresid'].values),'production':0.061}

OUT={'meta':{'N':int(len(D)),'note':'CES 2024; weighted; baseline=k5+resid (production parties)','govDistEta':gov_eta},
     'pol_items':[{'key':k,'label':l} for k,l,_ in POL],
     'demo_keys':list(DEMOF.keys()),
     'baseline':base_recs,'variants':variants}
with open('analysis/efa/cluster_explorer_data.json','w') as f: json.dump(OUT,f,indent=1)
print("wrote analysis/efa/cluster_explorer_data.json",flush=True)

# diagnostics for the DSA/LIB question
print("\nDSA vs LIB baseline centroid cosine:",round(cos(base_cent['DSA'],base_cent['LIB']),3))
print("DSA vs PRG:",round(cos(base_cent['DSA'],base_cent['PRG']),3),"| LIB vs SD:",round(cos(base_cent['LIB'],base_cent['SD']),3))
for tag in variants:
    print(f"\n[{tag}] survival:", {p:variants[tag]['survival'][p] for p in ['LIB','SD','PRG','DSA','STY','CUP','NAT']})
print("DONE",flush=True)
