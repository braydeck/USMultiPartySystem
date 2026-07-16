# Methodology

How 45,707 survey responses become a ten-party legislature. Every step uses a
published method; the goal is a transparent, reproducible pipeline, not a forecast.

## Data

**2024 Cooperative Election Study (CES)**, Harvard/YouGov. The CES is one of the
largest academic surveys of US political opinion (~60,000 respondents). The analysis
sample is **N = 45,707** after listwise deletion on the 24 policy items used for the
factor model plus the post-stratification weight (`commonpostweight`). Raw CES
microdata is downloaded from the source (Harvard Dataverse), not redistributed here;
see [`DATA_SOURCES.md`](DATA_SOURCES.md).

## 1. Factor analysis (5 ideological dimensions)

Polychoric exploratory factor analysis (EFA) with oblique (promax) rotation reduces
24 policy items to **5 latent dimensions**:

| Factor | Reads as |
|--------|----------|
| F1 — Security & Order | policing, border enforcement, surveillance |
| F2 — Electoral Skepticism | belief that elections are run fairly |
| F3 — Government Distrust | general institutional trust |
| F4 — Religious Traditionalism | church attendance, abortion, same-sex marriage |
| F5 — Populist Conservatism | immigration, fiscal, and racial-traditionalism cluster |

These are latent factors, not imposed categories: they are the patterns that emerge
from how responses actually correlate. Full item loadings are in
[`EFA_FACTORS.md`](EFA_FACTORS.md).

## 2. Clustering (the parties)

A Dirichlet Process Gaussian Mixture Model (DPGMM) groups respondents by their 5
factor scores. It returns **10 clusters**, all kept as parties — including cluster 7, the Order & Opportunity Party (OAO), a law-and-order Democratic bloc formerly labeled "Blue Dogs." Parties are not named by hand; the
labels are assigned afterward from each cluster's factor profile.

## 3. Ballot generation

Each respondent is turned into a ranked ballot by comparing their 5D factor-score
vector to each candidate's position in the same space. Similarity decays with a
Gaussian proximity kernel (σ = 0.35, η²-weighted per factor). Within a party, candidate
order is broken by a prominence prior (a 40/35/25 name-recognition split via
Plackett-Luce sampling), so the top candidate does not sweep all same-party ballots.

Two candidate fields are generated:
- **Party-line** — 3 identical-platform candidates per party (`STY_1`, `STY_2`, …).
- **Crossover** — 9 base candidates plus 28 variants, each shifted ±25% of the
  inter-party standard deviation on one axis (e.g. `STY_hi_so`, `CON_lo_pc`).

## 4. Elections

| Office | Method | Output |
|--------|--------|--------|
| House (873 seats, 180 multi-member districts) | STV — Droop quota, Gregory surplus transfers | `pure_multi/house/`, `factor_deviation/house/` |
| Senate (51 seats) | IRV and Ranked-Pairs Condorcet | `pure_multi/senate/`, `factor_deviation/senate/` |
| President | Rolling STV primary, then IRV + Condorcet general | `pure_multi/`, `factor_deviation/` |

Each office is run under both candidate fields and (for single-seat offices) both
counting methods, producing the four scenarios the app compares.

## Reproducibility

- Pipeline scripts live in [`../pipeline/`](../pipeline); the published per-party
  numbers come from the viz data files (see [`DATA_SOURCES.md`](DATA_SOURCES.md)).
- `python pipeline/print_canonical_numbers.py` prints the canonical House and Senate
  results straight from the viz data, so any figure quoted in a write-up can be checked.
- Apportionment: Hamilton method, ~380,000 people per seat (2020 Census).

## Caveats

This is a simulation, not a prediction. It assumes **sincere voting** (no strategic
ranking), a **static ideological space** (the factor structure is fit once and held
fixed), and **perfect party cohesion** in the legislation model. Party formation,
candidate emergence, campaign dynamics, money, and media are all absent. The CES sample
also skews more educated and engaged than the voting public. Full limitations are in
the app's "What Is This?" page under Caveats.
