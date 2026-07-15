# Electoral systems and polarization

Cross-national test of whether first-past-the-post / winner-take-all electoral systems are
associated with higher political polarization. **The writeup and all conclusions are in
[`FINDINGS.md`](FINDINGS.md).** This README is just how to reproduce it.

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # Python 3.11+ (validated on 3.13)
```

## Data

| Source | How to get it | In repo? |
|---|---|---|
| V-Dem (`v2cacamps` etc.) | `python src/acquire.py` downloads it; a slim cache (`data/raw/vdem_slim.parquet`) is committed | yes |
| QoG Standard (government type, legal origin, region, population) | `python src/acquire.py` | yes (committed) |
| **CSES IMD microdata** (citizen party like/dislike) | **Gated.** Register free at [cses.org](https://cses.org), download the IMD, and place the fixed-width files at `cses/cses_imd_syntax/cses_imd.dat` and `.../cses_imd.dct` | **no** (gitignored; ~570 MB, redistribution-restricted) |

**What runs without the CSES download:** the entire expert-measure (V-Dem) half — `build_panel.py`,
`analyze.py`, `analyze_bayes.py` — plus any figure that reads only the committed intermediate CSVs.
**What needs the CSES download:** everything citizen-level (`build_affpol.py`, `build_dyadic.py`,
`build_party_affect.py`, `build_cses_extras.py`, the `analyze_coldness_*`, `analyze_middle_clusters`,
`analyze_enp_mediation`, `analyze_affective_fractionalization`, and `viz_essay_panels` via
`affective_fractionalization.csv`).

## Run order

Full pipeline and per-script notes are in [`FINDINGS.md` §7](FINDINGS.md). Short version:

```bash
python src/acquire.py            # raw data (idempotent)
python src/build_panel.py        # country-year panel  -> data/analysis_panel.parquet
python src/analyze_bayes.py      # expert-measure hierarchical Bayesian
# --- citizen half (requires the CSES download) ---
python src/build_affpol.py       # + build_dyadic / build_party_affect / build_cses_extras
python src/analyze_coldness_robustness.py   # coldness + common-law control + strict FPTP
python src/analyze_enp_mediation.py         # FPTP -> concentration -> polarization
python src/analyze_affective_fractionalization.py
python src/viz_essay_panels.py   # -> outputs/fig_essay_panel_a.png, _b.png, fig_essay_panels.png
```

## Outputs

Every figure/table and the script that writes it are indexed in
[`outputs/README.md`](outputs/README.md). Superseded early outputs live in `outputs/archive/`.
Essay citations and paste-ready phrasings are in [`essay_sources.md`](essay_sources.md).

## Reproducibility caveats (see FINDINGS §6)

- Few FPTP democracies (3–6 in the citizen samples) → estimates are directional with wide intervals.
- FPTP is confounded with anglophone / common-law heritage and country size; the design is
  cross-country, so this cannot be fully separated.
- The citizen coldness result is measure-dependent and modest after controls (+0.30–0.44); the
  robust, headline finding is on the expert (V-Dem) measure.
