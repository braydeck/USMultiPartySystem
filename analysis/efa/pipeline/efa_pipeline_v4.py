#!/usr/bin/env python3
"""
EFA PIPELINE v4 — Final Item Set
==================================
25 items (+ CC24_421_2 = 26 total).
Tasks:
  1. Recode final item set
  2. Compute weighted listwise N
  3. Compute weighted polychoric correlation matrix (26×26 = 325 pairs)
  4. Save efa_variable_list.csv, polychoric_matrix.csv, efa_checkpoint_summary.txt
"""

import warnings; warnings.filterwarnings('ignore')
import os, sys, subprocess, time
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from scipy.stats import norm
from scipy.stats import multivariate_normal as mvn
from scipy.cluster.hierarchy import linkage, leaves_list
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

OUTPUT_DIR = '/Users/bdecker/Documents/STV/Claude'
DATA_PATH  = '/Users/bdecker/Documents/STV/2024 CES Base/CCES24_Common_OUTPUT_vv_topost_final.dta'
os.makedirs(OUTPUT_DIR, exist_ok=True)

DIVIDER = '=' * 72

# =============================================================================
# LOAD
# =============================================================================
print(f'\n{DIVIDER}\nLOADING DATA\n{DIVIDER}')
df = pd.read_stata(DATA_PATH, convert_categoricals=True,
                   convert_missing=False, convert_dates=False)
print(f'  Loaded: {df.shape[0]:,} rows × {df.shape[1]:,} columns')

# Use commonpostweight: calibrated for post-survey subsample.
# All items requiring listwise completion include post-survey items
# (440b/c, 421_1/2, 423, 424), so the effective sample is post-survey
# completers; commonpostweight makes that sample nationally representative.
w_post = df['commonpostweight'].values.astype(float)
w_pre  = df['commonweight'].values.astype(float)

# =============================================================================
# RECODE — 26 final items
# =============================================================================
def cat_to_num(series, label_map):
    return series.map(label_map).astype(float)

recode = {}

# RELIGION (pre-survey)
recode['pew_churatd'] = cat_to_num(df['pew_churatd'], {
    'Never': 1, 'Seldom': 2, 'A few times a year': 3,
    'Once or twice a month': 4, 'Once a week': 5,
    'More than once a week': 6, "Don't know": np.nan
})

# ECONOMIC PERCEPTIONS (pre-survey; higher = worse/more inflation)
recode['CC24_302'] = cat_to_num(df['CC24_302'], {
    'Increased a lot': 1, 'Increased somewhat': 2,
    'Stayed about the same': 3, 'Decreased somewhat': 4, 'Decreased a lot': 5
})
recode['CC24_303'] = cat_to_num(df['CC24_303'], {
    'Decreased a lot': 1, 'Decreased somewhat': 2, 'Stayed about the same': 3,
    'Increased somewhat': 4, 'Increased a lot': 5
})

# TAX/FISCAL POLICY (pre-survey; higher = more conservative/anti-spending)
recode['CC24_341a'] = cat_to_num(df['CC24_341a'], {'Support': 1, 'Oppose': 0})
recode['CC24_341c'] = cat_to_num(df['CC24_341c'], {'Support': 0, 'Oppose': 1})
recode['CC24_341d'] = cat_to_num(df['CC24_341d'], {'Support': 0, 'Oppose': 1})

# IMMIGRATION (pre-survey; higher = more restrictive)
recode['CC24_323a'] = cat_to_num(df['CC24_323a'], {'Support': 0, 'Oppose': 1})
recode['CC24_323b'] = cat_to_num(df['CC24_323b'], {'Support': 1, 'Oppose': 0})
recode['CC24_323d'] = cat_to_num(df['CC24_323d'], {'Support': 0, 'Oppose': 1})

# GUNS/POLICING (pre-survey; higher = more pro-gun/pro-police)
recode['CC24_321b'] = cat_to_num(df['CC24_321b'], {'Support': 1, 'Oppose': 0})
recode['CC24_321d'] = cat_to_num(df['CC24_321d'], {'Support': 1, 'Oppose': 0})
recode['CC24_321e'] = cat_to_num(df['CC24_321e'], {'Support': 0, 'Oppose': 1})

# ABORTION (pre-survey; higher = more restrictive)
cc325 = pd.to_numeric(df['CC24_325'].astype(str), errors='coerce')
recode['CC24_325']  = 40.0 - cc325   # 0=no limit→40; 40=never→0; reversed
recode['CC24_324b'] = cat_to_num(df['CC24_324b'], {'Support': 1, 'Oppose': 0})

# CIVIL RIGHTS / LIBERTIES (pre-survey; higher = more conservative)
recode['CC24_340a'] = cat_to_num(df['CC24_340a'], {'Support': 0, 'Oppose': 1})
recode['CC24_340b'] = cat_to_num(df['CC24_340b'], {'Support': 0, 'Oppose': 1})
recode['CC24_340c'] = cat_to_num(df['CC24_340c'], {'Support': 0, 'Oppose': 1})
recode['CC24_340e'] = cat_to_num(df['CC24_340e'], {'Support': 1, 'Oppose': 0})
recode['CC24_340f'] = cat_to_num(df['CC24_340f'], {'Support': 1, 'Oppose': 0})

# RACIAL / GENDER ATTITUDES (post-survey; higher = more conservative)
# 440b: "Racial problems are rare/isolated" — Agree = conservative
# 440c: "Women seek to gain power over men" — Agree = conservative
_con_agree = {'Strongly agree': 5, 'Somewhat agree': 4,
              'Neither agree nor disagree': 3,
              'Somewhat disagree': 2, 'Strongly disagree': 1}
recode['CC24_440b'] = cat_to_num(df['CC24_440b'], _con_agree)
recode['CC24_440c'] = cat_to_num(df['CC24_440c'], _con_agree)

# ELECTION TRUST (post-survey; higher = more distrustful)
# 421_1: "Elections in the U.S. are fair"
# 421_2: "Your state/local gov conducted a fair and accurate election in 2024"
# Agree = trust = coded 1; Disagree = distrust = coded 5
_elec = {'Strongly agree': 1, 'Somewhat agree': 2,
         'Neither agree nor disagree': 3,
         'Somewhat disagree': 4, 'Strongly disagree': 5}
recode['CC24_421_1'] = cat_to_num(df['CC24_421_1'], _elec)
recode['CC24_421_2'] = cat_to_num(df['CC24_421_2'], _elec)

# GOVERNMENT TRUST (post-survey; higher = less trust)
# 423: "How much trust in the federal government handling the nation's problems?"
# 424: "How much trust in your state government handling the state's problems?"
_govt = {'A great deal': 1, 'A fair amount': 2, 'Not very much': 3, 'None at all': 4}
recode['CC24_423'] = cat_to_num(df['CC24_423'], _govt)
recode['CC24_424'] = cat_to_num(df['CC24_424'], _govt)

# DIAGNOSTIC VARS
recode['pid7'] = cat_to_num(df['pid7'], {
    'Strong Democrat': 1, 'Not very strong Democrat': 2, 'Lean Democrat': 3,
    'Independent': 4, 'Lean Republican': 5, 'Not very strong Republican': 6,
    'Strong Republican': 7, 'Not sure': np.nan
})
recode['ideo5'] = cat_to_num(df['ideo5'], {
    'Very liberal': 1, 'Liberal': 2, 'Moderate': 3,
    'Conservative': 4, 'Very conservative': 5, 'Not sure': np.nan
})

data = pd.DataFrame(recode)
data['commonpostweight'] = w_post
data['commonweight']     = w_pre

EFA_VARS = [
    'pew_churatd',
    'CC24_302', 'CC24_303',
    'CC24_341a', 'CC24_341c', 'CC24_341d',
    'CC24_323a', 'CC24_323b', 'CC24_323d',
    'CC24_321b', 'CC24_321d', 'CC24_321e',
    'CC24_325',  'CC24_324b',
    'CC24_340a', 'CC24_340b', 'CC24_340c', 'CC24_340e', 'CC24_340f',
    'CC24_440b', 'CC24_440c',
    'CC24_421_1', 'CC24_421_2',
    'CC24_423',  'CC24_424',
]
N_VARS = len(EFA_VARS)
print(f'\n  EFA items: {N_VARS}')
print(f'  {EFA_VARS}')

# =============================================================================
# LISTWISE N
# =============================================================================
N_TOTAL = len(data)
complete = data[EFA_VARS].notna().all(axis=1)
N_eff    = complete.sum()
W_eff    = data.loc[complete, 'commonpostweight'].sum()
print(f'\n  Listwise N = {N_eff:,} ({100*N_eff/N_TOTAL:.1f}%)')
print(f'  Weighted N = {W_eff:,.0f}')

# Restrict to listwise sample for diagnostics
d = data[complete].copy().reset_index(drop=True)
w = d['commonpostweight'].values

# =============================================================================
# ITEM DIAGNOSTICS — weighted partyID R² and ideology R²
# =============================================================================
print(f'\n{DIVIDER}\nITEM DIAGNOSTICS\n{DIVIDER}')

from statsmodels.tools import add_constant
from statsmodels.regression.linear_model import WLS

def weighted_r2(y, x, wts):
    mask = ~(np.isnan(y) | np.isnan(x))
    if mask.sum() < 10:
        return np.nan
    y_, x_, w_ = y[mask], x[mask], wts[mask]
    w_ = w_ / w_.mean()
    X = add_constant(x_)
    try:
        m = WLS(y_, X, weights=w_).fit()
        return m.rsquared
    except:
        return np.nan

pid  = d['pid7'].values
ideo = d['ideo5'].values

diag_rows = []
print(f'  {"Variable":<18} {"N_valid":>8} {"% miss":>7} {"PID R²":>8} {"IDEO R²":>8}')
for v in EFA_VARS:
    s = data[v]
    n_miss = s.isna().sum()
    pct_miss = 100 * n_miss / N_TOTAL
    r2_pid  = weighted_r2(d[v].values, pid,  w)
    r2_ideo = weighted_r2(d[v].values, ideo, w)
    print(f'  {v:<18} {N_TOTAL-n_miss:>8,} {pct_miss:>6.1f}%  {r2_pid:>8.4f}  {r2_ideo:>8.4f}')
    diag_rows.append({
        'variable': v,
        'n_valid': N_TOTAL - n_miss,
        'pct_missing': round(pct_miss, 2),
        'partyID_r2': round(r2_pid, 4),
        'ideology_r2': round(r2_ideo, 4),
    })
diag_df = pd.DataFrame(diag_rows).set_index('variable')

# =============================================================================
# WEIGHTED POLYCHORIC CORRELATION MATRIX
# =============================================================================
print(f'\n{DIVIDER}\nWEIGHTED POLYCHORIC MATRIX ({N_VARS}×{N_VARS} = {N_VARS*(N_VARS-1)//2} pairs)\n{DIVIDER}')
BIG = 6.5

def weighted_polychoric(x, y, wts):
    mask = ~(np.isnan(x) | np.isnan(y))
    x_, y_, w_ = x[mask], y[mask], wts[mask]
    if len(x_) < 30:
        return np.nan
    x_cats = np.sort(np.unique(x_))
    y_cats = np.sort(np.unique(y_))
    nx, ny = len(x_cats), len(y_cats)
    if nx < 2 or ny < 2:
        return np.nan
    xi = np.searchsorted(x_cats, x_)
    yi = np.searchsorted(y_cats, y_)
    w_ = w_ / w_.sum()
    ct = np.zeros((nx, ny))
    for ii, jj, ww in zip(xi, yi, w_):
        ct[ii, jj] += ww
    x_marg = ct.sum(axis=1)
    y_marg = ct.sum(axis=0)
    tau_x = np.concatenate([
        [-BIG],
        norm.ppf(np.clip(np.cumsum(x_marg)[:-1], 1e-7, 1-1e-7)),
        [BIG]
    ])
    tau_y = np.concatenate([
        [-BIG],
        norm.ppf(np.clip(np.cumsum(y_marg)[:-1], 1e-7, 1-1e-7)),
        [BIG]
    ])
    def neg_log_lik(rho):
        cov = [[1.0, rho], [rho, 1.0]]
        H, K = np.meshgrid(tau_x, tau_y, indexing='ij')
        pts  = np.column_stack([H.ravel(), K.ravel()])
        cdf  = mvn(mean=[0,0], cov=cov).cdf(pts).reshape(nx+1, ny+1)
        P    = np.diff(np.diff(cdf, axis=0), axis=1)
        P    = np.maximum(P, 1e-12)
        return -np.sum(ct * np.log(P))
    res = minimize_scalar(neg_log_lik, bounds=(-0.9999, 0.9999),
                          method='bounded', options={'xatol': 1e-5})
    return float(res.x)

# Build matrix
poly_mat = np.eye(N_VARS)
pairs = [(i, j) for i in range(N_VARS) for j in range(i+1, N_VARS)]
n_pairs = len(pairs)
t0 = time.time()

for k, (i, j) in enumerate(pairs):
    r = weighted_polychoric(d[EFA_VARS[i]].values,
                            d[EFA_VARS[j]].values, w)
    poly_mat[i, j] = poly_mat[j, i] = r
    if (k+1) % 25 == 0:
        elapsed = time.time() - t0
        eta = elapsed / (k+1) * (n_pairs - k - 1)
        print(f'  {k+1}/{n_pairs} pairs  ({elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)')

print(f'  Done in {time.time()-t0:.1f}s')

poly_df = pd.DataFrame(poly_mat, index=EFA_VARS, columns=EFA_VARS)

# Redundant pairs |r| > 0.70
print(f'\n  PAIRS WITH |r| > 0.70:')
red_rows = []
for i in range(N_VARS):
    for j in range(i+1, N_VARS):
        r = poly_mat[i, j]
        if abs(r) > 0.70:
            va, vb = EFA_VARS[i], EFA_VARS[j]
            print(f'    {va} × {vb}  r={r:+.4f}')
            red_rows.append({'var_a': va, 'var_b': vb, 'r': round(r, 4)})

# Top 10 by |r|
off_diag = [(abs(poly_mat[i,j]), poly_mat[i,j], EFA_VARS[i], EFA_VARS[j])
            for i in range(N_VARS) for j in range(i+1, N_VARS)]
off_diag.sort(reverse=True)
print(f'\n  TOP 10 POLYCHORIC CORRELATIONS:')
for _, r, va, vb in off_diag[:10]:
    print(f'    {va:18s} × {vb:18s}  r={r:+.4f}')

# =============================================================================
# HEATMAP
# =============================================================================
dist = 1 - np.abs(poly_mat)
np.fill_diagonal(dist, 0)
dist = np.clip(dist, 0, None)
lnk  = linkage(dist[np.tril_indices(N_VARS, k=-1)], method='ward')
order = leaves_list(lnk)

sorted_vars = [EFA_VARS[i] for i in order]
sorted_mat  = poly_mat[np.ix_(order, order)]

fig, ax = plt.subplots(figsize=(14, 12))
cmap = sns.diverging_palette(240, 10, as_cmap=True)
im = ax.imshow(sorted_mat, cmap=cmap, vmin=-1, vmax=1, aspect='auto')
ax.set_xticks(range(N_VARS)); ax.set_xticklabels(sorted_vars, rotation=90, fontsize=8)
ax.set_yticks(range(N_VARS)); ax.set_yticklabels(sorted_vars, fontsize=8)
plt.colorbar(im, ax=ax, label='Polychoric r')
ax.set_title('Weighted Polychoric Correlation Matrix — EFA v4 (25 items)\n'
             f'Hierarchical clustering (Ward), N={N_eff:,}', fontsize=11)
plt.tight_layout()
heatmap_path = os.path.join(OUTPUT_DIR, 'polychoric_heatmap_v4.png')
fig.savefig(heatmap_path, dpi=150)
plt.close()
print(f'\n  Heatmap saved: {heatmap_path}')

# =============================================================================
# SAVE polychoric_matrix.csv
# =============================================================================
poly_path = os.path.join(OUTPUT_DIR, 'polychoric_matrix.csv')
poly_df.round(4).to_csv(poly_path)
print(f'  Polychoric matrix saved: {poly_path}')

# =============================================================================
# BUILD efa_variable_list.csv
# =============================================================================
# Master labels for all 55 original items
ALL_LABELS = {
    'CC24_330a': 'Ideology self-placement (VL=1 to VC=7)',
    'pew_churatd': 'Church attendance frequency',
    'pew_religimp': 'Importance of religion in life',
    'pew_prayer': 'Prayer frequency',
    'pew_bornagain': 'Born-again/evangelical identity (binary)',
    'CC24_301': 'National economy: better or worse past year',
    'CC24_302': 'Household income: change past year',
    'CC24_303': 'Perceived price change past year (rev: high=inflation)',
    'CC24_309d_8': 'Financial fragility: can\'t cover $400 emergency [binary]',
    'CC24_341a': 'Support extend 2017 tax cuts',
    'CC24_341b': 'Oppose raise corporate tax to 28% [rev]',
    'CC24_341c': 'Oppose allow $400k+ tax rates to rise [rev]',
    'CC24_341d': 'Oppose $150B infrastructure spending [rev]',
    'CC24_323a': 'Oppose grant legal status to working immigrants [rev]',
    'CC24_323b': 'Support increase border patrols',
    'CC24_323d': 'Oppose Dreamers pathway to citizenship [rev]',
    'CC24_321b': 'Support easier concealed carry permits',
    'CC24_321c': 'Oppose background checks on all gun sales [rev; ceiling]',
    'CC24_321d': 'Support increase police by 10%',
    'CC24_321e': 'Oppose decrease police by 10% [rev]',
    'CC24_325':  'Abortion weeks limit reversed (40-weeks; high=restrictive)',
    'CC24_324b': 'Support permit abortion only rape/incest/life danger',
    'CC24_324c': 'Support make abortion illegal ALL circumstances [floor]',
    'CC24_324d': 'Oppose expand abortion access [rev]',
    'CC24_340a': 'Oppose prohibit contraceptive restrictions [rev]',
    'CC24_340b': 'Oppose prohibit abortion service restrictions [rev]',
    'CC24_340c': 'Oppose require same-sex marriage recognition [rev]',
    'CC24_340e': 'Support renew post-9/11 surveillance programs',
    'CC24_340f': 'Support deny asylum at border',
    'CC24_440a': 'Disagree: white people have advantages [high=conservative]',
    'CC24_440b': 'Agree: racial problems are rare/isolated',
    'CC24_440c': 'Agree: women seek to gain power over men',
    'CC24_440d': 'Agree: women are too easily offended',
    'CC24_441a': 'Agree: Blacks should work up like other minorities',
    'CC24_441b': 'Disagree: slavery created conditions [high=conservative]',
    'CC24_420_1': 'Mil. intervention: ensure oil supply [binary]',
    'CC24_420_2': 'Mil. intervention: destroy terrorist camp [binary]',
    'CC24_420_3': 'Mil. intervention: genocide/civil war [binary]',
    'CC24_420_4': 'Mil. intervention: spread democracy [binary]',
    'CC24_420_5': 'Mil. intervention: protect allies [binary]',
    'CC24_420_6': 'Mil. intervention: UN/intl law [binary]',
    'CC24_420_7': 'Mil. intervention: NONE/isolationist [exclusive-none]',
    'CC24_421_1': 'Disagree: U.S. elections are fair [high=distrust]',
    'CC24_421_2': 'Disagree: state/local election in 2024 was fair [high=distrust]',
    'CC24_423':   'Low trust: federal government [4-pt; high=less trust]',
    'CC24_424':   'Low trust: state government [4-pt; high=less trust]',
    'CC24_312a': 'Approve Biden [partisan proxy]',
    'CC24_312b': 'Approve U.S. Congress [11.9% Not sure]',
    'CC24_312c': 'Approve U.S. Supreme Court',
    'CC24_312d': 'Approve Governor [direction varies by state]',
    'CC24_312e': 'Approve State legislature [direction varies by state]',
    'CC24_312f': 'Approve House rep [direction varies; 30% Not sure]',
    'CC24_312g': 'Approve Senator 1 [direction varies; 22% Not sure]',
    'CC24_312h': 'Approve Senator 2 [direction varies; 25% Not sure]',
    'CC24_312i': 'Approve Harris [partisan proxy]',
}

DROP_REASONS = {
    'CC24_330a':  'Partisan proxy: ideology self-placement (PID R²=0.568); dominates Factor 1',
    'pew_religimp': 'Redundant with pew_churatd (r=0.82); higher PID R²',
    'pew_prayer': 'Dropped by user: reduces N by ~1,520; redundant with pew_churatd',
    'pew_bornagain': 'Redundant with pew_religimp (r=0.77); binary with 67% modal share',
    'CC24_301':   'Partisan proxy: economy retrospective (PID R²=0.338); Biden approval proxy in 2024',
    'CC24_309d_8': 'Dropped by user: binary from multi-select; low variance (82.5% = 0); CC24_309e preferred',
    'CC24_341b':  'Redundant with CC24_341a (r>0.70); dropped by user',
    'CC24_321c':  'Ceiling effect: 93% Support background checks; near-zero variance',
    'CC24_324c':  'Floor effect: 89% Oppose making abortion illegal in all circumstances',
    'CC24_324d':  'Dropped by user: highly redundant with immigration/ideology cluster (r>0.79 with 6 items)',
    'CC24_440a':  'Dropped by user: redundant with CC24_440b (r=0.71); higher PID R²',
    'CC24_440d':  'Dropped by user: redundant with CC24_440c (r=0.77)',
    'CC24_441a':  'Dropped by user: racial resentment item; collinearity concern vs Factor 1',
    'CC24_441b':  'Dropped by user: racial resentment item; collinearity concern vs Factor 1',
    'CC24_420_1': 'Compositional/check-all-that-apply: mutual exclusivity creates structurally invalid polychoric correlations',
    'CC24_420_2': 'Compositional/check-all-that-apply: mutual exclusivity creates structurally invalid polychoric correlations',
    'CC24_420_3': 'Compositional/check-all-that-apply: mutual exclusivity creates structurally invalid polychoric correlations',
    'CC24_420_4': 'Compositional/check-all-that-apply: mutual exclusivity creates structurally invalid polychoric correlations',
    'CC24_420_5': 'Compositional/check-all-that-apply: mutual exclusivity creates structurally invalid polychoric correlations',
    'CC24_420_6': 'Compositional/check-all-that-apply: mutual exclusivity creates structurally invalid polychoric correlations',
    'CC24_420_7': 'Compositional exclusive-none: near-perfect artificial negative correlations with items 1-6',
    'CC24_312a':  'Partisan proxy: Biden approval (PID R²=0.568); r=0.977 with CC24_312i',
    'CC24_312b':  'Dropped by user: 11.9% missing (4,947 "Not sure" post-completers drag down N)',
    'CC24_312c':  'Dropped by user: SCOTUS approval loaded on partisan axis, not cross-cutting',
    'CC24_312d':  'Direction inconsistent: partisan valence varies by state governor party',
    'CC24_312e':  'Direction inconsistent: partisan valence varies by state legislature; 20.5% missing',
    'CC24_312f':  'Direction inconsistent: direction varies by rep; 29.7% Not sure → NaN',
    'CC24_312g':  'Direction inconsistent: direction varies by senator; 22.4% Not sure → NaN',
    'CC24_312h':  'Direction inconsistent: direction varies by senator; 25.0% Not sure → NaN',
    'CC24_312i':  'Partisan proxy: Harris approval (PID R²=0.630); r=0.977 with CC24_312a',
}

# Read original v2 stats (partyID_r2 etc. computed on full sample)
v2 = pd.read_csv(os.path.join(OUTPUT_DIR, 'efa_variable_list.csv'))
v2_stats = {}
for _, row in v2.iterrows():
    v2_stats[row['variable_name']] = row

# Build final list
ALL_55 = list(ALL_LABELS.keys())
rows = []
for v in ALL_55:
    action = 'KEEP' if v in EFA_VARS else 'DROP'
    reason = '' if action == 'KEEP' else DROP_REASONS.get(v, 'See notes')
    label  = ALL_LABELS[v]
    stats  = v2_stats.get(v, {})
    rows.append({
        'variable_name':     v,
        'question_label':    label,
        'survey_wave':       'post' if v in ('CC24_440a','CC24_440b','CC24_440c','CC24_440d',
                                              'CC24_441a','CC24_441b','CC24_420_1','CC24_420_2',
                                              'CC24_420_3','CC24_420_4','CC24_420_5','CC24_420_6',
                                              'CC24_420_7','CC24_421_1','CC24_421_2','CC24_423',
                                              'CC24_424') else 'pre',
        'n_valid':           stats.get('n_valid', ''),
        'pct_missing':       stats.get('pct_missing', ''),
        'weighted_variance': stats.get('weighted_variance', ''),
        'modal_share_pct':   stats.get('modal_share_pct', ''),
        'partyID_r2':        stats.get('partyID_r2', ''),
        'ideology_r2':       stats.get('ideology_r2', ''),
        'final_action':      action,
        'drop_reason':       reason,
    })

varlist_df = pd.DataFrame(rows)
varlist_path = os.path.join(OUTPUT_DIR, 'efa_variable_list.csv')
varlist_df.to_csv(varlist_path, index=False)
print(f'  Variable list saved: {varlist_path}')

# =============================================================================
# CHECKPOINT SUMMARY
# =============================================================================
keeps = [r for r in rows if r['final_action'] == 'KEEP']
drops = [r for r in rows if r['final_action'] == 'DROP']

# Items by domain
DOMAINS = {
    'Religion':       ['pew_churatd'],
    'Econ Perception':['CC24_302','CC24_303'],
    'Tax/Fiscal':     ['CC24_341a','CC24_341c','CC24_341d'],
    'Immigration':    ['CC24_323a','CC24_323b','CC24_323d'],
    'Guns/Policing':  ['CC24_321b','CC24_321d','CC24_321e'],
    'Abortion':       ['CC24_325','CC24_324b'],
    'Civil Rights':   ['CC24_340a','CC24_340b','CC24_340c','CC24_340e','CC24_340f'],
    'Racial/Gender':  ['CC24_440b','CC24_440c'],
    'Election Trust': ['CC24_421_1','CC24_421_2'],
    'Govt Trust':     ['CC24_423','CC24_424'],
}

# Redundant pairs in final set
red_in_keep = [(r['var_a'], r['var_b'], r['r']) for r in red_rows
               if r['var_a'] in EFA_VARS and r['var_b'] in EFA_VARS]

# Highest and lowest PID R² in final set
diag_keep = diag_df.loc[EFA_VARS].sort_values('partyID_r2', ascending=False)

summary_path = os.path.join(OUTPUT_DIR, 'efa_checkpoint_summary.txt')
with open(summary_path, 'w') as f:
    def w(s=''): f.write(s + '\n')
    w('EFA PIPELINE CHECKPOINT — CES 2024 POLITICAL TYPOLOGY ANALYSIS')
    w('Steps 1–4 Complete (v4). Final item set confirmed. Ready for EFA.')
    w('=' * 72)
    w()
    w('ITEM COUNTS')
    w('-----------')
    w(f'  KEEP:     {len(keeps)} items (EFA item pool)')
    w(f'  DROP:     {len(drops)} items')
    w(f'  TOTAL:    {len(rows)} original candidates')
    w()
    w('SAMPLE SIZE')
    w('-----------')
    w(f'  Original N:                 60,000')
    w(f'  Post-survey completers:     49,432 (tookpost=Yes)')
    w(f'  After listwise deletion:    {N_eff:,} ({100*N_eff/60000:.1f}% of full sample)')
    w(f'  Weighted N (commonpostweight): {W_eff:,.0f}')
    w(f'  Primary driver of exclusion: 10,568 pre-survey-only respondents')
    w(f'    (all post-survey items require post-completion)')
    w()
    w('FINAL EFA ITEM SET (25 items)')
    w('-----------------------------')
    for domain, items in DOMAINS.items():
        kept = [v for v in items if v in EFA_VARS]
        if kept:
            w(f'  {domain}:')
            for v in kept:
                lbl = ALL_LABELS[v]
                r2  = diag_df.loc[v, 'partyID_r2'] if v in diag_df.index else '?'
                w(f'    {v:<18}  PID R²={r2:.3f}  {lbl}')
    w()
    w('DROPPED ITEMS SUMMARY')
    w('---------------------')
    drop_categories = {
        'Partisan proxies (dominate Factor 1)':
            ['CC24_330a','CC24_301','CC24_312a','CC24_312i'],
        'Compositional/invalid for polychoric EFA':
            ['CC24_420_1','CC24_420_2','CC24_420_3','CC24_420_4',
             'CC24_420_5','CC24_420_6','CC24_420_7'],
        'Direction inconsistent across respondents':
            ['CC24_312d','CC24_312e','CC24_312f','CC24_312g','CC24_312h'],
        'Ceiling/floor effects':
            ['CC24_321c','CC24_324c'],
        'Redundant (r>0.70) — lower-signal item retained':
            ['pew_religimp','pew_bornagain','CC24_341b','CC24_324d',
             'CC24_440a','CC24_440d'],
        'Racial resentment (user decision — collinearity concern)':
            ['CC24_441a','CC24_441b'],
        'High missingness / user decision':
            ['CC24_309d_8','CC24_312b','CC24_312c',
             'pew_prayer'],
    }
    for cat, items in drop_categories.items():
        w(f'  {cat}:')
        for v in items:
            w(f'    {v:<18}  {DROP_REASONS.get(v,"")[:70]}')
    w()
    w('POLYCHORIC CORRELATION NOTES')
    w('----------------------------')
    if red_in_keep:
        w(f'  Pairs with |r| > 0.70 remaining in final set:')
        for va, vb, r in red_in_keep:
            w(f'    {va} × {vb}  r={r:+.4f}')
    else:
        w('  No pairs with |r| > 0.70 remain in final item set.')
    w()
    w('  TOP 10 POLYCHORIC CORRELATIONS:')
    for _, r, va, vb in off_diag[:10]:
        w(f'    {va:<18} × {vb:<18}  r={r:+.4f}')
    w()
    w('  ITEMS WITH HIGHEST PID R² (most partisan — monitor in EFA):')
    for v in diag_keep.head(6).index:
        r2 = diag_keep.loc[v, 'partyID_r2']
        w(f'    {v:<18}  PID R²={r2:.4f}  {ALL_LABELS[v][:55]}')
    w()
    w('  ITEMS WITH LOWEST PID R² (most cross-partisan):')
    for v in diag_keep.tail(6).index:
        r2 = diag_keep.loc[v, 'partyID_r2']
        w(f'    {v:<18}  PID R²={r2:.4f}  {ALL_LABELS[v][:55]}')
    w()
    w('SAVED FILES')
    w('-----------')
    w(f'  1. {varlist_path}')
    w(f'  2. {poly_path}')
    w(f'  3. {summary_path}')
    w(f'  4. {heatmap_path}')
    w()
    w('NEXT STEP: Proceed to EFA (Step 5).')
    w('  Recommended: PAF + Oblimin, parallel analysis for k, solutions k=3/4/5.')
    w('  Weight: commonpostweight. Input: polychoric_matrix.csv, N=' + str(N_eff))
    w('=' * 72)

print(f'  Checkpoint summary saved: {summary_path}')

# Final confirmation print
print(f'\n{DIVIDER}\nCOMPLETE\n{DIVIDER}')
print(f'  Items:        {N_VARS}')
print(f'  Listwise N:   {N_eff:,} ({100*N_eff/60000:.1f}%)')
print(f'  Weighted N:   {W_eff:,.0f}')
if red_in_keep:
    print(f'  Redundant pairs remaining: {len(red_in_keep)}')
    for va, vb, r in red_in_keep:
        print(f'    {va} × {vb}  r={r:+.4f}')
else:
    print('  Redundant pairs |r|>0.70 remaining: 0')
print(f'\n  Files saved to {OUTPUT_DIR}/')
print(DIVIDER)
