# Church-attendance "Don't know" leak: effect on party assignments

The 493 church "Don't know" respondents (1.56% of weighted sample) do not move the parties beyond what dropping any 493 random respondents does. That holds in the chain as briefed and in the exact production chain.

Script: `church_dk_impact.py` (seed 42; runs end to end in about 10 minutes). Log: `run.log`. Tables: `outputs/`.

## Finding that changes the brief's run A

Production's `efa_update.py` does not score the canonical recode. It scores raw numeric codes. Eighteen of the 24 items, church included, run in the opposite direction from `canonical_recode` and from the frozen polychoric matrix. The six that agree are CC24_302, CC24_325, CC24_421_1, CC24_421_2, CC24_423 and CC24_424. Item pairs coded this way agree in sign with the frozen matrix on 69% of pairs with |r| > 0.1. The canonical recode agrees on 100%.

- Scores built with production's coding match the saved `FS_F1..F3` at |r| = 1.000. They then reproduce the saved parties at ARI 1.000 (run P). A DPGMM refit on the saved scores also returns ARI 1.000, so the DPGMM is deterministic on identical input.
- The brief's run A (canonical recode, church = 7 for "Don't know") matches saved F3 at only |r| = 0.20. It matches the saved parties at ARI 0.495. The gap from a fresh refit to production comes from this item coding. DPGMM noise does not explain it.
- Raw church runs 1 = more than once a week through 6 = never, with 7 = "Don't know". The loadings read church in the reverse direction. So production scores "Don't know" as one step more religious than "more than once a week", and it scores everyone else's attendance backwards.
- In CC24_423 and CC24_424, raw code 8 is labeled "None at all", not "Not sure". Production recodes it to the midpoint (2) for 7,354 respondents on CC24_423.

Two measurements follow: the brief's runs on the canonical chain (A), and the same comparison on the exact production chain (P).

## Run A versus the saved production parties

ARI 0.495 on 45,707. Majority-party labels are one-to-one with all ten production codes.

| Production share, sorted (%) | A share, sorted (%) |
|---|---|
| 19.2, 14.1, 12.4, 9.8, 9.2 | 17.7, 16.5, 11.1, 9.9, 9.8 |
| 9.0, 8.6, 6.2, 6.0, 5.6 | 8.9, 8.1, 7.1, 5.5, 5.3 |

## Canonical chain: A versus B (the 493 dropped, polychoric recomputed)

- ARI 0.955 on the 45,214 shared respondents. 2.04% of them change party (weighted). B has 10 clusters.
- Every party's share moves by 0.52 pp or less. Full table: `outputs/A_verdict_table.csv`.
- The recomputed polychoric differs from the frozen matrix by at most 0.014.
- In A, the 493 sat 42% in STY, 18% POP, 16% CON, 8% NAT, 5% OAO and 4% CUP. Of their weight, 2 to 3% sat in each of LBR and LIB, and under 1% in each of DSA and PRG. In production they sat 23% STY, 19% LBR, 17% POP, 16% CON (`outputs/A_where_dk_sat.csv`).
- Noise floor, 493 random non-"Don't know" respondents dropped (seeds 42–46): ARI 0.986, 0.982, 0.638, 0.987, 0.982, with 0.6% to 22.0% changing party. Seed 44 flips OAO (−3.2 pp) and CON (+5.0 pp).
- B on the frozen matrix (`B_frozen`) lands in that same alternate solution: ARI 0.670, 21.8% changed. The DPGMM has at least two nearby solutions. Dropping any 493 rows can tip it into either one.

## Production chain: P versus P without the 493 (frozen matrix)

- P reproduces production at ARI 1.000. Production labels are used directly.
- Dropping the 493 gives ARI 0.929, with 4.27% changing party. Share changes are LBR −1.1 pp, POP +1.7 pp and STY −0.6 pp. Every other party moves 0.1 pp or less.
- Noise floor (seeds 42–46): ARI 0.48 to 0.65, with 25% to 42% changing party. Per-party swings reach 8.4 pp (POP) and 7.8 pp (LBR). Full table: `outputs/P_verdict_table.csv`.

## Verdict

The "Don't know" change is within the noise floor in both chains, for every party. In the canonical chain, A to B moves 2.0% of respondents at ARI 0.955. Random 493-row drops move 0.6% to 22%. In two of the ten parties, LBR (+0.29 pp) and DSA (−0.10 pp), B's share change slightly exceeds the five noise runs' largest. Both changes are under 0.3 pp. In the production chain, dropping the 493 disturbs the parties less than any random 493-row drop does. Random drops move production's own fit far more, at ARI 0.48 to 0.65.
