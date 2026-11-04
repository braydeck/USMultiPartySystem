# NEXT: CES typology (revised §3c rule)   (written 2026-11-04 by the session that ran the revised rule and chose the nine)

## Where it stands
- Ruled (`DECISIONS.md` 2026-11-04): the parties are the revised rule's cap-9 clusters on plain scores; residualization
  dropped for CES; the ten and the cap-8 rebuild are superseded.
- Revised rule run: `stage_c_v2.py` -> `outputs/stage_c_v2/` (41 items, factors RT/TR/SO/PC, labels for caps 2-10).
  Residualized run kept in `outputs/stage_c_v2_residualized/`.
- Profiles: `outputs/profile_nine/index.html` (`profile_ten.py 9`), `outputs/profile_v2_k9/` (`profile_v2.py 9`);
  the ten's pages are `outputs/profile_ten/`, `outputs/profile_v2/`.
- Held-out domestic items (`heldout_domestic.py`, `heldout_merge_a.py`): ten 0.169, nine 0.162, production 0.130.
- Unverified: the ten's page still shows redraw figures from the residualized run (`outputs/v2_draws/`).

## Handed off in parallel
- `analysis/efa/rebuild_nine_parties/NEXT.md`: the production rebuild. Waits on the researcher for party names and
  quiz design, not on anything here.

## Running
- Factor-redraw test on the nine, detached (survives VS Code restarts): `v2_draws.py 9` -> `outputs/v2_draws_k9/`,
  log `outputs/v2_draws_k9_run.log`, started 2026-11-04, ~5 h. Rerun the same way if it died:
  `caffeinate -i .venv/bin/python -u v2_draws.py 9` from this folder (it resumes from `draw_labels.npz`).

## Next steps
1. When the redraw finishes: report per-cluster kept median and draws with a cluster under half against the ten
   (`outputs/v2_draws/summary.csv`, residualized) and the current ten (`outputs/four_dim_draws/`). Add it to
   `profile_nine` (`profile_ten.py` reads redraws only for cap 10; point `REDRAWS` at `v2_draws_k9` for cap 9).
2. Open, researcher's call: rename RT/PC to "Cultural Conservatism" / "Economic Right"; whether two immigration
   items are enough; checkbox items stay out; optional leave-one-battery-out held-out test.
3. Nothing here is committed. Commit with explicit paths when the researcher asks.

## Don't redo
- Cap choice: caps 7, 8 and 10 lose to 9 on stability or convergence; the 100-seed cap-9 run (`cap9_seeds.py`) was
  on residualized starts and is superseded by the plain-score run.
- Seed 48's better-bound cap-10 solution was checked and rejected (`resid_check_ces.py`, `DECISIONS.md`).
- ANES residualization is the researcher's to handle; don't message the ANES session about it.
- `.venv/bin/python` only; kill only this session's own processes (the ANES session runs jobs here too).
