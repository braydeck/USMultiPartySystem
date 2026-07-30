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
