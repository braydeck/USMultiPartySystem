# CES 2024 Political Typology — Project Guide

## What Is This Project?

This project takes the **2024 Cooperative Election Study (CES)** — a large national survey of ~45,000 American voters — and uses it to model what an American **multi-party electoral system** might look like.

The pipeline runs in three main stages:

1. **Factor Analysis + Clustering** — Discover latent political dimensions in survey responses; cluster respondents into 10 distinct voter types.
2. **STV Simulation** — Run a Single Transferable Vote (proportional representation) election using ranked-choice ballots derived from cluster probabilities.
3. **Analysis & Visualization** — Examine seat counts, transfer patterns, inter-party affinities, and rich demographic cluster profiles.

---

## The 10 Parties

Party IDs (C0–C9) are derived from DPGMM clustering. All 10 clusters are active parties; C7 = OAO (Order & Opportunity Party), the former "Blue Dogs," a law-and-order Democratic bloc kept as its own party (`DISSOLVED_PARTIES = []`).

| ID | Name | Character |
|----|------|-----------|
| C0 | Conservative | Mainstream center-right |
| C1 | Labor (LBR) | Center-left, institutionalist (older artifacts abbreviate SD) |
| C2 | Solidarity | Disaffected working-class left |
| C3 | Nationalist | Populist right, immigration focus |
| C4 | Liberal | College-educated moderates |
| C5 | Populist | Right-of-center reformists |
| C6 | Civic Union Party | True centrists / cross-pressured |
| C7 | OAO (Order & Opportunity) | Law-and-order Democrats (former "Blue Dogs"); active, wins seats |
| C8 | DSA | Progressive left |
| C9 | Progressive | Progressive elite |

---

## Project Layout

```
/Users/bdecker/Documents/STV/
│
├── 2024 CES Base/
│   └── CCES24_Common_OUTPUT_vv_topost_final.dta   ← 947 MB Stata file (raw survey)
│
└── Claude/
    ├── data/                      ← Core model inputs
    │   ├── typology_cluster_assignments.csv   (45,707 rows; prob_cluster_0..9 + weight)
    │   ├── efa_factor_scores.csv              (45,707 rows; 5 factor scores + weight)
    │   └── polychoric_matrix.csv              (24×24 polychoric correlation matrix)
    │
    ├── analysis/
    │   ├── efa/                   ← EFA model outputs (loadings, variance, phi matrices)
    │   └── clustering/            ← DPGMM outputs (profiles, Mahalanobis distances)
    │
    ├── outputs/                   ← All STV simulation outputs
    │   ├── baseline/              ← Main STV run (all 10 parties active; nothing dissolved, DISSOLVED_PARTIES = [])
    │   │   ├── ballots_checkpoint.parquet
    │   │   ├── district_apportionment.csv
    │   │   ├── stv_results_by_district.csv
    │   │   ├── stv_seat_summary.csv
    │   │   ├── transfer_matrix_10party.csv
    │   │   ├── transfer_matrix_directed.csv
    │   │   └── transfer_asymmetry_report.csv
    │   ├── scenario_a/            ← What-if: dissolve OAO/C7 (counterfactual; OAO is active in baseline)
    │   ├── scenario_b/            ← What-if: dissolve OAO/C7 + C2 (Solidarity)
    │   ├── archive/affinity/      ← Inter-party affinity matrices (4 measures) — STALE 9×9, exclude OAO; regenerate as 10×10
    │   ├── profiles/              ← Cluster profile HTML reports + stats CSV
    │   └── scenario_comparison.csv
    │
    └── archive/
        ├── scripts/               ← Older EFA/clustering scripts (superseded)
        └── old_docs/              ← Earlier documentation drafts
```

**Scripts** live in the worktree root:
`/Users/bdecker/Documents/STV/.claude/worktrees/busy-ramanujan/`

---

## How to Run Things

All commands are run from the **worktree root** with `python3`.

### Full STV simulation (from scratch)
```bash
python3 stv_main.py
# ~3.5s — runs all 5 steps, writes to Claude/outputs/baseline/
```

### Resume from a specific step
```bash
python3 stv_main.py --steps 3,4,5   # skip steps 1–2, use ballot checkpoint
python3 stv_main.py --steps 5        # seat summary only (requires step 3 data)
```

### Dissolution scenarios (A and B) — optional what-if capability, archived
```bash
python3 stv_scenarios.py    # now under pipeline/archive/; not part of the baseline
# Reads baseline checkpoint, runs two counterfactual STV elections that dissolve
# one or more otherwise-active parties:
#   Scenario A → Claude/outputs/scenario_a/
#   Scenario B → Claude/outputs/scenario_b/
# Also writes Claude/outputs/scenario_comparison.csv
```

### Affinity matrices
```bash
python3 stv_affinity.py
# Computes 4 inter-party affinity measures → Claude/outputs/affinity/
```

### Cluster profile reports
```bash
python3 cluster_profile_viz.py
# Generates cluster_report.html (full detail) and cluster_heatmap.html
# → Claude/outputs/profiles/
```

---

## What the Outputs Mean

### `stv_seat_summary.csv`
National and regional (Urban/Suburban/Rural) seat counts per party. Key columns:
- `party` — cluster ID (0–9)
- `NATIONAL` — total seats won nationally
- `pct_national` — share of all seats
- `URBAN`, `SUBURBAN`, `RURAL` — seats by density tier

### `transfer_matrix_directed.csv`
When party A is eliminated in an STV round, what % of its votes transfer to party B?
- Row = eliminated party, Column = receiving party
- Values are global percentages (not row-normalized)
- See `transfer_matrix_10party.csv` for the symmetric version

### `affinity/` outputs
Four complementary measures of inter-party closeness. **The files currently on disk
(`data/outputs/archive/affinity/`) are stale 9×9 matrices that exclude OAO/C7** and
predate its reinstatement as a full party; they should be regenerated as 10×10:

| File | What it measures |
|------|-----------------|
| `second_choice_global_pct.csv` | % of all voters who rank B 2nd when A is 1st |
| `second_choice_row_pct.csv` | % of A's own voters who rank B 2nd |
| `mean_rank_proximity.csv` | Full preference ordering proximity (0=far, 1=close) |
| `factor_mahalanobis.csv` | Ideological distance in 5D factor space |

### `cluster_report.html`
Interactive party-by-party profile with demographic breakdowns, policy opinion distributions, and voting history charts. Open in any browser; use the left rail to switch parties.

### `cluster_heatmap.html`
Compact heatmap view across all parties simultaneously.

---

## Key Numbers to Know

- **45,707** survey respondents (after listwise deletion on 24 survey items)
- **180** simulated congressional districts
- **873** total seats (≈ U.S. House scaled by 380,000 pop/seat)
- **10** parties; **10** active (baseline dissolves none)
- **5** latent factors from EFA
- Ballot checkpoint: ~35 MB parquet, loads in ~0.2s

---

## Scenarios Explained

**Baseline** — All 10 parties compete; nothing is pre-dissolved (`DISSOLVED_PARTIES = []`). OAO/C7 is a full, active party and wins ~15 party-line seats. This is the production default.

**Scenario A** (counterfactual) — Dissolves OAO/C7. Because OAO is active in the baseline, this is a genuine what-if: OAO voters transfer to their next-ranked active party and OAO's ~15 seats redistribute.

**Scenario B** (counterfactual) — Dissolves both OAO/C7 and C2 (Solidarity). Tests what happens when both parties dissolve, redistributing OAO's ~15 seats and Solidarity's 130 seats.

The dissolution machinery (`pre_dissolved` lists, `-2` pre-dissolved encoding) still exists as a capability, but it is only exercised by these optional scenario runs — never by the baseline.

---

## Dependencies

```
python3 ≥ 3.10
numpy, pandas, scipy
pyarrow          (parquet I/O)
pyreadstat       (Stata DTA reading)
plotly           (HTML visualizations)
```
