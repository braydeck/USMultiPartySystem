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
| Conservative | 202 | 23.1% | 19.2% |
| Labor | 158 | 18.1% | 14.1% |
| Solidarity | 129 | 14.8% | 12.4% |
| Populist | 104 | 11.9% | 9.0% |
| Liberal | 92 | 10.5% | 9.2% |
| Civic Union Party | 89 | 10.2% | 8.6% |
| Nationalist | 43 | 4.9% | 9.8% |
| DSA | 26 | 3.0% | 6.0% |
| Order and Opportunity Party | 15 | 1.7% | 6.2% |
| Progressive | 15 | 1.7% | 5.6% |

**Conservative is the largest party (202).** Total = 873 across all ten parties. The crossover-field House result
is `fdHouseSeats.json` (a different scenario — candidates shift on one axis).

### `clusterProfiles.json` → `seatsHouse` is now safe to quote
It used to hold a cluster *population baseline* (CON=164, SD=166, STY=160), which is what made
older write-ups call SD the largest party. `prepare_data.py` now sources it from
`pure_multi/house/stv_seat_summary.csv`, the same run the House tab shows, so it is identical
to `houseSeats.json` for all ten parties. Verified 2026-09-12.

One naming difference between the two files: cluster 8 is `DSA` in `houseSeats.json` and
`Democratic Socialists` in `clusterProfiles.json`. Join on `party` (the code), not `partyName`.

*The `canonical` / `canonical_triple` directories are kept for their inputs:* the pure_multi
and factor_deviation runs read their `ballots_checkpoint.parquet` + `district_apportionment.csv`.
The outdated 850-seat `canonical/stv_seat_summary.csv` was deleted 2026-09-12, along with the
`transfer_matrix_10party.csv` that predated OAO — `transferMatrix.json` is now built from
`pure_multi/house/transfer_matrix_10party.csv`.

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
| LBR | 15 | 30 | 17 | 33 |
| STY | 29 | 12 | 30 | 6 |
| CON | 1 | 7 | 1 | 12 |
| POP | 5 | 2 | 2 | 0 |
| CUP | 1 | 0 | 1 | 0 |

These four files are the no-turnout-weighting (λ=0) runs. The app defaults to a 5% turnout gap
and reads `pureMultiSenate{Condorcet,IRV}TurnoutL5.json` instead, where the totals differ.

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
