#!/usr/bin/env python3
"""Validated turnout by 2024 party, per CES wave — presidential vs midterm composition.

Provenance: this is the computation from session 60b42fb9 (2026-07-22/23), recovered from that
session's transcript. It produced viz/src/data/partyPopulation.json's turnoutPresidential /
turnoutMidterm, which drive the Single Race cycle model — but it was never committed, so the file
was unreproducible and prepare_data.py clobbered it. Committing it closes that hole.

Method (unchanged, and the imposed 2024 Gaussian is an INTENTIONAL design choice — do not
relitigate): train a supervised GaussianMixture on the 2024 canonical cluster labels over the
largest shared item set (2022's 21 items, minus imm_dacawall / imm_border25b), then impose it on
each prior wave. 2024 itself uses its canonical labels, restricted to the shared-item sample.

ONE correction from the original: the 2024 turnout spec. The original used
`voted = pd.to_numeric(TS_g2024).notna()`, which counts code 7 — matched-but-did-NOT-vote — as a
voter. Codes 1-6 are a validated vote; 7 and missing are not. 2022's spec was already right
(`notna & != 'did not vote'`), so turnoutMidterm was correct and only 2024 moved:

    party   was   now   canonical pipeline
    CON    66.8  63.4   63.2
    LBR    60.1  55.7   54.8
    STY    38.0  33.3   32.5
    LIB    78.4  75.4   75.4
    PRG    83.3  81.3   81.4
    overall 63.1  59.5   59.1

The corrected figures agree with the canonical pipeline within 0.2pp on every party, from a
different sample — that agreement is the gate. 2020 (60.5%) and 2022 (55.7%) reproduce the
original exactly, confirming the method is faithfully preserved.

Writes outputs/turnout_by_wave.csv, which prepare_data.py reads.
"""
import pandas as pd, numpy as np, sys, warnings
warnings.filterwarnings('ignore')
from sklearn.mixture import GaussianMixture
sys.path.insert(0, 'analysis/efa/previous_years')
from common import io_paths as io, crosswalk as cwmod
from independent.wave_items import get_items, recode_items

PID3_LABEL = {'Democrat': 1, 'Republican': 2, 'Independent': 3, 'Other': 4, 'Not sure': 5}
CODES = ['CON','LBR','STY','NAT','LIB','POP','CUP','OAO','DSA','PRG']
NAMES = {'CON':'Conservative','LBR':'Labor','STY':'Solidarity','NAT':'Nationalist',
         'LIB':'Liberal','POP':'Populist','CUP':'Civic Union','OAO':'Order & Opp.',
         'DSA':'Dem. Socialist','PRG':'Progressive'}
CANONICAL_24 = [
    'pew_churatd','CC24_302','CC24_303','CC24_341a','CC24_341c','CC24_341d',
    'CC24_323a','CC24_323b','CC24_323d','CC24_321b','CC24_321d','CC24_321e',
    'CC24_325','CC24_324b','CC24_340b','CC24_340c','CC24_340e','CC24_340f',
    'CC24_440b','CC24_440c','CC24_421_1','CC24_421_2','CC24_423','CC24_424',
]
TURNOUT = {'2018': 'CL_2018gvm', '2020': 'CL_2020gvm', '2022': 'TS_g2022', '2024': 'TS_g2024'}
WAVE_TYPE = {'2018': 'midterm', '2020': 'presidential', '2022': 'midterm', '2024': 'presidential'}
cw = cwmod.load()

# Use the largest shared set (2022's 21 items) for the Gaussian model
items_cfg = get_items('2022')
shared_cfg, shared_cids = [], []
for it in items_cfg:
    cid = it['construct_id']
    if cid in ('imm_dacawall','imm_border25b'): continue
    row = cw[cw['construct_id'] == cid]
    if len(row) == 0: continue
    r = row.iloc[0]
    if r.get('cov_2022') in ('exact','equivalent') and pd.notna(r.get('var_2024')) and r.get('var_2024') != '':
        shared_cfg.append(it); shared_cids.append(cid)

# Build 2024 supervised Gaussian on shared items
tp = pd.read_csv(io.ROOT / 'data/processed/typology_cluster_assignments.csv')
cw24_sub = cw[cw['construct_id'].isin(shared_cids) & cw['var_2024'].notna()]
vars24 = list(set(cw24_sub['var_2024']))
all_vars = list(set(CANONICAL_24 + vars24 + ['commonpostweight','pid3', TURNOUT['2024'], 'newsint']))
all_cols = pd.read_stata(str(io.dta_path('2024')), iterator=True).variable_labels()
all_vars = [v for v in all_vars if v in all_cols]
df24 = pd.read_stata(str(io.dta_path('2024')), columns=all_vars,
                     convert_categoricals=True, convert_missing=False, convert_dates=False)
w24 = pd.to_numeric(df24['commonpostweight'], errors='coerce').values.astype(float)
canon_mask = ~np.isnan(w24)
for var in CANONICAL_24:
    if var not in df24.columns: continue
    col = df24[var]
    if col.dtype.name == 'category': canon_mask &= col.notna().values
    else: canon_mask &= pd.to_numeric(col, errors='coerce').notna().values
cluster24 = np.full(len(df24), -1, dtype=int)
cluster24[canon_mask] = tp['cluster'].values
items24 = cwmod.recode_wave(df24, '2024', levels={'exact','equivalent'}, cw=cw24_sub)
mask24 = canon_mask.copy()
for cid in shared_cids:
    if cid in items24.columns: mask24 &= items24[cid].notna().values
X24 = items24.loc[mask24, shared_cids].values
w24m = w24[mask24]; y24 = cluster24[mask24]

mu24 = np.average(X24, axis=0, weights=w24m)
std24 = np.sqrt(np.average((X24 - mu24)**2, axis=0, weights=w24m))
std24[std24 < 0.01] = 1.0
Z24 = (X24 - mu24) / std24

gm = GaussianMixture(n_components=10, covariance_type='full', max_iter=1, n_init=1, random_state=42)
gm.fit(Z24)
for pk in range(10):
    mk = y24 == pk; wk = w24m[mk]; wn = wk / wk.sum()
    gm.means_[pk] = (wn[:, None] * Z24[mk]).sum(0)
    diff = Z24[mk] - gm.means_[pk]
    gm.covariances_[pk] = (wn[:, None, None] * (diff[:, :, None] * diff[:, None, :])).sum(0) + np.eye(len(shared_cids)) * 0.01
    gm.weights_[pk] = wk.sum() / w24m.sum()
gm.precisions_cholesky_ = np.array([np.linalg.cholesky(np.linalg.inv(c)) for c in gm.covariances_])

# 2024 canonical turnout first
tv24 = df24.loc[mask24, TURNOUT['2024']]
# 2024 TS_g2024: numeric codes = voted, NaN = unmatched/didn't vote
_v24 = pd.to_numeric(tv24, errors='coerce')
# CORRECTED: TS_g2024 codes 1-6 are a validated vote; 7 is matched-but-did-not-vote and
# missing is unmatched. The original counted both as voters (`notna`), inflating 2024.
voted_24 = ((_v24 >= 1) & (_v24 <= 6)).values

RESULT = {}
print('TURNOUT BY PARTY ACROSS WAVES (imposed 2024 Gaussian, corrected 2024 spec)')
print('='*100)
print()
print('Turnout = validated voter file match (Catalist 2018/2020, TargetSmart 2022/2024).')
print('NaN = not matched to voter file or did not vote. "did not vote" explicit in 2022.')
print()

# 2024 canonical turnout
print('2024 (canonical, presidential):')
print(f'  {"party":>5} {"name":>14} {"share":>6} {"turnout":>7} {"newsint":>8}')
for pk in range(10):
    mk = y24 == pk; wk = w24m[mk]
    to = 100 * wk[voted_24[mk]].sum() / wk.sum()
    # newsint
    ni = df24.loc[mask24, 'newsint'].iloc[mk] if 'newsint' in df24.columns else None
    ni_str = ''
    if ni is not None:
        ni_obj = ni.astype('object')
        most_int = 0
        for val in ni_obj.unique():
            if pd.isna(val): continue
            s = str(val).strip().lower()
            if 'most' in s or 'always' in s or 'follow' in s:
                most_int = 100 * wk[ni_obj.values == val].sum() / wk.sum()
        ni_str = f'{most_int:.0f}%'
    print(f'  {CODES[pk]:>5} {NAMES[CODES[pk]]:>14} {gm.weights_[pk]*100:>5.1f}% {to:>6.1f}% {ni_str:>8}')
    RESULT.setdefault('2024', {})[CODES[pk]] = round(float(to), 1)
print(f'  overall: {100*w24m[voted_24].sum()/w24m.sum():.1f}%')

# Now for each prior wave
for wave in ['2022', '2020', '2018']:
    # Get shared items for THIS wave
    wave_cfg = get_items(wave)
    w_shared_cfg, w_shared_cids = [], []
    for it in wave_cfg:
        cid = it['construct_id']
        if cid in ('imm_dacawall','imm_border25b'): continue
        row = cw[cw['construct_id'] == cid]
        if len(row) == 0: continue
        r = row.iloc[0]
        if r.get(f'cov_{wave}') in ('exact','equivalent') and pd.notna(r.get('var_2024')) and r.get('var_2024') != '':
            w_shared_cfg.append(it); w_shared_cids.append(cid)
    
    variables = [it['variable'] for it in w_shared_cfg]
    tv = TURNOUT[wave]
    all_cols_w = pd.read_stata(str(io.dta_path(wave)), iterator=True).variable_labels()
    need = [v for v in variables + [io.WEIGHT_COL, 'pid3', tv, 'newsint'] if v in all_cols_w]
    df = pd.read_stata(str(io.dta_path(wave)), columns=need,
                      convert_categoricals=True, convert_missing=False, convert_dates=False)
    D = recode_items(df, w_shared_cfg)
    w = pd.to_numeric(df[io.WEIGHT_COL], errors='coerce').values.astype(float)
    pid3 = pd.to_numeric(df['pid3'].astype('object').map(PID3_LABEL), errors='coerce').values.astype(float)
    mask = D[w_shared_cids].notna().all(axis=1) & ~np.isnan(w)
    X = D.loc[mask, w_shared_cids].values
    wm = w[mask.values]; pm = pid3[mask.values]
    
    # Turnout coding
    tv_col = df.loc[mask.values, tv] if tv in df.columns else None
    if tv_col is not None:
        if wave in ('2018', '2020'):
            # Catalist: any non-NaN = voted
            voted = tv_col.notna().values
        elif wave == '2022':
            # TargetSmart: non-NaN AND not 'did not vote' = voted
            tv_obj = tv_col.astype('object')
            voted = tv_col.notna().values & (tv_obj.values != 'did not vote')
        else:
            voted = pd.to_numeric(tv_col, errors='coerce').notna().values
    else:
        voted = np.zeros(len(X), dtype=bool)
    
    # Newsint
    ni_col = df.loc[mask.values, 'newsint'].astype('object') if 'newsint' in df.columns else None
    
    # Impose 2024 Gaussian — need to align items to the 2024 shared set
    # Map this wave's items to the 2024 training items
    # Some items may not exist in this wave (e.g., trust items in 2018)
    X_for_gm = np.full((len(X), len(shared_cids)), np.nan)
    for i, cid in enumerate(shared_cids):
        if cid in w_shared_cids:
            j = w_shared_cids.index(cid)
            X_for_gm[:, i] = X[:, j]
        else:
            # missing item — fill with 2024 mean (neutral)
            X_for_gm[:, i] = mu24[i]
    
    Z = (X_for_gm - mu24) / std24
    imposed = gm.predict(Z)
    
    print(f'\n{wave} ({WAVE_TYPE[wave]}):')
    print(f'  {"party":>5} {"name":>14} {"share":>6} {"turnout":>7} {"newsint":>8}  D/R')
    for pk in range(10):
        mk = imposed == pk; wk = wm[mk]
        if wk.sum() == 0: continue
        sh = 100 * wk.sum() / wm.sum()
        to = 100 * wk[voted[mk]].sum() / wk.sum()
        dem = 100 * wk[pm[mk]==1].sum() / wk.sum()
        rep = 100 * wk[pm[mk]==2].sum() / wk.sum()
        
        ni_str = ''
        if ni_col is not None:
            ni_sub = ni_col.iloc[np.where(mk)[0]]
            most_int = 0
            for val in ni_sub.unique():
                if pd.isna(val): continue
                s = str(val).strip().lower()
                if 'most' in s or 'always' in s:
                    most_int = 100 * wk[ni_sub.values == val].sum() / wk.sum()
            ni_str = f'{most_int:.0f}%'
        
        print(f'  {CODES[pk]:>5} {NAMES[CODES[pk]]:>14} {sh:>5.1f}% {to:>6.1f}% {ni_str:>8}  {dem:.0f}/{rep:.0f}')
        RESULT.setdefault(wave, {})[CODES[pk]] = round(float(to), 1)
    print(f'  overall: {100*wm[voted].sum()/wm.sum():.1f}%')

# Summary: presidential vs midterm drop per party
print(f'\n\n{"="*100}')
print(f'PRESIDENTIAL → MIDTERM TURNOUT DROP BY PARTY')
print(f'{"="*100}')
print(f'\n  {"party":>5} {"name":>14} {"2024(P)":>7} {"2022(M)":>7} {"drop":>5} | {"2020(P)":>7} {"2018(M)":>7} {"drop":>5} | {"avg_drop":>8}')


# ── Emit the CSV prepare_data.py reads ───────────────────────────────────────────────────────
import csv as _csv
_out = io.compare_dir() / "turnout_by_wave.csv"
_pres, _mid = RESULT.get("2024", {}), RESULT.get("2022", {})
with open(_out, "w", newline="", encoding="utf-8") as _f:
    _wr = _csv.writer(_f)
    _wr.writerow(["party", "turnoutPresidential", "turnoutMidterm"])
    for _p in CODES:
        if _p in _pres and _p in _mid:
            _wr.writerow([_p, _pres[_p], _mid[_p]])
print(f"\nSaved {_out}")
