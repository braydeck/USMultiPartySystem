# Current Parties in the Parties Tab — Design

## Intent

On the **Parties tab** (`viz/src/tabs/CompareTab.tsx`), let the user pull today's
real parties — **Democratic, Independent, Republican** — into the comparison
alongside the ten formulated typology parties, and quantify **how different** each
formulated party is from the current ones. Current parties get a **full profile**
(every factor bar, policy row, demographic row, distribution, and constellation
ellipse), behind their own selector toggle group. A dedicated readout reports each
selected formulated party's **distance from today's parties** in two metrics.

This answers a question the tab can't currently ask: the formulated parties are
built from the same voters who today identify as D/I/R, so *"where does today's
Democratic Party sit in this new space, and how far is Progressive / Labor / DSA
from it?"* becomes visible and measured.

## Decisions (locked)

- **Definition of current parties:** self-reported party ID (`pid3`) only.
  `1 → DEM (Democratic)`, `2 → REP (Republican)`, `3 → IND (Independent)`.
  `pid3 ∈ {4 Other, 5 Not sure}` are dropped. No vote-based "third party."
- **Profile depth:** full — current parties are full columns in every row, not
  just factor space.
- **Distance metrics:** show **both** — factor-space (η²-weighted σ) and
  policy-space (mean per-item divergence).
- **Distance scope:** each selected *formulated* party vs the three current
  parties only (no full pairwise matrix).
- **Colors / treatment:** classic D/R/I hues, **desaturated + dashed outline**, so
  current parties read as "status quo" and stay visually distinct from the
  formulated-party palette.

## Codes, names, colors

New codes `DEM`, `IND`, `REP` (no collision with the ten party codes or FD
variants). Added to `viz/src/constants/parties.ts`:

- `PARTY_NAMES`: `DEM: 'Democratic'`, `IND: 'Independent'`, `REP: 'Republican'`.
- `PARTY_COLORS` (muted): `DEM: '#5b7fa6'` (muted blue), `IND: '#8a8f98'` (slate
  gray), `REP: '#a66b6b'` (muted red). `getBlendColor` already falls back to
  `PARTY_COLORS[code]`, so no change needed there.
- `CURRENT_PARTIES = ['DEM','IND','REP'] as const` and a helper
  `isCurrentParty(code: string): boolean`. Consumers use this to (a) render the
  dashed outline and (b) order current parties immediately after the US baseline.

## Data pipeline

### New script: `pipeline/build_current_party_profiles.py`

Computes the DEM/IND/REP counterpart of every existing per-cluster statistic by
**re-running the same aggregation grouped by `pid3`** on the row-aligned EFA
sample, then emits the three consumer artifacts the viz reads.

Inputs (both already present and row-aligned, N = 45,707):
- `CCES24_Common_OUTPUT_vv_topost_final (2).dta` (raw items)
- `data/processed/typology_cluster_assignments.csv` (`pid3`, `commonpostweight`,
  `FS_F1..FS_F5` / `FS_F4_resid`/`FS_F5_resid`, `cluster`)

Alignment follows `pipeline/add_compare_items.py`: listwise-filter the raw sample
to the same N=45,707 in the same row order as the typology file, then group rows by
`pid3` (weighted by `commonpostweight`).

Recode rules are ported from `analysis/efa/pipeline/efa_update.py` and
`pipeline/add_compare_items.py` (`REV_BINARY`, `CC24_325 = 40 − raw`, `CC24_303`
check, `CC24_423/424` value-8 → 2, `ideo5` value-6 → NaN, the `bin`/`incr`
families, etc.). The **variable list and per-variable metadata**
(`type`, `stat_label`, `question`, `domain`) are read from
`data/outputs/profiles/cluster_stats.csv`, so the output matches the existing rows
1:1 and no variable is missed or mislabeled.

Outputs:
1. `data/outputs/profiles/current_party_stats.csv` — same schema as
   `cluster_stats.csv` but with columns `overall`, `DEM`, `IND`, `REP` in place of
   `c0..c9`. Intermediate artifact consumed by `prepare_data.py`.
2. Injected DEM/IND/REP entries in `distributions.json` `parties` (range /
   composition / heatmap items).
3. Injected DEM/IND/REP entries in `clusterIntensity.json` items' `parties`.
4. `viz/src/data/currentPartyProfiles.json` — one object per current party in the
   **same shape as a `ClusterProfile`** (`variables`, `F1..F5`, `z_F*`,
   `pctile_F*`, `party`, `partyName`), built by reusing `prepare_data.py`'s
   `_extract_policy_vars` / factor-centroid logic against the pid3 columns.

Factor scores per current party = `commonpostweight`-weighted mean of
`FS_F1..FS_F5` over that pid3 group; `z_`/`pctile_` computed against the same
population mean/SD `build_cluster_profiles` already uses.

### Built-in correctness gate

For every variable, the script recomputes `overall` from the raw sample and
**asserts it equals the existing `overall`** in `cluster_stats.csv` (within a small
tolerance). A full match proves the recode is faithful and therefore the DEM/IND/REP
columns are trustworthy; any mismatch fails the build loudly with the offending
variable. This is the correctness contract for the whole feature.

### Wiring into `prepare_data.py`

- `build_cluster_profiles` is unchanged (still 10 clusters).
- A new `build_current_party_profiles()` in `prepare_data.py` reads
  `current_party_stats.csv` and writes `currentPartyProfiles.json`, reusing the
  existing variable/factor builders.
- **Default approach:** the new script *post-injects* DEM/IND/REP into the emitted
  `distributions.json` and `clusterIntensity.json` (computing each pid3 group's
  range/composition/heatmap and intensity values from the raw sample with the same
  recode), leaving `build_distributions` and `compute_intensity` untouched. This
  keeps the cluster builders and their diffs minimal. The correctness gate still
  guards the injected values.

## Viz changes

All in `viz/src/tabs/CompareTab.tsx` plus small shared pieces.

### Data plumbing

- Import `currentPartyProfiles.json`; merge its entries into the lookups so
  `getVariables` / `getFactorScores` resolve DEM/IND/REP: extend both to check a
  third source (`currentParties`) after `clusters` and `fdProfiles`.
- `DIST.parties` and the intensity items already carry DEM/IND/REP after the
  pipeline injection — no viz change needed for those beyond selecting the codes.

### Selector

- `PartySelector` gains a third, optional group (`currentParties?: {code,label}[]`)
  rendered as its own popover mirroring the Crossover popover: a **"Current
  parties"** trigger with DEM / IND / REP chips. Selected current-party chips stay
  visible in the bar when the popover is closed, like crossover chips.
- Current-party chips (and their bars/labels app-wide) get a **dashed outline** via
  `isCurrentParty(code)`.

### Ordering

`orderedSelected` and every fixed-order render place current parties immediately
after the US baseline column and before the formulated parties. Factor bars that
sort by z keep sorting by z (the dashed treatment is enough to distinguish them);
the US-anchored columns (heatmaps, stacked bars, intensity) use
US → DEM → IND → REP → formulated.

### Factor scores & constellation

- `FactorBarRow` already renders any code with a factor score — current parties
  appear automatically once selected, with the dashed treatment.
- `IdeologicalConstellation` receives current parties as additional nodes (ellipses
  built from each pid3 group's factor spread, same as `clusterSpreads`). The
  pipeline emits a `currentPartySpreads` companion mirroring `clusterSpreads`;
  the constellation renders current-party ellipses dashed.

### Signature marks & divergence

Current parties participate fully: cohesion dot, D/M-vs-US mark, and the ◆
divergence test (`maxGap`) all include their values, since they are ordinary
columns once selected.

### Distance readout — "Distance from today's parties"

New component (e.g. `viz/src/components/parties/CurrentPartyDistance.tsx`), shown
when ≥1 formulated party is selected. For each selected formulated party, a row
listing DEM / IND / REP with both metrics, nearest highlighted:

- **Factor distance** — `sqrt( Σ_f η²_f · (z_party,f − z_current,f)² )` over the
  displayed factors `F1, F2, F4, F5` (F3 excluded, matching
  `FACTORS_BY_DISCRIMINATION`); η² from `factorLoadings.json` as already loaded.
  Reported in σ.
- **Policy divergence** — mean over all shared CES items of the per-item distance
  already computed in the tab (`itemSignature` distance for scalars, `tvd`/`emd`
  for distribution items). Reuses the existing functions; no new distance math.

Reads like: `PRG — nearest Democratic 1.9σ / 28 · Independent 3.1σ / 44 ·
Republican 4.2σ / 61`. Placed directly under the Factor Scores card.

## Files touched

**New**
- `pipeline/build_current_party_profiles.py`
- `viz/src/data/currentPartyProfiles.json` (generated)
- `viz/src/components/parties/CurrentPartyDistance.tsx`

**Modified**
- `viz/scripts/prepare_data.py` — emit `currentPartyProfiles.json`,
  `currentPartySpreads`, and inject DEM/IND/REP into distributions + intensity.
- `viz/src/constants/parties.ts` — codes, names, muted colors, `CURRENT_PARTIES`,
  `isCurrentParty`.
- `viz/src/components/shared/PartySelector.tsx` — third toggle group + dashed chips.
- `viz/src/tabs/CompareTab.tsx` — merge current-party lookups, ordering, wire the
  selector group, render the distance readout, pass current parties to the
  constellation.
- `viz/src/components/house/IdeologicalConstellation.tsx` — accept + render
  current-party ellipses (dashed).

## Out of scope

- 2024-vote-based groups and a "third party" bucket.
- Full pairwise distance matrix among all selected entities.
- Current parties on any tab other than Parties.
- Geographic / within-party variation (parties are ideological, not regional).

## Correctness & testing

- **Pipeline gate:** the `overall`-recompute assertion must pass for all ~348
  variables before any JSON is written.
- **Spot checks:** DEM/REP should sit near opposite ends of the strongest factor
  (F5), IND between them; verify against known CES marginals (e.g. `pid3` party
  ideology means).
- **Viz:** selecting DEM/IND/REP alone renders a coherent full profile; combined
  with formulated parties, divergence marks and the distance readout populate;
  dashed treatment is visible in chips, bars, and the constellation.
- Build passes `tsc`/lint; `prepare_data.py` runs clean end to end.
