# CES listwise check: re-estimated loadings

Written 2026-11-02. CES 2024 Common Content, 49,432 respondents with `commonpostweight` (45,214 complete on
all 24 items, 4,218 dropped by listwise deletion today). Scripts: `reestimate_loadings.py`, `rescore_refit.py`.

**Re-estimating the factor loadings on all 49,432 respondents dissolves CUP and leaves the other eight
parties recognizable. The loading change that does it is the size of ordinary resampling noise, and it
dissolves CUP whether or not the 4,218 dropped respondents are added.**

## The loadings

- The pairwise polychoric matrix on all 49,432 moves no correlation by more than 0.032 from the listwise
  matrix (mean 0.007). The largest moves all involve the abortion-ban item `CC24_324b`.
- Factor congruence with production (Tucker φ): Security & Order 0.996, Religious Traditionalism 0.987,
  Institutional Distrust 0.985, Populist Conservatism 0.982, Government Distrust 0.964. All five clear the
  0.95 "essentially identical" bar.
- Individual loadings move up to 0.15. Federal government trust `CC24_423` shifts from Government Distrust
  (0.65 → 0.55) toward Institutional Distrust (0.26 → 0.40).
- A 50-draw bootstrap of the listwise sample, no pairwise change at all, moves loadings as far: median
  largest loading change 0.09 to 0.18 per factor. The pairwise φ sits at about the bootstrap median for
  every factor (42% to 74% of draws are further from the listwise solution). Some bootstrap draws rotate
  much further (Government Distrust φ as low as 0.57).
- Parallel analysis gives k = 4 on the production, listwise and pairwise matrices alike.
- Code change is negligible: the exact polychoric reproduces production's matrix to within 0.015 per cell
  on production's own sample, and production's matrix refits to `efa_loadings_k5_final.csv` exactly.

## The parties

Rescored with the pairwise loadings (49,428 eligible; 4 answer under half of some factor's items) and
refit with the production 20-seed DPGMM procedure: 4 solutions, modal 10 of 20, ARI 0.61 against
production. Production seeds under frozen loadings range 0.65 to 0.97 against production.

| Party | Production share | Refit share | Members kept |
|---|---|---|---|
| NAT | 9.4% | 10.9% | 99% |
| DSA | 5.9% | 5.9% | 92% |
| PRG | 5.9% | 5.2% | 90% |
| CON | 20.5% | 24.1% | 90% |
| STY | 17.4% | 19.8% | 89% |
| POP | 11.0% | 11.6% | 85% |
| LBR | 10.7% | 9.6% | 66% |
| DAL | 8.2% | 9.3% | 64% |
| CUP | 11.1% | 3.6% | 13% |

- Production CUP's members go to CON (42%), STY (17%), POP (15%), DAL (12%); 13% stay.
- The refit cluster matched to CUP is a different group: high Security & Order (+0.96 SD), low on both
  distrust factors (−0.99, −1.00), low Religious Traditionalism (−0.37) and low Populist Conservatism
  (−0.74). Production CUP is +0.66, −0.90, −0.54, +0.37, +0.21. The refit cluster draws 22% of DAL.
- Scoring only the 45,214 complete respondents with the same pairwise loadings gives the same result:
  ARI 0.62, CUP keeps 13%, the other eight keep 63% to 99%. Adding the dropped respondents moves nothing.
  The earlier frozen-loadings refit with the dropped added matched production at ARI 0.97.

## What this bears on

- Listwise deletion is not what threatens the typology. Adding the 4,218 respondents changes party shares
  by under 0.8 pp under frozen loadings, and changes nothing further under new loadings.
- CUP depends on one draw of the loadings. The production bootstrap (`analysis/bootstrap/recluster.py`)
  refits the DPGMM on fixed factor scores, so its intervals carry clustering and vote uncertainty but not
  loading uncertainty.
- Untested: how often CUP survives across bootstrap loading draws. That needs a DPGMM refit per draw
  (about 3 minutes each at 20 seeds).

## Outputs

`outputs/loadings_compare.csv`, `outputs/loadings_bootstrap.csv`, `outputs/loadings_pairwise.csv`,
`outputs/polychoric_{repro,listwise,pairwise}.csv`, `outputs/reestimate_run.log`;
`outputs/rescore_parties[_complete].csv`, `outputs/rescore_profiles[_complete].csv`,
`outputs/rescore_labels[_complete].npz`, `outputs/rescore[_complete]_run.log`. The score files
`outputs/rescore_scores[_complete].csv` (17 MB) are not committed; `rescore_refit.py` rebuilds them in
seconds from the cached matrix and labels.
