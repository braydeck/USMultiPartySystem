# Nine-party typology: observed result and re-clustering bootstrap

The nine-party typology elects CON president under national IRV, with CON beating LBR by 2.5 points in the final round. Ranked Pairs elects STY. The 200-draw re-clustering bootstrap shows the same pattern. IRV elects CON in 152 of 200 draws (0.76). Ranked Pairs elects STY in 158 of 200 (0.79) and POP in the other 42. The two methods name the same winner in 37 of 200 draws.

All results use the app defaults: ballot depth top7, turnout gap 5%, double magnitude (873 House seats) and rawMulti. Each bootstrap draw re-clusters a resample of respondents. The election then runs on the full observed electorate of 45,214 respondents, so only the parties change between draws. Party IDs are matched to the seed-61 ten-party typology. The Senate figures are the observed default tree, not a bootstrap modal winner.

## Observed (full data, cap 9)

Five seeds (42 to 46, n_init 5) converge on the same nine clusters, with ARI 0.999. Seed 45 has the best lower bound (697.6) and is the one kept. The nine clusters match nine of the ten seed-61 parties. Each matched party retains 87% to 100% of its seed-61 voters. OAO has no cluster, and its ID fields only a zero-vote candidate, who drops out of the primary at the first stage.

| Party | Share % | Retained from seed 61 % | House STV | Party list | Senate IRV | Senate Ranked Pairs |
|---|---|---|---|---|---|---|
| CON | 20.5 | 89.0 | 201 | 193 | 22 | 11 |
| LBR | 10.7 | 93.4 | 130 | 108 | 23 | 12 |
| STY | 17.4 | 96.7 | 106 | 86 | 3 | 19 |
| NAT | 9.4 | 99.4 | 73 | 109 | 0 | 0 |
| LIB | 8.2 | 87.3 | 87 | 89 | 0 | 0 |
| POP | 11.0 | 93.2 | 115 | 99 | 3 | 8 |
| CUP | 11.1 | 89.0 | 95 | 93 | 0 | 1 |
| OAO | 0 | 0 | 0 | 0 | 0 | 0 |
| DSA | 5.9 | 99.4 | 31 | 38 | 0 | 0 |
| PRG | 5.9 | 100.0 | 35 | 58 | 0 | 0 |

The primary finalists are CON, LBR, LIB, POP and STY. At triple magnitude (1,726 seats), STV gives CON 394, LBR 245, STY 219, POP 188, NAT 178, LIB 178, CUP 166, PRG 89 and DSA 69. Under per-state IRV in the electoral college, LBR leads with 460 of 975 electors, short of the 488 majority.

## Bootstrap, 200 draws

| National IRV winner | Draws | P |
|---|---|---|
| CON | 152 | 0.76 |
| STY | 24 | 0.12 |
| POP | 14 | 0.07 |
| LBR | 10 | 0.05 |

| National Ranked Pairs winner | Draws | P |
|---|---|---|
| STY | 158 | 0.79 |
| POP | 42 | 0.21 |

The IRV final round is CON against LBR in 160 of 200 draws. The median final-round margin is 3.5 points, the 10th to 90th percentile range is 1.4 to 10.2, and 33 draws are decided by under 2 points. Each House figure below is the median, with the 10th to 90th percentile in brackets. It counts only the draws where that party's ID went to a cluster holding at least 50% of the seed-61 party's voters.

| Party | Matched ≥ 50% | ID left empty | Primary finalist | House STV | Party list | Senate IRV median | Senate RP median |
|---|---|---|---|---|---|---|---|
| CON | 200 | 0 | 200 | 206 (161-234) | 196 (145-215) | 24 | 10 |
| LBR | 194 | 0 | 193 | 135 (106-147) | 113 (79-124) | 20 | 12 |
| STY | 199 | 1 | 161 | 110 (101-122) | 91 (85-99) | 4 | 18 |
| NAT | 200 | 0 | 26 | 74 (67-81) | 112 (105-118) | 0 | 0 |
| LIB | 146 | 51 | 139 | 100 (77-141) | 102 (82-136) | 1 | 0 |
| POP | 199 | 0 | 111 | 113 (101-130) | 106 (94-123) | 2 | 10 |
| CUP | 164 | 3 | 91 | 90 (77-102) | 80 (63-106) | 1 | 1 |
| OAO | 6 | 122 | 3 | 21 (12-26) | 42 (22-45) | 0 | 0 |
| DSA | 192 | 0 | 1 | 24 (12-35) | 31 (25-38) | 0 | 0 |
| PRG | 163 | 23 | 39 | 37 (30-109) | 61 (53-121) | 0 | 0 |

OAO is the empty ID in 122 draws. LIB is empty in 51 draws, PRG in 23, CUP in 3 and STY in 1. In 82 draws, every non-empty ID holds at least 50% of its seed-61 party. In the remaining 118, at least one cluster is a recombination of seed-61 parties. Bootstrap clusterings agree with the observed nine-party fit at median ARI 0.737 (10th to 90th percentile 0.640 to 0.926). Restricted to the 82 cleanly matched draws, IRV elects CON in 69 and Ranked Pairs elects STY in 78.

The electoral college is not a headline. Under per-state IRV, the leading party has a majority of electors in 35 of 200 draws, and CON leads in 119.

## Files

- `run_k9_bootstrap.py` is the driver. It is resumable, and its provenance and method are in the docstring.
- `observed.csv` holds the observed row.
- `per_draw.csv` holds one row per draw. It records shares, retention (`ret_*`), STV and list seats at double and triple magnitude, the presidency, the Senate and the electoral college.
- `summarize.py` prints the tables above.
- `seed61_party_ids.csv` is the frozen seed-61 caseid-to-party map that IDs are matched against.

Runtime is 38 minutes for the observed fit plus 200 draws. The draws take a median of 11 s each, and six single-threaded fits run alongside the election pipeline.
