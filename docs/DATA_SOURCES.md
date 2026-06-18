# Data Sources — Single Source of Truth

Before quoting any simulation number in a doc, post, or README, get it from the file
listed here (or run `python pipeline/print_canonical_numbers.py`). **Do not hand-read
`clusterProfiles.json` for seat counts** — that is the mistake that put wrong numbers in
every write-up.

The **viz data files (`viz/src/data/*.json`) are canonical** — they are what's published
and what the app displays. Treat them as ground truth for public-facing claims.

## House party sizes ("seats won", "largest party")

**Source:** `viz/src/data/houseSeats.json` (= `data/outputs/pure_multi/house/stv_seat_summary.csv`)
This is the **party-line** (a.k.a. `rawMulti` / pure_multi) STV result — the viz's default House view.

| Party | Seats | Seat % | Pop % |
|-------|------:|------:|------:|
| Conservative | 202 | 23.1% | 18.7% |
| Social Democrat | 164 | 18.8% | 15.6% |
| Solidarity | 130 | 14.9% | 15.0% |
| Civic Union Party | 103 | 11.8% | 9.9% |
| Populist | 99 | 11.3% | 11.0% |
| Liberal | 93 | 10.7% | 9.3% |
| Nationalist | 46 | 5.3% | 9.2% |
| DSA | 22 | 2.5% | 6.3% |
| Progressive | 14 | 1.6% | 5.0% |

**Conservative is the largest party (202).** Total = 873. The crossover-field House result
is `fdHouseSeats.json` (a different scenario — candidates shift on one axis).

### DO NOT use these for "seats won"
- `clusterProfiles.json` → `seatsHouse` (CON=164, **SD=166**, STY=160): cluster *population
  baseline*, not an election result. This is the field that made every old doc say "SD is
  largest." It only sizes the IdeologicalConstellation dots.
- `data/outputs/No_C7_canonical/stv_seat_summary.csv` (CON=136, total **750**): an **outdated
  seat summary** — never quote it for seat counts; it predates the pure_multi result.
  *The `No_C7_canonical` / `No_C7_triple` directories themselves are NOT dead and are kept on
  purpose:* the pure_multi and factor_deviation runs read their `ballots_checkpoint.parquet`
  + `district_apportionment.csv` as inputs, and the viz's `transferMatrix.json` is built from
  `No_C7_canonical/transfer_matrix_10party.csv`. Only the seat-summary CSV is stale.

## Senate seats (51, four scenarios)

| Scenario | Source file |
|----------|-------------|
| Crossover × Condorcet | `viz/src/data/fdSenateCondorcet.json` |
| Crossover × IRV | `viz/src/data/fdSenateIRV.json` |
| Pure-partisan × Condorcet | `viz/src/data/pureMultiSenateCondorcet.json` |
| Pure-partisan × IRV | `viz/src/data/pureMultiSenateIRV.json` |

Each is an array of 51 records; `senatorParty` = winning party, `senatorCode` = winning
candidate variant, `stateAbbr`/`stateFips` = state. Party totals:

| Party | Cross-Cond | Cross-IRV | Pure-Cond | Pure-IRV |
|-------|:--:|:--:|:--:|:--:|
| STY | 34 | 19 | 33 | 11 |
| SD | 11 | 27 | 15 | 26 |
| CON | 1 | 3 | 1 | 11 |
| POP | 5 | 1 | 1 | 2 |
| CUP | 0 | 1 | 1 | 0 |
| LIB | 0 | 0 | 0 | 1 |

## Party policy %s and demographics

**Source:** `viz/src/data/clusterProfiles.json` → `variables[KEY]` per party.
- `variables[KEY].pct` = that party's support/share; `.overall` = national average; `.question` = label.
- `keyPositions` = the party's top differentiating positions (what the viz card shows).
- Factor scores `F1`–`F5` and `z_F*`/`pctile_F*` are stable; the per-policy `pct` values
  were **regenerated at least once**, so older write-ups drifted. Always re-pull.
- Solidarity (STY) has **below-average union membership** (4.4% current vs 5.8% national;
  9.1% former vs 16.0%). Despite the name, do **not** describe them as a union/labor party.

Variable-key quirks (EFA doc key vs data key, non-percentage items) are documented inline in
the viz; check `clusterProfiles.json` to confirm a key before mapping it.

## Quick check

```
python pipeline/print_canonical_numbers.py
```
Prints the House party-line totals, all four Senate scenarios, and the "do not use" list.
