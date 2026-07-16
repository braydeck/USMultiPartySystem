# AGENT_CONTEXT.md
## Full Technical Reference for AI Agents

> This document is written for Claude Code (and similar agents) to maintain complete
> working context across conversation sessions. Read this before touching any script.

---

## Absolute Paths (all hardcoded in `stv_config.py`)

```python
BASE_DIR        = Path("/Users/bdecker/Documents/STV")
DTA_PATH        = BASE_DIR / "2024 CES Base" / "CCES24_Common_OUTPUT_vv_topost_final.dta"
TYPOLOGY_PATH   = BASE_DIR / "Claude" / "data" / "typology_cluster_assignments.csv"
EFA_SCORES_PATH = BASE_DIR / "Claude" / "data" / "efa_factor_scores.csv"
OUTPUT_DIR      = BASE_DIR / "Claude" / "outputs" / "baseline"    # baseline STV run
SCENARIOS_ROOT  = BASE_DIR / "Claude" / "outputs"                 # parent of all scenarios
```

The **worktree** (where scripts live) is:
`/Users/bdecker/Documents/STV/.claude/worktrees/busy-ramanujan/`

The **source tree** (where data/outputs live) is:
`/Users/bdecker/Documents/STV/Claude/`

---

## Scripts and Their Roles

| Script | Role | Key outputs |
|--------|------|-------------|
| `stv_config.py` | Shared constants only — no logic | — |
| `stv_step1.py` | Load DTA + typology; build weighted ballots | in-memory |
| `stv_step2.py` | Apportion seats per district (Hamilton) | `district_apportionment.csv` |
| `stv_step3.py` | Run STV per district | `stv_results_by_district.csv` |
| `stv_step4.py` | Build transfer matrices from STV traces | `transfer_matrix_*.csv` |
| `stv_step5.py` | Build seat summary table | `stv_seat_summary.csv` |
| `stv_main.py` | Orchestrates steps 1–5; CLI `--steps` flag; passes `pre_dissolved=DISSOLVED_PARTIES` (baseline `[]`) | all of above + checkpoint parquet |
| `stv_scenarios.py` (archived) | *Scenario capability:* re-runs steps 3–5 with alternative `pre_dissolved` parties to model dissolving one or more parties. Now under `pipeline/archive/`; not the baseline. | `scenario_a/`, `scenario_b/`, `scenario_comparison.csv` |
| `stv_affinity.py` | 4 inter-party affinity measures | `affinity/*.csv` |
| `cluster_profile_viz.py` | Cluster demographic/policy HTML reports | `profiles/*.html`, `profiles/cluster_stats.csv` |

**Dependency graph:**
```
stv_config.py
    ↓
stv_step1 → stv_step2 → [district_apportionment.csv]
                 ↓
           stv_step3 → [stv_results_by_district.csv]   ← stv_affinity reads checkpoint
                 ↓                                        (does NOT need step3 in-memory)
           stv_step4 → [transfer_matrix_*.csv]
                 ↓
           stv_step5 → [stv_seat_summary.csv]

stv_scenarios.py (archived scenario capability) loads:
  - OUTPUT_DIR / district_apportionment.csv
  - OUTPUT_DIR / ballots_checkpoint.parquet
  - OUTPUT_DIR / stv_seat_summary.csv      (baseline, already computed)
  then calls run_all_districts() with an example pre_dissolved list, e.g. [7] or [7,2]
  writes to SCENARIOS_ROOT / "scenario_a" / and SCENARIOS_ROOT / "scenario_b" /
  NOTE: the baseline itself dissolves nothing (DISSOLVED_PARTIES = []); these are
        optional what-if runs, not the production model.
```

---

## Critical Data Join Pattern

`typology_cluster_assignments.csv` has **no `caseid`**. It aligns positionally with the DTA:

```python
import pyreadstat
meta = pyreadstat.read_dta(DTA_PATH, metadataonly=True)  # fast metadata probe

df_dta, _ = pyreadstat.read_dta(DTA_PATH, usecols=DTA_READ_COLS, apply_value_formats=False)
# DTA_READ_COLS = ["caseid","faminc_new","region","urbancity","commonpostweight"] + ITEMS_24

# Listwise deletion mask — must match exactly what produced the typology CSV
mask = df_dta[ITEMS_24 + ["commonpostweight"]].notna().all(axis=1)
# ITEMS_24 = ITEMS_25 minus "CC24_340a" (dropped in EFA update)

df_aux = df_dta.loc[mask, DTA_AUX_COLS].reset_index(drop=True)   # 45,707 rows
df_typo = pd.read_csv(TYPOLOGY_PATH)                               # 45,707 rows
df = pd.concat([df_typo, df_aux], axis=1)                         # positional alignment
```

**NEVER** join by position without applying the same listwise deletion mask — row counts will not match.

---

## Ballot Checkpoint (`ballots_checkpoint.parquet`)

Written by `stv_main.py` after step 1. Contains the full working dataset for STV.

**Shape:** 45,707 rows × many columns

**Key columns:**

| Column | Type | Description |
|--------|------|-------------|
| `ballot` | list[int] (stored) / np.int8 array (runtime) | Ranked party order; 10 elements (0–9) |
| `cluster` | int64 | Hard cluster assignment (argmax of prob_cluster_k) |
| `prob_cluster_0` … `prob_cluster_9` | float64 | Soft cluster probabilities (sum to 1) |
| `commonpostweight` | float64 | Survey post-stratification weight |
| `FS_F1` … `FS_F5_resid` | float64 | 5 EFA factor scores |
| `inputstate` | int64 | State FIPS code |
| `urbancity` | float64 | 1=City, 2=Suburb, 3=Town, 4=Rural |
| `region` | float64 | CES region code |
| `faminc_new` | float64 | Family income bracket (1–16, 97=refused) |

**Restore ballot arrays after loading parquet:**
```python
df = pd.read_parquet(CHECKPOINT_PATH)
df["ballot"] = df["ballot"].apply(lambda b: np.array(b, dtype=np.int8))
```

---

## Party / Cluster Reference

```python
PARTY_LABELS = {
    0: "Conservative",       # CON
    1: "Labor",              # LBR (older artifacts abbreviate this SD)
    2: "Solidarity",         # STY
    3: "Nationalist",        # NAT
    4: "Liberal",            # LIB
    5: "Populist",           # POP
    6: "Civic Union Party",  # CUP
    7: "OAO",                # Order & Opportunity Party (former "Blue Dogs") — active, wins ~15 party-line seats
    8: "DSA",                # DSA
    9: "Progressive",        # PRG
}
DISSOLVED_PARTIES = []    # baseline dissolves nothing; all 10 clusters are active parties
N_PARTIES = 10
PROB_COLS = [f"prob_cluster_{k}" for k in range(10)]
```

**Cluster ID → abbreviation mapping** (for display/labeling):
- C0 CON (Conservative), C1 LBR (Labor; older artifacts use SD), C2 STY (Solidarity), C3 NAT (Nationalist),
  C4 LIB (Liberal), C5 POP (Populist), C6 CUP (Civic Union Party), C7 OAO (Order & Opportunity),
  C8 DSA, C9 PRG (Progressive)

---

## Apportionment Logic (stv_step2.py)

- `POP_PER_SEAT = 380_000`
- Each state gets seats ∝ population (2020 Census); distributed across density tiers (Urban/Suburban/Rural) using `STATE_URBAN_PCT` lookup.
- Minimum 1 seat per state.
- Result: **180 districts**, **873 total seats**
- District IDs: `"{FIPS_abbr}_{tier}_d{n}"` e.g. `"CA_URBAN_d1"`

---

## STV Algorithm (stv_step3.py)

- Droop quota: `floor(total_votes / (seats + 1)) + 1`
- `pre_dissolved` parties are eliminated at position 0 before any rounds; their weighted votes transfer immediately to next-ranked active party. In the baseline `pre_dissolved` is empty, so all 10 parties compete.
- Each round: tally active votes → if any party meets quota, elect and redistribute surplus; else eliminate lowest-vote party and redistribute all their votes.
- Continues until all seats filled or no active candidates remain.
- `run_all_districts(df, apportionment, pre_dissolved=DISSOLVED_PARTIES)` → list of result dicts (baseline `DISSOLVED_PARTIES = []`; a scenario may pass e.g. `[7]` to dissolve OAO)

---

## Transfer Matrix Format (stv_step4.py)

`transfer_matrix_directed.csv` — **directed** (not symmetric):
- Row = eliminated party, Column = receiving party
- Values = global percentage of total weighted votes in the entire election
- Diagonal is 0; rows do NOT sum to 100 (global %, not row-normalized)

`transfer_matrix_10party.csv` — symmetric (average of directed + its transpose)

---

## Affinity Matrices (stv_affinity.py)

**STALE ARTIFACTS — regenerate.** The affinity CSVs currently on disk live in
`data/outputs/archive/affinity/` and are genuinely **9×9 with C7/OAO excluded**
(row/column order `[0,1,2,3,4,5,6,8,9]`). They predate OAO's reinstatement as a
full party. Since OAO is now active (`DISSOLVED_PARTIES = []`), these should be
regenerated as **10×10** including cluster 7. Do NOT treat the archived files as
current; the shapes below describe the stale artifacts, not the intended output.

**`second_choice_global_pct.csv`** — `w[A→B_2nd] / w_total * 100`
**`second_choice_row_pct.csv`** — `w[A→B_2nd] / w_A * 100` (row-normalized ≈ 100)
**`mean_rank_proximity.csv`** — symmetrized, 0=far, 1=close; computed from all ballot positions
**`factor_mahalanobis.csv`** — Mahalanobis distance between cluster centroids in 5D factor space

Effective ballot construction in the archived (stale) 9×9 build removed C7:
```python
# STALE: the archived matrices dropped cluster 7. A regenerated 10×10 build
# should keep all clusters and NOT filter party 7.
effective = np.array([[p for p in row if p != 7] for row in raw_ballots], dtype=np.int8)
# archived shape: (45707, 9); effective[:,0] = effective 1st choice
```

---

## Cluster Profile Tool (cluster_profile_viz.py)

**Inputs:**
- `TYPO_PATH` = `Claude/data/typology_cluster_assignments.csv`
- `DTA_PATH` (from stv_config) = raw survey
- `EFA_SCORES_PATH` = `Claude/data/efa_factor_scores.csv`

**Outputs:** `Claude/outputs/profiles/`
- `cluster_stats.csv` — tabular stats for all items × all clusters
- `cluster_report.html` — full interactive Plotly report (one section per cluster)
- `cluster_heatmap.html` — compact heatmap (all clusters simultaneously)

**Variable types in ITEM_META:**
| Type | display | heatmap stat |
|------|---------|-------------|
| `binary` | % Yes bar | % yes |
| `categorical` | stacked bar (one trace per cat) | mode category % |
| `ordinal` | stacked bar + mean diamond | mean |
| `continuous` | IQR range bar (Q25-Q75) + median diamond | median |

**Age column note:** `age` is derived (`2024 - birthyr`) inside `load_data()` after DTA load. It is NOT a DTA column, but it IS in ITEM_META. The "WARNING: columns not in DTA" message for `age` is normal and expected.

**Plotly hidden-div resize fix** (important for correct rendering):
```javascript
section.querySelectorAll('.js-plotly-plot').forEach(function(div) {
    if (window.Plotly) { Plotly.Plots.resize(div); }
});
```
This must fire with a `setTimeout` after any section becomes visible. **Do NOT** use `window.dispatchEvent(new Event('resize'))` — it doesn't propagate to specific div elements.

---

## Scenario Script Details (stv_scenarios.py — archived scenario capability)

The scenario runner is now under `pipeline/archive/`. It is an **optional what-if
tool**, not part of the baseline. The baseline dissolves nothing.

```python
SCENARIOS = {
    "scenario_a": {"label": "...", "pre_dissolved": [7]},      # dissolve OAO (C7)
    "scenario_b": {"label": "...", "pre_dissolved": [7, 2]},   # dissolve OAO + Solidarity
}
# Output dirs: SCENARIOS_ROOT / "scenario_a"  and  SCENARIOS_ROOT / "scenario_b"
# Comparison:  SCENARIOS_ROOT / "scenario_comparison.csv"
```

Scenario A dissolves OAO (C7) — a counterfactual that removes an otherwise-active
party (OAO wins ~15 party-line seats in the baseline). Scenario B additionally
dissolves C2 (Solidarity, 130 seats → redistributed). Neither reflects the
production model, where all 10 parties are active.

---

## DTA Metadata Access Pattern

```python
import pyreadstat
_, meta = pyreadstat.read_dta(DTA_PATH, metadataonly=True)
# meta.column_names  → list of column names
# meta.column_labels → list of labels (zip with column_names for dict)
# meta.variable_value_labels → {varname: {code_float: "label_str"}}
labels_dict = dict(zip(meta.column_names, meta.column_labels))
val_labels = meta.variable_value_labels  # e.g. val_labels["employ"][1.0] = "Full-time"
```

CES DTA values come as **floats** (1.0, 2.0…) even for coded integers. Comparisons like `series == 1` work correctly across int/float in pandas.

---

## ITEMS_24 (Listwise Deletion Mask)

ITEMS_25 minus `CC24_340a` (dropped during EFA update — insufficient variance). These 24 items define the analysis sample.

```python
ITEMS_25 = [
    "pew_churatd", "CC24_302", "CC24_303", "CC24_341a", "CC24_341c",
    "CC24_341d",   "CC24_323a", "CC24_323b", "CC24_323d", "CC24_321b",
    "CC24_321d",   "CC24_321e", "CC24_325",  "CC24_324b", "CC24_340a",  # ← dropped
    "CC24_340b",   "CC24_340c", "CC24_340e", "CC24_340f", "CC24_440b",
    "CC24_440c",   "CC24_421_1","CC24_421_2","CC24_423",  "CC24_424",
]
ITEMS_24 = [it for it in ITEMS_25 if it != "CC24_340a"]
```

---

## Sanity Checks / Expected Values

| Check | Expected |
|-------|----------|
| `len(df)` after join | 45,707 |
| `district_apportionment.csv` rows | 180 |
| Total seats (baseline) | 873 |
| OAO (C7) seats (party-line) | 15 (active party) |
| `effective.shape` (archived 9×9 affinity — stale) | (45707, 9) |
| `second_choice_row_pct.sum(axis=1)` (archived 9×9) | ≈ 100 for all rows |
| `mean_rank_proximity.diagonal()` (archived 9×9) | 0 (excluded) |
| C0 Mahalanobis distance to C3 | ≈ 0.967 (from clustering checkpoint) |

---

## Common Pitfalls

1. **Wrong `out_dir` root in stv_scenarios.py** — use `SCENARIOS_ROOT / name`, not `OUTPUT_DIR / name`. Scenarios go in `Claude/outputs/scenario_a/`, not inside `baseline/`.

2. **Restoring ballot arrays from parquet** — parquet stores lists, not numpy arrays. Always apply `.apply(lambda b: np.array(b, dtype=np.int8))` after loading.

3. **Age not in DTA** — `age` is computed post-load (`2024 - birthyr`). Add `birthyr` to `wanted` in `load_data()`, not `age` directly.

4. **Positional join requirement** — NEVER join typology CSV to DTA by index unless the same `mask` (ITEMS_24 + commonpostweight notna) is applied first.

5. **`faminc_new == 97`** — "Prefer not to answer"; treat as missing in income analyses.

6. **Plotly stacked bar one-trace bug** — a single `go.Bar` trace with `x=list_of_values, y=["Cluster"]` renders only the first segment. Always use one trace per category.

7. **Weighted quantile** — use `np.interp(q, cumulative_weight_fraction, sorted_values)`, not `np.quantile()` (which ignores survey weights).

---

## Running Commands

```bash
# From worktree root:
python3 stv_main.py                        # full baseline run
python3 stv_main.py --steps 3,4,5          # resume from ballot checkpoint
python3 stv_scenarios.py                   # run dissolution scenarios
python3 stv_affinity.py                    # compute affinity matrices
python3 cluster_profile_viz.py             # generate HTML cluster profiles
```

Preferred Python: **`python3`** (system default on this machine)
