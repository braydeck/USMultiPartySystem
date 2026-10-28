# DPGMM seed sweep

The presidential winner changes with the clustering solution. National IRV elects four different parties across six seeds: LBR at seed 61, POP at 43, STY at 45, and CON at 42, 53 and 58. Ranked Pairs elects STY at four of six seeds and POP at the other two. Conservative is the largest House STV party at every seed, with 162 to 224 of 873 seats.

Each row is one representative seed per solution family in `data/processed/dpgmm_seed_selection.csv`. Seed 61 is the kept medoid. All rows use the app defaults: ballot depth top7, turnout gap 5%, double magnitude, rawMulti. The Senate figures are the observed `pure_multi_turnout_l5_top7` tree, not the bootstrap modal winner that the Senate map renders. Bootstraps were not rebuilt.

Seed 61 is the control. Rebuilt in this harness, all 1,629 output files it shares with the main checkout match. Four parquet checkpoints differ only in file metadata, and their tables are identical.

| Seed | Lower bound | ARI vs 61 | Primary finalists | Pres. IRV (final round) | Pres. Ranked Pairs | Senate IRV, top 3 | Senate Ranked Pairs, top 3 |
|---|---|---|---|---|---|---|---|
| 61 | 1,502 | 1.00 | CON CUP LBR LIB STY | LBR 51.4 v CON 48.6 | STY | LBR 18, CON 15, STY 15 | STY 23, POP 14, LBR 11 |
| 43 | 1,447 | 0.83 | CON CUP LBR LIB POP | POP 63.9 v CON 36.1 | POP | STY 19, CON 13, POP 9 | POP 19, STY 17, LBR 10 |
| 45 | 1,391 | 0.74 | CON CUP LBR LIB STY | STY 55.2 v CON 44.8 | STY | CON 23, LBR 14, STY 5, POP 5 | STY 17, LBR 16, POP 9 |
| 42 | 1,705 | 0.67 | CON CUP LBR POP STY | CON 50.7 v LBR 49.3 | STY | CON 23, LBR 22, STY 5 | STY 22, LBR 16, CON 9 |
| 53 | 2,522 | 0.64 | CON LBR LIB NAT STY | CON 50.5 v LBR 49.5 | STY | CON 24, LBR 21, STY 5 | STY 21, LBR 13, CON 9 |
| 58 | 1,170 | 0.60 | CON LBR LIB OAO POP | CON 50.4 v LBR 49.6 | POP | CON 22, LBR 22, POP 4 | POP 16, LBR 15, STY 13 |

House STV seats (double, 873):

| Seed | CON | LBR | STY | NAT | LIB | POP | CUP | OAO | DSA | PRG |
|---|---|---|---|---|---|---|---|---|---|---|
| 61 | 189 | 130 | 111 | 70 | 102 | 117 | 82 | 26 | 24 | 22 |
| 43 | 190 | 106 | 107 | 71 | 131 | 114 | 76 | 26 | 23 | 29 |
| 45 | 205 | 124 | 90 | 72 | 113 | 104 | 104 | 9 | 24 | 28 |
| 42 | 199 | 128 | 109 | 75 | 81 | 103 | 91 | 7* | 48 | 32 |
| 53 | 224 | 136 | 100 | 69 | 104 | 105 | 85 | 6 | 32 | 12 |
| 58 | 162 | 126 | 79 | 73 | 81 | 120 | 74* | 98 | 26 | 34 |

Weighted party share (%):

| Seed | CON | LBR | STY | NAT | LIB | POP | CUP | OAO | DSA | PRG |
|---|---|---|---|---|---|---|---|---|---|---|
| 61 | 16.4 | 10.0 | 17.3 | 8.9 | 8.2 | 11.2 | 10.0 | 7.2 | 5.5 | 5.4 |
| 43 | 16.4 | 8.0 | 16.4 | 8.9 | 10.7 | 11.3 | 10.0 | 7.4 | 5.3 | 5.7 |
| 45 | 19.3 | 9.2 | 15.8 | 9.2 | 9.4 | 10.1 | 10.9 | 4.9 | 5.7 | 5.5 |
| 42 | 20.1 | 10.0 | 17.3 | 9.4 | 7.5 | 10.1 | 10.9 | 4.2* | 5.9 | 4.8 |
| 53 | 21.5 | 10.0 | 16.5 | 9.4 | 9.5 | 9.7 | 9.3 | 3.9 | 5.6 | 4.7 |
| 58 | 16.6 | 10.0 | 14.3 | 9.1 | 7.9 | 11.4 | 8.4* | 11.5 | 5.2 | 5.7 |

\* The party ID is a label only. At seed 42, the cluster matched to OAO retains 0.0% of the reference OAO. That cluster is 61% seed-61 DSA and 39% seed-61 PRG, and the seed-61 OAO voters land mostly in CON. At seed 58, the cluster matched to CUP retains 0.2% of the reference CUP and is 74% seed-61 STY, while the seed-61 CUP voters land in "OAO". Seed 53's PRG retains 40% and its DSA 49%. LBR is the weakest match at every seed, retaining 36% to 48% of the reference (47.5% at seed 61). Every other party at every seed retains at least 50%, and NAT retains 86% or more everywhere. The `ret_ref_*` columns in `results.csv` give retention against `party_id_reference.csv`, and the `ret_61_*` columns give retention against seed 61.

`results.csv` also holds the triple-magnitude STV seats (`house3_*`), Sainte-Laguë party-list seats (`list_*` and `list3_*`, at λ = 5%), the full Senate counts, and the per-state IRV electoral-college leader. The electoral college uses 975 electors with a 488 majority, and seeds 42 and 53 deadlock.

Rerun with `python3 analysis/efa/exploration/seed_sweep/run_seed_sweep.py --work-dir <scratch> --main-checkout <main STV checkout>`. One seed takes about 105 s, and the full run takes about 13 minutes including the restore of seed 61.
