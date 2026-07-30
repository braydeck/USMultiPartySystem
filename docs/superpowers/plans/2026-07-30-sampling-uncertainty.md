# Sampling Uncertainty and Probabilistic Seat Counts — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace exact seat counts with the most likely chamber plus a visible sampling range, and make every drill-down agree with the headline.

**Architecture:** A Python harness resamples CES respondents (stratified within state, N preserved), re-runs the four real pipelines per draw into temp dirs, and aggregates per-party seat distributions and per-state win probabilities into seven small `uncertainty*.json` files. The viz reads those files, shows the modal chamber as the headline with whiskers for the range, and substitutes a representative example run in the handful of states where the observed run would contradict the modal winner.

**Tech Stack:** Python 3.13 + numpy/pandas (no pytest in this repo — Python verification is assertion-based scripts run with `python3`), React 19 + TypeScript + Vite + Tailwind + shadcn/ui, vitest for JS tests.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-30-sampling-uncertainty-design.md`. Read it before starting.
- **Nothing canonical is written by the harness.** All pipeline output goes to temp dirs.
- **1000 draws, 7 turnout stops** (λ = 0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30), house ballot depth 7.
- Draw `d` uses seed `42 + d`. Record the seed in output.
- **Stratified within state, per-state N preserved exactly.** No draw may fail.
- Suffixes match `_build_turnout_variant`: `Turnout`, `TurnoutL5`, `TurnoutL10`, `TurnoutL15`, `TurnoutL20`, `TurnoutL25`, `TurnoutL30`.
- Cluster→party map (identical in every pipeline): `{0:CON, 1:LBR, 2:STY, 3:NAT, 4:LIB, 5:POP, 6:CUP, 7:OAO, 8:DSA, 9:PRG}`.
- **Never call these "credible intervals."** They are bootstrap percentile intervals. Copy must say so.
- **Never show candidate initials in UI** (project convention). Party labels only. `buildDisplayLabels` collapses `CON_1`→`CON` where a party fields one candidate.
- **Methodology copy goes in About → Caveats only.** Simulation cards get at most one short line each.
- Commit after every task. Direct to `main` (personal project convention, no PR flow).
- `turnout_weights` reads `TURNOUT_WEIGHT`/`TURNOUT_LAMBDA` at **import** time and macOS uses `spawn`, so workers must set `os.environ` then import pipeline modules **inside** the worker function. Threads will not work — pipelines carry module-level `OUTPUT_DIR` globals.

## File Structure

**Created:**

| path | responsibility |
| --- | --- |
| `analysis/bootstrap/__init__.py` | empty package marker |
| `analysis/bootstrap/resample.py` | `stratified_indices` — the only randomness |
| `analysis/bootstrap/inject.py` | `resampled_inputs` context manager patching `pd.read_csv` |
| `analysis/bootstrap/contests.py` | `run_draw` — one draw across all four contests |
| `analysis/bootstrap/representative.py` | `pick_representative` — modal slate → modal order → medoid |
| `analysis/bootstrap/aggregate.py` | `build_uncertainty` — draws → output dict |
| `analysis/bootstrap/selftest.py` | assertion-based verification, run with `python3` |
| `analysis/bootstrap_uncertainty.py` | CLI + multiprocessing over draws |
| `viz/src/components/shared/SeatWhisker.tsx` | whisker overlay primitive |
| `viz/src/components/shared/UncertaintyDetail.tsx` | collapsed interval + stability detail |
| `viz/src/lib/uncertainty.ts` | types + stop-indexed accessor |
| `viz/src/lib/uncertainty.test.ts` | vitest for the accessor and sum invariants |

**Modified:** `viz/scripts/prepare_data.py` (modal vote model), `viz/src/components/house/SeatShareBar.tsx`, `viz/src/components/senate/{SenateCompositionCard,SenateMap,SenateCoalitionCard,SenateWinnowCard,SenateCondorcetView}.tsx`, `viz/src/tabs/{SenateTab,HouseTab,PresidencyTab,PrimaryTab,LegislationTab,AboutTab}.tsx`, `viz/src/types/index.ts`.

---

## Phase 1 — Bootstrap harness

### Task 1: Stratified resampling core

**Files:**
- Create: `analysis/bootstrap/__init__.py`, `analysis/bootstrap/resample.py`, `analysis/bootstrap/selftest.py`

**Interfaces:**
- Produces: `stratified_indices(strata: np.ndarray, seed: int) -> np.ndarray` — int64 array, same length as `strata`, where every stratum contributes exactly its original count of (resampled, with-replacement) row positions.

- [ ] **Step 1: Write the failing test**

Create `analysis/bootstrap/selftest.py`:

```python
#!/usr/bin/env python3
"""Assertion-based verification for the bootstrap harness. Run: python3 analysis/bootstrap/selftest.py

This repo has no pytest; these are plain asserts so they run with the stdlib interpreter.
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from analysis.bootstrap.resample import stratified_indices


def test_preserves_stratum_sizes():
    strata = np.array([1, 1, 1, 2, 2, 3])
    idx = stratified_indices(strata, seed=42)
    assert len(idx) == len(strata), f"length {len(idx)} != {len(strata)}"
    got = Counter(strata[idx])
    assert got == Counter(strata), f"stratum sizes changed: {got} vs {Counter(strata)}"


def test_only_draws_within_stratum():
    strata = np.array([1, 1, 1, 2, 2, 3])
    idx = stratified_indices(strata, seed=7)
    # Resampled rows appear grouped by stratum, in sorted stratum order.
    assert list(strata[idx]) == sorted(strata), "rows leaked across strata"


def test_is_deterministic_and_seed_sensitive():
    strata = np.repeat(np.arange(20), 30)
    a = stratified_indices(strata, seed=42)
    b = stratified_indices(strata, seed=42)
    c = stratified_indices(strata, seed=43)
    assert np.array_equal(a, b), "same seed gave different draws"
    assert not np.array_equal(a, c), "different seeds gave identical draws"


def test_resamples_with_replacement():
    strata = np.zeros(200, dtype=int)
    idx = stratified_indices(strata, seed=1)
    assert len(set(idx.tolist())) < len(idx), "no duplicates — not sampling with replacement"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} checks passed")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV" && python3 analysis/bootstrap/selftest.py`
Expected: `ModuleNotFoundError: No module named 'analysis.bootstrap'`

- [ ] **Step 3: Write the minimal implementation**

Create `analysis/bootstrap/__init__.py` as an empty file. Create `analysis/bootstrap/resample.py`:

```python
"""Stratified respondent resampling — the only source of randomness in the harness."""

import numpy as np


def stratified_indices(strata: np.ndarray, seed: int) -> np.ndarray:
    """Row positions resampled with replacement *within* each stratum.

    Each stratum contributes exactly its original count, so per-state N never
    changes and no pipeline can fail by dropping a state below MIN_RESPONDENTS.
    Rows come back grouped in sorted stratum order; only positional consistency
    across the row-aligned input files matters, not the original ordering.
    """
    rng = np.random.default_rng(seed)
    out = np.empty(len(strata), dtype=np.int64)
    pos = 0
    for s in np.unique(strata):
        members = np.flatnonzero(strata == s)
        out[pos:pos + len(members)] = rng.choice(members, size=len(members), replace=True)
        pos += len(members)
    assert pos == len(strata), f"covered {pos} of {len(strata)} rows"
    return out
```

- [ ] **Step 4: Run it to verify it passes**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV" && python3 analysis/bootstrap/selftest.py`
Expected: 6 lines of `ok` then `6 checks passed`

- [ ] **Step 5: Commit**

```bash
cd "/Users/bdecker/Local Projects/Personal/STV"
git add analysis/bootstrap/
git commit -m "Add stratified respondent resampling for the bootstrap harness"
```

---

### Task 2: Input injection

**Files:**
- Create: `analysis/bootstrap/inject.py`
- Modify: `analysis/bootstrap/selftest.py`

**Interfaces:**
- Consumes: `stratified_indices` from Task 1.
- Produces: `resampled_inputs(idx: np.ndarray, extra_paths: Iterable[Path] = ()) -> ContextManager[None]`. Inside the block, `pd.read_csv` returns `df.iloc[idx].reset_index(drop=True)` for the four per-respondent processed files plus any `extra_paths`; everything else reads normally. Also exports `PROCESSED_FILES: tuple[Path, ...]` and `N_RESPONDENTS: int = 45707`.

- [ ] **Step 1: Write the failing test**

Append to `analysis/bootstrap/selftest.py`, before the `__main__` block:

```python
def test_injection_reindexes_targets():
    import pandas as pd
    from analysis.bootstrap.inject import PROCESSED_FILES, resampled_inputs

    target, turnout = PROCESSED_FILES[0], PROCESSED_FILES[2]
    real = pd.read_csv(target)
    idx = stratified_indices(real["inputstate"].values, seed=42)
    with resampled_inputs(idx):
        got = pd.read_csv(target)
        other = pd.read_csv(turnout)
    assert len(got) == len(real), "row count changed"
    assert len(other) == len(real), "second target not length-preserved"
    assert list(got["inputstate"]) == list(real["inputstate"].values[idx]), "wrong reindex"
    assert list(got.index) == list(range(len(got))), "index not reset"


def test_injection_leaves_non_targets_alone():
    """A file that is not per-respondent must read normally inside the block."""
    import pandas as pd
    from analysis.bootstrap.inject import resampled_inputs

    root = Path(__file__).resolve().parents[2]
    other = root / "data" / "outputs" / "pure_multi" / "state_candidate_profiles.csv"
    before = pd.read_csv(other)
    idx = stratified_indices(pd.read_csv(root / "data" / "processed" / "efa_factor_scores.csv")["inputstate"].values, seed=1)
    with resampled_inputs(idx):
        during = pd.read_csv(other)
    assert len(during) == len(before), "a non-target file was reindexed"


def test_injection_restores_pandas_and_asserts_on_mismatch():
    import pandas as pd
    from analysis.bootstrap.inject import PROCESSED_FILES, resampled_inputs

    target = PROCESSED_FILES[0]
    original = pd.read_csv
    try:
        with resampled_inputs(np.arange(10)):
            pd.read_csv(target)
    except AssertionError:
        pass
    else:
        raise AssertionError("no AssertionError on length mismatch")
    assert pd.read_csv is original, "pandas was not restored after the block raised"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV" && python3 analysis/bootstrap/selftest.py`
Expected: `ModuleNotFoundError: No module named 'analysis.bootstrap.inject'`

- [ ] **Step 3: Write the implementation**

Create `analysis/bootstrap/inject.py`:

```python
"""Patch pandas so the row-aligned per-respondent files return a resampled view.

All five files are 45,707 rows in the same respondent order, and each pipeline
asserts len(efa) == len(typology), so reindexing them with one shared index vector
keeps every downstream mask, weight and county lookup consistent. presidential_ballots.csv
is row-aligned too, so reindexing it is equivalent to regenerating ballots from the
resampled respondents and far cheaper.
"""

import contextlib
from pathlib import Path
from typing import Iterable

import pandas as pd

BASE = Path(__file__).resolve().parents[2]
PROCESSED = BASE / "data" / "processed"

N_RESPONDENTS = 45707

PROCESSED_FILES = (
    PROCESSED / "efa_factor_scores.csv",
    PROCESSED / "typology_cluster_assignments.csv",
    PROCESSED / "turnout_propensity.csv",
    PROCESSED / "voter_county_fips.csv",
)


def ballots_path(tree: str = "pure_multi") -> Path:
    return BASE / "data" / "outputs" / tree / "presidential_ballots.csv"


@contextlib.contextmanager
def resampled_inputs(idx, extra_paths: Iterable[Path] = ()):
    """Within this block, reads of the per-respondent files return df.iloc[idx]."""
    real = pd.read_csv
    targets = {str(p) for p in PROCESSED_FILES} | {str(p) for p in extra_paths}

    def patched(path, *args, **kwargs):
        df = real(path, *args, **kwargs)
        if str(path) in targets:
            assert len(df) == len(idx), (
                f"{Path(path).name}: {len(df)} rows but index has {len(idx)}"
            )
            df = df.iloc[idx].reset_index(drop=True)
        return df

    pd.read_csv = patched
    try:
        yield
    finally:
        pd.read_csv = real
```

- [ ] **Step 4: Run it to verify it passes**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV" && python3 analysis/bootstrap/selftest.py`
Expected: 9 `ok` lines, `9 checks passed`

- [ ] **Step 5: Commit**

```bash
cd "/Users/bdecker/Local Projects/Personal/STV"
git add analysis/bootstrap/
git commit -m "Add resampled-input injection for the bootstrap harness"
```

---

### Task 3: One draw across all four contests

**Files:**
- Create: `analysis/bootstrap/contests.py`
- Modify: `analysis/bootstrap/selftest.py`

**Interfaces:**
- Consumes: `stratified_indices`, `resampled_inputs`, `ballots_path`.
- Produces: `run_draw(seed: int, lam: float, depth: int = 7, observed: bool = False) -> dict` returning:

```python
{
  "seed": int,
  "senate": {"cond": {fips: code}, "irv": {fips: code},
             "paths": {fips: {"slate": [codes], "elim": [codes|None], "rounds": [...]}}},
  "house": {party_code: seats},
  "primary": [codes],           # surviving slate at the last winnowing point
  "president": {"irv": code, "cond": code},
}
```
`observed=True` skips resampling and runs on the real sample, which is how the `observed` fields and the regression check are produced.

- [ ] **Step 1: Write the failing test**

Append to `selftest.py` before `__main__`:

```python
def test_observed_draw_matches_committed_counts():
    """The observed-sample draw must reproduce the committed deterministic seat counts.
    If this fails, the harness is resampling something it shouldn't."""
    import json
    from collections import Counter
    from analysis.bootstrap.contests import run_draw

    got = run_draw(seed=0, lam=0.05, depth=7, observed=True)

    root = Path(__file__).resolve().parents[2]
    committed = json.loads((root / "viz" / "src" / "data" / "pureMultiSenateIRVTurnoutL5.json").read_text())
    want = Counter(x["senatorParty"] for x in committed)
    have = Counter(c.rsplit("_", 1)[0] for c in got["senate"]["irv"].values())
    assert have == want, f"IRV senate drifted: {dict(have)} vs {dict(want)}"

    cond_committed = json.loads((root / "viz" / "src" / "data" / "pureMultiSenateCondorcetTurnoutL5.json").read_text())
    want_c = Counter(x["senatorParty"] for x in cond_committed)
    have_c = Counter(c.rsplit("_", 1)[0] for c in got["senate"]["cond"].values())
    assert have_c == want_c, f"Condorcet senate drifted: {dict(have_c)} vs {dict(want_c)}"

    assert sum(got["house"].values()) == 873, f"house total {sum(got['house'].values())} != 873"
    assert len(got["primary"]) == 5, f"primary slate has {len(got['primary'])} candidates, expected 5"
    assert got["president"]["irv"], "no presidential IRV winner"


def test_resampled_draw_preserves_state_counts():
    from analysis.bootstrap.contests import run_draw
    got = run_draw(seed=43, lam=0.05, depth=7)
    assert len(got["senate"]["irv"]) == 51, f"{len(got['senate']['irv'])} senate races, expected 51"
    assert sum(got["house"].values()) == 873, "house total changed under resampling"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV" && python3 analysis/bootstrap/selftest.py`
Expected: `ModuleNotFoundError: No module named 'analysis.bootstrap.contests'`

- [ ] **Step 3: Write the implementation**

Create `analysis/bootstrap/contests.py`:

```python
"""Run one bootstrap draw through all four real pipelines.

Env must be set before importing any pipeline module (turnout_weights reads
TURNOUT_WEIGHT/TURNOUT_LAMBDA at import time), so the imports live inside
_pipelines() and a worker process must only ever see one lambda.
"""

import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from .inject import BASE, PROCESSED, ballots_path, resampled_inputs
from .resample import stratified_indices

CLUSTER_TO_PARTY = {0: "CON", 1: "LBR", 2: "STY", 3: "NAT", 4: "LIB",
                    5: "POP", 6: "CUP", 7: "OAO", 8: "DSA", 9: "PRG"}

_MODS = {}


def _pipelines(lam: float):
    """Import the pipeline modules once per process, with env already set."""
    if _MODS:
        assert _MODS["lam"] == lam, "a worker saw two different lambdas; use one Pool per stop"
        return _MODS
    os.environ["TURNOUT_WEIGHT"] = "1"
    os.environ["TURNOUT_LAMBDA"] = str(lam)
    sys.path.insert(0, str(BASE / "pipeline" / "pure_only"))
    import run_pure_multi_house_stv as hou
    import run_pure_multi_presidential as pres
    import run_pure_multi_primary as prim
    import run_pure_multi_senate as sen
    _MODS.update(lam=lam, sen=sen, hou=hou, prim=prim, pres=pres)
    return _MODS


def _quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def run_draw(seed: int, lam: float, depth: int = 7, observed: bool = False) -> dict:
    m = _pipelines(lam)
    sen, hou, prim, pres = m["sen"], m["hou"], m["prim"], m["pres"]

    if observed:
        idx = np.arange(len(pd.read_csv(PROCESSED / "efa_factor_scores.csv")))
    else:
        state = pd.read_csv(PROCESSED / "efa_factor_scores.csv")["inputstate"].values
        idx = stratified_indices(state, seed=seed)

    tmp = Path(tempfile.mkdtemp(prefix=f"boot_{seed}_"))
    extra = (ballots_path("pure_multi"),)

    with resampled_inputs(idx, extra_paths=extra):
        # ── senate ────────────────────────────────────────────────────────────
        sen_dir = tmp / "senate"
        real_sen_out, sen.OUTPUT_DIR = sen.OUTPUT_DIR, sen_dir
        try:
            _quiet(sen.main, ballot_depth=0)
        finally:
            sen.OUTPUT_DIR = real_sen_out
        cond = {f'{int(k):02d}': v for k, v in
                pd.read_csv(sen_dir / "senate_composition.csv")[["state_fips", "senator_code"]].values}
        irv = {f'{int(k):02d}': v for k, v in
               pd.read_csv(sen_dir / "senate_irv_composition.csv")[["state_fips", "senator_code"]].values}
        rounds = json.loads((sen_dir / "senate_irv_rounds.json").read_text())
        paths = {}
        for fips, st in rounds.items():
            rs = st["rounds"]
            paths[fips] = {
                "slate": sorted({c["code"] for c in rs[0]["candidates"]}),
                "elim": [next((c["code"] for c in rd["candidates"] if c["eliminated"]), None)
                         for rd in rs[:-1]],
                "rounds": rs,
            }

        # ── house ─────────────────────────────────────────────────────────────
        hou_out = tmp / "house_run" / "house"
        _quiet(hou.main, output_dir=hou_out, ballot_depth=depth, label="BOOTSTRAP")
        hou_dir = (hou_out.parent.parent / (hou_out.parent.name + f"_top{depth}") / hou_out.name
                   if depth else hou_out)
        hs = pd.read_csv(hou_dir / "stv_seat_summary.csv")
        house = {CLUSTER_TO_PARTY[int(r.party)]: int(r.NATIONAL) for r in hs.itertuples()}

        # ── primary → president (president reads the primary's finalists) ─────
        real_prim_out, prim.OUTPUT_DIR = prim.OUTPUT_DIR, tmp / "prim"
        try:
            _quiet(prim.main)
        finally:
            prim.OUTPUT_DIR = real_prim_out
        pr = pd.read_csv(tmp / "prim" / "primary_results_2028.csv")
        last = pr["winnowing_point"].unique()[-1]
        primary = sorted(pr[(pr.winnowing_point == last) & (pr.status == "surviving")]["candidate_code"])

        real_pres_out, pres.OUTPUT_DIR = pres.OUTPUT_DIR, tmp / "pres"
        real_pres_prim, pres.PRIMARY_PATH = pres.PRIMARY_PATH, tmp / "prim" / "primary_results_2028.csv"
        try:
            _quiet(pres.main)
        finally:
            pres.OUTPUT_DIR = real_pres_out
            pres.PRIMARY_PATH = real_pres_prim
        nat = pd.read_csv(tmp / "pres" / "irv" / "irv_presidential_national_2028.csv")
        won = nat[nat["winner"].astype(str).str.strip() == "True"]
        irv_pres = won["candidate_code"].iloc[0] if len(won) else ""
        cm = pd.read_csv(tmp / "pres" / "irv" / "condorcet_matchups_2028.csv")
        cond_pres = str(cm["condorcet_winner"].iloc[0]) if "condorcet_winner" in cm.columns and len(cm) else ""

    return {"seed": seed,
            "senate": {"cond": cond, "irv": irv, "paths": paths},
            "house": house,
            "primary": primary,
            "president": {"irv": irv_pres, "cond": cond_pres}}
```

- [ ] **Step 4: Run it to verify it passes**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV" && python3 analysis/bootstrap/selftest.py`
Expected: 11 `ok` lines, `11 checks passed`. If `run_pure_multi_presidential` has no `PRIMARY_PATH` or `OUTPUT_DIR` module global, run `grep -n "^PRIMARY_PATH\|^OUTPUT_DIR" pipeline/pure_only/run_pure_multi_presidential.py` and adjust the attribute names to match, keeping the save/restore pattern.

- [ ] **Step 5: Verify nothing canonical was written**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV" && git status --porcelain data/outputs/`
Expected: empty output.

- [ ] **Step 6: Commit**

```bash
cd "/Users/bdecker/Local Projects/Personal/STV"
git add analysis/bootstrap/
git commit -m "Run one bootstrap draw across senate, house, primary and president"
```

---

### Task 4: Representative-run selection

**Files:**
- Create: `analysis/bootstrap/representative.py`
- Modify: `analysis/bootstrap/selftest.py`

**Interfaces:**
- Produces: `pick_representative(draws: list[dict], fips: str, winner_party: str) -> dict | None` returning `{"rounds": [...], "slate": [...], "elim": [...], "share": float}` where `share` is the bucket's share of that party's wins. Returns `None` if the party never wins that state.

- [ ] **Step 1: Write the failing test**

Append to `selftest.py`:

```python
def test_representative_run_is_coherent_and_matches_winner():
    from analysis.bootstrap.contests import run_draw
    from analysis.bootstrap.representative import pick_representative

    draws = [run_draw(seed=42 + d, lam=0.05, depth=7) for d in range(12)]
    fips = "56"  # Wyoming
    winners = [d["senate"]["irv"][fips].rsplit("_", 1)[0] for d in draws]
    top = Counter(winners).most_common(1)[0][0]

    rep = pick_representative(draws, fips, top)
    assert rep is not None, f"no representative run for {top} in {fips}"
    rs = rep["rounds"]
    for rd in rs:
        total = sum(c["pct"] for c in rd["candidates"])
        assert abs(total - 100.0) < 0.5, f"round {rd['round']} sums to {total}, not 100"
    final = max(rs[-1]["candidates"], key=lambda c: c["pct"])
    assert final["code"].rsplit("_", 1)[0] == top, (
        f"representative run's winner {final['code']} is not {top}")
    assert 0 < rep["share"] <= 1


def test_representative_returns_none_for_never_winner():
    from analysis.bootstrap.contests import run_draw
    from analysis.bootstrap.representative import pick_representative
    draws = [run_draw(seed=42 + d, lam=0.05, depth=7) for d in range(4)]
    assert pick_representative(draws, "56", "DSA") is None
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV" && python3 analysis/bootstrap/selftest.py`
Expected: `ModuleNotFoundError: No module named 'analysis.bootstrap.representative'`

- [ ] **Step 3: Write the implementation**

Create `analysis/bootstrap/representative.py`:

```python
"""Pick one real draw that produces a given winner and is typical of such draws.

Averaging across draws is not an option: round 3 cannot be averaged across draws
that eliminated different candidates in round 2, because the active sets differ, so
the tallies are not commensurable and transfers would not sum. Instead: narrow to
the most common slate, then the most common elimination order within it, then take
the medoid of that bucket.
"""

from collections import Counter

import numpy as np


def pick_representative(draws: list, fips: str, winner_party: str):
    wins = [d for d in draws
            if fips in d["senate"]["irv"]
            and d["senate"]["irv"][fips].rsplit("_", 1)[0] == winner_party]
    if not wins:
        return None

    def slate_of(d):
        return tuple(d["senate"]["paths"][fips]["slate"])

    def elim_of(d):
        return tuple(d["senate"]["paths"][fips]["elim"])

    top_slate = Counter(slate_of(d) for d in wins).most_common(1)[0][0]
    in_slate = [d for d in wins if slate_of(d) == top_slate]
    top_elim = Counter(elim_of(d) for d in in_slate).most_common(1)[0][0]
    bucket = [d for d in in_slate if elim_of(d) == top_elim]

    # Medoid: the draw whose round-1 vote vector is closest to the bucket mean.
    keys = sorted(top_slate)
    def vec(d):
        r1 = {c["code"]: c["pct"] for c in d["senate"]["paths"][fips]["rounds"][0]["candidates"]}
        return np.array([r1.get(k, 0.0) for k in keys])
    M = np.vstack([vec(d) for d in bucket])
    medoid = bucket[int(np.argmin(((M - M.mean(axis=0)) ** 2).sum(axis=1)))]

    p = medoid["senate"]["paths"][fips]
    return {"rounds": p["rounds"], "slate": list(p["slate"]), "elim": list(p["elim"]),
            "share": len(bucket) / len(wins)}
```

- [ ] **Step 4: Run it to verify it passes**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV" && python3 analysis/bootstrap/selftest.py`
Expected: 13 `ok` lines, `13 checks passed`

- [ ] **Step 5: Commit**

```bash
cd "/Users/bdecker/Local Projects/Personal/STV"
git add analysis/bootstrap/
git commit -m "Add representative-run selection for switch states"
```

---

### Task 5: Aggregation and the CLI

**Files:**
- Create: `analysis/bootstrap/aggregate.py`, `analysis/bootstrap_uncertainty.py`
- Modify: `analysis/bootstrap/selftest.py`

**Interfaces:**
- Consumes: everything from Tasks 1–4.
- Produces: `build_uncertainty(draws, observed, nDraws, seed) -> dict` matching the spec's JSON shape exactly, and a CLI writing `viz/src/data/uncertainty{Suffix}.json`.

- [ ] **Step 1: Write the failing test**

Append to `selftest.py`:

```python
def test_aggregate_sums_and_shape():
    from analysis.bootstrap.aggregate import build_uncertainty
    from analysis.bootstrap.contests import run_draw

    observed = run_draw(seed=0, lam=0.05, depth=7, observed=True)
    draws = [run_draw(seed=42 + d, lam=0.05, depth=7) for d in range(12)]
    u = build_uncertainty(draws, observed, n_draws=len(draws), seed=42)

    for method in ("cond", "irv"):
        seats = u["senate"][method]["seats"]
        assert sum(v["modal"] for v in seats.values()) == 102, (
            f"{method} modal sums to {sum(v['modal'] for v in seats.values())}, not 102")
        exp = sum(v["expected"] for v in seats.values())
        assert abs(exp - 102) < 1e-6, f"{method} expected sums to {exp}, not 102"
        for p, v in seats.items():
            assert v["lo"] <= v["modal"] <= v["hi"] or v["lo"] <= v["expected"] <= v["hi"], (
                f"{method}/{p}: interval [{v['lo']},{v['hi']}] excludes both centres")
        for fips, s in u["senate"][method]["states"].items():
            assert 0 < s["pModal"] <= 1
            assert abs(sum(s["dist"].values()) - 1.0) < 1e-6, f"{fips} dist does not sum to 1"

    hs = u["house"]["seats"]
    assert sum(v["modal"] for v in hs.values()) == 873, "house modal does not sum to 873"
    assert abs(sum(v["expected"] for v in hs.values()) - 873) < 1e-6

    assert u["nDraws"] == len(draws) and u["seed"] == 42
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV" && python3 analysis/bootstrap/selftest.py`
Expected: `ModuleNotFoundError: No module named 'analysis.bootstrap.aggregate'`

- [ ] **Step 3: Write the aggregator**

Create `analysis/bootstrap/aggregate.py`:

```python
"""Turn a list of draw results into the uncertainty payload the viz reads.

Three statistics per party, and they answer different questions:
  observed  the deterministic run on the real sample (regression anchor)
  modal     the most likely winner in each state, doubled — sums to chamber size
  expected  mean seat count across draws — also sums to chamber size, by linearity
"""

from collections import Counter, defaultdict

import numpy as np

from .representative import pick_representative

SENATE_MULTIPLIER = 2  # one winner per state fills both of that state's seats


def _party(code):
    return code.rsplit("_", 1)[0] if code else ""


def _seat_stats(per_draw_counts, parties, observed_counts, multiplier=1):
    out = {}
    for p in parties:
        series = np.array([c.get(p, 0) * multiplier for c in per_draw_counts], dtype=float)
        out[p] = {
            "expected": round(float(series.mean()), 2),
            "lo": int(np.percentile(series, 2.5)),
            "hi": int(np.percentile(series, 97.5)),
            "observed": int(observed_counts.get(p, 0) * multiplier),
        }
    return out


def _senate_block(draws, observed, method):
    fips_list = sorted(observed["senate"][method])
    states, modal_counts = {}, Counter()
    for fips in fips_list:
        winners = [_party(d["senate"][method][fips]) for d in draws if fips in d["senate"][method]]
        dist = Counter(winners)
        n = sum(dist.values())
        obs_code = observed["senate"][method][fips]
        # Tie-break toward the observed winner so real data wins where draws are indifferent.
        best = max(dist.items(), key=lambda kv: (kv[1], kv[0] == _party(obs_code)))
        modal_party = best[0]
        modal_counts[modal_party] += 1
        entry = {
            "observed": obs_code,
            "modal": modal_party,
            "pModal": round(best[1] / n, 4),
            "pObserved": round(dist.get(_party(obs_code), 0) / n, 4),
            "dist": {k: round(v / n, 4) for k, v in dist.most_common()},
            "substituted": _party(obs_code) != modal_party,
        }
        if entry["substituted"] and method == "irv":
            rep = pick_representative(draws, fips, modal_party)
            if rep:
                entry["repRounds"] = rep["rounds"]
                entry["repShare"] = round(rep["share"], 4)
        # Decomposition for close races: how often each party makes the slate,
        # reaches the last round, wins, and wins given it got there.
        if entry["pModal"] < 0.70:
            entry["decomp"] = _decomp(draws, fips, method)
        states[fips] = entry

    per_draw = [Counter(_party(c) for c in d["senate"][method].values()) for d in draws]
    obs_counts = Counter(_party(c) for c in observed["senate"][method].values())
    parties = sorted({p for c in per_draw for p in c} | set(obs_counts) | set(modal_counts))
    seats = _seat_stats(per_draw, parties, obs_counts, SENATE_MULTIPLIER)
    for p in parties:
        seats[p]["modal"] = modal_counts.get(p, 0) * SENATE_MULTIPLIER
    return {
        "seats": seats,
        "states": states,
        "nSubstituted": sum(1 for s in states.values() if s["substituted"]),
        "nBelow50": sum(1 for s in states.values() if s["pModal"] < 0.50),
    }


def _decomp(draws, fips, method):
    slate = Counter(); final = Counter(); win = Counter(); win_given = Counter()
    n = 0
    for d in draws:
        p = d["senate"]["paths"].get(fips)
        if not p:
            continue
        n += 1
        w = _party(d["senate"][method][fips])
        win[w] += 1
        for c in {_party(x) for x in p["slate"]}:
            slate[c] += 1
        last = {_party(c["code"]) for c in p["rounds"][-1]["candidates"]}
        for c in last:
            final[c] += 1
        if w in last:
            win_given[w] += 1
    out = {}
    for c in slate:
        out[c] = {
            "slate": round(slate[c] / n, 4),
            "final": round(final.get(c, 0) / n, 4),
            "win": round(win.get(c, 0) / n, 4),
            "winIfFinal": round(win_given.get(c, 0) / final[c], 4) if final.get(c) else None,
        }
    return out


def build_uncertainty(draws, observed, n_draws, seed):
    out = {"nDraws": n_draws, "seed": seed, "senate": {}}
    for method in ("cond", "irv"):
        out["senate"][method] = _senate_block(draws, observed, method)

    hp = [Counter(d["house"]) for d in draws]
    ho = Counter(observed["house"])
    parties = sorted({p for c in hp for p in c} | set(ho))
    hseats = _seat_stats(hp, parties, ho)
    # House modal: per-party mode of its own seat-count distribution, then rescale the
    # largest party so the chamber sums exactly (modes of marginals need not sum).
    for p in parties:
        series = [c.get(p, 0) for c in hp]
        hseats[p]["modal"] = Counter(series).most_common(1)[0][0]
    total = sum(hseats[p]["modal"] for p in parties)
    target = sum(ho.values())
    if total != target and parties:
        biggest = max(parties, key=lambda p: hseats[p]["modal"])
        hseats[biggest]["modal"] += target - total
    out["house"] = {"seats": hseats}

    slate = Counter()
    for d in draws:
        for c in d["primary"]:
            slate[c] += 1
    out["primary"] = {"slate": {k: round(v / len(draws), 4) for k, v in slate.most_common()},
                      "observedSlate": observed["primary"]}

    out["president"] = {}
    for method in ("irv", "cond"):
        c = Counter(_party(d["president"][method]) for d in draws if d["president"][method])
        tot = sum(c.values()) or 1
        out["president"][method] = {"dist": {k: round(v / tot, 4) for k, v in c.most_common()},
                                   "observed": _party(observed["president"][method]),
                                   "modal": c.most_common(1)[0][0] if c else ""}
    return out
```

- [ ] **Step 4: Run it to verify it passes**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV" && python3 analysis/bootstrap/selftest.py`
Expected: 14 `ok` lines, `14 checks passed`

- [ ] **Step 5: Write the CLI**

Create `analysis/bootstrap_uncertainty.py`:

```python
#!/usr/bin/env python3
"""Bootstrap sampling uncertainty for every contest at every turnout stop.

Writes viz/src/data/uncertainty{Suffix}.json. Nothing canonical is written; every
pipeline run goes to a temp dir.

  python3 analysis/bootstrap_uncertainty.py                 # all 7 stops, 1000 draws
  python3 analysis/bootstrap_uncertainty.py --draws 50 --stops 5   # quick check

One Pool per stop: a worker may only ever see one lambda, because turnout_weights
reads it at import time.
"""

import argparse
import json
import multiprocessing as mp
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "viz" / "src" / "data"
STOPS = [(0, "Turnout"), (5, "TurnoutL5"), (10, "TurnoutL10"), (15, "TurnoutL15"),
         (20, "TurnoutL20"), (25, "TurnoutL25"), (30, "TurnoutL30")]


def _work(args):
    seed, lam, depth = args
    import sys
    sys.path.insert(0, str(BASE))
    from analysis.bootstrap.contests import run_draw
    try:
        return run_draw(seed=seed, lam=lam, depth=depth)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "seed": seed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=1000)
    ap.add_argument("--depth", type=int, default=7)
    ap.add_argument("--procs", type=int, default=max(1, (mp.cpu_count() or 2) - 2))
    ap.add_argument("--stops", default="", help="comma-separated stop percentages, e.g. 0,5")
    a = ap.parse_args()

    import sys
    sys.path.insert(0, str(BASE))
    from analysis.bootstrap.aggregate import build_uncertainty
    from analysis.bootstrap.contests import run_draw

    want = {int(s) for s in a.stops.split(",") if s.strip()} if a.stops else None
    stops = [(p, s) for p, s in STOPS if want is None or p in want]

    for pct, suffix in stops:
        lam = pct / 100.0
        t0 = time.time()
        observed = run_draw(seed=0, lam=lam, depth=a.depth, observed=True)
        with mp.Pool(a.procs) as pool:
            results = pool.map(_work, [(42 + d, lam, a.depth) for d in range(a.draws)])
        failed = [r for r in results if "error" in r]
        draws = [r for r in results if "error" not in r]
        assert not failed, f"{len(failed)} draws failed, first: {failed[0]['error']}"
        u = build_uncertainty(draws, observed, n_draws=len(draws), seed=42)
        path = OUT / f"uncertainty{suffix}.json"
        path.write_text(json.dumps(u, separators=(",", ":"), sort_keys=True))
        irv = u["senate"]["irv"]
        print(f"{suffix:12s} {len(draws)} draws  {time.time()-t0:5.0f}s  "
              f"substituted={irv['nSubstituted']} below50={irv['nBelow50']}  "
              f"-> {path.name} ({path.stat().st_size/1024:.0f}KB)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Smoke test the CLI on one stop with few draws**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV" && python3 analysis/bootstrap_uncertainty.py --draws 20 --stops 5`
Expected: one line like `TurnoutL5   20 draws  ...s substituted=N below50=M -> uncertaintyTurnoutL5.json (..KB)`

Then confirm nothing canonical moved: `git status --porcelain data/outputs/` → empty.

- [ ] **Step 7: Commit**

```bash
cd "/Users/bdecker/Local Projects/Personal/STV"
git add analysis/
git commit -m "Aggregate bootstrap draws into per-stop uncertainty payloads"
```

---

### Task 6: Run the full bootstrap

**Files:**
- Create: `viz/src/data/uncertainty{Turnout,TurnoutL5,…,TurnoutL30}.json` (7 files, generated)

- [ ] **Step 1: Run the full sweep**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV" && python3 analysis/bootstrap_uncertainty.py 2>&1 | tail -12`
Expected: 7 lines, one per stop. Roughly 85 minutes total on 12 cores. `substituted` should be small (3 for IRV at L5 per the spec's findings).

- [ ] **Step 2: Verify the regression anchor and the sums**

Run:

```bash
cd "/Users/bdecker/Local Projects/Personal/STV" && python3 - <<'PY'
import json, collections, pathlib
D = pathlib.Path('viz/src/data')
for suf in ['Turnout','TurnoutL5','TurnoutL10','TurnoutL15','TurnoutL20','TurnoutL25','TurnoutL30']:
    u = json.loads((D/f'uncertainty{suf}.json').read_text())
    for m, name in (('irv','pureMultiSenateIRV'), ('cond','pureMultiSenateCondorcet')):
        s = u['senate'][m]['seats']
        committed = json.loads((D/f'{name}{suf}.json').read_text())
        want = collections.Counter(x['senatorParty'] for x in committed)
        for p, v in s.items():
            assert v['observed'] == want.get(p, 0)*2, f'{suf}/{m}/{p}: observed {v["observed"]} != {want.get(p,0)*2}'
        assert sum(v['modal'] for v in s.values()) == 102, f'{suf}/{m} modal != 102'
        assert abs(sum(v['expected'] for v in s.values()) - 102) < 1e-6
    h = u['house']['seats']
    assert sum(v['modal'] for v in h.values()) == 873, f'{suf} house modal != 873'
    print(f'{suf:12s} ok  irv substituted={u["senate"]["irv"]["nSubstituted"]}')
PY
```

Expected: 7 `ok` lines, no assertion errors.

- [ ] **Step 3: Commit the generated data**

```bash
cd "/Users/bdecker/Local Projects/Personal/STV"
git add viz/src/data/uncertainty*.json
git commit -m "Add bootstrapped uncertainty data for every turnout stop"
```

---

## Phase 2 — Modal-chamber vote model

### Task 7: Recompute the vote models from the modal chamber

**Files:**
- Modify: `viz/scripts/prepare_data.py` (`build_senate_vote_model_wfp` around `:3175`, `build_house_vote_model_wfp`, `_build_turnout_variant` at `:3276`)

**Interfaces:**
- Consumes: `uncertainty{Suffix}.json` from Task 6.
- Produces: `senateVoteModel{Suffix}.json` / `houseVoteModel{Suffix}.json` whose Raw-Multi columns come from the modal chamber. `_lf_prob_pass(seat_counts: dict, cluster_by_var: dict, majority: int = 26)` is unchanged — it only needs a `{party: seats}` dict.

- [ ] **Step 1: Add a modal-seat reader**

In `viz/scripts/prepare_data.py`, above `build_senate_vote_model_wfp`, add:

```python
def _modal_seats(suffix: str, chamber: str, method: str | None = None):
    """Per-party seat counts from the modal chamber, on the 51-seat senate basis
    (_lf_prob_pass uses majority=26), or the 873-seat house basis. Returns None when
    the uncertainty payload is absent so the builder falls back to the observed run."""
    path = DATA_OUT / f"uncertainty{suffix}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        u = json.load(f)
    if chamber == "senate":
        seats = u["senate"][method]["seats"]
        return {p: v["modal"] // 2 for p, v in seats.items() if v["modal"] > 0}
    seats = u["house"]["seats"]
    return {p: v["modal"] for p, v in seats.items() if v["modal"] > 0}
```

- [ ] **Step 2: Use it in the senate vote model**

Replace the seat-counting block at `prepare_data.py:3194-3200`:

```python
    cond_seats, irv_seats = {}, {}
    for r in read_csv(src / "senate" / "senate_composition.csv"):
        p = r["senator_code"].rsplit("_", 1)[0]; cond_seats[p] = cond_seats.get(p, 0) + 1
    for r in read_csv(src / "senate" / "senate_irv_composition.csv"):
        p = r["senator_code"].rsplit("_", 1)[0]; irv_seats[p] = irv_seats.get(p, 0) + 1
```

with:

```python
    cond_seats, irv_seats = {}, {}
    for r in read_csv(src / "senate" / "senate_composition.csv"):
        p = r["senator_code"].rsplit("_", 1)[0]; cond_seats[p] = cond_seats.get(p, 0) + 1
    for r in read_csv(src / "senate" / "senate_irv_composition.csv"):
        p = r["senator_code"].rsplit("_", 1)[0]; irv_seats[p] = irv_seats.get(p, 0) + 1
    # The headline chamber is the modal one, so the legislation model must describe
    # that chamber rather than the single observed run.
    _suffix = out_name.replace("senateVoteModel", "").replace(".json", "")
    cond_seats = _modal_seats(_suffix, "senate", "cond") or cond_seats
    irv_seats = _modal_seats(_suffix, "senate", "irv") or irv_seats
```

- [ ] **Step 3: Regenerate and verify the totals still make sense**

Run:

```bash
cd "/Users/bdecker/Local Projects/Personal/STV" && python3 viz/scripts/prepare_data.py 2>&1 | grep -i "skip\|error" | head
```

Expected: only the known `SKIP NoStyTurnout variant (dormant)` line.

Then:

```bash
cd "/Users/bdecker/Local Projects/Personal/STV" && git diff --stat viz/src/data/senateVoteModel*.json viz/src/data/houseVoteModel*.json
```

Expected: non-empty diffs for the `Turnout*` variants (the modal chamber differs from the observed one), and `viz/src/data/partyPopulation.json` must NOT be emptied — if it is, `git checkout viz/src/data/partyPopulation.json` (a known pruned-input hazard in `build_party_population`).

- [ ] **Step 4: Commit**

```bash
cd "/Users/bdecker/Local Projects/Personal/STV"
git add viz/scripts/prepare_data.py viz/src/data/
git commit -m "Compute the legislation vote models from the modal chamber"
```

---

## Phase 3 — Shared viz primitives

### Task 8: Uncertainty types and accessor

**Files:**
- Create: `viz/src/lib/uncertainty.ts`, `viz/src/lib/uncertainty.test.ts`

**Interfaces:**
- Produces:

```ts
export interface SeatInterval { modal: number; expected: number; lo: number; hi: number; observed: number }
export interface StateUncertainty {
  observed: string; modal: string; pModal: number; pObserved: number;
  dist: Record<string, number>; substituted: boolean;
  repRounds?: SenateIrvRound[]; repShare?: number;
  decomp?: Record<string, { slate: number; final: number; win: number; winIfFinal: number | null }>;
}
export interface MethodUncertainty {
  seats: Record<string, SeatInterval>; states: Record<string, StateUncertainty>;
  nSubstituted: number; nBelow50: number;
}
export interface UncertaintyData {
  nDraws: number; seed: number;
  senate: { cond: MethodUncertainty; irv: MethodUncertainty };
  house: { seats: Record<string, SeatInterval> };
  primary: { slate: Record<string, number>; observedSlate: string[] };
  president: Record<'irv' | 'cond', { dist: Record<string, number>; observed: string; modal: string }>;
}
export const UNCERTAINTY_STOPS: UncertaintyData[];
export function uncertaintyAt(gi: number): UncertaintyData | undefined;
export function chamberTotal(seats: Record<string, SeatInterval>, key: 'modal' | 'observed'): number;
```

- [ ] **Step 1: Write the failing test**

Create `viz/src/lib/uncertainty.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { uncertaintyAt, chamberTotal, UNCERTAINTY_STOPS } from './uncertainty'

describe('uncertainty accessor', () => {
  it('exposes one payload per turnout stop', () => {
    expect(UNCERTAINTY_STOPS).toHaveLength(7)
  })

  it('returns undefined outside the stop range', () => {
    expect(uncertaintyAt(-1)).toBeUndefined()
    expect(uncertaintyAt(7)).toBeUndefined()
  })

  it('senate modal and observed chambers both total 102 at every stop', () => {
    for (let gi = 0; gi < 7; gi++) {
      const u = uncertaintyAt(gi)!
      for (const m of ['cond', 'irv'] as const) {
        expect(chamberTotal(u.senate[m].seats, 'modal')).toBe(102)
        expect(chamberTotal(u.senate[m].seats, 'observed')).toBe(102)
      }
    }
  })

  it('house modal totals 873 at every stop', () => {
    for (let gi = 0; gi < 7; gi++) {
      expect(chamberTotal(uncertaintyAt(gi)!.house.seats, 'modal')).toBe(873)
    }
  })

  it('expected seats sum to the chamber size', () => {
    const u = uncertaintyAt(1)!
    const sum = Object.values(u.senate.irv.seats).reduce((s, v) => s + v.expected, 0)
    expect(sum).toBeCloseTo(102, 4)
  })

  it('every state distribution sums to 1', () => {
    const u = uncertaintyAt(1)!
    for (const s of Object.values(u.senate.irv.states)) {
      const sum = Object.values(s.dist).reduce((a, b) => a + b, 0)
      expect(sum).toBeCloseTo(1, 3)
    }
  })

  it('substituted states carry a representative run whose winner is the modal party', () => {
    const u = uncertaintyAt(1)!
    for (const s of Object.values(u.senate.irv.states)) {
      if (!s.substituted || !s.repRounds) continue
      const last = s.repRounds[s.repRounds.length - 1].candidates
      const top = [...last].sort((a, b) => b.pct - a.pct)[0]
      expect(top.code.split('_')[0]).toBe(s.modal.split('_')[0])
      for (const rd of s.repRounds) {
        const total = rd.candidates.reduce((a, c) => a + c.pct, 0)
        expect(total).toBeCloseTo(100, 0)
      }
    }
  })
})
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV/viz" && npx vitest run src/lib/uncertainty.test.ts`
Expected: FAIL — `Failed to resolve import "./uncertainty"`

- [ ] **Step 3: Write the implementation**

Create `viz/src/lib/uncertainty.ts`:

```ts
// Bootstrap sampling uncertainty, one payload per turnout stop. These are bootstrap
// percentile intervals, not credible intervals — see About → Caveats.
import u0 from '../data/uncertaintyTurnout.json';
import u5 from '../data/uncertaintyTurnoutL5.json';
import u10 from '../data/uncertaintyTurnoutL10.json';
import u15 from '../data/uncertaintyTurnoutL15.json';
import u20 from '../data/uncertaintyTurnoutL20.json';
import u25 from '../data/uncertaintyTurnoutL25.json';
import u30 from '../data/uncertaintyTurnoutL30.json';
import type { SenateIrvRound } from '../types';

export interface SeatInterval {
  modal: number; expected: number; lo: number; hi: number; observed: number;
}

export interface StateUncertainty {
  observed: string;
  modal: string;
  pModal: number;
  pObserved: number;
  dist: Record<string, number>;
  substituted: boolean;
  repRounds?: SenateIrvRound[];
  repShare?: number;
  decomp?: Record<string, { slate: number; final: number; win: number; winIfFinal: number | null }>;
}

export interface MethodUncertainty {
  seats: Record<string, SeatInterval>;
  states: Record<string, StateUncertainty>;
  nSubstituted: number;
  nBelow50: number;
}

export interface UncertaintyData {
  nDraws: number;
  seed: number;
  senate: { cond: MethodUncertainty; irv: MethodUncertainty };
  house: { seats: Record<string, SeatInterval> };
  primary: { slate: Record<string, number>; observedSlate: string[] };
  president: Record<'irv' | 'cond', { dist: Record<string, number>; observed: string; modal: string }>;
}

export const UNCERTAINTY_STOPS = [u0, u5, u10, u15, u20, u25, u30] as unknown as UncertaintyData[];

export function uncertaintyAt(gi: number): UncertaintyData | undefined {
  return UNCERTAINTY_STOPS[gi];
}

export function chamberTotal(
  seats: Record<string, SeatInterval>,
  key: 'modal' | 'observed',
): number {
  return Object.values(seats).reduce((s, v) => s + v[key], 0);
}
```

- [ ] **Step 4: Run it to verify it passes**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV/viz" && npx vitest run src/lib/uncertainty.test.ts`
Expected: 7 passing tests

- [ ] **Step 5: Commit**

```bash
cd "/Users/bdecker/Local Projects/Personal/STV"
git add viz/src/lib/uncertainty.ts viz/src/lib/uncertainty.test.ts
git commit -m "Add uncertainty types and stop-indexed accessor"
```

---

### Task 9: SeatWhisker primitive and SeatRangeStrip

**Files:**
- Create: `viz/src/components/shared/SeatWhisker.tsx`, `viz/src/components/shared/SeatRangeStrip.tsx`, `viz/src/lib/whisker.ts`, `viz/src/lib/whisker.test.ts`

**Interfaces:**
- Produces: `whiskerGeometry(lo, hi, centre, max) -> { leftPct, widthPct, centrePct } | null` in `lib/whisker.ts` (pure, testable); `<SeatWhisker lo hi centre max title? />` rendering an absolutely-positioned overlay (parent must be `relative`); and `<SeatRangeStrip seats order label />` rendering one compact range row per seat-holding party.
- Two consumers, two shapes: the House's bars are one per party so a whisker sits directly on them, but the Senate's chamber bar is stacked, so an inline whisker would overlap into neighbouring segments. The strip is the Senate's answer.

- [ ] **Step 1: Write the failing test**

Create `viz/src/lib/whisker.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { whiskerGeometry } from './whisker'

describe('whiskerGeometry', () => {
  it('maps values onto percentages of the axis', () => {
    expect(whiskerGeometry(20, 40, 30, 100)).toEqual({ leftPct: 20, widthPct: 20, centrePct: 30 })
  })
  it('scales to a non-100 axis maximum', () => {
    expect(whiskerGeometry(10, 20, 15, 50)).toEqual({ leftPct: 20, widthPct: 20, centrePct: 30 })
  })
  it('returns null for a degenerate axis', () => {
    expect(whiskerGeometry(1, 2, 1.5, 0)).toBeNull()
  })
  it('returns null when the interval has no width', () => {
    expect(whiskerGeometry(5, 5, 5, 100)).toBeNull()
  })
  it('clamps to the axis so it cannot overflow the track', () => {
    const g = whiskerGeometry(-10, 120, 50, 100)!
    expect(g.leftPct).toBe(0)
    expect(g.leftPct + g.widthPct).toBeLessThanOrEqual(100)
  })
})
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV/viz" && npx vitest run src/lib/whisker.test.ts`
Expected: FAIL — `Failed to resolve import "./whisker"`

- [ ] **Step 3: Write the implementation**

Create `viz/src/lib/whisker.ts`:

```ts
/** Geometry for a whisker overlay, in percentages of an axis running 0…max.
 *  Clamped so a wide interval can never overflow its track. Null when there is
 *  nothing meaningful to draw. */
export function whiskerGeometry(
  lo: number, hi: number, centre: number, max: number,
): { leftPct: number; widthPct: number; centrePct: number } | null {
  if (!(max > 0) || !(hi > lo)) return null;
  const pct = (v: number) => Math.min(100, Math.max(0, (v / max) * 100));
  const leftPct = pct(lo);
  return { leftPct, widthPct: pct(hi) - leftPct, centrePct: pct(centre) };
}
```

Create `viz/src/components/shared/SeatWhisker.tsx`:

```tsx
import { whiskerGeometry } from '../../lib/whisker';

/** A whisker overlay for an existing bar: a horizontal span from lo to hi with a
 *  centre tick at the expected value. Absolutely positioned, so the parent must be
 *  `relative`. Renders nothing when there is no interval, so consumers degrade
 *  gracefully at stops without uncertainty data. */
export function SeatWhisker({ lo, hi, centre, max, title }: {
  lo: number; hi: number; centre: number; max: number; title?: string;
}) {
  const g = whiskerGeometry(lo, hi, centre, max);
  if (!g) return null;
  return (
    <div className="absolute inset-y-0 pointer-events-none" aria-hidden="true" title={title}>
      <div className="absolute top-1/2 -translate-y-1/2 h-px bg-foreground/70"
        style={{ left: `${g.leftPct}%`, width: `${g.widthPct}%` }} />
      {[g.leftPct, g.leftPct + g.widthPct].map((x, i) => (
        <div key={i} className="absolute top-1/2 -translate-y-1/2 w-px h-2 bg-foreground/70"
          style={{ left: `${x}%` }} />
      ))}
      <div className="absolute top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-foreground/85 -ml-[3px]"
        style={{ left: `${g.centrePct}%` }} />
    </div>
  );
}
```

- [ ] **Step 4: Write SeatRangeStrip**

Create `viz/src/components/shared/SeatRangeStrip.tsx`:

```tsx
import { useMemo } from 'react';
import { PARTY_COLORS, PARTY_NAMES } from '../../constants/parties';
import { SeatWhisker } from './SeatWhisker';
import type { SeatInterval } from '../../lib/uncertainty';

/** Compact always-visible range rows, one per seat-holding party: the 95% span, the
 *  expected value, and a tick at the most likely count. Used where the chamber bar is
 *  stacked and an inline whisker would overlap into neighbouring parties' segments. */
export function SeatRangeStrip({ seats, order, label }: {
  seats: Record<string, SeatInterval>;
  order: string[];
  label: string;
}) {
  const rows = useMemo(
    () => order
      .map(p => ({ party: p, iv: seats[p] }))
      .filter((r): r is { party: string; iv: SeatInterval } =>
        !!r.iv && (r.iv.modal > 0 || r.iv.hi > 0)),
    [seats, order],
  );
  const max = useMemo(() => Math.max(1, ...rows.map(r => r.iv.hi)), [rows]);

  if (!rows.length) return null;

  return (
    <div className="space-y-1 pt-1">
      <div className="text-[10px] text-muted-foreground">{label}</div>
      {rows.map(({ party, iv }) => {
        const color = PARTY_COLORS[party] ?? '#6b7280';
        return (
          <div key={party} className="flex items-center gap-2">
            <span className="w-10 shrink-0 text-[10px] font-bold text-right" style={{ color }}>
              {party}
            </span>
            <div className="relative flex-1 h-4 rounded bg-muted/50">
              <div className="absolute inset-y-1 rounded-sm" style={{
                left: `${(iv.lo / max) * 100}%`,
                width: `${((iv.hi - iv.lo) / max) * 100}%`,
                backgroundColor: color,
                opacity: 0.28,
              }} />
              <SeatWhisker lo={iv.lo} hi={iv.hi} centre={iv.expected} max={max}
                title={`${PARTY_NAMES[party] ?? party}: ${iv.lo}–${iv.hi} seats across resamples, ${iv.expected.toFixed(1)} expected`} />
              <div className="absolute inset-y-0 w-0.5" title={`most likely: ${iv.modal}`}
                style={{ left: `${(iv.modal / max) * 100}%`, backgroundColor: color }} />
            </div>
            <span className="w-24 shrink-0 text-[10px] tabular-nums text-muted-foreground">
              <span className="font-semibold text-foreground">{iv.modal}</span> · {iv.lo}–{iv.hi}
            </span>
          </div>
        );
      })}
      <div className="flex items-center gap-2">
        <span className="w-10 shrink-0" />
        <div className="flex-1 flex justify-between text-[9px] text-muted-foreground">
          <span>0</span><span>{max} seats</span>
        </div>
        <span className="w-24 shrink-0" />
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Run it to verify everything passes**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV/viz" && npx vitest run src/lib/whisker.test.ts && npx tsc -b && npx eslint src/components/shared/SeatWhisker.tsx src/components/shared/SeatRangeStrip.tsx`
Expected: 5 passing tests, tsc silent, eslint silent

- [ ] **Step 6: Commit**

```bash
cd "/Users/bdecker/Local Projects/Personal/STV"
git add viz/src/lib/whisker.ts viz/src/lib/whisker.test.ts viz/src/components/shared/SeatWhisker.tsx viz/src/components/shared/SeatRangeStrip.tsx
git commit -m "Add SeatWhisker overlay and SeatRangeStrip"
```

---

### Task 10: UncertaintyDetail expander

**Files:**
- Create: `viz/src/components/shared/UncertaintyDetail.tsx`

**Interfaces:**
- Consumes: `MethodUncertainty`, `SeatInterval` from Task 8.
- Produces: `<UncertaintyDetail seats states nDraws stateLabel />` where `stateLabel?: (fips: string) => string`. Collapsed by default.

- [ ] **Step 1: Write the component**

Create `viz/src/components/shared/UncertaintyDetail.tsx`:

```tsx
import { useMemo, useState } from 'react';
import { PARTY_COLORS, PARTY_NAMES, getContrastText } from '../../constants/parties';
import type { SeatInterval, StateUncertainty } from '../../lib/uncertainty';

const party = (code: string) => code.split('_')[0];

function Pill({ code }: { code: string }) {
  const p = party(code);
  const color = PARTY_COLORS[p] ?? '#6b7280';
  return (
    <span className="inline-flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded leading-none shrink-0 chip-text"
      style={{ backgroundColor: color, color: getContrastText(color) }}>{p}</span>
  );
}

export function UncertaintyDetail({ seats, states, nDraws, stateLabel }: {
  seats: Record<string, SeatInterval>;
  states?: Record<string, StateUncertainty>;
  nDraws: number;
  stateLabel?: (fips: string) => string;
}) {
  const [open, setOpen] = useState(false);

  const rows = useMemo(
    () => Object.entries(seats).filter(([, v]) => v.modal > 0 || v.observed > 0 || v.hi > 0)
      .sort((a, b) => b[1].modal - a[1].modal),
    [seats],
  );
  const close = useMemo(
    () => Object.entries(states ?? {}).filter(([, s]) => s.pModal < 0.70)
      .sort((a, b) => a[1].pModal - b[1].pModal),
    [states],
  );

  return (
    <div className="pt-3 border-t border-border/50">
      <button onClick={() => setOpen(o => !o)}
        className="text-[11px] font-semibold text-muted-foreground hover:text-foreground"
        aria-expanded={open}>
        {open ? '▾' : '▸'} Range across {nDraws.toLocaleString()} resamples
      </button>

      {open && (
        <div className="mt-3 space-y-4">
          <div>
            <div className="grid grid-cols-[auto_1fr_1fr_1fr] gap-x-3 gap-y-1 text-[10px] items-center">
              <span className="text-muted-foreground uppercase tracking-wider">Party</span>
              <span className="text-muted-foreground uppercase tracking-wider">Most likely</span>
              <span className="text-muted-foreground uppercase tracking-wider">Expected</span>
              <span className="text-muted-foreground uppercase tracking-wider">95% range</span>
              {rows.map(([p, v]) => (
                <div key={p} className="contents">
                  <Pill code={p} />
                  <span className="tabular-nums text-foreground font-semibold">{v.modal}</span>
                  <span className="tabular-nums text-muted-foreground">{v.expected.toFixed(1)}</span>
                  <span className="tabular-nums text-muted-foreground">{v.lo}–{v.hi}</span>
                </div>
              ))}
            </div>
          </div>

          {close.length > 0 && (
            <div>
              <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">
                Closest races
              </div>
              <div className="space-y-1.5">
                {close.map(([fips, s]) => (
                  <div key={fips} className="flex items-start gap-2 text-[10px]">
                    <span className="w-8 shrink-0 font-semibold text-foreground">
                      {stateLabel ? stateLabel(fips) : fips}
                    </span>
                    <Pill code={s.modal} />
                    <span className="tabular-nums text-foreground font-semibold w-10">
                      {Math.round(s.pModal * 100)}%
                    </span>
                    <span className="text-muted-foreground">
                      {Object.entries(s.dist).slice(1, 4)
                        .map(([p, v]) => `${p} ${Math.round(v * 100)}%`).join(' · ')}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify it compiles and lints**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV/viz" && npx tsc -b && npx eslint src/components/shared/UncertaintyDetail.tsx`
Expected: both silent

- [ ] **Step 3: Commit**

```bash
cd "/Users/bdecker/Local Projects/Personal/STV"
git add viz/src/components/shared/UncertaintyDetail.tsx
git commit -m "Add collapsed uncertainty detail block"
```

---

## Phase 4 — Senate

### Task 11: Modal headline and whiskers on the senate composition card

**Files:**
- Modify: `viz/src/components/senate/SenateCompositionCard.tsx`, `viz/src/tabs/SenateTab.tsx`

**Interfaces:**
- Consumes: `uncertaintyAt`, `SeatWhisker`, `UncertaintyDetail`.
- Produces: `SenateCompositionCard` gains optional props `condU?: MethodUncertainty`, `irvU?: MethodUncertainty`, `nDraws?: number`. When present, bars use `modal` counts and carry whiskers; when absent the card behaves exactly as today.

- [ ] **Step 1: Thread the data in from SenateTab**

In `viz/src/tabs/SenateTab.tsx`, add the import:

```tsx
import { uncertaintyAt } from '../lib/uncertainty';
```

After the existing `const irvRM = ...` line, add:

```tsx
  // Sampling uncertainty at the active stop. Party-line only — the Crossover pipeline
  // is not bootstrapped, so these are undefined there and every consumer degrades.
  const unc = rawMultiOn ? uncertaintyAt(gi) : undefined;
```

Change the composition card call site from `<SenateCompositionCard condSeats={condRM} irvSeats={irvRM} />` to:

```tsx
      <SenateCompositionCard condSeats={condRM} irvSeats={irvRM}
        condU={unc?.senate.cond} irvU={unc?.senate.irv} nDraws={unc?.nDraws} />
```

- [ ] **Step 2: Use modal counts and add the range strip**

In `SenateCompositionCard.tsx`, add these imports:

```tsx
import { SeatRangeStrip } from '../shared/SeatRangeStrip';
import { UncertaintyDetail } from '../shared/UncertaintyDetail';
import type { MethodUncertainty } from '../../lib/uncertainty';
```

Leave `SenateCompBar` exactly as it is. The chamber bar is stacked, so a per-party whisker drawn inside a segment would have to extend into neighbouring parties' segments to show its range, and would read as belonging to the wrong party. The ranges go in a separate strip below instead.

Replace the `stats` memo's tally so it prefers modal counts:

```tsx
  const stats = useMemo(() => {
    const tally = (seats: FDSenateSeat[]) => {
      const c: Record<string, number> = {};
      for (const s of seats) {
        const p = s.senatorParty ?? s.senatorCode.split('_')[0];
        c[p] = (c[p] ?? 0) + 1;
      }
      return c;
    };
    // Headline is the modal chamber where we have it — it is the most likely winner in
    // each state and still one winner per state, so it sums to the chamber size.
    const cond = condU
      ? Object.fromEntries(Object.entries(condU.seats).map(([p, v]) => [p, v.modal / 2]))
      : tally(condSeats);
    const irv = irvU
      ? Object.fromEntries(Object.entries(irvU.seats).map(([p, v]) => [p, v.modal / 2]))
      : tally(irvSeats);
    const parties = F5_ORDER.filter(p => (cond[p] ?? 0) > 0 || (irv[p] ?? 0) > 0);
    return {
      rows: parties.map(p => ({ party: p, cond: (cond[p] ?? 0) * 2, irv: (irv[p] ?? 0) * 2 })),
      total: condSeats.length * 2,
    };
  }, [condSeats, irvSeats, condU, irvU]);
```

Change the two preferential bars to build segments from `stats.rows`, and add a range strip under each:

```tsx
      <SenateCompBar label="Condorcet ×2" total={stats.total}
        segments={stats.rows.filter(r => r.cond > 0)
          .map(r => ({ party: r.party, n: r.cond, color: PARTY_COLORS[r.party] ?? '#6b7280' }))} />
      {condU && (
        <SeatRangeStrip seats={condU.seats} order={stats.rows.map(r => r.party)}
          label="Condorcet — range across resamples (tick = most likely, dot = expected)" />
      )}
      <SenateCompBar label="IRV ×2" total={stats.total}
        segments={stats.rows.filter(r => r.irv > 0)
          .map(r => ({ party: r.party, n: r.irv, color: PARTY_COLORS[r.party] ?? '#6b7280' }))} />
      {irvU && (
        <SeatRangeStrip seats={irvU.seats} order={stats.rows.map(r => r.party)}
          label="IRV — range across resamples (tick = most likely, dot = expected)" />
      )}
```

Add the detail block and the one-line summary just before the closing `</Card>`, after the existing explanatory `<p>`:

```tsx
      {irvU && nDraws && (
        <>
          <p className="text-[11px] text-muted-foreground/80">
            {irvU.nBelow50} of {condSeats.length} seats are close enough to flip on sampling alone.
          </p>
          <UncertaintyDetail seats={irvU.seats} states={irvU.states} nDraws={nDraws}
            stateLabel={f => FIPS_TO_ABBR[f] ?? f} />
        </>
      )}
```

Add a FIPS→abbr map at the top of the file, built from the seats already passed in:

```tsx
// Built from the seat array so it always matches whatever states the model covers.
function fipsToAbbr(seats: FDSenateSeat[]): Record<string, string> {
  return Object.fromEntries(seats.map(s => [s.stateFips, s.stateAbbr]));
}
```

and inside the component: `const FIPS_TO_ABBR = useMemo(() => fipsToAbbr(condSeats), [condSeats]);`

Update the props interface:

```tsx
export function SenateCompositionCard({ condSeats, irvSeats, condU, irvU, nDraws }: {
  condSeats: FDSenateSeat[];
  irvSeats: FDSenateSeat[];
  condU?: MethodUncertainty;
  irvU?: MethodUncertainty;
  nDraws?: number;
}) {
```

- [ ] **Step 3: Verify it compiles, lints and builds**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV/viz" && npx tsc -b && npx eslint src/components/senate/SenateCompositionCard.tsx src/tabs/SenateTab.tsx && npx vite build 2>&1 | grep -E "built in|error"`
Expected: tsc silent, eslint reports only the pre-existing `as any` / memoization errors in `SenateTab.tsx` (lines with `getFactorScore` and `fdVariantSeats`), build succeeds

- [ ] **Step 4: Verify in the browser**

```bash
cd "/Users/bdecker/Local Projects/Personal/STV/viz" && (npx vite preview --port 4319 > /tmp/preview.log 2>&1 &) ; sleep 4
cd /tmp && node -e "
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({viewport:{width:1280,height:1200},deviceScaleFactor:2});
  const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  await p.goto('http://localhost:4319/?tab=senate&method=irv&part=5',{waitUntil:'networkidle'});
  await p.waitForTimeout(2500);
  const card = p.locator('h3',{hasText:'FPTP Today vs Preferential'}).first().locator('xpath=ancestor::*[contains(@class,\"p-5\")][1]');
  await card.scrollIntoViewIfNeeded(); await p.waitForTimeout(500);
  await card.screenshot({path:'/tmp/comp.png'});
  console.log((await card.textContent()).replace(/\s+/g,' ').slice(0,400));
  console.log(errs.length?errs.join('\n'):'no page errors');
  await b.close();
})();
"
```

Expected: no page errors; the IRV row's seat numbers reflect the modal chamber and still total 102; the "close enough to flip" line appears. Read `/tmp/comp.png` to confirm the range strips render below each stacked bar with the modal tick inside the shaded span.

- [ ] **Step 5: Commit**

```bash
cd "/Users/bdecker/Local Projects/Personal/STV"
git add viz/src/components/senate/SenateCompositionCard.tsx viz/src/tabs/SenateTab.tsx
git commit -m "Show the modal senate chamber with sampling ranges"
```

---

### Task 12: Senate map hatch and tooltip probability

**Files:**
- Modify: `viz/src/components/senate/SenateMap.tsx`, `viz/src/tabs/SenateTab.tsx`

**Interfaces:**
- Consumes: `MethodUncertainty`.
- Produces: `<SenateMap seats states? />` where `states?: Record<string, StateUncertainty>`. When present, states with `pModal < 0.50` get a hatch overlay and every state's tooltip gains the win probability.

- [ ] **Step 1: Add the hatch pattern and probability**

In `SenateMap.tsx`, add to the props interface:

```tsx
import type { StateUncertainty } from '../../lib/uncertainty';

interface Props {
  seats: SenateSeat[];
  states?: Record<string, StateUncertainty>;
}
```

Inside `<ComposableMap>`, before `<Geographies>`, add the pattern definition:

```tsx
          <defs>
            {/* Diagonal hatch marks states whose winner flips on sampling. A numeric
                label is not an option here: this is a geoAlbersUsa projection and the
                least stable states (WY, ND, VT, DC, RI) are the smallest on screen. */}
            <pattern id="unstable-hatch" width="6" height="6" patternUnits="userSpaceOnUse"
              patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="6" stroke="#0f172a" strokeWidth="1.6" strokeOpacity="0.5" />
            </pattern>
          </defs>
```

Now replace the geography mapping so unstable states get a hatch overlay and every
tooltip carries the win probability.

Replace the whole `return (...)` inside the `.map` with a `<g>` wrapper so the hatch draws on top. This is the complete replacement — the `key` moves to the `<g>`, and the hatch layer is `pointerEvents: 'none'` so it never steals the tooltip hover:

```tsx
                return (
                  <g key={geo.rsmKey}>
                    <Geography
                      geography={geo}
                      fill={fill}
                      stroke="#cbd5e1"
                      strokeWidth={1}
                      style={{
                        default: { outline: 'none', cursor: seat ? 'pointer' : 'default' },
                        hover:   { outline: 'none', opacity: 0.8 },
                        pressed: { outline: 'none' },
                      }}
                      onMouseEnter={() => {
                        if (seat) {
                          const u = states?.[fips];
                          const prob = u ? ` — ${Math.round(u.pModal * 100)}% of resamples` : '';
                          setTooltip(`${seat.stateAbbr}: ${seat.senatorLabel} (${seat.senatorType})${prob}`);
                        }
                      }}
                      onMouseLeave={() => setTooltip(null)}
                    />
                    {states?.[fips] && states[fips].pModal < 0.5 && (
                      <Geography geography={geo} fill="url(#unstable-hatch)" stroke="none"
                        style={{ default: { outline: 'none', pointerEvents: 'none' },
                                 hover: { outline: 'none', pointerEvents: 'none' },
                                 pressed: { outline: 'none', pointerEvents: 'none' } }} />
                    )}
                  </g>
                );
```

Read `SenateMap.tsx` first: if the existing `<Geography>` has props not shown above, carry them onto the first `<Geography>` unchanged.

Add a legend line under the map, inside the outer `<div>`:

```tsx
      {states && (
        <div className="flex items-center gap-2 mt-2 text-[10px] text-muted-foreground">
          <svg width="14" height="14" aria-hidden="true">
            <rect width="14" height="14" fill="#e2e8f0" />
            <rect width="14" height="14" fill="url(#unstable-hatch)" />
          </svg>
          Hatched: the winner changes in more than half of resamples
        </div>
      )}
```

- [ ] **Step 2: Pass the data from SenateTab**

Change the map call site in `SenateTab.tsx` from `<SenateMap seats={activeSeats} />` to:

```tsx
        <SenateMap seats={activeSeats}
          states={method === 'condorcet' ? unc?.senate.cond.states : unc?.senate.irv.states} />
```

- [ ] **Step 3: Verify**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV/viz" && npx tsc -b && npx eslint src/components/senate/SenateMap.tsx && npx vite build 2>&1 | grep -E "built in|error"`
Expected: all clean

Then screenshot the map with the same playwright pattern as Task 11 Step 4, targeting the card containing `SenateMap`, and confirm Wyoming is hatched and the legend line appears.

- [ ] **Step 4: Commit**

```bash
cd "/Users/bdecker/Local Projects/Personal/STV"
git add viz/src/components/senate/SenateMap.tsx viz/src/tabs/SenateTab.tsx
git commit -m "Hatch senate states whose winner flips on sampling"
```

---

### Task 13: Substituted runs and the decomposition table

**Files:**
- Modify: `viz/src/components/senate/SenateCoalitionCard.tsx`, `viz/src/tabs/SenateTab.tsx`

**Interfaces:**
- Consumes: `StateUncertainty` (`repRounds`, `pModal`, `decomp`).
- Produces: `SenateCoalitionCard` gains `states?: Record<string, StateUncertainty>`. For a selected state with `repRounds`, the Sankey uses those rounds and a label says it is an example count; for `pModal < 0.70` a decomposition table renders below.

- [ ] **Step 1: Accept the uncertainty prop and prefer the representative run**

In `SenateCoalitionCard.tsx`, extend the props:

```tsx
import type { StateUncertainty } from '../../lib/uncertainty';

interface Props {
  data: SenateIrvRoundsData;
  states?: Record<string, StateUncertainty>;
}

export function SenateCoalitionCard({ data, states }: Props) {
```

After `const selected = selectedFips ? data.states[selectedFips] : null;` add:

```tsx
  const su = selectedFips ? states?.[selectedFips] : undefined;
  // In a state where the observed run names a different winner than the likely one, show a
  // representative run that produces the likely winner instead — a real coherent count,
  // labelled as an example rather than as measurement.
  const shownRounds = su?.repRounds ?? selected?.rounds;
  const shownWinner = su?.repRounds ? su.modal : selected?.winner;
```

Replace the `IRVSankey` call and the final-round block's data source with `shownRounds` / `shownWinner`:

```tsx
          <IRVSankey rounds={shownRounds!} irvWinner={shownWinner!} />
```

and change `finalRound` to derive from `shownRounds`:

```tsx
  const finalRound = shownRounds?.[shownRounds.length - 1];
```

- [ ] **Step 2: Add the example-count label and the decomposition table**

Immediately above the `<IRVSankey .../>` call, add:

```tsx
          {su?.repRounds && (
            <div className="text-[10px] text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1.5 mb-2">
              Example count producing the likely winner ({su.modal.split('_')[0]},{' '}
              {Math.round(su.pModal * 100)}% of resamples). The observed sample gives{' '}
              {su.observed.split('_')[0]} at {Math.round(su.pObserved * 100)}%. Individual
              percentages here illustrate one path rather than measuring this state.
            </div>
          )}
```

Below the final-round block, still inside the selected-state branch, add:

```tsx
          {su?.decomp && (
            <div className="pt-3 border-t border-border/50">
              <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest mb-2">
                Across {Object.keys(su.dist).length > 0 ? 'resamples' : ''} — why this race is close
              </div>
              <div className="grid grid-cols-[auto_1fr_1fr_1fr_1fr] gap-x-3 gap-y-1 text-[10px] items-center">
                <span className="text-muted-foreground">Party</span>
                <span className="text-muted-foreground">Makes final 5</span>
                <span className="text-muted-foreground">Reaches last round</span>
                <span className="text-muted-foreground">Wins</span>
                <span className="text-muted-foreground">Wins if it gets there</span>
                {Object.entries(su.decomp)
                  .sort((a, b) => b[1].win - a[1].win)
                  .filter(([, d]) => d.slate > 0.02)
                  .map(([p, d]) => (
                    <div key={p} className="contents">
                      <PartyPill party={p} />
                      <span className="tabular-nums text-muted-foreground">{Math.round(d.slate * 100)}%</span>
                      <span className="tabular-nums text-muted-foreground">{Math.round(d.final * 100)}%</span>
                      <span className="tabular-nums text-foreground font-semibold">{Math.round(d.win * 100)}%</span>
                      <span className="tabular-nums text-muted-foreground">
                        {d.winIfFinal == null ? '—' : `${Math.round(d.winIfFinal * 100)}%`}
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          )}
```

- [ ] **Step 3: Pass the prop from SenateTab**

Change `<SenateCoalitionCard data={irvRoundsStops[gi]} />` to:

```tsx
          <SenateCoalitionCard data={irvRoundsStops[gi]} states={unc?.senate.irv.states} />
```

- [ ] **Step 4: Verify in the browser**

Run tsc, eslint and build as in Task 11 Step 3. Then screenshot the coalition card with Wyoming selected:

```bash
cd /tmp && node -e "
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({viewport:{width:1280,height:1400},deviceScaleFactor:2});
  const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  await p.goto('http://localhost:4319/?tab=senate&method=irv&part=5',{waitUntil:'networkidle'});
  await p.waitForTimeout(2500);
  const card = p.locator('h3',{hasText:'How Senators Build'}).first().locator('xpath=ancestor::*[contains(@class,\"p-4\")][1]');
  await card.locator('select').selectOption({label:'WY'});
  await p.waitForTimeout(1200); await card.scrollIntoViewIfNeeded(); await p.waitForTimeout(500);
  await card.screenshot({path:'/tmp/wy.png'});
  console.log(errs.length?errs.join('\n'):'no page errors');
  await b.close();
})();
"
```

Expected: no page errors. Read `/tmp/wy.png` and confirm the amber example-count label, a Sankey ending on CON, and the decomposition table.

- [ ] **Step 5: Commit**

```bash
cd "/Users/bdecker/Local Projects/Personal/STV"
git add viz/src/components/senate/SenateCoalitionCard.tsx viz/src/tabs/SenateTab.tsx
git commit -m "Show a representative run and decomposition for close senate races"
```

---

## Phase 5 — Remaining tabs

### Task 14: House whiskers

**Files:**
- Modify: `viz/src/components/house/SeatShareBar.tsx`, `viz/src/components/house/ScenarioComparison.tsx`, `viz/src/tabs/HouseTab.tsx`

**Interfaces:**
- Produces: `SeatShareBar` gains optional `lo?: number; hi?: number; centre?: number`, rendering a `SeatWhisker` inside its existing track (which is already `relative`). `ScenarioComparison` gains `houseU?: Record<string, SeatInterval>` and passes intervals to the seat-share bar only (population bars have no sampling interval of this kind).

- [ ] **Step 1: Extend SeatShareBar**

In `viz/src/components/house/SeatShareBar.tsx`, add the import and props:

```tsx
import { getContrastText } from '../../constants/parties';
import { SeatWhisker } from '../shared/SeatWhisker';

export function SeatShareBar({ pct, max, color, label, faded, outline, dashed, lo, hi, centre }: {
  pct: number; max: number; color: string; label: string;
  faded?: boolean; outline?: boolean; dashed?: boolean;
  lo?: number; hi?: number; centre?: number;
}) {
```

Inside the returned track `<div>`, after the label `<span>`, add:

```tsx
      {lo != null && hi != null && centre != null && (
        <SeatWhisker lo={lo} hi={hi} centre={centre} max={max}
          title={`95% of resamples: ${lo.toFixed(1)}–${hi.toFixed(1)}%`} />
      )}
```

- [ ] **Step 2: Pass intervals through ScenarioComparison**

In `ScenarioComparison.tsx`, add to `Props`:

```tsx
  houseU?: Record<string, import('../../lib/uncertainty').SeatInterval>;
```

and to the destructured params: `houseU`.

The bar's axis is in **percent** (`max={maxPct}`) but `houseU` is in **seats**, so the bounds must be converted with the same denominator the row's own `seatPct` was computed from. Both branches of this component already have that denominator in scope as a local (`rmTotal` in the first, `totalSeats` in the second) — use it directly rather than re-deriving it by dividing, which blows up when `seatPct` is near zero.

First, read `ScenarioComparison.tsx:40-75` and note two things: the name of the seat-total local in the branch you are editing, and whether `r.party` holds a cluster index (a number) or a party code (a string). `houseU` is keyed by party code (`CON`, `LBR`, …), so if `r.party` is numeric you must index with `CLUSTER_TO_PARTY[r.party]`, which is already imported in this file.

Then replace the seat-share `<Bar>` at line 103 with:

```tsx
                {(() => {
                  const key = typeof r.party === 'number' ? CLUSTER_TO_PARTY[r.party] : r.party;
                  const u = houseU?.[key];
                  const denom = SEAT_TOTAL_LOCAL;   // rmTotal or totalSeats — see note above
                  const toPct = (n: number) => (n / denom) * 100;
                  return (
                    <Bar pct={r.seatPct} max={maxPct} color={c}
                      label={`${seatLabel} ${r.seatPct.toFixed(1)}% (${r.seats})`}
                      lo={u ? toPct(u.lo) : undefined}
                      hi={u ? toPct(u.hi) : undefined}
                      centre={u ? toPct(u.expected) : undefined} />
                  );
                })()}
```

Substitute the actual local name for `SEAT_TOTAL_LOCAL`. If the two branches use different names, each branch's bar uses its own.

- [ ] **Step 3: Pass the data from HouseTab**

In `viz/src/tabs/HouseTab.tsx`, add `import { uncertaintyAt } from '../lib/uncertainty';`, compute `const houseU = scenario === 'rawMulti' ? uncertaintyAt(gi)?.house.seats : undefined;` next to the other stop-indexed values, and add `houseU={houseU}` to the `<ScenarioComparison .../>` call at line ~374.

- [ ] **Step 4: Verify**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV/viz" && npx tsc -b && npx vitest run && npx vite build 2>&1 | grep -E "built in|error"`
Expected: all clean, 12+ tests passing

Screenshot the House tab's "Population vs Seat Share" card with the playwright pattern from Task 11 and confirm whiskers appear on the seat bars only.

- [ ] **Step 5: Commit**

```bash
cd "/Users/bdecker/Local Projects/Personal/STV"
git add viz/src/components/house/ viz/src/tabs/HouseTab.tsx
git commit -m "Add sampling whiskers to house seat-share bars"
```

---

### Task 15: Presidency and Primary win probabilities

**Files:**
- Modify: `viz/src/tabs/PresidencyTab.tsx`, `viz/src/tabs/PrimaryTab.tsx`

**Interfaces:**
- Consumes: `uncertaintyAt(gi)?.president`, `uncertaintyAt(gi)?.primary`.
- Produces: one compact line per tab. No new components.

- [ ] **Step 1: Add the presidency line**

In `PresidencyTab.tsx`, add `import { uncertaintyAt } from '../lib/uncertainty';`. Find the stop index the tab already uses for its turnout state (the same `gi` pattern as `SenateTab`; if the tab stores the stop as a string, convert with `GAP_STOPS.indexOf(Number(part))`). Beneath the headline winner display, add:

```tsx
      {(() => {
        const pu = uncertaintyAt(gi)?.president;
        if (!pu) return null;
        const d = pu.irv.dist;
        const top = Object.entries(d).slice(0, 3);
        return (
          <p className="text-[11px] text-muted-foreground">
            Across resamples: {top.map(([p, v]) => `${PARTY_NAMES[p] ?? p} ${Math.round(v * 100)}%`).join(' · ')}
          </p>
        );
      })()}
```

- [ ] **Step 2: Add the primary line**

In `PrimaryTab.tsx`, same import, and beneath the final-slate display add:

```tsx
      {(() => {
        const su = uncertaintyAt(gi)?.primary;
        if (!su) return null;
        const shaky = Object.entries(su.slate).filter(([, v]) => v < 0.9)
          .sort((a, b) => a[1] - b[1]).slice(0, 4);
        if (!shaky.length) return null;
        return (
          <p className="text-[11px] text-muted-foreground">
            Least certain finalists across resamples:{' '}
            {shaky.map(([c, v]) => `${c.split('_')[0]} ${Math.round(v * 100)}%`).join(' · ')}
          </p>
        );
      })()}
```

- [ ] **Step 3: Verify**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV/viz" && npx tsc -b && npx vite build 2>&1 | grep -E "built in|error"`
Expected: clean. Load `?tab=presidency` and `?tab=primary` in the browser and confirm no page errors and the lines render.

- [ ] **Step 4: Commit**

```bash
cd "/Users/bdecker/Local Projects/Personal/STV"
git add viz/src/tabs/PresidencyTab.tsx viz/src/tabs/PrimaryTab.tsx
git commit -m "Show winner and finalist probabilities on Presidency and Primary"
```

---

## Phase 6 — Methodology

### Task 16: About → Caveats card

**Files:**
- Modify: `viz/src/tabs/AboutTab.tsx`

- [ ] **Step 1: Add the card**

In the `{active === 'caveats' && (` block of `AboutTab.tsx`, immediately after the "Stress-tested, not hand-picked" `<Card>`, insert:

```tsx
          <Card className="p-5">
            <div className="font-semibold text-foreground mb-2">How precise are the seat counts?</div>
            <div className="space-y-3 text-sm text-muted-foreground leading-relaxed">
              <p>
                Every party here is a stable ideological type, but which individual respondent lands in
                which is a statistical estimate. To find out how much that matters, each state&apos;s
                respondents are resampled 1,000 times and the whole election is re-run on every draw.
                The headline is the <strong className="text-foreground">most likely</strong> winner in
                each state; the whiskers show the range across draws.
              </p>
              <p>
                Most results barely move. A handful do. Wyoming has the smallest sample of any state at
                70 respondents, and its observed result is the less likely one: Conservative wins 54% of
                resamples, Populist 28%. The reason is worth stating, because it is not that Populist is
                weaker. The two are evenly matched head-to-head — each wins 59% of the time once they
                meet — but Conservative reaches the final round 93% of the time and Populist only 48%.
                Populist won the observed sample because it survived that far, which happens less than
                half the time.
              </p>
              <p>
                Where the observed run names a different winner than the likely one, the vote-flow chart
                for that state shows an <strong className="text-foreground">example count</strong> that
                produces the likely winner instead, chosen to be typical of such counts. Those individual
                percentages illustrate one path; they are not measurements of that state. This affects
                three states under IRV and six under Condorcet.
              </p>
              <p>
                One method turns out to be markedly more stable than the other, and not because of sample
                size. Under Condorcet, 20 of 51 races reproduce their winner in over 90% of draws; under
                IRV only 10 do. The gap persists in large states: Washington&apos;s Condorcet winner holds
                in 100% of draws while its IRV winner holds in 39%. IRV eliminates candidates one at a
                time, so a small shift in votes can change the whole elimination path. Condorcet compares
                every pair at once and has no path to change. That is a real argument about method choice,
                not a quirk of this data.
              </p>
              <p className="text-[11px]">
                These are <strong className="text-foreground">bootstrap percentile intervals</strong>, not
                credible intervals — an election outcome is a complex, discontinuous function of the data,
                so resampling is the right tool. Per-party ranges do not sum to the chamber size, because
                two parties cannot both land at their maximum; the most-likely and expected chambers both
                do sum correctly. And this captures <em>sampling</em> uncertainty only: candidate fields
                are held fixed, so the true uncertainty is wider than shown.
              </p>
            </div>
          </Card>
```

- [ ] **Step 2: Verify**

Run: `cd "/Users/bdecker/Local Projects/Personal/STV/viz" && npx tsc -b && npx eslint src/tabs/AboutTab.tsx && npx vite build 2>&1 | grep -E "built in|error"`
Expected: clean

Load `?tab=about&about=caveats` and confirm the card renders.

- [ ] **Step 3: Final full verification**

```bash
cd "/Users/bdecker/Local Projects/Personal/STV/viz" && npx tsc -b && npx vitest run && npx eslint src/lib src/components/shared 2>&1 | tail -3 && npx vite build 2>&1 | grep -E "built in"
```

Expected: tsc silent, all vitest passing, no lint errors in the new files, build succeeds.

Then walk the manual checklist from the spec's Verification section: senate headline sums to 102, slider updates intervals, Wyoming hatched and substituted, house sums to 873, legislation reflects the modal chamber, Crossover degrades with no layout break.

- [ ] **Step 4: Commit**

```bash
cd "/Users/bdecker/Local Projects/Personal/STV"
git add viz/src/tabs/AboutTab.tsx
git commit -m "Document sampling uncertainty in About/Caveats"
```

---

## Self-review

**Spec coverage:** resampling design → Task 1; injection → Task 2; harness and per-draw contests → Task 3; representative-run rule → Task 4; output payload → Task 5; the run itself → Task 6; vote model → Task 7; types/accessor → Task 8; `SeatWhisker` → Task 9; `UncertaintyDetail` → Task 10; modal headline + whiskers → Task 11; map hatch → Task 12; substituted runs + decomposition → Task 13; house → Task 14; presidency/primary → Task 15; About → Task 16. Every locked decision and every Verification bullet maps to a step.

**Known gaps deliberately left:** the spec's `LegislationTab.tsx` row needs no code change — Task 7 changes the data it already reads, and Task 16 Step 3 verifies it. Crossover degradation needs no code either: `unc` is `undefined` when `pipeline !== 'rawMulti'` and every consumer prop is optional.

**Two places the implementer must check rather than assume:** Task 3 Step 4 (the presidential module's `OUTPUT_DIR`/`PRIMARY_PATH` global names) and Task 14 Step 2 (whether `ScenarioComparison`'s row party field is a cluster index or a party code). Both are flagged inline with the command to run.

**Type consistency check:** `SeatInterval` (`modal`/`expected`/`lo`/`hi`/`observed`) is defined in Task 8 and consumed with those exact keys in Tasks 10, 11, 14. `StateUncertainty` (`observed`/`modal`/`pModal`/`pObserved`/`dist`/`substituted`/`repRounds`/`repShare`/`decomp`) is defined in Task 8 and consumed in Tasks 10, 12, 13. `whiskerGeometry(lo, hi, centre, max)` in Task 9 is called with that argument order by `SeatWhisker` and by `SeatShareBar` in Task 14. `run_draw(seed, lam, depth, observed)` in Task 3 is called with those keywords in Tasks 4, 5 and the CLI. `build_uncertainty(draws, observed, n_draws, seed)` in Task 5 is called with those keywords in the CLI and the selftest.
