# American Multi-Party Electoral Simulation

A full-stack simulation of what American politics might look like under proportional representation, using real ideological data from the **2024 Cooperative Election Study (CES)** — 60,000+ respondents, 45,707 after listwise deletion.

> For the full technical reference (agent/developer guide), see [`docs/AGENTS.md`](docs/AGENTS.md).
> For detailed EFA factor loadings, see [`docs/EFA_FACTORS.md`](docs/EFA_FACTORS.md).

## Overview

This project explores what American politics might look like under different electoral rules:
- **Multi-party proportional representation** instead of winner-take-all
- **Single Transferable Vote (STV)** primaries with Droop quota surplus transfers
- **A rolling presidential primary** with geographic balance across 4 rounds
- **Instant Runoff Voting (IRV)** for senate general elections
- **Condorcet/Copeland general elections** with proportional elector allocation
---

## Pipeline at a Glance

```
2024 CES Survey (N=45,707)
        │
        ▼
  Exploratory Factor Analysis (EFA)
  24 policy items → 5 latent ideological dimensions (F1–F5)
        │
        ▼
  DPGMM Clustering
  Factor scores → 10 voter typology clusters (C0–C9)
        │
        ├──────────────────────────────────────┐
        ▼                                      ▼
  House STV Simulation                   Senate Simulation
  873 seats / 180 districts              51 senators (one per state)
  Droop quota + Gregory surplus          STV primary → Ranked Pairs Condorcet
  Canonical: No_C7_canonical/            Condorcet + IRV scenarios
        │                                      │
        └──────────────┬───────────────────────┘
                       ▼
             Chamber Vote Model
             37 binary policy items
             Sum-of-Binomials → P(pass)
                       │
                       ▼
           Cross-Chamber Coalition Analysis
           23 types × 5 factors
           Per-factor alignment (k=2 poles + absolute tiers)
```

---

## The 10-Party Typology

Produced by **Dirichlet Process Gaussian Mixture Model (DPGMM)** clustering on 5 EFA factor scores. C7 is **permanently dissolved** — never competes for seats; their ballots transfer to next-ranked active party.

| ID | Abbrev | Name | Character | ~Electorate |
|----|--------|------|-----------|-------------|
| C0 | CON | Conservative | Mainstream center-right; pro-law enforcement, economically traditional | ~19% |
| C1 | SD | Social Democrat | Center-left institutionalist; supports safety net, moderate on social issues | ~16% |
| C2 | STY | Solidarity | Disaffected working-class left; skeptical of institutions, economically left but low union density | ~15% |
| C3 | NAT | Nationalist | Populist right; strong on immigration, anti-establishment, very high F5 | ~9% |
| C4 | LIB | Liberal | College-educated progressive; socially liberal, moderate-left economics | ~9% |
| C5 | POP | Populist | Right-of-center reformists; skeptical of elections, high F2 + F5 | ~11% |
| C6 | CUP | Civic Union Party | True centrists; cross-pressured, low electoral skepticism | ~10% |
| C7 | — | Blue Dogs *(dissolved)* | Conservative Democrats; pre-eliminated in all simulations, 0 seats | — |
| C8 | DSA | DSA | Progressive left; far left on security, high electoral skepticism | ~6% |
| C9 | PRG | Progressive | Progressive elite; urban, far left across most dimensions | ~5% |

**House seat counts (party-line, canonical):** CON=202, SD=164, STY=130, POP=99, CUP=103, LIB=93, DSA=22, NAT=46, PRG=14, C7=0 (dissolved). Conservative is the largest party. Source: `viz/src/data/houseSeats.json` — see **[docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)**. *(Do not quote `clusterProfiles.json` `seatsHouse` for seat counts — it's a population baseline, not seats won.)*

---

## The 5 Ideological Factors (EFA)

Factor scores are standardized to the survey population (mean≈0, SD≈1). Absolute tier thresholds reflect position relative to the full electorate:

| Tier | Score Range |
|------|-------------|
| Very High | > +0.75 |
| High | +0.25 to +0.75 |
| Medium | −0.25 to +0.25 |
| Low | −0.75 to −0.25 |
| Very Low | < −0.75 |

### F1 — Security & Order
**High** = pro-law enforcement, pro-border security, pro-surveillance
**Low** = civil libertarian, anti-enforcement
*Top items: support increased police (+0.73), increase border patrols (+0.71), deny asylum (+0.66), oppose decreasing police (+0.65)*

### F2 — Electoral Skepticism
**High** = believes elections are NOT run fairly; distrusts voting systems
**Low** = trusts electoral institutions
*Top items: state/local elections not fair (+0.90), US elections not fair (+0.73)*
Note: Near-orthogonal to partisan ID — STY, POP, and DSA all score High despite being ideologically distant on F1/F5.

### F3 — Government Distrust
**High** = low trust in federal and state government
**Low** = trusts government institutions
*Top items: distrust federal govt (+0.66), distrust state govt (+0.48)*
**Key finding: All 23 winning coalition types score Medium on F3 (range −0.21 to +0.13) — this axis does not differentiate winning coalitions at all.**

### F4 — Religious Traditionalism
**High** = traditional religious values; conservative on abortion and same-sex marriage
**Low** = secular, socially progressive
*Top items: church attendance (+0.69), abortion week limits (+0.69), oppose same-sex marriage recognition (+0.65)*

### F5 — Populist Conservatism
**High** = populist-right; anti-immigration, fiscal conservatism, racial traditionalism
**Low** = progressive-left
*Top items (negative-loaded): racial resentment (−0.62), oppose police reform (−0.56), oppose Dreamers (−0.54), oppose tax hike on $400k+ (−0.53)*
NAT is the extreme high end (+1.51); PRG (−0.99) and LIB (−0.95) are the extreme low end.

---

## House STV Simulation

**Scripts:** `pipeline/stv_main.py` and supporting `pipeline/stv_step1.py`–`pipeline/stv_step5.py`
**Published result:** `data/outputs/pure_multi/house/stv_seat_summary.csv` → `viz/src/data/houseSeats.json` (the party-line view the viz shows).
**Note:** published seat counts come from `pure_multi`, *not* from `data/outputs/No_C7_canonical/stv_seat_summary.csv` (an outdated 750-seat summary — don't quote it). The `No_C7_*` directories are retained on purpose: the pure_multi and factor_deviation runs read their `ballots_checkpoint.parquet` + `district_apportionment.csv`, and the viz transfer matrix is built from `No_C7_canonical/transfer_matrix_10party.csv`. See [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).

- **873 seats** across **180 multi-member districts** (Urban / Suburban / Rural tiers per state)
- Apportionment: Hamilton method, ~380,000 pop/seat from 2020 Census
- **Droop quota:** `⌊ total_weight / (seats + 1) ⌋ + 1`
- **Gregory surplus transfer:** fractional weight redistribution when a candidate exceeds quota
- **C7 pre-dissolved:** their voters' ballots skip to next-ranked active party before Round 1
- Ballots derived from DPGMM soft cluster probabilities via Plackett-Luce ranking

**Seat results (party-line, canonical):**

| Party | Seats | % | Urban | Suburban | Rural |
|-------|-------|---|-------|----------|-------|
| CON | 202 | 23.1% | 106 | 68 | 28 |
| SD | 164 | 18.8% | 96 | 51 | 17 |
| STY | 130 | 14.9% | 71 | 50 | 9 |
| CUP | 103 | 11.8% | 59 | 30 | 14 |
| POP | 99 | 11.3% | 47 | 38 | 14 |
| LIB | 93 | 10.7% | 62 | 26 | 5 |
| NAT | 46 | 5.3% | 16 | 18 | 12 |
| DSA | 22 | 2.5% | 14 | 6 | 2 |
| PRG | 14 | 1.6% | 10 | 3 | 1 |

---

## Senate Simulation

**Scripts:** `pipeline/run_senate_simulation.py` (Condorcet), `pipeline/run_senate_irv.py` (IRV)
**Output:** `data/outputs/senate/`

- **51 senators** — one per state (50 states + DC)
- **Candidate generation per state:** up to 18 candidates
  - *Pure* candidates: any cluster with ≥5% weighted share in that state
  - *Co-occurrence straddlers*: blend candidates based on within-state top-2 cluster co-occurrence rates
  - *Wild card cross-aisle*: two clusters each ≥15% state share AND factor-space distance ≥1.40
- **Primary:** STV elimination → 5 finalists
- **General:** Ranked Pairs Condorcet → 1 senator (or IRV alternative)

Senate candidate factor positions use linear interpolation: `blend = w × pure_primary + (1−w) × pure_secondary`.

**Top seat types (IRV scenario):**

| Type | Seats | Description |
|------|-------|-------------|
| SD/STY | 10 | Social Democrat–Solidarity |
| CON/SD | 6 | Conservative–Social Democrat centrist |
| CON/STY | 5 | Conservative–Solidarity working-class right |
| STY/SD | 5 | Solidarity–Social Democrat |
| CON/POP | 4 | Conservative–Populist populist right |
| SD/LIB | 4 | Social Democrat–Liberal |
| CON/CUP | 4 | Conservative–Civic Union Party moderate |

---

## Chamber Vote Model

**Script:** `pipeline/chamber_vote_model.py`
**Outputs:** `data/outputs/senate/senate_vote_model.csv`, `data/outputs/house_vote_model.csv`

For each of **37 binary CC24\_ policy items**, models the probability of a bill passing a floor vote.

**Method — Sum-of-Independent-Binomials → Normal approximation:**
```
E[Y]    = Σᵢ nᵢ · pᵢ                               (expected yes votes)
σ²[Y]   = Σᵢ nᵢ · pᵢ · (1 − pᵢ)
P(pass) = 1 − Φ((majority − 0.5 − E[Y]) / σ[Y])    (continuity correction)
```
where `nᵢ` = seats held by type `i`, `pᵢ` = that type's % supporting / 100.

**Verdict thresholds:** PASS ≥67% | TOSS-UP 33–67% | FAIL ≤33%
**Results (both chambers):** 29 PASS / 1 TOSS-UP / 7 FAIL

These chambers are cross-cutting — they simultaneously pass both tax cuts AND tax hikes, both border enforcement AND Dreamer protections. Different majority coalitions form for each vote. This is expected behavior for proportional multi-party representation.

---

## Coalition Analysis

**Script:** `pipeline/cross_chamber_coalitions.py`
**Output:** `data/outputs/coalitions/`

Shows where senate and house party types align **within** each of the 5 factor dimensions — revealing issue-specific coalition partners rather than overall ideological proximity.

**23 types:** 20 senate types (blends + pure) + 3 house-only pure types not in senate (NAT, DSA, PRG).

**Per-factor analysis:**
- `k=2` poles: 1D k-means on the 23 winner types → which "side" each type falls on
- Absolute tiers: fixed EFA scale thresholds → position relative to the full electorate

| Output File | Contents |
|-------------|----------|
| `coalition_type_profiles.csv` | 23 rows: F1–F5 scores, chamber tag, seat counts |
| `coalition_factor_alignment.csv` | 115 rows: per-(factor × type) rank, k=2 pole, absolute tier |
| `coalition_pairwise.csv` | 253 pairs: per-factor distances, normalized alignment scores (0–1) |

---

## Output Files Reference

All outputs are under `data/outputs/`.

| File | Description |
|------|-------------|
| `No_C7_canonical/stv_seat_summary.csv` | House seat totals by party and density tier |
| `No_C7_canonical/stv_results_by_district.csv` | Per-district STV results with round-by-round elimination |
| `No_C7_canonical/transfer_matrix_directed.csv` | Vote transfer % when each party is eliminated |
| `affinity/second_choice_row_pct.csv` | % of each party's voters ranking each other party 2nd |
| `affinity/mean_rank_proximity.csv` | Full preference ordering proximity (0=far, 1=close) |
| `affinity/factor_mahalanobis.csv` | Mahalanobis distance between cluster centroids in 5D factor space |
| `profiles/cluster_stats.csv` | Per-item statistics for all 10 clusters (policy + demographics) |
| `profiles/blend_stats.csv` | Same stats for senate blend candidate types |
| `senate/senate_composition.csv` | One row per state: Condorcet senator type + vote shares |
| `senate/senate_irv_composition.csv` | One row per state: IRV winner + runner-up |
| `senate/senate_chamber_profile.csv` | Policy/demographic profiles for 18 senate types + aggregates |
| `senate/senate_vote_model.csv` | 37-item bill passage probability (senate) |
| `senate/senate_voting_blocs.csv` | Ward clustering of senate types in 5D factor space |
| `senate/candidate_proximity.csv` | Pairwise Euclidean distance between senate candidate types |
| `house_chamber_profile.csv` | Policy/demographic profiles for house (canonical scenario) |
| `house_vote_model.csv` | 37-item bill passage probability (house) |
| `coalitions/coalition_type_profiles.csv` | 23 types with factor positions and seat counts |
| `coalitions/coalition_factor_alignment.csv` | Per-factor pole and tier assignments |
| `coalitions/coalition_pairwise.csv` | Pairwise factor alignment scores |

---

## Running the Pipeline

All scripts live in `pipeline/` and use relative paths anchored to the project root.

```bash
# ── STV House ──────────────────────────────────────────────────────────────
python3 pipeline/stv_main.py                       # Full run steps 1–5 (~3.5s)
python3 pipeline/stv_main.py --steps 3,4,5        # Resume from ballot checkpoint
python3 pipeline/stv_affinity.py                   # Inter-party affinity matrices
python3 pipeline/cluster_profile_viz.py            # HTML cluster profile reports

# ── Senate & Analysis ──────────────────────────────────────────────────────
python3 pipeline/run_senate_simulation.py          # Condorcet senate (~30s)
python3 pipeline/run_senate_irv.py                 # IRV senate alternative
python3 pipeline/generate_candidate_profiles.py    # Candidate factor centroids
python3 pipeline/generate_blend_stats.py           # Blend candidate policy profiles
python3 pipeline/senate_chamber_profile.py         # Senate chamber policy aggregate
python3 pipeline/house_chamber_profile.py          # House chamber policy aggregate
python3 pipeline/senate_voting_blocs.py            # Hierarchical voting bloc clustering
python3 pipeline/chamber_vote_model.py             # Bill passage probabilities
python3 pipeline/cross_chamber_coalitions.py       # Cross-chamber coalition analysis

# ── Visualization ──────────────────────────────────────────────────────────
cd viz && python3 scripts/prepare_data.py          # Regenerate JSON from outputs
npm run dev                                        # Dev server
npm run build                                      # Production build → dist/
```

---

## Dependencies

```
python3 >= 3.10
numpy
pandas
scipy
scikit-learn
pyreadstat      # Stata .dta reading
pyarrow         # Parquet I/O for ballot checkpoint
plotly          # HTML cluster profile visualizations
```

---

## Data Sources

| Dataset | Description | Path |
|---------|-------------|------|
| 2024 CES | ~60,000 respondents, 2024 Cooperative Election Study | `data/raw/2024 CES Base/CCES24_Common_OUTPUT_vv_topost_final.dta` |
| Typology | DPGMM cluster assignments (45,707 rows) | `data/processed/typology_cluster_assignments.csv` |
| EFA scores | 5 factor scores per respondent | `data/processed/efa_factor_scores.csv` |
| Polychoric matrix | 24×24 polychoric correlation matrix | `data/processed/polychoric_matrix.csv` |

**Analysis sample:** N=45,707 after listwise deletion (24 items + `commonpostweight` non-missing).
