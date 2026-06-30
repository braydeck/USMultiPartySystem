#!/usr/bin/env python3
"""Build the JSON for the 5-D vs 6-D comparison infographic, from sixdim_labels.csv
(produced by sixdim_cluster.py). Per cluster: composition vs the production 9 parties,
factor profile (5 factors + foreign-policy engagement), policy support, demographics,
and strength = DPGMM assignment confidence (5-D from production posteriors, 6-D from refit)."""
import json, numpy as np, pandas as pd
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent.parent
DTA=ROOT/"CCES24_Common_OUTPUT_vv_topost_final (2).dta"
ITEMS_25=['pew_churatd','CC24_302','CC24_303','CC24_341a','CC24_341c','CC24_341d','CC24_323a','CC24_323b','CC24_323d','CC24_321b','CC24_321d','CC24_321e','CC24_325','CC24_324b','CC24_340a','CC24_340b','CC24_340c','CC24_340e','CC24_340f','CC24_440b','CC24_440c','CC24_421_1','CC24_421_2','CC24_423','CC24_424']
ITEMS=[x for x in ITEMS_25 if x!='CC24_340a']
DEMO=['birthyr','gender4','educ','race','hispanic','faminc_new','urbancity','pid3','ideo5','pew_bornagain']
POL=[('CC24_341a','Extend 2017 tax cuts','bin'),('CC24_341c','Raise tax rates on $400k+ earners','bin'),('CC24_341d','Spend $150B/yr on infrastructure','bin'),
 ('CC24_323b','Increase border patrols','bin'),('CC24_323a','Grant legal status to long-term undocumented','bin'),('CC24_323d','Pathway to status for Dreamers','bin'),
 ('CC24_340f','Deny asylum at border','bin'),('CC24_321d','Increase police 10%','bin'),('CC24_321e','Decrease police by 10%','bin'),('CC24_321b','Easier concealed carry','bin'),
 ('CC24_324b','Abortion only rape/incest/life','bin'),('CC24_340b','Prohibit restrictions on abortion access','bin'),('CC24_340c','Recognize same-sex & interracial marriage','bin'),('CC24_340e','Renew surveillance programs','bin'),
 ('CC24_440b','Agree: racial problems are rare','ge4'),('CC24_440c','Agree: women seek power over men','ge4'),
 ('CC24_421_1','Agree: US elections are fair','ge4'),('CC24_421_2','Agree: 2024 local election was fair','ge4'),
 ('CC24_423','Low trust in federal govt','ge3'),('CC24_424','Low trust in state govt','ge3'),('pew_churatd','Attend church monthly+','ge4cap')]

lab=pd.read_csv(ROOT/'analysis/efa/sixdim_labels.csv')
fs=pd.read_csv(ROOT/'data/processed/efa_factor_scores.csv')
df=pd.read_stata(DTA, columns=ITEMS+DEMO+['commonpostweight'], convert_categoricals=True, convert_missing=False, convert_dates=False)
mask=df[ITEMS+['commonpostweight']].notna().all(1); df=df[mask].reset_index(drop=True)
assert len(df)==len(lab)==len(fs)
w=lab['w'].values
ca={'Strongly agree':5,'Somewhat agree':4,'Neither agree nor disagree':3,'Somewhat disagree':2,'Strongly disagree':1}
def cmap(col,m): return df[col].map(m).astype(float)
def polpct(key,typ,m):
    if typ=='bin': v=df[key].map({'Support':1.0,'Oppose':0.0}).astype(float).values
    elif typ=='ge4': raw=cmap(key,ca).values; v=np.where(np.isnan(raw),np.nan,(raw>=4).astype(float))
    elif typ=='ge3': raw=cmap(key,{'A great deal':1,'A fair amount':2,'Not very much':3,'None at all':4}).values; v=np.where(np.isnan(raw),np.nan,(raw>=3).astype(float))
    elif typ=='ge4cap': raw=cmap(key,{'Never':1,'Seldom':2,'A few times a year':3,'Once or twice a month':4,'Once a week':5,'More than once a week':6}).values; v=np.where(np.isnan(raw),np.nan,(raw>=4).astype(float))
    ok=~np.isnan(v); mm=m&ok
    return round(float((w[mm]*v[mm]).sum()/w[mm].sum()*100),0) if mm.any() else None
# demographics
age=2024-pd.to_numeric(df['birthyr'],errors='coerce')
g=df['gender4']; female=(g=='Woman').astype(float); female[~g.isin(['Man','Woman','Non-binary','Other'])]=np.nan
edu=df['educ']; college=edu.isin(['4-year','Post-grad']).astype(float); college[~edu.isin(['No HS','High school graduate','Some college','2-year','4-year','Post-grad'])]=np.nan
race=df['race']
white=(race=='White').astype(float); black=(race=='Black').astype(float); hisp=(race=='Hispanic').astype(float)
for s in (white,black,hisp): s[race.isin(['skipped','not asked'])]=np.nan
finc=['Less than $10,000','$10,000 - $19,999','$20,000 - $29,999','$30,000 - $39,999','$40,000 - $49,999','$50,000 - $59,999','$60,000 - $69,999','$70,000 - $79,999','$80,000 - $99,999','$100,000 - $119,999','$120,000 - $149,999','$150,000 - $199,999','$200,000 - $249,999','$250,000 - $349,999','$350,000 - $499,999','$500,000 or more']
fmap={v:i+1 for i,v in enumerate(finc)}; fam=df['faminc_new'].map(fmap); lowinc=(fam<=5).astype(float); lowinc[fam.isna()]=np.nan
urb=df['urbancity']; city=(urb=='City').astype(float); rural=(urb=='Rural area').astype(float)
for s in (city,rural): s[~urb.isin(['City','Suburb','Town','Rural area','Other'])]=np.nan
born=df['pew_bornagain']; bornagain=(born=='Yes').astype(float); bornagain[~born.isin(['Yes','No'])]=np.nan
pid=df['pid3']; dem=(pid=='Democrat').astype(float); rep=(pid=='Republican').astype(float); ind=(pid=='Independent').astype(float)
for s in (dem,rep,ind): s[~pid.isin(['Democrat','Republican','Independent','Other','Not sure'])]=np.nan
ideo=df['ideo5'].map({'Very liberal':1,'Liberal':2,'Moderate':3,'Conservative':4,'Very conservative':5})
DEMOF={'age':age.values,'female':female.values,'college':college.values,'white':white.values,'black':black.values,'hisp':hisp.values,'lowinc':lowinc.values,'city':city.values,'rural':rural.values,'bornagain':bornagain.values,'dem':dem.values,'rep':rep.values,'ind':ind.values,'ideo':ideo.values}
FACS=['FS_F1','FS_F2','FS_F3','FS_F4_resid','FS_F5_resid']; FACN=['enforce','elecSkep','govDist','relig','values']
FS=fs[FACS].values; fpe=lab['fp_engage'].values

def wmean(v,m):
    vv=v[m]; ww=w[m]; ok=~np.isnan(vv)
    return float((ww[ok]*vv[ok]).sum()/ww[ok].sum()) if ok.any() else None
def rec_for(m, conf):
    return {'wtPct':round(w[m].sum()/w.sum()*100,1),
            'conf':round(wmean(conf,m),2),
            'factors':{**{FACN[j]:round(wmean(FS[:,j],m),2) for j in range(5)}, 'FPengage':round(wmean(fpe,m),2)},
            'pol':{k:polpct(k,t,m) for k,_,t in POL},
            'demo':{d:(round(wmean(DEMOF[d],m)*(1 if d in('age','ideo') else 100),1)) for d in DEMOF}}
ORDER=['PRG','DSA','LIB','SD','STY','CUP','POP','CON','NAT','C7']
prod=lab['prod_party'].values; six=lab['sixdim'].values; conf5=lab['conf5'].values; conf6=lab['conf6'].values

baseline=[]
for p in ORDER:
    m=prod==p
    if not m.any(): continue
    r=rec_for(m,conf5); r['party']=p; baseline.append(r)

variant=[]
for cl in sorted(np.unique(six)):
    m=six==cl; r=rec_for(m,conf6); r['id']=int(cl)
    comp={}
    for p in ORDER:
        v=round(w[m&(prod==p)].sum()/w[m].sum()*100,0)
        if v>=8: comp[p]=v
    r['composition']=dict(sorted(comp.items(),key=lambda kv:-kv[1]))
    variant.append(r)

# survival
survival={}
for p in ORDER:
    mp=prod==p; tot=w[mp].sum()
    if tot==0: continue
    dist={int(k):w[mp&(six==k)].sum()/tot for k in np.unique(six)}
    bc=max(dist,key=dist.get); pur=dist[bc]
    clushare=w[mp&(six==bc)].sum()/w[six==bc].sum()
    survival[p]='preserved' if (pur>=0.6 and clushare>=0.5) else ('split' if pur<0.6 else 'absorbed')

OUT={'meta':{'N':int(len(lab)),
     'conf5':round(float(np.average(conf5,weights=w)),3),'conf6':round(float(np.average(conf6,weights=w)),3),
     'eff6':int(len(np.unique(six)))},
     'pol_items':[{'key':k,'label':l} for k,l,t in POL],
     'demo_keys':list(DEMOF.keys()),'factor_names':FACN+['FPengage'],
     'baseline':baseline,'sixdim':variant,'survival':survival}
json.dump(OUT, open(ROOT/'analysis/efa/sixdim_data.json','w'), indent=1)
print("wrote analysis/efa/sixdim_data.json — baseline",len(baseline),"sixdim clusters",len(variant))
print("survival:",survival)
