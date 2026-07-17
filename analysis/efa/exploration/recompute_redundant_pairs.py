#!/usr/bin/env python3
"""
Recompute redundancy-screening artifacts with CORRECT weighted polychoric
correlation. Supersedes the buggy redundant_pairs.csv (inflated magnitudes,
one sign-flipped pair).

- Weighted polychoric/tetrachoric MLE reused from efa_pipeline_v4.py
  (cross-checked against archive/old_scripts/efa_pipeline_step4.py).
- Item universe: attitudinal/policy + govt-trust + religion items from
  efa_variable_list.csv. EXCLUDES approval battery (CC24_312*), ideology
  self-placement (CC24_330*), multi-select/compositional (CC24_309d*,
  CC24_420*), and vote items.
- Listwise PER PAIR (each rho uses cases complete on that pair only).
- Weight: commonpostweight.
"""

import warnings; warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from scipy.stats import norm
from scipy.stats import multivariate_normal as mvn
from statsmodels.tools import add_constant
from statsmodels.regression.linear_model import WLS

DATA_PATH = '/Users/bdecker/Local Projects/Personal/STV/data/raw/2024 CES Base/CCES24_Common_OUTPUT_vv_topost_final.dta'
OUT_CSV   = '/Users/bdecker/Local Projects/Personal/STV/analysis/efa/redundant_pairs.csv'

print('Loading data...')
df = pd.read_stata(DATA_PATH, convert_categoricals=True,
                   convert_missing=False, convert_dates=False)
print(f'  {df.shape[0]:,} rows x {df.shape[1]:,} cols')

w_post = df['commonpostweight'].values.astype(float)

# ---------------------------------------------------------------------------
# RECODE — item universe (v4 conventions; extra dropped items from archive,
# which use the identical direction rules)
# ---------------------------------------------------------------------------
def cat_to_num(series, m):
    return series.map(m).astype(float)

recode = {}

# RELIGION
recode['pew_churatd'] = cat_to_num(df['pew_churatd'], {
    'Never': 1, 'Seldom': 2, 'A few times a year': 3,
    'Once or twice a month': 4, 'Once a week': 5,
    'More than once a week': 6, "Don't know": np.nan})
recode['pew_religimp'] = cat_to_num(df['pew_religimp'], {
    'Not at all important': 1, 'Not too important': 2,
    'Somewhat important': 3, 'Very important': 4})
recode['pew_prayer'] = cat_to_num(df['pew_prayer'], {
    'Never': 1, 'Seldom': 2, 'A few times a month': 3,
    'Once a week': 4, 'A few times a week': 5,
    'Once a day': 6, 'Several times a day': 7, "Don't know": np.nan})
recode['pew_bornagain'] = cat_to_num(df['pew_bornagain'], {'No': 0, 'Yes': 1})

# ECON PERCEPTIONS (v4 conventions)
recode['CC24_302'] = cat_to_num(df['CC24_302'], {
    'Increased a lot': 1, 'Increased somewhat': 2, 'Stayed about the same': 3,
    'Decreased somewhat': 4, 'Decreased a lot': 5})
recode['CC24_303'] = cat_to_num(df['CC24_303'], {
    'Decreased a lot': 1, 'Decreased somewhat': 2, 'Stayed about the same': 3,
    'Increased somewhat': 4, 'Increased a lot': 5})

# TAX/FISCAL
recode['CC24_341a'] = cat_to_num(df['CC24_341a'], {'Support': 1, 'Oppose': 0})
recode['CC24_341b'] = cat_to_num(df['CC24_341b'], {'Support': 0, 'Oppose': 1})
recode['CC24_341c'] = cat_to_num(df['CC24_341c'], {'Support': 0, 'Oppose': 1})
recode['CC24_341d'] = cat_to_num(df['CC24_341d'], {'Support': 0, 'Oppose': 1})

# IMMIGRATION
recode['CC24_323a'] = cat_to_num(df['CC24_323a'], {'Support': 0, 'Oppose': 1})
recode['CC24_323b'] = cat_to_num(df['CC24_323b'], {'Support': 1, 'Oppose': 0})
recode['CC24_323d'] = cat_to_num(df['CC24_323d'], {'Support': 0, 'Oppose': 1})

# GUNS/POLICING
recode['CC24_321b'] = cat_to_num(df['CC24_321b'], {'Support': 1, 'Oppose': 0})
recode['CC24_321c'] = cat_to_num(df['CC24_321c'], {'Support': 0, 'Oppose': 1})
recode['CC24_321d'] = cat_to_num(df['CC24_321d'], {'Support': 1, 'Oppose': 0})
recode['CC24_321e'] = cat_to_num(df['CC24_321e'], {'Support': 0, 'Oppose': 1})

# ABORTION
cc325 = pd.to_numeric(df['CC24_325'].astype(str), errors='coerce')
recode['CC24_325']  = 40.0 - cc325
recode['CC24_324b'] = cat_to_num(df['CC24_324b'], {'Support': 1, 'Oppose': 0})
recode['CC24_324c'] = cat_to_num(df['CC24_324c'], {'Support': 1, 'Oppose': 0})
recode['CC24_324d'] = cat_to_num(df['CC24_324d'], {'Support': 0, 'Oppose': 1})

# CIVIL RIGHTS / LIBERTIES
recode['CC24_340a'] = cat_to_num(df['CC24_340a'], {'Support': 0, 'Oppose': 1})
recode['CC24_340b'] = cat_to_num(df['CC24_340b'], {'Support': 0, 'Oppose': 1})
recode['CC24_340c'] = cat_to_num(df['CC24_340c'], {'Support': 0, 'Oppose': 1})
recode['CC24_340e'] = cat_to_num(df['CC24_340e'], {'Support': 1, 'Oppose': 0})
recode['CC24_340f'] = cat_to_num(df['CC24_340f'], {'Support': 1, 'Oppose': 0})

# RACIAL / GENDER (5-pt agree scales)
_lib_agree = {'Strongly agree': 1, 'Somewhat agree': 2, 'Neither agree nor disagree': 3,
              'Somewhat disagree': 4, 'Strongly disagree': 5}
_con_agree = {'Strongly agree': 5, 'Somewhat agree': 4, 'Neither agree nor disagree': 3,
              'Somewhat disagree': 2, 'Strongly disagree': 1}
recode['CC24_440a'] = cat_to_num(df['CC24_440a'], _lib_agree)   # white advantages: agree=liberal
recode['CC24_440b'] = cat_to_num(df['CC24_440b'], _con_agree)
recode['CC24_440c'] = cat_to_num(df['CC24_440c'], _con_agree)
recode['CC24_440d'] = cat_to_num(df['CC24_440d'], _con_agree)
recode['CC24_441a'] = cat_to_num(df['CC24_441a'], _con_agree)   # "work up without favors": agree=conservative
recode['CC24_441b'] = cat_to_num(df['CC24_441b'], _lib_agree)   # slavery created conditions: agree=liberal

# ELECTION TRUST
_elec = {'Strongly agree': 1, 'Somewhat agree': 2, 'Neither agree nor disagree': 3,
         'Somewhat disagree': 4, 'Strongly disagree': 5}
recode['CC24_421_1'] = cat_to_num(df['CC24_421_1'], _elec)
recode['CC24_421_2'] = cat_to_num(df['CC24_421_2'], _elec)

# GOVT TRUST
_govt = {'A great deal': 1, 'A fair amount': 2, 'Not very much': 3, 'None at all': 4}
recode['CC24_423'] = cat_to_num(df['CC24_423'], _govt)
recode['CC24_424'] = cat_to_num(df['CC24_424'], _govt)

# PID for diagnostics
recode['pid7'] = cat_to_num(df['pid7'], {
    'Strong Democrat': 1, 'Not very strong Democrat': 2, 'Lean Democrat': 3,
    'Independent': 4, 'Lean Republican': 5, 'Not very strong Republican': 6,
    'Strong Republican': 7, 'Not sure': np.nan})

data = pd.DataFrame(recode)

# Item universe screened for redundancy (excludes 312*, 330*, 309d*, 420*, votes)
ITEMS = [
    'pew_churatd', 'pew_religimp', 'pew_prayer', 'pew_bornagain',
    'CC24_302', 'CC24_303',
    'CC24_341a', 'CC24_341b', 'CC24_341c', 'CC24_341d',
    'CC24_323a', 'CC24_323b', 'CC24_323d',
    'CC24_321b', 'CC24_321c', 'CC24_321d', 'CC24_321e',
    'CC24_325', 'CC24_324b', 'CC24_324c', 'CC24_324d',
    'CC24_340a', 'CC24_340b', 'CC24_340c', 'CC24_340e', 'CC24_340f',
    'CC24_440a', 'CC24_440b', 'CC24_440c', 'CC24_440d',
    'CC24_441a', 'CC24_441b',
    'CC24_421_1', 'CC24_421_2',
    'CC24_423', 'CC24_424',
]
print(f'  Item universe: {len(ITEMS)} items')

# ---------------------------------------------------------------------------
# WEIGHTED POLYCHORIC (from efa_pipeline_v4.py)
# ---------------------------------------------------------------------------
BIG = 6.5

def weighted_polychoric(x, y, wts):
    # NaN weights: commonpostweight is NaN for 10,568 pre-survey-only
    # respondents. Per-pair listwise must drop them too, else the weighted
    # contingency table becomes all-NaN and the optimizer returns a
    # degenerate boundary value.
    mask = ~(np.isnan(x) | np.isnan(y) | np.isnan(wts))
    x_, y_, w_ = x[mask], y[mask], wts[mask]
    if len(x_) < 30:
        return np.nan, mask.sum()
    x_cats = np.sort(np.unique(x_)); y_cats = np.sort(np.unique(y_))
    nx, ny = len(x_cats), len(y_cats)
    if nx < 2 or ny < 2:
        return np.nan, mask.sum()
    xi = np.searchsorted(x_cats, x_); yi = np.searchsorted(y_cats, y_)
    w_ = w_ / w_.sum()
    ct = np.zeros((nx, ny))
    for ii, jj, ww in zip(xi, yi, w_):
        ct[ii, jj] += ww
    x_marg = ct.sum(axis=1); y_marg = ct.sum(axis=0)
    tau_x = np.concatenate([[-BIG], norm.ppf(np.clip(np.cumsum(x_marg)[:-1], 1e-7, 1-1e-7)), [BIG]])
    tau_y = np.concatenate([[-BIG], norm.ppf(np.clip(np.cumsum(y_marg)[:-1], 1e-7, 1-1e-7)), [BIG]])
    def nll(rho):
        cov = [[1.0, rho], [rho, 1.0]]
        H, K = np.meshgrid(tau_x, tau_y, indexing='ij')
        pts = np.column_stack([H.ravel(), K.ravel()])
        cdf = mvn(mean=[0, 0], cov=cov).cdf(pts).reshape(nx+1, ny+1)
        P = np.diff(np.diff(cdf, axis=0), axis=1)
        P = np.maximum(P, 1e-12)
        return -np.sum(ct * np.log(P))
    res = minimize_scalar(nll, bounds=(-0.9999, 0.9999), method='bounded',
                          options={'xatol': 1e-5})
    return float(res.x), mask.sum()

# ---------------------------------------------------------------------------
# Weighted PID R^2 per item (listwise on that item)
# ---------------------------------------------------------------------------
def weighted_r2(y, x, wts):
    m = ~(np.isnan(y) | np.isnan(x) | np.isnan(wts))
    if m.sum() < 10:
        return np.nan
    y_, x_, w_ = y[m], x[m], wts[m]
    w_ = w_ / w_.mean()
    try:
        return WLS(y_, add_constant(x_), weights=w_).fit().rsquared
    except Exception:
        return np.nan

pid = data['pid7'].values
pid_r2 = {v: weighted_r2(data[v].values, pid, w_post) for v in ITEMS}

# ---------------------------------------------------------------------------
# Full matrix, listwise per pair
# ---------------------------------------------------------------------------
print('Computing polychoric matrix (listwise per pair)...')
n = len(ITEMS)
R = np.eye(n)
Npair = {}
import time; t0 = time.time()
for i in range(n):
    for j in range(i+1, n):
        r, npr = weighted_polychoric(data[ITEMS[i]].values, data[ITEMS[j]].values, w_post)
        R[i, j] = R[j, i] = r
        Npair[(ITEMS[i], ITEMS[j])] = npr
print(f'  done in {time.time()-t0:.0f}s')

Rdf = pd.DataFrame(R, index=ITEMS, columns=ITEMS)
Rdf.round(4).to_csv('/Users/bdecker/Local Projects/Personal/STV/analysis/efa/polychoric_matrix_redundancy_screen.csv')

# ---------------------------------------------------------------------------
# Emit all pairs with corrected |r| >= 0.60
# ---------------------------------------------------------------------------
KEEP = set(pd.read_csv('/Users/bdecker/Local Projects/Personal/STV/analysis/efa/efa_variable_list.csv')
           .query("final_action=='KEEP'")['variable_name'])

rows = []
for i in range(n):
    for j in range(i+1, n):
        r = R[i, j]
        if np.isnan(r) or abs(r) < 0.60:
            continue
        va, vb = ITEMS[i], ITEMS[j]
        r2a, r2b = pid_r2[va], pid_r2[vb]
        a_keep, b_keep = va in KEEP, vb in KEEP
        # preferred_retain: if exactly one is retained, that one; else lower PID R^2
        if a_keep and not b_keep:
            pref, drop = va, vb
        elif b_keep and not a_keep:
            pref, drop = vb, va
        else:
            if (r2a if not np.isnan(r2a) else 9) <= (r2b if not np.isnan(r2b) else 9):
                pref, drop = va, vb
            else:
                pref, drop = vb, va
        rat = (f"|r|={abs(r):.2f}; retain {pref} (PID R2={pid_r2[pref]:.3f}) "
               f"over {drop} (PID R2={pid_r2[drop]:.3f})")
        rows.append({
            'var_a': va, 'var_b': vb, 'polychoric_r': round(r, 4),
            'partyID_r2_a': round(r2a, 4), 'partyID_r2_b': round(r2b, 4),
            'preferred_retain': pref, 'suggested_drop': drop, 'rationale': rat,
        })

out = pd.DataFrame(rows).sort_values('polychoric_r', key=lambda s: s.abs(), ascending=False)
header = ("# SUPERSEDES the buggy polychoric pass. Corrected weighted polychoric "
          "(commonpostweight, listwise per pair) via efa_pipeline_v4.py MLE. "
          "Pairs with corrected |r|>=0.60. See redundancy_recheck_notes.md.\n")
with open(OUT_CSV, 'w') as f:
    f.write(header)
    out.to_csv(f, index=False)
print(f'  wrote {OUT_CSV} ({len(out)} pairs)')

# Print key checks
print('\nKEY PAIR CHECKS:')
for a, b in [('CC24_341a','CC24_341b'), ('CC24_440a','CC24_440b'),
             ('pew_churatd','pew_bornagain'), ('pew_churatd','pew_religimp'),
             ('CC24_323a','CC24_323d'), ('CC24_321d','CC24_321e'),
             ('CC24_421_1','CC24_421_2'), ('CC24_340b','CC24_340f'),
             ('CC24_441a','CC24_441b'), ('CC24_441a','CC24_440b'),
             ('CC24_441b','CC24_440b')]:
    if a in ITEMS and b in ITEMS:
        print(f'  {a} x {b}: r={Rdf.loc[a,b]:+.4f}')

# Corrected max-|r| of each flagged-drop item vs any RETAINED item
print('\nFLAGGED-DROP items: max |r| vs any RETAINED item:')
for v in ['CC24_341b','CC24_440a','CC24_441a','CC24_441b','pew_bornagain']:
    best = max(((abs(Rdf.loc[v,k]), k, Rdf.loc[v,k]) for k in KEEP if k in ITEMS and k != v),
               key=lambda t: t[0])
    print(f'  {v}: max |r|={best[0]:.3f} vs {best[1]} (r={best[2]:+.3f})')
