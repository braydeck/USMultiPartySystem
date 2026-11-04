# AGENTS.md: CES typology validation (ANES / GSS / CES team modules)

Read this first if you are an AI agent working in or citing from this folder. Owner: Brayden Decker (bdecker).
Set up 2026-11-02. Project-wide rules live in the repo's `CLAUDE.md`; this file covers the validation workstream only.

## What this study is

Tests whether the CES 2024 typology (five factors, nine parties) holds up in other surveys. ANES 2024 is tested two
ways: a matched EFA and clustering on the 18 items ANES shares with the CES (frozen crosswalk), and an independent EFA
and segmentation on ANES's own attitude items. A CES-to-ANES classifier is next. The plan is
`UNTRACKED/plans/ces_anes_gss_validation_plan.md`.

## Sources of truth (cite these, nothing else)

| Question | Current source | Notes |
|---|---|---|
| ANES independent segments (who is in which segment) | `anes/outputs/stage_c_nofp/clusters.csv`, `entry_test.csv`, `caps.csv` (primary since 2026-11-03; with-foreign-policy sensitivity in `anes/outputs/stage_c/`; named export pending rebuild) | Built by `anes/stage_c.py --no-foreign-policy` then `anes/stage_c_export.py` (shared Stage C rule, `docs/EFA_ITEM_SELECTION_ROBUSTNESS.md` §3c) |
| What each ANES segment looks like | Pending rebuild on the corrected pool (2026-11-03); the four-segment page is archived |  Built by `anes/segment_portraits_page.py` from `segment_descriptors.csv` (`anes/describe_segments.py`) |
| Matched vs independent ANES clusters side by side | Pending rebuild (2026-11-03) | `anes/describe_clusters.py` writes the JSON, `anes/cluster_profiles_page.py` renders it |
| ANES's own factor structure | `anes/outputs/stage_c_nofp/loadings_k7.csv`, `retention.csv` (with foreign policy: `anes/outputs/stage_c/`) | Built by `anes/stage_c.py` (§3c as revised 2026-11-03: k bounded to 3-7, 50-resample retention) |
| Whether the CES factors replicate on matched items | `anes/outputs/matched_loadings_anes_k5.csv`, `anes/outputs/bootstrap_phi_summary.csv` | `anes/matched_efa.py`, `anes/bootstrap_phi.py` |
| Whether CES parties survive in ANES-sized samples | `anes/outputs/clustering/benchmark_summary.csv` | Built by `anes/matched_clustering.py` |
| Which CES 2024 team-module items could profile clusters | `ces_team_modules_scan.md` | Scanned 2026-10-27 |
| How often each ANES factor passes the entry test across resamples | `anes/outputs/stage_c/entry_test.csv` (`resample_pass`, `resample_matched`) | Built by `anes/stage_c.py` |
| Whether ANES's segment count is limited by sample size or factor count | `anes/outputs/clustering/size_dims_recheck/summary.csv` | Built by `anes/size_dims_recheck.py` (2026-11-03, on the archived k = 17 run's items and respondents) |
| What ANES's factors merge into at CES's factor count | `anes/outputs/consolidation/merging_k4.csv`, `phi_k4.csv` (and k5) | Built by `anes/consolidation_check.py` (2026-11-03, pre-spending-battery pool, against the archived k = 17 factors) |
| How well ANES segments describe items they weren't built from (§3c step 6) | `anes/outputs/heldout/curve.csv`, `compare.csv`, `items.csv` | Built by `anes/heldout_test.py` (2026-11-03); leave-one-battery-out version `anes/outputs/heldout_lobo/curve.csv`, `steps.csv`, `items.csv` by `anes/heldout_lobo.py` |
| How each ANES pool item is coded | `anes/outputs/item_audit/audit.txt`, `flags.csv` | Built by `anes/item_audit.py` (2026-11-03) |
| Rulings and definitions | `DECISIONS.md` | |

Anything not in this table is working material. **Anything in `_ARCHIVE (superseded, do not cite)/` is superseded and
must never be cited**; `_ARCHIVE (superseded, do not cite)/MOVED.tsv` lists where each file came from and why.

## Folder map

```
/            AGENTS.md, DECISIONS.md, NEXT.md, ces_team_modules_scan.md
anes/        scripts, config/ (frozen crosswalk, independent item pool), outputs/
_ARCHIVE (superseded, do not cite)/
```

`anes/` is kept separate from the numbered layout: it is a code folder whose scripts import each other by path.

## Rules

- **Data stays local.** ANES and CES microdata live in `UNTRACKED/` and are never committed or pasted into a
  shareable output.
- **Report numbers come from the build.** Edit the script and rebuild; never hand-edit a generated HTML file.
- **Superseded is not a source.** Retire old outputs with the research-project-setup `archive.py`; never leave `.bak`
  copies beside current files.
- **Decisions go in DECISIONS.md** the day they're made, with the date.
- **Paths have spaces.** Quote them. Run scripts with the repo's `.venv/bin/python`.

## Start of every session

Read `NEXT.md` before anything else: it says where the work stands, what's waiting on the researcher, and what not to
redo. End each stage with the `handoff` skill, which rewrites it.
