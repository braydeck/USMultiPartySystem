# AGENTS.md — Full Technical Reference

> This document is written for Claude Code and similar agents to maintain complete working context across conversation sessions. **Read this before touching any script.**
>
> Supersedes: `busy-ramanujan/docs/AGENT_CONTEXT.md` and `busy-ramanujan/docs/PROJECT_GUIDE.md` (those files are partially stale — kept as historical reference only).

---

## Read This First

The project uses **two git worktrees** that share the same output directory:

| Worktree | Path | Role |
|----------|------|------|
| `charming-johnson` | `/Users/bdecker/Documents/STV/.claude/worktrees/charming-johnson/` | All analysis scripts (senate, house profiles, vote model, coalitions) |
| `busy-ramanujan` | `/Users/bdecker/Documents/STV/.claude/worktrees/busy-ramanujan/` | STV pipeline (ballots, apportionment, STV rounds, affinity, cluster viz) |

**Shared output directory:** `/Users/bdecker/Documents/STV/Claude/outputs/`

Scripts in both worktrees read from and write to the same `Claude/outputs/` tree. There is no syncing needed — it's a shared filesystem path.

The active branch for new development is **charming-johnson**. When starting a new session, check which worktree you're in and `cd` to the correct one before running scripts.

---

## Canonical Scenario Rules

These are permanent project conventions. Never change them without explicit user instruction.

| Rule | Value |
|------|-------|
| C7 = OAO (Order & Opportunity) | **Active party** — the former "Blue Dogs," a law-and-order Democratic bloc, kept and renamed. `DISSOLVED_PARTIES = []` in `stv_config.py`. Dissolving is a *scenario* option, not the baseline. |
| C2 (Solidarity / STY) | **ALWAYS active.** Never add to `DISSOLVED_PARTIES`. |
| Default STV output | `Claude/outputs/No_C7_canonical/` |
| `round_elim_c{x}` encoding | `−1` = elected, `−2` = pre-dissolved (only for parties in a scenario's `pre_dissolved` list; never occurs in the baseline), `N≥1` = eliminated in round N, `None` = not present in district |

Old output directories `baseline/` and `no_C2/` exist as historical artifacts. Do not regenerate them unless explicitly asked.

---

## Absolute Paths

All hardcoded in `stv_config.py` (busy-ramanujan):

```python
BASE_DIR        = Path("/Users/bdecker/Documents/STV")
DTA_PATH        = BASE_DIR / "DataSets" / "2024 CES Base" / "CCES24_Common_OUTPUT_vv_topost_final.dta"
TYPOLOGY_PATH   = BASE_DIR / "Claude" / "data" / "typology_cluster_assignments.csv"
EFA_SCORES_PATH = BASE_DIR / "Claude" / "data" / "efa_factor_scores.csv"
OUTPUT_DIR      = BASE_DIR / "Claude" / "outputs" / "No_C7_canonical"
SCENARIOS_ROOT  = BASE_DIR / "Claude" / "outputs"
```

Note: The DTA file is large (~947 MB). Steps 1–2 of the STV pipeline read it; steps 3–5 use the ballot checkpoint parquet. Always prefer `--steps 3,4,5` to skip the slow DTA read when the ballot checkpoint exists.

---

## Scripts Inventory

### busy-ramanujan (STV Pipeline)

| Script | Role | Key Outputs |
|--------|------|-------------|
| `stv_config.py` | Shared constants, party labels, paths — no logic | — |
| `stv_step1.py` | Load DTA + typology; build weighted ranked ballots | in-memory |
| `stv_step2.py` | Apportion seats per district (Hamilton method) | `district_apportionment.csv` |
| `stv_step3.py` | Run STV per district (Droop quota + Gregory surplus) | `stv_results_by_district.csv` |
| `stv_step4.py` | Build transfer matrices from STV vote traces | `transfer_matrix_*.csv` |
| `stv_step5.py` | Summarize seat counts by party | `stv_seat_summary.csv` |
| `stv_main.py` | Orchestrates steps 1–5; CLI `--steps` flag; passes `pre_dissolved=DISSOLVED_PARTIES` (baseline `[]`) | all of the above + `ballots_checkpoint.parquet` |
| `stv_scenarios.py` (archived) | *Scenario capability:* re-runs steps 3–5 with alternative `pre_dissolved` lists to model dissolving one or more parties. Now under `pipeline/archive/`; not part of the baseline. | `scenario_*/` subdirs |
| `stv_affinity.py` | 4 inter-party affinity measures | `affinity/*.csv` |
| `cluster_profile_viz.py` | Cluster demographic/policy HTML reports | `profiles/*.html`, `profiles/cluster_stats.csv` |

### charming-johnson (Analysis)

| Script | Role | Key Outputs |
|--------|------|-------------|
| `run_senate_simulation.py` | State-by-state senate (Condorcet) | `senate/senate_composition.csv`, `senate_condorcet_results.csv` |
| `run_senate_irv.py` | State-by-state senate (IRV) | `senate/senate_irv_composition.csv`, `senate_irv_rounds.csv` |
| `generate_candidate_profiles.py` | Factor centroids for all candidate types | `senate/senate_candidate_factor_centroids.csv`, `candidate_factor_centroids.csv` |
| `generate_blend_stats.py` | Policy/demographic profiles for blend types | `profiles/blend_stats.csv` |
| `senate_chamber_profile.py` | Seat-weighted policy aggregate for senate | `senate/senate_chamber_profile.csv` |
| `house_chamber_profile.py` | Seat-weighted policy aggregate for house | `house_chamber_profile.csv` |
| `senate_voting_blocs.py` | Ward hierarchical clustering in 5D factor space | `senate/senate_voting_blocs.csv` |
| `chamber_vote_model.py` | Bill passage probability for 37 policy items | `senate/senate_vote_model.csv`, `house_vote_model.csv` |
| `cross_chamber_coalitions.py` | Cross-chamber factor alignment (23 types) | `coalitions/*.csv` |
| `analyze_senate_ideology.py` | Additional senate ideology diagnostics | `senate/senate_ideology_balance.csv` |
| `report_blend_profiles.py` | Human-readable blend profile report | `senate/blend_profiles.txt` |

---

## Party Reference

House Seats = party-line STV result (`viz/src/data/houseSeats.json`); see [DATA_SOURCES.md](DATA_SOURCES.md).

| ID | Abbrev | Full Name | Status | House Seats |
|----|--------|-----------|--------|-------------|
| C0 | CON | Conservative | Active | 202 |
| C1 | LBR | Labor | Active | 164 |
| C2 | STY | Solidarity | Active | 130 |
| C3 | NAT | Nationalist | Active | 46 |
| C4 | LIB | Liberal | Active | 93 |
| C5 | POP | Populist | Active | 99 |
| C6 | CUP | Civic Union Party | Active | 103 |
| C7 | OAO | Order & Opportunity | **ACTIVE** | 15 |
| C8 | DSA | DSA | Active | 22 |
| C9 | PRG | Progressive | Active | 14 |

**Total active seats:** 873. `N_PARTIES = 10`, `PROB_COLS = [f"prob_cluster_{k}" for k in range(10)]`

---

## EFA Factor Reference

Final 24-item solution (CC24_340a dropped due to near-Heywood condition λ=−0.947). Factors are oblique (correlated); Phi matrix shows F1↔F4 (+0.55) and F1↔F5 (−0.51) are the strongest inter-factor correlations.

For detailed loadings per item, see [`EFA_FACTORS.md`](EFA_FACTORS.md).

### F1 — Security & Order (high = pro-enforcement)
Top items: increase police (+0.73), border patrols (+0.71), deny asylum (+0.66), oppose police cuts (+0.65), surveillance (+0.49)
- CON: +0.767 (Very High) | LIB: −0.462 (Low) | DSA: −1.303 (Very Low) | PRG: −1.260 (Very Low)

### F2 — Institutional Distrust (high = distrust elections)
Top items: state elections not fair (+0.90), US elections not fair (+0.73), distrust state govt (+0.38)
- POP: +0.759 (Very High) | STY: +0.658 (High) | CUP: −0.817 (Very Low) | LIB: −0.744 (Very Low)
- **Cross-cutting:** STY, POP, and DSA all score High despite opposing positions on F1 and F5.

### F3 — Government Distrust (residual) (residual)
Top items: distrust federal govt (+0.66), distrust state govt (+0.48)
- **All 23 winning types score Medium (range: −0.21 to +0.13). F3 does not differentiate winning coalitions.**

### F4 — Religious Traditionalism (high = religious/traditional)
Top items: church attendance (+0.69), abortion week limits (+0.69), oppose same-sex marriage recognition (+0.65)
- NAT: +0.457 (High) | DSA: −0.387 (Low) | PRG: −0.387 (Low)
- No winning type reaches Very High (> +0.75); none reach Very Low.

### F5 — Populist Conservatism (high = populist-right, low = progressive-left)
Top items (negative-loaded, higher F5 = conservative position): racial resentment (−0.62), oppose police reform (−0.56), oppose Dreamers (−0.54), oppose $400k+ tax hike (−0.53)
- NAT: +1.510 (Very High) | POP: +0.990 (Very High) | PRG: −0.990 (Very Low) | LIB: −0.950 (Very Low)

### Absolute Tier Thresholds

| Tier | Score |
|------|-------|
| Very High | > +0.75 |
| High | +0.25 to +0.75 |
| Medium | −0.25 to +0.25 |
| Low | −0.75 to −0.25 |
| Very Low | < −0.75 |

---

## Data Join Pattern

**Critical:** `typology_cluster_assignments.csv` has **no `caseid`** column. It aligns **positionally** with the DTA after the same listwise deletion mask is applied.

```python
# ITEMS_24 = ITEMS_25 minus CC24_340a (dropped in EFA update)
mask = df_dta[ITEMS_24 + ["commonpostweight"]].notna().all(axis=1)

df_aux  = df_dta.loc[mask, DTA_AUX_COLS].reset_index(drop=True)  # 45,707 rows
df_typo = pd.read_csv(TYPOLOGY_PATH)                               # 45,707 rows
df      = pd.concat([df_typo, df_aux], axis=1)                    # positional alignment
```

**NEVER** join typology to DTA by index without applying this identical mask — row counts will not match and the join will be silently wrong.

### ITEMS_24 (the 24-item listwise deletion set)

```python
ITEMS_25 = [
    "pew_churatd", "CC24_302",   "CC24_303",   "CC24_341a",  "CC24_341c",
    "CC24_341d",   "CC24_323a",  "CC24_323b",  "CC24_323d",  "CC24_321b",
    "CC24_321d",   "CC24_321e",  "CC24_325",   "CC24_324b",  "CC24_340a",  # ← dropped
    "CC24_340b",   "CC24_340c",  "CC24_340e",  "CC24_340f",  "CC24_440b",
    "CC24_440c",   "CC24_421_1", "CC24_421_2", "CC24_423",   "CC24_424",
]
ITEMS_24 = [it for it in ITEMS_25 if it != "CC24_340a"]
```

---

## Ballot Checkpoint

Written by `stv_main.py` after step 1. Stored at `No_C7_canonical/ballots_checkpoint.parquet`.

**Shape:** 45,707 rows × many columns

| Column | Type | Description |
|--------|------|-------------|
| `ballot` | list[int] → np.int8 array | Ranked party order (10 elements, 0–9); parquet stores as list |
| `cluster` | int64 | Hard cluster (argmax of soft probs) |
| `prob_cluster_0` … `prob_cluster_9` | float64 | Soft DPGMM probabilities (sum to 1) |
| `commonpostweight` | float64 | Survey post-stratification weight |
| `FS_F1` … `FS_F5` | float64 | 5 EFA factor scores |
| `inputstate` | int64 | State FIPS code |
| `urbancity` | float64 | 1=City, 2=Suburb, 3=Town, 4=Rural |

**Always restore ballot arrays after loading parquet:**
```python
df = pd.read_parquet(checkpoint_path)
df["ballot"] = df["ballot"].apply(lambda b: np.array(b, dtype=np.int8))
```

---

## STV Algorithm

**Droop quota:** `⌊ total_weight / (seats + 1) ⌋ + 1`

**Pre-dissolution (scenario option, not the baseline):** Any party listed in `pre_dissolved` is eliminated at position 0 before any rounds; each of its voters' ballot pointers advance to their next-ranked active party and their weighted votes transfer immediately. In the baseline `DISSOLVED_PARTIES = []`, so nothing is pre-dissolved and all 10 parties (including OAO/C7) compete. Dissolving a party is only exercised via the archived scenario runner.

**Each round:**
1. Tally active vote weights per active party
2. If any party ≥ quota: elect them, compute surplus factor = `(tally − quota) / tally`, redistribute votes at reduced weight to next-ranked active party
3. Else: eliminate the lowest-tally party; redistribute all their votes at full weight to next-ranked active party
4. Repeat until all seats filled or no active candidates remain

**`round_elim_c{x}` values:**
- `-1` = elected
- `-2` = pre-dissolved before any round (only for parties in `pre_dissolved`; in the baseline no party gets `-2` since `DISSOLVED_PARTIES = []`)
- `N ≥ 1` = eliminated in round N (1-indexed)
- `None` = party had zero-weight voters in this district (not present)

---

## Senate Simulation

One senator per state via a two-stage process:

### Stage 1 — Candidate Generation (per state)
```python
PURE_THRESHOLD     = 0.05   # min weighted mean prob_cluster to generate a pure candidate
COOC_MIN_SHARE     = 0.04   # min share for co-occurrence straddler eligibility
WILDCARD_MIN_SHARE = 0.15   # both clusters need ≥15% for wild card
WILDCARD_MIN_DIST  = 1.40   # min 5D factor-space distance for cross-aisle wild card
MAX_COOC_STRADDLERS = 6
MAX_WILDCARDS       = 2
MAX_CANDIDATES      = 18
STV_SURVIVORS       = 5     # STV primary winnows to this many finalists
```

**Candidate types:**
- **Pure:** one per cluster exceeding `PURE_THRESHOLD` in state
- **Co-occurrence straddler:** derived from within-state top-2 cluster co-occurrence matrix; blend weight = co-occurrence rate
- **Wild card:** cross-aisle candidates when two clusters each ≥15% AND factor distance ≥1.40

**Blend factor position:** `blend_F = w_p × centroid_primary + (1 − w_p) × centroid_secondary`

### Stage 2 — General Election
- **STV primary** → 5 finalists
- **Ranked Pairs Condorcet** → 1 senator (majority preference winner)
- **IRV alternative** (`run_senate_irv.py`) → used for comparison; produces slightly different composition

---

## Chamber Vote Model

**Binary policy items only:** filtered to `stat_label == "% Supporting"` AND `variable.str.startswith("CC24_")` → **37 items**. This excludes demographic items (pew_bornagain, milstat, etc.) that share the same `stat_label`.

**Formula:**
```python
mu     = sum(n_t * p_t for each type t)                   # expected yes votes
sigma2 = sum(n_t * p_t * (1 - p_t) for each type t)
sigma  = sqrt(sigma2)
z      = (majority - 0.5 - mu) / sigma                    # continuity correction
prob   = 1.0 - norm.cdf(z)
```

**Majority thresholds:** Senate = 26/51 | House = 437/873

**Verdict:** PASS ≥ 0.67 | TOSS-UP 0.33–0.67 | FAIL ≤ 0.33

---

## Coalition Analysis

**Types:** 23 total
- 20 senate types from `senate/senate_candidate_factor_centroids.csv` (blends + pure winners)
- 3 house-only additions from `candidate_factor_centroids.csv`: NAT, DSA, PRG

**Chamber tags:** `both` (pure type winning seats in both chambers), `senate` (blend or senate-only pure), `house` (NAT, DSA, PRG — house only)

**k=2 poles:** 1D k-means on the 23 types for each factor — relative split within winner set.
**Absolute tiers:** fixed thresholds (±0.25, ±0.75) against the EFA population scale.

**Pairwise alignment score:** `1 − (per_factor_dist / max_dist)` where 1.0 = identical, 0.0 = maximally opposed on that factor. `overall_align` uses 5D Euclidean distance.

---

## Key Output Files

| File | Shape | Key Columns |
|------|-------|-------------|
| `No_C7_canonical/stv_seat_summary.csv` | 10×9 | `party`, `party_name`, `NATIONAL`, `URBAN`, `SUBURBAN`, `RURAL`, `pct_national` |
| `No_C7_canonical/stv_results_by_district.csv` | 180×many | `district_id`, `seats`, `round_elim_c{0..9}` |
| `No_C7_canonical/transfer_matrix_directed.csv` | 10×10 | row=eliminated, col=receiving, value=global % |
| `archive/affinity/second_choice_row_pct.csv` | 9×9 (STALE) | C7/OAO excluded; rows sum ≈ 100. Predates OAO reinstatement — regenerate as 10×10. |
| `archive/affinity/mean_rank_proximity.csv` | 9×9 (STALE) | 0=far, 1=close; symmetric; C7/OAO excluded. Regenerate as 10×10. |
| `archive/affinity/factor_mahalanobis.csv` | 9×9 (STALE) | Mahalanobis distance in 5D factor space; C7/OAO excluded. Regenerate as 10×10. |
| `profiles/cluster_stats.csv` | 285×34 | `variable`, `stat_label`, `stat_value`, `c0`…`c9` |
| `profiles/blend_stats.csv` | 285×many | same format, columns = blend candidate labels |
| `senate/senate_composition.csv` | 51×many | `state_fips`, `senator_label`, `senator_type`, `primary_cluster`, `secondary_cluster` |
| `senate/senate_irv_composition.csv` | 51×many | `winner_label`, `runner_up_label`, `n_irv_rounds` |
| `senate/senate_chamber_profile.csv` | 285×34 | `variable`, `stat_label`, `stat_value`, 18 type cols + 10 aggregate cols |
| `senate/senate_voting_blocs.csv` | 30×many | `scenario`, `n_blocs`, `bloc`, `seats`, `members`, centroid cols |
| `senate/senate_vote_model.csv` | 37×many | `variable`, `description`, `cond_prob_pass`, `cond_verdict`, `irv_prob_pass`, `irv_verdict` |
| `house_chamber_profile.csv` | 285×17 | `variable`, `stat_label`, 10 party type cols + `house_chamber` |
| `house_vote_model.csv` | 37×many | `variable`, `description`, `house_prob_pass`, `house_verdict` |
| `coalitions/coalition_type_profiles.csv` | 23×9 | `type`, `chamber`, F1–F5, seat count cols |
| `coalitions/coalition_factor_alignment.csv` | 115×many | `factor`, `type`, `score`, `rank`, `k2_label`, `tier_label` |
| `coalitions/coalition_pairwise.csv` | 253×many | `type_a`, `type_b`, per-factor `_dist` and `_align` cols, `overall_align` |

---

## Running Commands

```bash
# From busy-ramanujan/
python3 stv_main.py                          # Full STV run (~3.5s)
python3 stv_main.py --steps 3,4,5           # Skip DTA read, use checkpoint
python3 stv_affinity.py                      # Affinity matrices (~5s)
python3 cluster_profile_viz.py               # Cluster HTML reports (~15s)

# From charming-johnson/
python3 run_senate_simulation.py             # Condorcet senate (~30s)
python3 run_senate_irv.py                    # IRV senate (~30s)
python3 generate_candidate_profiles.py       # Factor centroids for all types
python3 generate_blend_stats.py              # Blend policy profiles
python3 senate_chamber_profile.py            # Senate chamber aggregate
python3 house_chamber_profile.py             # House chamber aggregate
python3 senate_voting_blocs.py               # Voting bloc clustering
python3 chamber_vote_model.py                # Bill passage model
python3 cross_chamber_coalitions.py          # Coalition analysis
```

---

## Sanity Check Values

| Check | Expected |
|-------|----------|
| N after listwise deletion | 45,707 |
| Total districts | 180 |
| Total house seats | 873 |
| OAO (C7) house seats | 15 (party-line baseline; OAO is an active party) |
| Senate senators | 51 |
| `round_elim_c7` in all districts | not `−2` in baseline (`DISSOLVED_PARTIES = []`); `−2` only appears when C7 is in a scenario's `pre_dissolved` list |
| Senate vote model items | 37 |
| Coalition analysis types | 23 |
| `second_choice_row_pct` row sums (archived 9×9) | ≈ 100 |
| `mean_rank_proximity` diagonal (archived 9×9) | 0 (self-excluded) |

---

## Common Pitfalls

1. **Positional join** — NEVER join typology CSV to DTA by index without the ITEMS_24 + commonpostweight `notna()` mask. Silent wrong alignment if mask differs.

2. **Ballot arrays from parquet** — parquet stores as Python lists, not numpy arrays. Always apply `.apply(lambda b: np.array(b, dtype=np.int8))` after loading.

3. **`age` column** — `age` is computed post-load as `2024 - birthyr`. It is NOT in the DTA directly. Add `birthyr` to the column read list, then derive `age`. The "WARNING: columns not in DTA" message for `age` in cluster_profile_viz is expected.

4. **`faminc_new == 97`** — means "Prefer not to answer." Treat as missing in income analyses.

5. **CC24_ filter in vote model** — The `stat_label == "% Supporting"` filter alone is not enough. Always also apply `variable.str.startswith("CC24_")` to exclude demographic binary items (pew_bornagain, milstat, children under 18, etc.) that share the same label.

6. **DTA float-coded values** — CES DTA values come as floats (1.0, 2.0…). Comparisons like `series == 1` work correctly across int/float in pandas.

7. **Old scenario paths** — `baseline/`, `no_C2/` are legacy. Never regenerate or write to them. All current work uses `No_C7_canonical/`.

8. **Senate blend centroid math** — blend factor positions are computed as linear interpolation: `w_p × centroid_primary + (1−w_p) × centroid_secondary`. The weight `w_p` is the primary cluster share in the co-occurrence pair.

9. **DTA path** — The DTA file is in `DataSets/` (with capital S), not `2024 CES Base/` directly at root. Full path: `/Users/bdecker/Documents/STV/DataSets/2024 CES Base/CCES24_Common_OUTPUT_vv_topost_final.dta`

10. **Worktree confusion** — Scripts in `busy-ramanujan` import from each other via relative paths. Always run them from the `busy-ramanujan/` directory, not from `charming-johnson/`.
