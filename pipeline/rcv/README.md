# RCV Pipeline — Alaska & Maine

Every number on the IRV Case Studies tab is computed from ballot-level cast vote
records, not transcribed from published round summaries. That matters because the
interesting quantities — the pairwise (Condorcet) matrix and the multi-seat STV
result — do not exist in any official report; only ballots produce them.

## Build

```bash
bash   pipeline/rcv/download_cvrs.sh   # ~130 MB down, ~4 GB unpacked, gitignored
python pipeline/rcv/build_all.py       # writes data/outputs/rcv/*.json
cd viz && python3 scripts/prepare_data.py
```

`build_all.py` runs the three builders below and is the only entry point you need.

## Sources

| Builder | Covers | Source |
|---|---|---|
| `process_dominion_cvr.py` | All 6 Alaska statewide RCV contests | Dominion CVR exports from the [Alaska Division of Elections](https://www.elections.alaska.gov/election-results/) |
| `fetch_ranked_vote.py` | Maine's 2018 CD2 general and 6 ranked primaries | [ranked.vote](https://ranked.vote/) report JSON (CVR-derived, CC-BY) |
| `official_reports.py` | Maine 2022 CD2 general | [Maine SoS RCV summary report](https://www.maine.gov/sos/cec/elec/results/) — rounds only; no CVR released |

Maine's 2022 CD2 is the one contest without ballot-level data, so it carries
`condorcetAvailable: false` and the viz says so rather than guessing.

`candidates.py` holds display names and ballot-line parties; both builders route
candidate lists through it, and it raises on an unknown general-election candidate
rather than silently emitting a blank party.

## Which contests are included

Only contests RCV actually governed. Alaska's 2022 Governor and 2024 President
races are built even though a first-choice majority ended them in one round —
that fact is reported on the tab. Contests where ranked ballots do not apply
(Maine's state general elections) appear only in the coverage grid.

Alaska adopted RCV in 2020 (Ballot Measure 2, first used 2022) for all state and
federal general elections. Maine adopted it in 2016 (Question 5, first used 2018)
for federal general elections and all primaries, but not for state general
elections.

## Validation

The Dominion processor was checked against two independent references:

- **Official round tallies.** Final-round results match the Division of Elections
  to within 9 votes out of ~250,000 (0.004%) on every Alaska contest, and every
  round's ordering and eliminations match.
- **ranked.vote's independent CVR processing.** On the 2022 special election, all
  twelve pairwise cells agree to within 0.03 percentage points, and the ballot
  count matches exactly (192,289).

First-round shares differ from the Division's *summary report* by up to ~0.5pp
because a ballot whose first ranking is blank is counted here for its next ranked
candidate, as the RCV tabulation itself does, while the summary report's
"first choice" column counts literal rank-1 marks. The `provenance` field on every
race records the exact file the numbers came from.

## Tabulation rules

Following Alaska statute as implemented by the Division of Elections: an overvote
exhausts the ballot at that rank, a single skipped rank is passed over, two
consecutive skipped ranks exhaust the ballot, and a repeated candidate is ignored
after the first ranking. Alaska eliminates one candidate per round; Maine
batch-eliminates trailing candidates who cannot mathematically catch the next one
up (`--batch-eliminate`).

STV uses a Droop quota with Weighted Inclusive Gregory surplus transfers, run at
double the state's current seat count — Alaska's one at-large seat becomes two.
Maine is not run per-district: the proposal pools both districts into a single
4-seat delegation, and no statewide ranked ballots exist to tabulate that from, so
the tab shows the CES simulation's delegation instead.

## Legacy

`process_rcv.py` was the earlier CSV-based script, deleted 2026-08-10. It had never
been run against real data, nothing in the build imported it, and its STV routine
counted eliminated candidates as elected. `process_dominion_cvr.py` supersedes it;
recover the old file from git history if it is ever wanted.

## USDA RUCC codes (County Tier Map — unrelated to RCV)

Download `rucc2013.xlsx` from [USDA ERS](https://www.ers.usda.gov/data-products/rural-urban-continuum-codes/)
and save as `data/raw/rucc2013.csv` with columns `FIPS`, `RUCC_2013`.
RUCC 1–3 → URBAN, 4–5 → SUBURBAN, 6–9 → RURAL.
