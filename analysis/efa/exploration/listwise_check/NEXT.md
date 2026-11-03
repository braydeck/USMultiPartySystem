# NEXT: CES listwise check   (written 2026-11-02 by the session that re-estimated the loadings, refit, and scanned caps)

## Where it stands
- Done and ruled (`DECISIONS.md` 2026-11-02): replace production with the rescored cap-8 typology; no items added.
- Evidence in `findings.md`: loadings hold (φ ≥ 0.964; changes within bootstrap noise); the new loadings dissolve CUP with or without the 4,218 added respondents; cap 8 is the most reproducible cap (`outputs/kscan/`).
- Per-party survival numbers behind the ruling (production cap 9 vs rescored caps 8 and 9) were computed inline from `k_stability/outputs/fair/labels.npz` and `outputs/kscan/labels.npz`; they're in `DECISIONS.md`, not in a script.

## Handed off in parallel
- `analysis/efa/rebuild_eight_parties/NEXT.md`: the production rebuild. Not waiting on anything from here.

## Next steps (optional, after the rebuild)
1. Loading-draw test: the 50 draws in `outputs/loadings_bootstrap.csv` (rebuild each with seed-42 resampling as in `reestimate_loadings.py`), score, run the 20-seed DPGMM at cap 8, record each party's kept share. Not a gate (`DECISIONS.md`).
2. Larger CES item pool as its own check. Rule proposed by the ANES session: curate for construct reasons, never cull for missingness, handle missing answers at scoring. An earlier uncurated CES pool gave an unstable factor solution. This is the test that squares CES with ANES: ANES got the Stage A/B screen only (99 items, 10 clean factors); CES got the screen plus a discretionary domain-coverage trim, justified because the screened ~63-item CES pool was numerically degenerate (Heywood cases, non-positive-definite, k ≈ 2–3, dominated by the `CC24_444` state-culture battery; `docs/EFA_ITEM_SELECTION_ROBUSTNESS.md` §6). CES only; the ANES pool doesn't change. Rule, fixed before running: (a) the Stage A/B screen; (b) numerical check: no Heywood case, positive-definite matrix, parallel-analysis k matching the fitted factors; (c) if it fails, drop items one at a time from the dominating battery, most partisan first (Stage B tie-break), until (b) passes; nothing else is trimmed. ANES passes at (b). Judge party changes against the step-1 noise floor; report per-party kept share and Jaccard, not just factor φ.
3. Cap rule: count a party dissolved by its failure share across resamples, not mean Jaccard < 0.5 (a party that vanishes in half the resamples passes the mean rule). Researcher hasn't ruled.

## Don't redo
- Caches in `outputs/` (three polychoric matrices, bootstrap draws, refit and scan labels). `rescore_scores*.csv` are uncommitted; `rescore_refit.py` rebuilds them in seconds.
- `.venv/bin/python` only (scipy 1.17 exact polychoric).
- `docs/EFA_ITEM_SELECTION_ROBUSTNESS.md` predates the 2026-10 rescore: its factor-layer verdicts stand (the polychoric was always label-coded), its party-layer columns and the "F3 is a near-null residual" limitation are stale.
