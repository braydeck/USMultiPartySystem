# Current Parties in the Parties Tab — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add today's real parties — Democratic / Independent / Republican (from `pid3`) — as full-profile comparison columns in the Parties tab, plus a "distance from today's parties" readout in factor space and policy space.

**Architecture:** A new pipeline script recomputes every existing per-cluster statistic grouped by `pid3` instead of by cluster, gated by an assertion that each variable's recomputed national `overall` matches the value already in `cluster_stats.csv` (proving the recode is faithful). `prepare_data.py` then emits `currentPartyProfiles.json` and injects DEM/IND/REP into `distributions.json`; `compute_intensity.py` injects them into `clusterIntensity.json`. The viz treats DEM/IND/REP as three more selectable codes behind a "Current parties" selector group, rendered dashed/desaturated, with a dedicated distance component.

**Tech Stack:** Python 3.13 + pandas/numpy (pipeline); React + TypeScript + Vite + Tailwind + shadcn/ui (viz); vitest (JS unit tests). Data source: `CCES24_Common_OUTPUT_vv_topost_final (2).dta` + `data/processed/typology_cluster_assignments.csv` (row-aligned, N=45,707).

## Global Constraints

- **Codes:** `DEM`, `IND`, `REP` only. `pid3` mapping: `1→DEM`, `2→REP`, `3→IND`; `pid3 ∈ {4,5}` dropped. No vote-based groups, no "third party".
- **Weighting:** every statistic uses `commonpostweight`.
- **Row alignment:** listwise-filter the raw `.dta` to `notna` on the 24 EFA anchor items + `commonpostweight`, `reset_index(drop=True)`; it then aligns 1:1 by row position to `typology_cluster_assignments.csv` (assert equal length). This is the exact trick in `pipeline/add_compare_items.py` and `pipeline/compute_intensity.py` — copy it, do not reinvent.
- **Correctness gate:** no current-party artifact is written unless every variable's recomputed `overall` matches the existing `cluster_stats.csv` `overall` within 0.3 pp.
- **Copy rule:** party labels are "Democratic" / "Independent" / "Republican". Never show `pid3` codes or candidate initials in UI. No editorial/comparative commentary in any copy.
- **Colors (muted):** `DEM #5b7fa6`, `IND #8a8f98`, `REP #a66b6b`. Current parties render with a dashed outline everywhere (chips, bars, constellation) via `isCurrentParty(code)`.
- **Distance factors:** `F1, F2, F4, F5` (F3 excluded, matching `FACTORS_BY_DISCRIMINATION` in `CompareTab.tsx`).
- **Run command (regenerate all JSON):** `cd viz && python3 scripts/prepare_data.py`.

---

## File Structure

**New**
- `pipeline/build_current_party_profiles.py` — recodes all `cluster_stats.csv` variables grouped by `pid3`; writes `current_party_stats.csv`, `current_party_continuous.csv`, and `viz/src/data/currentPartySpreads.json`. Owns all raw-data → pid3 aggregation + the gate.
- `viz/src/lib/partyDistance.ts` — pure factor-space distance helper (+ vitest).
- `viz/src/lib/partyDistance.test.ts` — tests for the above.
- `viz/src/components/parties/CurrentPartyDistance.tsx` — the "Distance from today's parties" card.
- Generated: `viz/src/data/currentPartyProfiles.json`, `viz/src/data/currentPartySpreads.json`, `data/outputs/profiles/current_party_stats.csv`, `data/outputs/profiles/current_party_continuous.csv`.

**Modified**
- `pipeline/compute_intensity.py` — add DEM/IND/REP to every intensity item's `parties`.
- `viz/scripts/prepare_data.py` — new `build_current_party_profiles()` (→ `currentPartyProfiles.json`); `build_distributions()` extended to emit DEM/IND/REP; both wired into `__main__`.
- `viz/src/constants/parties.ts` — codes, names, colors, `CURRENT_PARTIES`, `isCurrentParty`.
- `viz/src/components/shared/PartySelector.tsx` — third "Current parties" toggle group + dashed chips.
- `viz/src/components/house/IdeologicalConstellation.tsx` — render current-party nodes + ellipses dashed.
- `viz/src/tabs/CompareTab.tsx` — merge current-party lookups, ordering, wire the selector group, pass current parties to the constellation, render the distance card.

---

## Task 1: Pipeline — `current_party_stats.csv` + correctness gate

**Files:**
- Create: `pipeline/build_current_party_profiles.py`
- Reads: `CCES24_Common_OUTPUT_vv_topost_final (2).dta`, `data/processed/typology_cluster_assignments.csv`, `data/outputs/profiles/cluster_stats.csv`
- Writes: `data/outputs/profiles/current_party_stats.csv`

**Interfaces:**
- Produces: `current_party_stats.csv` with columns `variable,domain,type,stat_label,question,overall,DEM,IND,REP` — one row per row in `cluster_stats.csv`, same order.
- The gate function `check_overall(recomputed_overall: float, stored_overall: float) -> bool` (tolerance 0.3 pp).

The recoder is **value-label-driven and generic**, with a small per-variable override table. For each `cluster_stats.csv` row it computes the DEM/IND/REP weighted statistic that matches the row's `type` + `stat_label`, then recomputes `overall` (all substantive respondents) and asserts it equals the stored `overall`. Any mismatch is printed and fails the build; the fix is to add the offending variable to the override table.

- [ ] **Step 1: Scaffold — load, align, group by pid3**

Create `pipeline/build_current_party_profiles.py`:

```python
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
import json
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


def load_aligned():
    """Return (dc, pid, w, reader) — the listwise sample row-aligned to typo, plus pid3 & weight."""
    reader = pd.io.stata.StataReader(str(DTA))
    df = pd.read_stata(DTA, convert_categoricals=False)
    mask = df[ANCHOR + ['commonpostweight']].notna().all(axis=1)
    dc = df[mask].reset_index(drop=True)
    typo = pd.read_csv(TYPO)
    assert len(dc) == len(typo), f"row mismatch {len(dc)} vs {len(typo)}"
    pid = pd.to_numeric(typo['pid3'], errors='coerce').values
    w = dc['commonpostweight'].values.astype(float)
    return dc, pid, w, reader
```

- [ ] **Step 2: Add the weighted-stat helpers + value-label recoder**

Append:

```python
def masks(pid):
    """pid3 group boolean masks for DEM/IND/REP + the all-substantive base."""
    return {"DEM": pid == 1, "REP": pid == 2, "IND": pid == 3}


def wmean(vals, w, m):
    v = vals[m]; ww = w[m]; ok = ~np.isnan(v)
    return round(float((ww[ok] * v[ok]).sum() / ww[ok].sum()), 4) if ok.any() and ww[ok].sum() > 0 else np.nan


def wshare(binvals, w, m):
    """Weighted % where binvals==1 (0/1/NaN vector)."""
    return round(100.0 * wmean(binvals, w, m), 4) if not np.isnan(wmean(binvals, w, m)) else np.nan


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
```

The generic recoder maps a `(type, stat_label)` pair to a 0/1 vector (for share rows) or a numeric vector (for mean/continuous rows), using the raw variable's value labels. Add:

```python
# Per-variable recode overrides (documented in efa_update.py / add_compare_items.py).
# raw code adjustments applied BEFORE any stat is computed.
REV_BINARY = {"CC24_341c","CC24_341d","CC24_323a","CC24_323d","CC24_321e","CC24_340b","CC24_340c"}

def raw_numeric(dc, var):
    """Raw numeric column with documented pre-recodes applied (EFA-consistent)."""
    x = dc[var].values.astype(float)
    if var in ("CC24_423", "CC24_424"):
        x = np.where(x == 8, 2.0, x)           # "Not sure" -> midpoint
    if var == "ideo5":
        x = np.where(x == 6, np.nan, x)         # "Not sure" -> NaN
    if var == "CC24_325":
        x = 40.0 - x                             # weeks -> restrictiveness
    return x
```

- [ ] **Step 3: Write the row dispatcher over cluster_stats.csv**

Append the main aggregation. For each stats row, resolve the underlying raw variable, compute the DEM/IND/REP + recomputed-overall values by dispatching on `type`, and record. `stat_label` selects which value-label category a `*_dist` row measures. `binary`/`binary_agree` are `% Supporting`/`% Agreeing`: `raw==1 → 1`, `raw==2 → 0` (flipped for `REV_BINARY`). `likert5`/`ordinal`/`approval4`/`trust` mean rows are weighted means of the numeric code. `continuous` rows are weighted `Median`/`Q25`/`Q75`.

```python
def substantive_codes(reader, var):
    """[(code, label)] excluding non-substantive (9/98/99 + labels like 'skipped'/'not sure')."""
    setname = dict(zip(reader._varlist, reader._lbllist))
    labs = reader.value_labels().get(setname.get(var, ''), {})
    DROP = ('skipped','not asked','not sure',"don't know",'dk','refused')
    out = []
    for c in sorted(int(k) for k in labs.keys()):
        t = str(labs[c]).strip().lower()
        if any(d in t for d in DROP) or c in (9, 98, 99):
            continue
        out.append((c, str(labs[c])))
    return out


def compute_row(dc, reader, w, grp, row):
    """Return {'overall':x,'DEM':..,'IND':..,'REP':..} for one cluster_stats row, or None to skip."""
    var, typ, lbl = row['variable'], row['type'], row['stat_label']
    ALL = np.ones(len(dc), bool)
    def out(vec_or_fn):
        r = {'overall': vec_or_fn(ALL)}
        for code, m in grp.items():
            r[code] = vec_or_fn(m)
        return r
    # share rows -> 0/1 vector
    if typ in ('binary', 'binary_agree'):
        x = raw_numeric(dc, var)
        one = 0.0 if var in REV_BINARY else 1.0
        b = np.where(x == 1, (0.0 if one == 0.0 else 1.0), np.where(x == 2, (1.0 if one == 0.0 else 0.0), np.nan))
        return out(lambda m: wshare(b, w, m))
    if typ.endswith('_dist'):
        if var not in dc.columns:
            return None
        codes = substantive_codes(reader, var)
        # Match this row's stat_label ("% <label>") to a value-label category.
        target = lbl.replace('%', '').strip().lower()
        sel = [c for c, l in codes if l.strip().lower() == target]
        if not sel:
            return None            # label mismatch -> leave to override table / skip
        x = dc[var].values.astype(float)
        valid = np.isin(x, [c for c, _ in codes])
        b = np.where(np.isin(x, sel) & valid, 1.0, np.where(valid, 0.0, np.nan))
        return out(lambda m: wshare(b, w, m))
    if typ in ('likert5', 'ordinal', 'approval4', 'trust'):
        x = raw_numeric(dc, var)
        return out(lambda m: wmean(x, w, m))
    if typ == 'continuous':
        x = raw_numeric(dc, var)
        q = {'Median': 0.5, 'Q25': 0.25, 'Q75': 0.75}.get(lbl)
        if q is None:
            return None
        return out(lambda m: wpctile(x, w, m, q))
    return None
```

- [ ] **Step 4: Assemble, run the gate, write the CSV**

Append `main()` and entrypoint:

```python
def main():
    dc, pid, w, reader = load_aligned()
    grp = masks(pid)
    stats = pd.read_csv(STATS)
    out_rows, gate_fail, skipped = [], [], []
    for _, row in stats.iterrows():
        res = compute_row(dc, reader, w, grp, row)
        rec = {k: row[k] for k in ('variable', 'domain', 'type', 'stat_label', 'question')}
        if res is None:
            skipped.append(row['variable'] + ' / ' + str(row['stat_label']))
            rec.update({'overall': row.get('overall'), 'DEM': np.nan, 'IND': np.nan, 'REP': np.nan})
        else:
            stored = float(row['overall']) if str(row.get('overall')) not in ('', 'nan') else np.nan
            if not np.isnan(res['overall']) and not np.isnan(stored) and abs(res['overall'] - stored) > GATE_TOL:
                gate_fail.append((row['variable'], row['stat_label'], res['overall'], stored))
            rec.update({'overall': row['overall'], 'DEM': res['DEM'], 'IND': res['IND'], 'REP': res['REP']})
        out_rows.append(rec)

    if skipped:
        print(f"SKIPPED {len(skipped)} rows (no recode / label mismatch):")
        for s in skipped[:40]:
            print("   ", s)
    if gate_fail:
        print(f"\nGATE FAILURES ({len(gate_fail)}) — recomputed overall != stored:")
        for v, l, got, exp in gate_fail[:40]:
            print(f"    {v} / {l}: got {got} expected {exp}")
        raise SystemExit("Correctness gate failed — fix recode/override for the vars above.")

    cols = ['variable', 'domain', 'type', 'stat_label', 'question', 'overall', 'DEM', 'IND', 'REP']
    pd.DataFrame(out_rows)[cols].to_csv(OUT_STATS, index=False)
    print(f"\nwrote {OUT_STATS.relative_to(ROOT)} — {len(out_rows)} rows, {len(skipped)} skipped, gate OK")


if __name__ == '__main__':
    main()
```

- [ ] **Step 5: Run the gate and drive skips/failures to zero-material**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV" && python3 pipeline/build_current_party_profiles.py`

Expected on first run: it either passes, or prints GATE FAILURES / SKIPPED for a handful of variables with nonstandard coding. For each failure, add the fix to `raw_numeric` (pre-recode) or add a value-label alias so `stat_label` matches. Re-run until: **no GATE FAILURES**, and every SKIPPED row is a variable that is genuinely covered elsewhere (a `*_dist` component already surfaced via `distributions.json`/`clusterIntensity.json`) — log those explicitly so nothing is silently dropped. The `overall` column is copied from `cluster_stats.csv` so skipped rows still carry a US baseline; only their DEM/IND/REP are blank.

Expected final line: `wrote data/outputs/profiles/current_party_stats.csv — <N> rows, <k> skipped, gate OK`

- [ ] **Step 6: Commit**

```bash
cd "/Users/bdecker/Local Projects/Personal/STV"
git add pipeline/build_current_party_profiles.py data/outputs/profiles/current_party_stats.csv
git commit -m "Pipeline: recompute cluster_stats variables by pid3 (current-party stats) with overall-match gate"
```

---

## Task 2: Pipeline — continuous ranges + factor spreads by pid3

**Files:**
- Modify: `pipeline/build_current_party_profiles.py`
- Writes: `data/outputs/profiles/current_party_continuous.csv`, `viz/src/data/currentPartySpreads.json`

**Interfaces:**
- Consumes: `load_aligned()`, `masks()`, `wpctile()` from Task 1.
- Produces:
  - `current_party_continuous.csv` — columns `var,unit,party,p10,q25,median,q75,p90` for `var ∈ {age, income_k, abortion_weeks}`, `party ∈ {DEM,IND,REP}` (matches the schema `build_distributions()` reads from `distributions_continuous.csv`).
  - `currentPartySpreads.json` — list of `{party, n, mean_F1..mean_F5, sd_F1..sd_F5, cov_F1_F2..cov_F4_F5}` for DEM/IND/REP (same shape as `clusterSpreads.json`).

- [ ] **Step 1: Add continuous-range computation**

Append to `pipeline/build_current_party_profiles.py`:

```python
OUT_CONT = ROOT / "data" / "outputs" / "profiles" / "current_party_continuous.csv"

# (out_var, unit, raw_col, transform)
CONT_VARS = [
    ("age", "yrs", "birthyr", lambda x: 2024.0 - x),
    ("abortion_weeks", "wks", "CC24_325", lambda x: x),   # raw weeks (NOT the 40- recode)
    ("income_k", "$k", "faminc_new", None),               # handled via bracket midpoints below
]
FAMINC_MID = {1:5,2:15,3:25,4:35,5:45,6:55,7:65,8:75,9:90,10:110,11:135,12:175,13:225,14:300,15:425,16:600}

def build_continuous(dc, pid, w):
    grp = masks(pid)
    rows = []
    for out_var, unit, col, tf in CONT_VARS:
        raw = dc[col].values.astype(float)
        if out_var == "income_k":
            vals = np.array([FAMINC_MID.get(int(v), np.nan) if not np.isnan(v) else np.nan for v in raw])
        else:
            vals = tf(raw)
            vals = np.where(vals > 130, np.nan, vals) if out_var == "age" else vals
        for code, m in grp.items():
            rows.append({"var": out_var, "unit": unit, "party": code,
                "p10": wpctile(vals, w, m, .10), "q25": wpctile(vals, w, m, .25),
                "median": wpctile(vals, w, m, .50), "q75": wpctile(vals, w, m, .75),
                "p90": wpctile(vals, w, m, .90)})
    pd.DataFrame(rows).to_csv(OUT_CONT, index=False)
    print(f"wrote {OUT_CONT.relative_to(ROOT)} — {len(rows)} rows")
```

> **Note:** confirm `faminc_new` bracket midpoints against the existing `distributions_continuous.csv` `income_k` medians for the 10 clusters — if `build_distributions` already used a different mapping, reuse that exact one (grep `FAMINC` / `faminc` in `pipeline/add_compare_items.py`). The `income_k` median for each pid3 group should land plausibly between the cluster extremes.

- [ ] **Step 2: Add factor-spread computation**

Append:

```python
OUT_SPREADS = ROOT / "viz" / "src" / "data" / "currentPartySpreads.json"
FCOLS = {"F1":"FS_F1","F2":"FS_F2","F3":"FS_F3","F4":"FS_F4","F5":"FS_F5"}

def build_spreads(pid):
    typo = pd.read_csv(TYPO)
    w = typo['commonpostweight'].values.astype(float)
    fmap = dict(FCOLS)
    if "FS_F4" not in typo.columns:
        fmap["F4"], fmap["F5"] = "FS_F4_resid", "FS_F5_resid"
    F = {k: pd.to_numeric(typo[v], errors='coerce').values for k, v in fmap.items()}
    out = []
    for code, sel in {"DEM": pid == 1, "REP": pid == 2, "IND": pid == 3}.items():
        ww = w[sel]; ws = ww.sum()
        rec = {"party": code, "n": int(sel.sum())}
        means = {}
        for k in ("F1","F2","F3","F4","F5"):
            x = F[k][sel]; mu = float((ww * x).sum() / ws); means[k] = mu
            rec[f"mean_{k}"] = round(mu, 4)
            rec[f"sd_{k}"] = round(float(np.sqrt((ww * (x - mu) ** 2).sum() / ws)), 4)
        ks = ("F1","F2","F3","F4","F5")
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                a, b = ks[i], ks[j]
                rec[f"cov_{a}_{b}"] = round(float((ww * (F[a][sel]-means[a]) * (F[b][sel]-means[b])).sum() / ws), 4)
        out.append(rec)
    OUT_SPREADS.write_text(json.dumps(out, indent=2))
    print(f"wrote {OUT_SPREADS.relative_to(ROOT)} — {len(out)} parties")
```

- [ ] **Step 3: Call both from `main()`**

In `main()`, after the CSV is written, add:

```python
    build_continuous(dc, pid, w)
    build_spreads(pid)
```

- [ ] **Step 4: Run and spot-check**

Run: `python3 pipeline/build_current_party_profiles.py`

Verify the DEM/REP factor separation is real (DEM and REP should sit far apart on F5, the strongest discriminator; IND between). Run:

```bash
python3 -c "import json; d={r['party']:r for r in json.load(open('viz/src/data/currentPartySpreads.json'))}; print({k:round(d[k]['mean_F5'],2) for k in ('DEM','IND','REP')})"
```

Expected: `mean_F5` for DEM and REP have opposite signs and IND is between them (magnitude sanity, not an exact value).

- [ ] **Step 5: Commit**

```bash
git add pipeline/build_current_party_profiles.py data/outputs/profiles/current_party_continuous.csv viz/src/data/currentPartySpreads.json
git commit -m "Pipeline: current-party continuous ranges + factor spreads by pid3"
```

---

## Task 3: Pipeline — inject DEM/IND/REP into `clusterIntensity.json`

**Files:**
- Modify: `pipeline/compute_intensity.py`
- Writes: `viz/src/data/clusterIntensity.json`

**Interfaces:**
- Produces: each item in `clusterIntensity.json`'s `items[]` gains `DEM`/`IND`/`REP` keys in its `parties` dict (same per-category share arrays as clusters, same reversal for `diverging`).

- [ ] **Step 1: Read pid3 alongside cluster labels**

In `pipeline/compute_intensity.py`, in `main()`, right after `cl = typo['cluster'].values`, add:

```python
    pid = pd.to_numeric(typo['pid3'], errors='coerce').values
    PID_GROUPS = {"DEM": pid == 1, "REP": pid == 2, "IND": pid == 3}
```

- [ ] **Step 2: Add current-party shares to each item's `parties`**

In the item loop, where `parties = {CLUSTER_TO_PARTY[k]: shares(var, codes, cl == k) for k in range(10)}` is built, append:

```python
        for code, m in PID_GROUPS.items():
            parties[code] = shares(var, codes, m)
```

This runs before the `if kind == 'diverging':` reversal block, so current parties are reversed identically to clusters (the reversal already maps over all of `parties`).

- [ ] **Step 3: Run and verify**

Run: `python3 pipeline/compute_intensity.py`

Verify: `python3 -c "import json; it=json.load(open('viz/src/data/clusterIntensity.json'))['items'][0]; print(sorted(it['parties'])); assert {'DEM','IND','REP'} <= set(it['parties'])"`

Expected: prints a code list including `DEM`, `IND`, `REP`; no assertion error.

- [ ] **Step 4: Commit**

```bash
git add pipeline/compute_intensity.py viz/src/data/clusterIntensity.json
git commit -m "Pipeline: add current parties (DEM/IND/REP) to clusterIntensity"
```

---

## Task 4: Pipeline — `currentPartyProfiles.json` + distributions injection

**Files:**
- Modify: `viz/scripts/prepare_data.py`
- Writes: `viz/src/data/currentPartyProfiles.json`, `viz/src/data/distributions.json`

**Interfaces:**
- Consumes: `data/outputs/profiles/current_party_stats.csv`, `data/outputs/profiles/current_party_continuous.csv` (Tasks 1–2); existing `_extract_policy_vars`, `collect_cluster_variables`, `read_csv`, `write_json`, `PARTY_NAMES`.
- Produces:
  - `currentPartyProfiles.json` — a list of 3 objects shaped like `ClusterProfile`: `{id, party, partyName, variables, F1..F5, z_F1..z_F5, pctile_F1..pctile_F5}` for DEM/IND/REP.
  - `distributions.json` `parties` gains `DEM`/`IND`/`REP` entries (range + composition/diverging/heatmap items).

- [ ] **Step 1: Add `build_current_party_profiles()` to `prepare_data.py`**

Add near `build_cluster_profiles` (after line ~1267):

```python
def build_current_party_profiles(out_name="currentPartyProfiles.json"):
    """Democratic/Independent/Republican (pid3) full profiles, shaped like ClusterProfile,
    from current_party_stats.csv (columns DEM/IND/REP) + factor means from the typology file."""
    cp_path = OUTPUTS / "profiles" / "current_party_stats.csv"
    rows = read_csv(cp_path)  # raises FileNotFoundError -> _run() skips, keeping committed JSON
    CODES = ["DEM", "IND", "REP"]
    NAMES = {"DEM": "Democratic", "IND": "Independent", "REP": "Republican"}
    COVERED_BY_DIST = {  # same set dropped in build_cluster_profiles
        'relig_protestant','relig_catholic','relig_jewish','relig_muslim','relig_none','relig_other',
        'vote16_clinton','vote16_trump','vote16_third','vote16_dnv',
        'vote20_biden','vote20_trump','vote20_third','vote20_dnv',
        'vote24_harris','vote24_trump','vote24_third','vote24_dnv'}
    profiles = {}
    for code in CODES:
        vars_ = _extract_policy_vars(rows, lambda r, c=code: (float(r[c]) if str(r.get(c)) not in ('', 'nan') else None))
        vars_ = {k: v for k, v in vars_.items() if k not in COVERED_BY_DIST}
        profiles[code] = {"id": code, "party": code, "partyName": NAMES[code], "variables": vars_}

    # Factor scores per pid3: weighted FS mean + z/pctile against the SAME pop mean/sd
    # build_cluster_profiles uses.
    typo_path = Path(__file__).parent.parent.parent / "data" / "processed" / "typology_cluster_assignments.csv"
    typo = read_csv(str(typo_path))
    fmap = {"F1":"FS_F1","F2":"FS_F2","F3":"FS_F3","F4":"FS_F4","F5":"FS_F5"}
    if "FS_F4" not in typo[0]:
        fmap["F4"], fmap["F5"] = "FS_F4_resid", "FS_F5_resid"
    W = [float(r["commonpostweight"]) for r in typo]
    pid = [ (int(float(r["pid3"])) if r.get("pid3") not in (None, '', 'nan') else 0) for r in typo ]
    pidcode = {1: "DEM", 2: "REP", 3: "IND"}
    N = len(typo)
    for fk, col in fmap.items():
        vals = [float(typo[i].get(col) or 0) for i in range(N)]
        mean = sum(vals) / N
        sd = (sum((v - mean) ** 2 for v in vals) / N) ** 0.5
        for code in CODES:
            idx = [i for i in range(N) if pidcode.get(pid[i]) == code]
            ws = sum(W[i] for i in idx)
            centroid = sum(vals[i] * W[i] for i in idx) / ws if ws > 0 else 0.0
            below = sum(1 for v in vals if v < centroid)
            profiles[code][fk] = round(centroid, 4)
            profiles[code][f"z_{fk}"] = round(centroid / sd, 2) if sd > 0 else 0
            profiles[code][f"pctile_{fk}"] = round(below / N * 100, 1)
    write_json([profiles[c] for c in CODES], out_name)
```

- [ ] **Step 2: Extend `build_distributions()` for DEM/IND/REP**

In `build_distributions()` (line ~3315): after `CODES = [...]`, add current codes and load the current-party stats index. Replace the `CODES` line and add a current-party index right after `index = {(r["variable"], ...)}`:

```python
    CUR = ["DEM", "IND", "REP"]
    for c in CUR:
        parties[c] = {}
```

After `index = {(r["variable"], r.get("stat_label", "")): r for r in stats}` add:

```python
    cp_rows = []
    cp_path = OUTPUTS / "profiles" / "current_party_stats.csv"
    if cp_path.exists():
        cp_rows = read_csv(cp_path)
    cp_index = {(r["variable"], r.get("stat_label", "")): r for r in cp_rows}

    def seg_val_col(sources, col, idx):
        tot = 0.0
        for v, lbl in sources:
            r = idx.get((v, lbl))
            if r:
                try:
                    tot += float(r.get(col) or 0)
                except (ValueError, TypeError):
                    pass
        return round(tot, 1)
```

In the continuous reader loop, current-party rows come from `current_party_continuous.csv`; add after the `distributions_continuous.csv` loop:

```python
    cpc = OUTPUTS / "profiles" / "current_party_continuous.csv"
    if cpc.exists():
        for r in read_csv(cpc):
            var = r["var"]
            if var == "income_k":
                income_med[r["party"]] = float(r["median"]); continue
            if var not in CONT_META:
                continue
            parties[r["party"]][var] = {k: float(r[k]) for k in ("p10","q25","median","q75","p90")}
```

In the `for key, viz, dom, q, order, segs, colors, pivot in DIST:` loop, after the existing `for k, code in enumerate(CODES):` block, add:

```python
        for code in CUR:
            parties[code][key] = {"pcts": [seg_val_col(src, code, cp_index) for _, src in segs]}
            if key == "income":
                parties[code][key]["value"] = income_med.get(code)
```

- [ ] **Step 3: Wire into `__main__`**

In the `for fn in (...)` tuple (line ~3532), add `build_current_party_profiles,` immediately after `build_cluster_profiles,`. (`build_distributions` is already last in the tuple and now emits current parties.)

- [ ] **Step 4: Run and verify**

Run: `cd viz && python3 scripts/prepare_data.py`

Verify:

```bash
python3 -c "import json; p=json.load(open('viz/src/data/currentPartyProfiles.json')); print([x['party'] for x in p], 'z_F5=', {x['party']:x['z_F5'] for x in p})"
python3 -c "import json; d=json.load(open('viz/src/data/distributions.json')); assert {'DEM','IND','REP'} <= set(d['parties']); print('dist DEM keys:', len(d['parties']['DEM']))"
```

Expected: three profiles `['DEM','IND','REP']` with opposite-signed `z_F5` for DEM vs REP; distributions `parties` contains DEM/IND/REP with a non-empty item set.

- [ ] **Step 5: Commit**

```bash
git add viz/scripts/prepare_data.py viz/src/data/currentPartyProfiles.json viz/src/data/distributions.json
git commit -m "Pipeline: emit currentPartyProfiles + inject current parties into distributions"
```

---

## Task 5: Viz — constants for current parties

**Files:**
- Modify: `viz/src/constants/parties.ts`

**Interfaces:**
- Produces: `CURRENT_PARTIES: readonly ['DEM','IND','REP']`; `isCurrentParty(code: string): boolean`; `PARTY_NAMES`/`PARTY_COLORS` extended with DEM/IND/REP.

- [ ] **Step 1: Add colors, names, and helpers**

In `viz/src/constants/parties.ts`, add to `PARTY_COLORS` (after the `OAO` entry, before the closing `}`):

```typescript
  // Current (real) parties — muted D/R/I, rendered dashed to read as "status quo".
  DEM: '#5b7fa6',
  IND: '#8a8f98',
  REP: '#a66b6b',
```

Add to `PARTY_NAMES`:

```typescript
  DEM: 'Democratic',
  IND: 'Independent',
  REP: 'Republican',
```

After the `F5_ORDER` / `partyOrder` block, add:

```typescript
// Today's real parties (pid3), shown after the US baseline in the Parties tab.
export const CURRENT_PARTIES = ['DEM', 'IND', 'REP'] as const;
const CURRENT_SET = new Set<string>(CURRENT_PARTIES);
/** True for the real-party codes (Democratic/Independent/Republican), which render dashed. */
export function isCurrentParty(code: string): boolean {
  return CURRENT_SET.has(code);
}
```

- [ ] **Step 2: Type-check**

Run: `cd viz && npx tsc -b --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add viz/src/constants/parties.ts
git commit -m "Viz: current-party codes, names, muted colors, isCurrentParty helper"
```

---

## Task 6: Viz — factor-distance library (TDD)

**Files:**
- Create: `viz/src/lib/partyDistance.ts`
- Test: `viz/src/lib/partyDistance.test.ts`

**Interfaces:**
- Produces:
  - `DISTANCE_FACTORS = ['F1','F2','F4','F5'] as const`
  - `factorDistance(a: Record<string, number>, b: Record<string, number>, eta: Record<string, number>): number` — η²-weighted RMS of z-score differences over `DISTANCE_FACTORS`, returned in σ. `a`/`b` are keyed `z_F1`… (uses `z_${f}`).
  - `policyDivergence(perItemDistances: number[]): number` — mean of per-item distances (0–100), `0` if empty.

- [ ] **Step 1: Write the failing test**

Create `viz/src/lib/partyDistance.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { factorDistance, policyDivergence, DISTANCE_FACTORS } from './partyDistance'

const eta = { F1: 0.25, F2: 0.20, F3: 0.10, F4: 0.15, F5: 0.40 }

describe('factorDistance', () => {
  it('is zero for identical vectors', () => {
    const a = { z_F1: 1, z_F2: -1, z_F4: 0.5, z_F5: 2 }
    expect(factorDistance(a, a, eta)).toBe(0)
  })
  it('ignores F3 (not in DISTANCE_FACTORS)', () => {
    const a = { z_F1: 0, z_F2: 0, z_F3: 0, z_F4: 0, z_F5: 0 }
    const b = { z_F1: 0, z_F2: 0, z_F3: 99, z_F4: 0, z_F5: 0 }
    expect(factorDistance(a, b, eta)).toBe(0)
    expect(DISTANCE_FACTORS).not.toContain('F3')
  })
  it('returns a weighted RMS in sigma units', () => {
    const a = { z_F1: 0, z_F2: 0, z_F4: 0, z_F5: 0 }
    const b = { z_F1: 0, z_F2: 0, z_F4: 0, z_F5: 1 }
    // only F5 differs by 1sigma; weighted RMS = sqrt(w5*1 / (w1+w2+w4+w5))
    const w = eta.F5 / (eta.F1 + eta.F2 + eta.F4 + eta.F5)
    expect(factorDistance(a, b, eta)).toBeCloseTo(Math.sqrt(w), 6)
  })
})

describe('policyDivergence', () => {
  it('averages per-item distances', () => {
    expect(policyDivergence([10, 20, 30])).toBeCloseTo(20, 6)
  })
  it('is zero for no items', () => {
    expect(policyDivergence([])).toBe(0)
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd viz && npx vitest run src/lib/partyDistance.test.ts`
Expected: FAIL — cannot resolve `./partyDistance`.

- [ ] **Step 3: Implement**

Create `viz/src/lib/partyDistance.ts`:

```typescript
// Distance between a formulated party and a current party, in the typology's own
// coordinate systems. Factor distance is the primary "how different" number; policy
// divergence is the secondary, per-item average.

export const DISTANCE_FACTORS = ['F1', 'F2', 'F4', 'F5'] as const;
export type DistanceFactor = typeof DISTANCE_FACTORS[number];

/** η²-weighted RMS of z-score differences over DISTANCE_FACTORS, in σ.
 *  `a`/`b` carry `z_F1`…`z_F5`; `eta` carries per-factor discriminatory value. */
export function factorDistance(
  a: Record<string, number>,
  b: Record<string, number>,
  eta: Record<string, number>,
): number {
  let wsum = 0, acc = 0;
  for (const f of DISTANCE_FACTORS) {
    const w = eta[f] ?? 0;
    const d = (a[`z_${f}`] ?? 0) - (b[`z_${f}`] ?? 0);
    wsum += w;
    acc += w * d * d;
  }
  return wsum > 0 ? Math.sqrt(acc / wsum) : 0;
}

/** Mean of per-item policy distances (each 0–100); 0 when there are no shared items. */
export function policyDivergence(perItemDistances: number[]): number {
  if (perItemDistances.length === 0) return 0;
  return perItemDistances.reduce((s, d) => s + d, 0) / perItemDistances.length;
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd viz && npx vitest run src/lib/partyDistance.test.ts`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add viz/src/lib/partyDistance.ts viz/src/lib/partyDistance.test.ts
git commit -m "Viz: factor-distance + policy-divergence helpers (tested)"
```

---

## Task 7: Viz — PartySelector "Current parties" group

**Files:**
- Modify: `viz/src/components/shared/PartySelector.tsx`

**Interfaces:**
- Consumes: `isCurrentParty` from `../../constants/parties`.
- Produces: `PartySelector` gains an optional prop `currentParties?: { code: string; label: string }[]`, rendered as a second popover ("Current parties") mirroring the crossover one; current-party chips render dashed.

- [ ] **Step 1: Add the prop and dashed chip treatment**

In `viz/src/components/shared/PartySelector.tsx`:

Update the import: `import { PARTY_NAMES, getBlendColor, getContrastText, isCurrentParty } from '../../constants/parties';`

Add to `Props`:

```typescript
  currentParties?: { code: string; label: string }[]; // today's real parties (dashed)
```

In the `chip` helper, make the border dashed for current parties — change the `<button>`'s `style` to:

```typescript
        style={{ borderColor: c, color: on ? getContrastText(c) : c,
                 backgroundColor: on ? c : 'transparent',
                 borderStyle: isCurrentParty(code) ? 'dashed' : 'solid' }}
```

- [ ] **Step 2: Render the Current-parties popover**

Add `currentParties` to the destructured props: `export function PartySelector({ selected, onToggle, baseParties, crossover, currentParties }: Props) {`

Add a second `useState`: `const [openCur, setOpenCur] = useState(false);`

Immediately after the crossover popover block (the `{crossover && crossover.length > 0 && (…)}`), add a parallel block:

```tsx
      {currentParties && currentParties.length > 0 && (
        <div className="relative">
          <button onClick={() => setOpenCur(o => !o)}
            className="text-[11px] font-medium text-muted-foreground hover:text-foreground border border-dashed border-border rounded-full px-2 py-1">
            {openCur ? '▾' : '＋'} Current parties
            {(() => { const n = currentParties.filter(o => selected.includes(o.code)).length; return n ? ` · ${n}` : ` (${currentParties.length})`; })()}
          </button>
          {openCur && (
            <>
              <div className="fixed inset-0 z-30" onClick={() => setOpenCur(false)} aria-hidden="true" />
              <div className="absolute left-0 mt-1 z-40 w-[min(90vw,360px)] flex flex-wrap gap-1 rounded-md border border-border bg-card shadow-lg p-2">
                {currentParties.map(o => chip(o.code, o.label))}
              </div>
            </>
          )}
        </div>
      )}
      {!openCur && currentParties?.filter(o => selected.includes(o.code)).map(o => chip(o.code, o.label))}
```

- [ ] **Step 3: Type-check**

Run: `cd viz && npx tsc -b --noEmit`
Expected: no errors (prop is optional; existing call sites unaffected).

- [ ] **Step 4: Commit**

```bash
git add viz/src/components/shared/PartySelector.tsx
git commit -m "Viz: PartySelector current-parties popover group (dashed chips)"
```

---

## Task 8: Viz — IdeologicalConstellation renders current parties

**Files:**
- Modify: `viz/src/components/house/IdeologicalConstellation.tsx`

**Interfaces:**
- Consumes: `isCurrentParty` from `../../constants/parties`; `ConstellationNode` (has `id,label,seats,F1..F5`); `ClusterSpread` (`{party, [k]:string|number}`).
- Produces: current-party nodes/ellipses render with a dashed stroke. No prop shape change — current parties arrive via the existing `nodes` + `clusterSpreads` arrays (CompareTab passes them merged in Task 9).

- [ ] **Step 1: Dash the stroke for current-party ellipses and nodes**

In `viz/src/components/house/IdeologicalConstellation.tsx`, add the import: `import { isCurrentParty } from '../../constants/parties';` (adjust relative depth if needed — from `components/house/` it is `'../../constants/parties'`).

Find the two ellipse-drawing blocks (`if (clusterSpreads && …)` near lines ~130 and ~297). For each ellipse `.attr('stroke', …)`, add a dash when the spread's `party` is a current party. In the loop `for (const cs of clusterSpreads)`, where the ellipse element is created, add:

```typescript
        if (isCurrentParty(String(cs.party))) ell.attr('stroke-dasharray', '4 3');
```

(Use the actual selection variable name the code assigns the ellipse to; if it is created inline without a variable, chain `.attr('stroke-dasharray', isCurrentParty(String(cs.party)) ? '4 3' : null)`.)

For the node circles, where `getStroke`/circle attributes are applied (line ~193 / node render ~383), add a dashed outline for current-party nodes:

```typescript
      .attr('stroke-dasharray', (n: ConstellationNode) => isCurrentParty(n.id) ? '3 2' : null)
```

- [ ] **Step 2: Verify build + visual smoke test**

Run: `cd viz && npx tsc -b --noEmit`
Expected: no errors.

Then follow the `run` skill to launch the app; on the Parties tab, once Task 9 wires the data, current-party ellipses/nodes appear dashed. (Pure-render change; no unit test.)

- [ ] **Step 3: Commit**

```bash
git add viz/src/components/house/IdeologicalConstellation.tsx
git commit -m "Viz: dashed constellation rendering for current parties"
```

---

## Task 9: Viz — CompareTab integration (lookups, selector, ordering, constellation)

**Files:**
- Modify: `viz/src/tabs/CompareTab.tsx`

**Interfaces:**
- Consumes: `currentPartyProfiles.json`, `currentPartySpreads.json`; `CURRENT_PARTIES`, `isCurrentParty` (constants); the DEM/IND/REP entries now present in `distributions.json` + `clusterIntensity.json`.
- Produces: DEM/IND/REP are fully selectable and render as columns in every section (in `orderedSelected`, current parties sort first in DEM→IND→REP order); the constellation shows their ellipses. Task 10 derives `selectedFormulated`/`selectedCurrent` from `orderedSelected`.

- [ ] **Step 1: Import current-party data and constants**

At the top of `viz/src/tabs/CompareTab.tsx`, add:

```typescript
import currentPartyProfilesData from '../data/currentPartyProfiles.json';
import currentPartySpreadsData from '../data/currentPartySpreads.json';
```

Extend the constants import to include `CURRENT_PARTIES, isCurrentParty` from `../constants/parties`.

Add a lookup near the top of the `CompareTab` function body:

```typescript
  const currentParties = currentPartyProfilesData as unknown as ClusterProfile[];
```

- [ ] **Step 2: Make `getVariables`/`getFactorScores` resolve current parties**

The module-level `getVariables` and `getFactorScores` take `(code, clusters, fdProfiles)`. Add current parties as a fallback lookup by extending both to check `currentPartyProfilesData` first. Update their bodies:

In `getVariables`, before the final `return {}`:

```typescript
  const cp = (currentPartyProfilesData as unknown as ClusterProfile[]).find(c => c.party === code);
  if (cp) return cp.variables as Record<string, { pct: number; question: string; domain: string }>;
```

In `getFactorScores`, before the final `return null`:

```typescript
  const cp = (currentPartyProfilesData as unknown as ClusterProfile[]).find(c => c.party === code);
  if (cp) return { F1: cp.F1, F2: cp.F2, F3: cp.F3, F4: cp.F4, F5: cp.F5 };
```

Add the import for the JSON at the top of the module (module scope, same file): `import currentPartyProfilesData from '../data/currentPartyProfiles.json';` (single import; Step 1's in-component alias can reference the same binding — keep one import).

- [ ] **Step 3: Wire the selector group + ordering**

Where `<PartySelector … />` is rendered, add the prop:

```tsx
            currentParties={CURRENT_PARTIES.map(code => ({ code, label: PARTY_NAMES[code] ?? code }))}
```

`orderedSelected` sorts by `F5_ORDER` index; current parties are not in `F5_ORDER` so `indexOf` returns -1 and they sort to the front — which is the desired "after US, before formulated" position (US is a separate baseline row/column, not in `selected`). To make the DEM→IND→REP order explicit, replace the `orderedSelected` comparator so current parties keep `CURRENT_PARTIES` order and sort before formulated parties:

```typescript
  const orderedSelected = useMemo(() => {
    const curIdx = (c: string) => (CURRENT_PARTIES as readonly string[]).indexOf(getPrimaryParty(c));
    return [...selected].sort((a, b) => {
      const ca = isCurrentParty(getPrimaryParty(a)), cb = isCurrentParty(getPrimaryParty(b));
      if (ca !== cb) return ca ? -1 : 1;                 // current parties first
      if (ca && cb) return curIdx(a) - curIdx(b);        // DEM -> IND -> REP
      return (F5_ORDER as readonly string[]).indexOf(getPrimaryParty(a)) -
             (F5_ORDER as readonly string[]).indexOf(getPrimaryParty(b));
    });
  }, [selected]);
```

- [ ] **Step 4: Add current parties to the constellation nodes + spreads**

Where `constellationNodes` is built (the `useMemo` returning `ConstellationNode[]`), append current-party nodes so their ellipses can render:

```typescript
      .concat(currentParties.map(c => ({
        id: c.party, label: c.party, seats: 0,
        F1: c.z_F1 ?? 0, F2: c.z_F2 ?? 0, F3: c.z_F3 ?? 0, F4: c.z_F4 ?? 0, F5: c.z_F5 ?? 0,
      })))
```

(Apply `.concat(...)` to the existing mapped array inside the `useMemo`.)

Where `<IdeologicalConstellation … clusterSpreads={clusterSpreads} … />` is rendered, merge in current-party spreads:

```tsx
        clusterSpreads={[...clusterSpreads, ...(currentPartySpreadsData as typeof clusterSpreads)]}
```

- [ ] **Step 5: Type-check + visual verification**

Run: `cd viz && npx tsc -b --noEmit`
Expected: no errors.

Then use the `run` skill: on the Parties tab, open "Current parties", select Democratic + Republican + a formulated party (e.g. PRG). Confirm: DEM/IND/REP appear as columns in factor bars, heatmaps, intensity, and distribution rows; the constellation shows dashed DEM/REP ellipses; divergence ◆ and signature marks populate for them.

- [ ] **Step 6: Commit**

```bash
git add viz/src/tabs/CompareTab.tsx
git commit -m "Viz: wire current parties into CompareTab (lookups, selector, ordering, constellation)"
```

---

## Task 10: Viz — "Distance from today's parties" card

**Files:**
- Create: `viz/src/components/parties/CurrentPartyDistance.tsx`
- Modify: `viz/src/tabs/CompareTab.tsx`

**Interfaces:**
- Consumes: `factorDistance`, `policyDivergence` from `../../lib/partyDistance`; `FACTOR_ETA` (η² map, already built in `CompareTab.tsx` from `factorLoadings.json`); `getBlendColor`, `PARTY_NAMES`, `isCurrentParty`.
- Produces: `CurrentPartyDistance` component rendering, for each selected formulated party, its factor distance (σ) and policy divergence to DEM/IND/REP with the nearest highlighted.

- [ ] **Step 1: Build the component**

Create `viz/src/components/parties/CurrentPartyDistance.tsx`:

```tsx
import { Card } from '@/components/ui/card';
import { factorDistance, policyDivergence } from '../../lib/partyDistance';
import { getBlendColor, PARTY_NAMES, CURRENT_PARTIES } from '../../constants/parties';

export interface DistanceInputs {
  /** z-score vectors keyed z_F1..z_F5, per party code (formulated + current). */
  zByCode: Record<string, Record<string, number>>;
  /** per-(formulated,current) list of shared per-item policy distances (0–100). */
  policyItems: Record<string, Record<string, number[]>>;
  /** η² per factor. */
  eta: Record<string, number>;
  /** selected formulated party codes, in display order. */
  formulated: string[];
}

export function CurrentPartyDistance({ zByCode, policyItems, eta, formulated }: DistanceInputs) {
  if (formulated.length === 0) return null;
  const curs = CURRENT_PARTIES.filter(c => zByCode[c]);
  if (curs.length === 0) return null;

  return (
    <Card className="overflow-hidden">
      <div className="px-4 py-3 border-b border-border/50 bg-muted">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">Distance from today's parties</span>
        <span className="text-xs text-muted-foreground ml-3">factor σ (η²-weighted) · policy divergence (avg per-item)</span>
      </div>
      <div className="divide-y divide-border/50">
        {formulated.map(code => {
          const rows = curs.map(cur => ({
            cur,
            fac: factorDistance(zByCode[code], zByCode[cur], eta),
            pol: policyDivergence(policyItems[code]?.[cur] ?? []),
          }));
          const nearest = rows.reduce((a, b) => (b.fac < a.fac ? b : a), rows[0]);
          return (
            <div key={code} className="px-4 py-2.5 flex items-center gap-3 flex-wrap">
              <span className="text-xs font-bold w-24 shrink-0" style={{ color: getBlendColor(code) }}>
                {PARTY_NAMES[code] ?? code}
              </span>
              <div className="flex flex-wrap gap-x-4 gap-y-1">
                {rows.map(r => (
                  <span key={r.cur}
                    className={`text-[11px] tabular-nums ${r.cur === nearest.cur ? 'font-semibold' : 'text-muted-foreground'}`}>
                    <span style={{ color: getBlendColor(r.cur) }}>{PARTY_NAMES[r.cur] ?? r.cur}</span>{' '}
                    {r.fac.toFixed(1)}σ / {Math.round(r.pol)}
                    {r.cur === nearest.cur && <span className="ml-1 text-amber-500">◀ nearest</span>}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
```

- [ ] **Step 2: Assemble inputs in CompareTab and render**

In `viz/src/tabs/CompareTab.tsx`, add the import: `import { CurrentPartyDistance } from '../components/parties/CurrentPartyDistance';`

Compute the distance inputs with a `useMemo` (place after `sectionVarMap`). `zByCode` pulls z-scores from `getFactorScores` via `rawToZ` for formulated parties and directly from `currentByCode[c].z_*` for current parties; `policyItems` reuses the tab's existing per-item distance (`itemSignature(...).distance` for scalar vars):

```typescript
  const selectedFormulated = useMemo(
    () => orderedSelected.filter(c => !isCurrentParty(getPrimaryParty(c))),
    [orderedSelected]);
  const selectedCurrent = useMemo(
    () => orderedSelected.filter(c => isCurrentParty(getPrimaryParty(c))),
    [orderedSelected]);

  const distanceInputs = useMemo(() => {
    const zByCode: Record<string, Record<string, number>> = {};
    // Same z definition for formulated AND current parties: raw factor score / POP_SD via
    // rawToZ. getFactorScores already resolves current parties (Task 9), so one path covers both.
    const addZ = (c: string) => {
      const fs = getFactorScores(c, clusters, fdProfiles);
      if (!fs) return;
      zByCode[c] = Object.fromEntries((['F1','F2','F3','F4','F5'] as const)
        .map(f => [`z_${f}`, rawToZ(fs[f], f)]));
    };
    selectedFormulated.forEach(addZ);
    selectedCurrent.forEach(addZ);

    const policyItems: Record<string, Record<string, number[]>> = {};
    for (const fcode of selectedFormulated) {
      policyItems[fcode] = {};
      for (const ccode of selectedCurrent) {
        const dists: number[] = [];
        for (const list of Object.values(sectionVarMap)) {
          for (const v of list) {
            if (v.pcts[fcode] === undefined || v.pcts[ccode] === undefined) continue;
            const df = itemSignature(v.key, fcode, v.pcts[fcode]!, v.overall ?? v.pcts[fcode]!, v.maxVal, sigFilter).distance;
            const dc = itemSignature(v.key, ccode, v.pcts[ccode]!, v.overall ?? v.pcts[ccode]!, v.maxVal, sigFilter).distance;
            dists.push(Math.abs(df - dc));
          }
        }
        policyItems[fcode][ccode] = dists;
      }
    }
    return { zByCode, policyItems };
  }, [selectedFormulated, selectedCurrent, sectionVarMap, clusters, fdProfiles, sigFilter]);
```

> **Note:** `itemSignature(...).distance` is each item's distance-from-US (0–100). The per-item formulated↔current policy distance is the absolute difference of their US-relative distances — a lightweight reuse of the existing metric. If a signed comparison reads better in review, switch to comparing raw `v.pcts` on the same 0–max scale; keep whichever the reviewer prefers, documented in one line.

Render the card right after the Factor Scores `</Card>` (before `{constellationCard}`):

```tsx
          <CurrentPartyDistance
            zByCode={distanceInputs.zByCode}
            policyItems={distanceInputs.policyItems}
            eta={FACTOR_ETA}
            formulated={selectedFormulated}
          />
```

- [ ] **Step 3: Type-check + full test run**

Run: `cd viz && npx tsc -b --noEmit && npx vitest run`
Expected: no type errors; all vitest suites pass (including `partyDistance.test.ts`).

- [ ] **Step 4: Visual verification**

Use the `run` skill: select Progressive + Nationalist + Democratic + Republican. Confirm the "Distance from today's parties" card shows PRG nearest to Democratic and NAT nearest to Republican, with both σ and divergence numbers, and the card hides when no formulated party is selected.

- [ ] **Step 5: Commit**

```bash
git add viz/src/components/parties/CurrentPartyDistance.tsx viz/src/tabs/CompareTab.tsx
git commit -m "Viz: 'Distance from today's parties' card (factor σ + policy divergence)"
```

---

## Final verification

- [ ] **Full pipeline regen is clean and idempotent**

Run: `python3 pipeline/build_current_party_profiles.py && python3 pipeline/compute_intensity.py && (cd viz && python3 scripts/prepare_data.py)`
Expected: gate OK; no tracebacks; `git diff --stat` shows only the four generated JSON/CSV artifacts changing.

- [ ] **Build passes**

Run: `cd viz && npm run build`
Expected: `tsc -b` + `vite build` succeed with no errors.

- [ ] **End-to-end visual pass** (via `run` skill)

On the Parties tab: current-party popover works; DEM/IND/REP render as dashed full columns everywhere; constellation shows dashed ellipses; distance card is correct and hides with no formulated selection; no candidate initials or `pid3` codes visible anywhere.
