#!/usr/bin/env python3
"""Recompute every cluster_stats.csv variable grouped by pid3 (self-ID'd party),
so the Parties tab can compare the formulated typology parties against today's
Democratic / Independent / Republican electorates.

pid3 mapping: 1->DEM, 2->REP, 3->IND; 4/5 dropped. Weighted by commonpostweight.
Row alignment mirrors pipeline/add_compare_items.py + compute_intensity.py.

Correctness gate: each variable's recomputed `overall` must match the existing
cluster_stats.csv `overall` within 0.3pp, or the build fails loudly.

Outputs:
  data/outputs/profiles/current_party_stats.csv
  data/outputs/profiles/current_party_continuous.csv   (Task 2)
  viz/src/data/currentPartySpreads.json                (Task 2)
"""
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DTA = ROOT / "CCES24_Common_OUTPUT_vv_topost_final (2).dta"
TYPO = ROOT / "data" / "processed" / "typology_cluster_assignments.csv"
STATS = ROOT / "data" / "outputs" / "profiles" / "cluster_stats.csv"
OUT_STATS = ROOT / "data" / "outputs" / "profiles" / "current_party_stats.csv"

# 24 EFA anchor items — used ONLY for the listwise mask / row alignment.
ITEMS_25 = ['pew_churatd','CC24_302','CC24_303','CC24_341a','CC24_341c','CC24_341d',
    'CC24_323a','CC24_323b','CC24_323d','CC24_321b','CC24_321d','CC24_321e','CC24_325',
    'CC24_324b','CC24_340a','CC24_340b','CC24_340c','CC24_340e','CC24_340f','CC24_440b',
    'CC24_440c','CC24_421_1','CC24_421_2','CC24_423','CC24_424']
ANCHOR = [x for x in ITEMS_25 if x != 'CC24_340a']  # 24 items, alignment only

PID_CODE = {1: "DEM", 2: "REP", 3: "IND"}   # 4/5 dropped
GATE_TOL = 0.3  # pp

# State-spending scale items: type=binary but recode is increase(1+2)->1, else(3-5)->0.
# (add_compare_items.py uses: np.isin(raw,[1,2]) -> 1 else np.isin(raw,[3,4,5]) -> 0)
INCR_BINARY = {"CC24_443_1","CC24_443_2","CC24_443_3","CC24_443_4","CC24_443_5"}

# Variables where code 8 = substantive (not skipped).
# CC24_423/424: code 8 = "None at all" (real trust-level code); in raw_numeric recoded -> 2
CODE8_SUBST = {"CC24_423","CC24_424"}

# Label aliases: (variable, cleaned_target) -> [list of cleaned raw labels that match].
# These handle abbreviated/reformatted labels in cluster_stats.csv that don't
# exactly match the raw DTA value labels after standard normalization.
LABEL_ALIAS = {
    # ordinal: "Stayed same" shortens "Stayed about the same"
    ('CC24_302', 'stayed same'): ['stayed about the same'],
    ('CC24_303', 'stayed same'): ['stayed about the same'],
    # likert5_dist: "% Agree" = code 2 (Somewhat agree), etc. (each is a single code)
    ('CC24_440a', 'agree'): ['somewhat agree'],
    ('CC24_440a', 'neither'): ['neither agree nor disagree'],
    ('CC24_440a', 'disagree'): ['somewhat disagree'],
    ('CC24_440b', 'agree'): ['somewhat agree'],
    ('CC24_440b', 'neither'): ['neither agree nor disagree'],
    ('CC24_440b', 'disagree'): ['somewhat disagree'],
    ('CC24_440c', 'agree'): ['somewhat agree'],
    ('CC24_440c', 'neither'): ['neither agree nor disagree'],
    ('CC24_440c', 'disagree'): ['somewhat disagree'],
    ('CC24_440d', 'agree'): ['somewhat agree'],
    ('CC24_440d', 'neither'): ['neither agree nor disagree'],
    ('CC24_440d', 'disagree'): ['somewhat disagree'],
    ('CC24_441a', 'agree'): ['somewhat agree'],
    ('CC24_441a', 'neither'): ['neither agree nor disagree'],
    ('CC24_441a', 'disagree'): ['somewhat disagree'],
    ('CC24_441b', 'agree'): ['somewhat agree'],
    ('CC24_441b', 'neither'): ['neither agree nor disagree'],
    ('CC24_441b', 'disagree'): ['somewhat disagree'],
    ('CC24_441e', 'agree'): ['somewhat agree'],
    ('CC24_441e', 'neither'): ['neither agree nor disagree'],
    ('CC24_441e', 'disagree'): ['somewhat disagree'],
    ('CC24_441f', 'agree'): ['somewhat agree'],
    ('CC24_441f', 'neither'): ['neither agree nor disagree'],
    ('CC24_441f', 'disagree'): ['somewhat disagree'],
    ('CC24_441g', 'agree'): ['somewhat agree'],
    ('CC24_441g', 'neither'): ['neither agree nor disagree'],
    ('CC24_441g', 'disagree'): ['somewhat disagree'],
    ('CC24_421_1', 'agree'): ['somewhat agree'],
    ('CC24_421_1', 'neither'): ['neither agree nor disagree'],
    ('CC24_421_1', 'disagree'): ['somewhat disagree'],
    ('CC24_421_2', 'agree'): ['somewhat agree'],
    ('CC24_421_2', 'neither'): ['neither agree nor disagree'],
    ('CC24_421_2', 'disagree'): ['somewhat disagree'],
    # trust_dist: "% Great deal" / "% Fair amount" — raw labels have "A" prefix
    ('CC24_423', 'great deal'): ['a great deal'],
    ('CC24_423', 'fair amount'): ['a fair amount'],
    ('CC24_424', 'great deal'): ['a great deal'],
    ('CC24_424', 'fair amount'): ['a fair amount'],
    # pew_churatd: frequency labels abbreviated with "/" and "x"
    ('pew_churatd', 'more than once/week'): ['more than once a week'],
    ('pew_churatd', 'once/week'): ['once a week'],
    ('pew_churatd', '1–2x/month'): ['once or twice a month'],
    ('pew_churatd', 'few times/year'): ['a few times a year'],
    # CC24_330a ideology 7-pt: "Moderate" -> raw "Middle of the Road"
    ('CC24_330a', 'moderate'): ['middle of the road'],
    # race: "Two or more races" -> "% Multiracial"
    ('race', 'multiracial'): ['two or more races'],
    # educ: abbreviated labels
    ('educ', 'hs grad'): ['high school graduate'],
    ('educ', '2-year degree'): ['2-year'],
    ('educ', '4-year degree'): ['4-year'],
    # faminc_new: income bracket labels (stat uses $k abbreviations)
    ('faminc_new', '<$10k'): ['less than $10,000'],
    ('faminc_new', '$10k–20k'): ['$10,000 - $19,999'],
    ('faminc_new', '$20k–30k'): ['$20,000 - $29,999'],
    ('faminc_new', '$30k–40k'): ['$30,000 - $39,999'],
    ('faminc_new', '$40k–50k'): ['$40,000 - $49,999'],
    ('faminc_new', '$50k–60k'): ['$50,000 - $59,999'],
    ('faminc_new', '$60k–70k'): ['$60,000 - $69,999'],
    ('faminc_new', '$70k–80k'): ['$70,000 - $79,999'],
    ('faminc_new', '$80k–100k'): ['$80,000 - $99,999'],
    ('faminc_new', '$100k–120k'): ['$100,000 - $119,999'],
    ('faminc_new', '$120k–150k'): ['$120,000 - $149,999'],
    ('faminc_new', '$150k–200k'): ['$150,000 - $199,999'],
    ('faminc_new', '$200k–250k'): ['$200,000 - $249,999'],
    ('faminc_new', '$250k–350k'): ['$250,000 - $349,999'],
    ('faminc_new', '$350k–500k'): ['$350,000 - $499,999'],
    ('faminc_new', '$500k+'): ['$500,000 or more'],
    # marstat: "Domestic/civil partnership" vs raw "Domestic / civil partnership" (spaces)
    ('marstat', 'domestic/civil partnership'): ['domestic / civil partnership'],
    # immstat: long sentences condensed to short keys
    ('immstat', 'immigrant, naturalized'): ['i am an immigrant to the usa and a naturalized citizen'],
    ('immstat', 'immigrant, not citizen'): ['i am an immigrant to the usa but not a citizen'],
    ('immstat', 'us-born, parent immigrant'): ['i was born in the usa but at least one of my parents is an immigrant'],
    ('immstat', 'us-born, grandparent immigrant'): ['my parents and i were born in the usa but at least one of my grandparents was an immigrant'],
    ('immstat', '3+ gen us-born'): ['my parents, grandparents and i were all born in the usa'],
    # sexuality: slash vs space-slash-space
    ('sexuality', 'heterosexual/straight'): ['heterosexual / straight'],
    ('sexuality', 'lesbian/gay woman'): ['lesbian / gay woman'],
    # union: long sentence -> short key
    ('union', 'current member'): ['yes, i am currently a member of a labor union'],
    ('union', 'former member'): ['i formerly was a member of a labor union'],
    ('union', 'never member'): ['i am not now, nor have i been, a member of a labor union'],
    # unionhh: long sentence -> short key
    ('unionhh', 'currently member'): ['yes, a member of my household is currently a union member'],
    ('unionhh', 'formerly member'): ['a member of my household was formerly a member of a labor union, but is not now'],
    ('unionhh', 'never member'): ['no, no one in my household has ever been a member of a labor union'],
    # presvote20post: last name -> full name
    ('presvote20post', 'biden'): ['joe biden'],
    ('presvote20post', 'trump'): ['donald trump'],
    ('presvote20post', 'jorgensen'): ['jo jorgensen'],
    ('presvote20post', 'hawkins'): ['howie hawkins'],
    ('presvote20post', 'did not vote'): ['did not vote for president'],
    # presvote16post
    ('presvote16post', 'clinton'): ['hillary clinton'],
    ('presvote16post', 'trump'): ['donald trump'],
    ('presvote16post', 'johnson'): ['gary johnson'],
    ('presvote16post', 'stein'): ['jill stein'],
    ('presvote16post', 'mcmullin'): ['evan mcmullin'],
    ('presvote16post', 'did not vote'): ['did not vote for president'],
    # gunown: condensed labels
    ('gunown', 'personally owns'): ['personally own a gun'],
    ('gunown', 'hh owns, not me'): ["don't personally own a gun, but someone in the household owns a gun"],
    ('gunown', 'no one in hh'): ['no one in the household owns a gun'],
}

# Synthetic variables: map synth name -> (raw_var, recode_fn).
# recode_fn(raw_array) -> 0/1/NaN binary array.
SYNTH_RAW = {
    'vote16_clinton': ('presvote16post', lambda x: np.where(x == 1, 1.0, np.where(np.isin(x, [1,2,3,4,5,6,7]), 0.0, np.nan))),
    'vote16_trump':   ('presvote16post', lambda x: np.where(x == 2, 1.0, np.where(np.isin(x, [1,2,3,4,5,6,7]), 0.0, np.nan))),
    'vote16_third':   ('presvote16post', lambda x: np.where(np.isin(x,[3,4,5,6]), 1.0, np.where(np.isin(x, [1,2,3,4,5,6,7]), 0.0, np.nan))),
    'vote16_dnv':     ('presvote16post', lambda x: np.where(x == 7, 1.0, np.where(np.isin(x, [1,2,3,4,5,6,7]), 0.0, np.nan))),
    'vote20_biden':   ('presvote20post', lambda x: np.where(x == 1, 1.0, np.where(np.isin(x, [1,2,3,4,5,6]), 0.0, np.nan))),
    'vote20_trump':   ('presvote20post', lambda x: np.where(x == 2, 1.0, np.where(np.isin(x, [1,2,3,4,5,6]), 0.0, np.nan))),
    'vote20_third':   ('presvote20post', lambda x: np.where(np.isin(x,[3,4,5]), 1.0, np.where(np.isin(x, [1,2,3,4,5,6]), 0.0, np.nan))),
    'vote20_dnv':     ('presvote20post', lambda x: np.where(x == 6, 1.0, np.where(np.isin(x, [1,2,3,4,5,6]), 0.0, np.nan))),
    'appr_biden':     ('CC24_312a', lambda x: np.where(np.isin(x,[1,2]), 1.0, np.where(np.isin(x, [1,2,3,4,5]), 0.0, np.nan))),
    'appr_harris':    ('CC24_312i', lambda x: np.where(np.isin(x,[1,2]), 1.0, np.where(np.isin(x, [1,2,3,4,5]), 0.0, np.nan))),
    'relig_protestant': ('religpew', lambda x: np.where(x==1, 1.0, np.where(np.isin(x,list(range(1,13))), 0.0, np.nan))),
    'relig_catholic':   ('religpew', lambda x: np.where(x==2, 1.0, np.where(np.isin(x,list(range(1,13))), 0.0, np.nan))),
    'relig_jewish':     ('religpew', lambda x: np.where(x==5, 1.0, np.where(np.isin(x,list(range(1,13))), 0.0, np.nan))),
    'relig_muslim':     ('religpew', lambda x: np.where(x==6, 1.0, np.where(np.isin(x,list(range(1,13))), 0.0, np.nan))),
    'relig_none':       ('religpew', lambda x: np.where(np.isin(x,[9,10,11]), 1.0, np.where(np.isin(x,list(range(1,13))), 0.0, np.nan))),
    'relig_other':      ('religpew', lambda x: np.where(np.isin(x,[3,4,7,8,12]), 1.0, np.where(np.isin(x,list(range(1,13))), 0.0, np.nan))),
}


def load_aligned():
    """Return (dc, pid, w, reader) — listwise sample row-aligned to typo, plus pid3 & weight."""
    reader = pd.io.stata.StataReader(str(DTA))
    # Call value_labels() first to populate _varlist/_lbllist internal state.
    reader.value_labels()
    df = pd.read_stata(DTA, convert_categoricals=False)
    mask = df[ANCHOR + ['commonpostweight']].notna().all(axis=1)
    dc = df[mask].reset_index(drop=True)
    typo = pd.read_csv(TYPO)
    assert len(dc) == len(typo), f"row mismatch {len(dc)} vs {len(typo)}"
    pid = pd.to_numeric(typo['pid3'], errors='coerce').values
    w = dc['commonpostweight'].values.astype(float)
    return dc, pid, w, reader


def build_synthetic_map(dc):
    """Build {synth_var: array} for computed variables from add_compare_items.py."""
    synth = {}
    # Single-source synthetics
    for name, (raw_var, fn) in SYNTH_RAW.items():
        if raw_var in dc.columns:
            synth[name] = fn(dc[raw_var].values.astype(float))
    # Multi-source: 2024 vote (CC24_401 = turnout, CC24_410 = vote choice)
    if 'CC24_401' in dc.columns and 'CC24_410' in dc.columns:
        t = dc['CC24_401'].values.astype(float)
        ch = dc['CC24_410'].values.astype(float)
        validturn = np.isin(t, [1, 2, 3, 4, 5])
        def v24(cond):
            b = np.where(cond, 1.0, 0.0).astype(float)
            b[~validturn] = np.nan
            return b
        synth['vote24_harris'] = v24(ch == 1)
        synth['vote24_trump']  = v24(ch == 2)
        synth['vote24_third']  = v24(np.isin(ch, [3, 4, 5, 6, 8]))
        synth['vote24_dnv']    = v24(t != 5)
    # Turnout
    if 'CC24_401' in dc.columns:
        t = dc['CC24_401'].values.astype(float)
        synth['reported_turnout_24'] = np.where(t == 5, 1.0, 0.0)
    if 'TS_g2024' in dc.columns:
        ts = dc['TS_g2024'].values.astype(float)
        synth['verified_turnout_24'] = np.where((~np.isnan(ts)) & (ts <= 6), 1.0, 0.0)
    # Religion importance: very/somewhat (1,2) -> 1; not too/not at all (3,4) -> 0
    if 'pew_religimp' in dc.columns:
        ri = dc['pew_religimp'].values.astype(float)
        synth['pew_religimp'] = np.where(np.isin(ri, [1, 2]), 1.0, np.where(np.isin(ri, [3, 4]), 0.0, np.nan))
    # Prayer: weekly or more (codes 1-4) -> 1
    if 'pew_prayer' in dc.columns:
        pr = dc['pew_prayer'].values.astype(float)
        synth['pew_prayer'] = np.where(np.isin(pr, [1, 2, 3, 4]), 1.0, np.where(np.isin(pr, [5, 6, 7]), 0.0, np.nan))
    # News interest: code 1 (Most of the time) -> 1; codes 2-4 -> 0
    if 'newsint' in dc.columns:
        ni = dc['newsint'].values.astype(float)
        synth['newsint'] = np.where(ni == 1, 1.0, np.where(np.isin(ni, [2, 3, 4]), 0.0, np.nan))
    # Age: 2024 - birthyr
    if 'birthyr' in dc.columns:
        by = dc['birthyr'].values.astype(float)
        age = 2024.0 - by
        synth['age'] = np.where((age >= 18) & (age <= 110), age, np.nan)
    # numkids: from numchildren (numeric count)
    if 'numchildren' in dc.columns:
        nc = dc['numchildren'].values.astype(float)
        synth['numkids'] = np.where((nc >= 0) & (nc <= 20), nc, np.nan)
    return synth


def build_dist_denom_map(reader, stats):
    """Pre-build {variable -> frozenset of denom codes} from cluster_stats dist rows.

    The denominator for each _dist variable = the union of all codes whose stat_labels
    appear in cluster_stats for that variable. This matches the original computation
    where denominators were built from valid response codes actually shown to users.
    """
    setname = dict(zip(reader._varlist, reader._lbllist))
    val_labels = reader.value_labels()

    denom_map = {}
    dist_rows = stats[stats['type'].str.endswith('_dist')]

    for var, grp in dist_rows.groupby('variable'):
        if var in ('numkids',):  # synthetic with no DTA variable
            continue
        lname = setname.get(var, '')
        labs = val_labels.get(lname, {})
        # Build inverted label -> code mapping (lower-cased)
        label_to_codes = {}
        for c, l in labs.items():
            clean = str(l).strip().lower()
            label_to_codes.setdefault(clean, []).append(int(c))

        denom_codes = set()
        for sl in grp['stat_label']:
            target = sl.replace('%', '').strip().lower()
            # Try alias first
            alias = LABEL_ALIAS.get((var, target))
            if alias is not None:
                for a in alias:
                    denom_codes.update(label_to_codes.get(a, []))
            else:
                denom_codes.update(label_to_codes.get(target, []))

        if denom_codes:
            denom_map[var] = frozenset(denom_codes)

    return denom_map


# ── Weighted stat helpers ──────────────────────────────────────────────────────

def masks(pid):
    """pid3 group boolean masks for DEM/IND/REP."""
    return {"DEM": pid == 1, "REP": pid == 2, "IND": pid == 3}


def wmean(vals, w, m):
    v = vals[m]; ww = w[m]; ok = ~np.isnan(v)
    return round(float((ww[ok] * v[ok]).sum() / ww[ok].sum()), 4) if ok.any() and ww[ok].sum() > 0 else np.nan


def wshare(binvals, w, m):
    """Weighted % where binvals==1 (0/1/NaN vector)."""
    r = wmean(binvals, w, m)
    return round(100.0 * r, 4) if not np.isnan(r) else np.nan


def wpctile(vals, w, m, q):
    """Weighted percentile q in [0,1] over group m (NaNs dropped)."""
    v = vals[m]; ww = w[m]; ok = ~np.isnan(v)
    v, ww = v[ok], ww[ok]
    if v.size == 0:
        return np.nan
    order = np.argsort(v); v, ww = v[order], ww[order]
    cw = np.cumsum(ww) - 0.5 * ww
    cw /= ww.sum()
    return round(float(np.interp(q, cw, v)), 4)


# ── Value-label helpers ────────────────────────────────────────────────────────

def get_label_to_codes(reader, var):
    """Return {cleaned_label -> [list of codes]} for a variable."""
    setname = dict(zip(reader._varlist, reader._lbllist))
    labs = reader.value_labels().get(setname.get(var, ''), {})
    result = {}
    for c, l in labs.items():
        clean = str(l).strip().lower()
        result.setdefault(clean, []).append(int(c))
    return result


def resolve_target_codes(reader, var, target_cleaned):
    """Return list of raw codes matching the cleaned stat_label target.

    Checks LABEL_ALIAS first, then falls back to exact label match.
    Returns [] if no match -> triggers skip for that row.
    """
    label_to_codes = get_label_to_codes(reader, var)
    alias = LABEL_ALIAS.get((var, target_cleaned))
    if alias is not None:
        result = []
        for a in alias:
            result.extend(label_to_codes.get(a, []))
        return result
    return label_to_codes.get(target_cleaned, [])


def substantive_mean_codes(reader, var):
    """Return set of valid codes for mean computation (drops skipped/not-asked/not-sure/dk).

    More aggressive than denom: drops ambiguous codes. Returns set of valid int codes.
    """
    setname = dict(zip(reader._varlist, reader._lbllist))
    labs = reader.value_labels().get(setname.get(var, ''), {})
    MEAN_DROP_KW = ('skipped', 'not asked', 'not sure', "don't know", 'dk',
                    'refused', 'prefer not to say')
    valid = set()
    for c, l in labs.items():
        c = int(c)
        t = str(l).strip().lower()
        if any(d in t for d in MEAN_DROP_KW) or c in (9, 98, 99):
            # Code 8 for trust vars is "None at all" — substantive, but raw_numeric
            # already recodes it to 2 (midpoint), so it's handled correctly there.
            if var in CODE8_SUBST and c == 8:
                valid.add(c)  # keep code 8 for trust vars (recoded -> 2 in raw_numeric)
            elif c == 8 and var not in CODE8_SUBST:
                continue
            else:
                continue
        valid.add(c)
    return valid


def raw_numeric(dc, var):
    """Raw numeric column with documented pre-recodes applied (EFA-consistent).

    Applies:
    - CC24_423/424: code 8 ("None at all") -> 2 (midpoint-impute, EFA-consistent)
    - ideo5: code 6 ("Not sure") -> NaN
    - CC24_325: 40 - x (weeks -> restrictiveness); NOT applied for continuous rows.
    """
    x = dc[var].values.astype(float)
    if var in ("CC24_423", "CC24_424"):
        x = np.where(x == 8, 2.0, x)
    if var == "ideo5":
        x = np.where(x == 6, np.nan, x)
    if var == "CC24_325":
        x = 40.0 - x                             # for mean (ordinal) only
    return x


# ── Row dispatcher ─────────────────────────────────────────────────────────────

def compute_row(dc, reader, w, grp, synth, denom_map, row):
    """Return {'overall': x, 'DEM': .., 'IND': .., 'REP': ..} or None to skip."""
    var, typ, lbl = row['variable'], row['type'], row['stat_label']
    ALL = np.ones(len(dc), bool)

    def out(fn):
        r = {'overall': fn(ALL)}
        for code, m in grp.items():
            r[code] = fn(m)
        return r

    # ── Synthetic binary vars (created by add_compare_items.py) ──────────────
    if var in synth and typ == 'binary':
        b = synth[var]
        return out(lambda m, b=b: wshare(b, w, m))

    # ── Synthetic age continuous ──────────────────────────────────────────────
    if var == 'age' and typ == 'continuous':
        x = synth.get('age')
        if x is None:
            return None
        q = {'Median': 0.5, 'Q25': 0.25, 'Q75': 0.75}.get(lbl)
        if q is None:
            return None
        return out(lambda m, x=x, q=q: wpctile(x, w, m, q))

    # ── numkids categorical_dist ──────────────────────────────────────────────
    if var == 'numkids' and typ == 'categorical_dist':
        x = synth.get('numkids')
        if x is None:
            return None
        target = lbl.replace('%', '').strip()
        valid = ~np.isnan(x)
        if target == '3+':
            sel = x >= 3
        else:
            try:
                n = int(target)
                sel = x == n
            except ValueError:
                return None
        b = np.where(sel & valid, 1.0, np.where(valid, 0.0, np.nan))
        return out(lambda m, b=b: wshare(b, w, m))

    # ── Variable must be in dc ────────────────────────────────────────────────
    if var not in dc.columns:
        return None

    # ── Binary / binary_agree rows ────────────────────────────────────────────
    if typ in ('binary', 'binary_agree'):
        x = dc[var].values.astype(float)
        if var in INCR_BINARY:
            # State spending scale: codes 1+2 = increase -> 1; codes 3-5 = 0
            b = np.where(np.isin(x, [1, 2]), 1.0, np.where(np.isin(x, [3, 4, 5]), 0.0, np.nan))
        else:
            # Support/oppose or selected/not-selected: code 1 -> 1, code 2 -> 0.
            # REV_BINARY applies only to EFA polychoric direction; '% Supporting'
            # always means code 1 in the original survey.
            b = np.where(x == 1, 1.0, np.where(x == 2, 0.0, np.nan))
        return out(lambda m, b=b: wshare(b, w, m))

    # ── Distribution rows -> match target code(s) against denom codes ─────────
    if typ.endswith('_dist'):
        target = lbl.replace('%', '').strip().lower()
        sel_codes = resolve_target_codes(reader, var, target)
        if not sel_codes:
            return None   # unresolved label -> skip (logged by caller)
        # Denominator = codes present in ALL dist stat_labels for this variable in cluster_stats
        denom_codes = denom_map.get(var)
        if denom_codes is None:
            return None
        x = dc[var].values.astype(float)
        valid = np.isin(x, list(denom_codes))
        b = np.where(np.isin(x, sel_codes) & valid, 1.0, np.where(valid, 0.0, np.nan))
        return out(lambda m, b=b: wshare(b, w, m))

    # ── Mean rows (likert5, ordinal, approval4, trust) ────────────────────────
    if typ in ('likert5', 'ordinal', 'approval4', 'trust'):
        x = raw_numeric(dc, var)
        # Mask out non-substantive codes (e.g. faminc_new code 97='Prefer not to say')
        valid_codes = substantive_mean_codes(reader, var)
        if valid_codes:
            raw_x = dc[var].values.astype(float)
            x = np.where(np.isin(raw_x, list(valid_codes)), x, np.nan)
        return out(lambda m, x=x: wmean(x, w, m))

    # ── Continuous rows (Median / Q25 / Q75) ─────────────────────────────────
    if typ == 'continuous':
        if var == 'CC24_325':
            # Continuous rows use raw weeks (not the 40-x reversal used for ordinal means)
            x = dc[var].values.astype(float)
            x = np.where((x >= 0) & (x <= 40), x, np.nan)
        else:
            x = raw_numeric(dc, var)
        q = {'Median': 0.5, 'Q25': 0.25, 'Q75': 0.75}.get(lbl)
        if q is None:
            return None
        return out(lambda m, x=x, q=q: wpctile(x, w, m, q))

    return None


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("Loading and aligning data...")
    dc, pid, w, reader = load_aligned()
    grp = masks(pid)
    synth = build_synthetic_map(dc)
    print(f"  Sample: {len(dc):,} rows  DEM={(pid==1).sum():,}  REP={(pid==2).sum():,}  IND={(pid==3).sum():,}")

    stats = pd.read_csv(STATS)
    print("Building denominator map from cluster_stats dist rows...")
    denom_map = build_dist_denom_map(reader, stats)

    out_rows, gate_fail, skipped = [], [], []

    for _, row in stats.iterrows():
        res = compute_row(dc, reader, w, grp, synth, denom_map, row)
        rec = {k: row[k] for k in ('variable', 'domain', 'type', 'stat_label', 'question')}
        if res is None:
            skipped.append(f"{row['variable']} / {row['stat_label']}")
            rec.update({'overall': row.get('overall'), 'DEM': np.nan, 'IND': np.nan, 'REP': np.nan})
        else:
            stored_raw = row.get('overall')
            stored = float(stored_raw) if str(stored_raw) not in ('', 'nan') else np.nan
            if not np.isnan(res['overall']) and not np.isnan(stored) and abs(res['overall'] - stored) > GATE_TOL:
                gate_fail.append((row['variable'], row['stat_label'], res['overall'], stored))
            # Use stored overall (authoritative); only DEM/IND/REP are newly computed
            rec.update({'overall': row['overall'], 'DEM': res['DEM'], 'IND': res['IND'], 'REP': res['REP']})
        out_rows.append(rec)

    # ── Report ────────────────────────────────────────────────────────────────
    print(f"\nTotal rows: {len(out_rows)}")
    if skipped:
        print(f"SKIPPED {len(skipped)} rows (unresolved label or variable not in sample):")
        for s in skipped:
            print(f"    {s}")

    if gate_fail:
        print(f"\nGATE FAILURES ({len(gate_fail)}) — recomputed overall != stored (tol={GATE_TOL}pp):")
        for v, l, got, exp in gate_fail:
            print(f"    {v} / {l}: got {got:.4f}  expected {exp:.4f}  diff={abs(got-exp):.4f}")
        raise SystemExit("Correctness gate failed — fix recode/override for the vars above.")

    cols = ['variable', 'domain', 'type', 'stat_label', 'question', 'overall', 'DEM', 'IND', 'REP']
    pd.DataFrame(out_rows)[cols].to_csv(OUT_STATS, index=False)
    print(f"\nwrote {OUT_STATS.relative_to(ROOT)} — {len(out_rows)} rows, {len(skipped)} skipped, gate OK")


if __name__ == '__main__':
    main()
