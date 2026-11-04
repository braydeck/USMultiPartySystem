"""Carry each respondent's House density tier over to the nine-party row set (2026-11-04).

run_house_canonical.py reads density_tier positionally from data/outputs/canonical/ballots_checkpoint.parquet, which
held one row per respondent of the old 45,214-row typology. The 45,214 keep their old tier by caseid (old row i =
old typology row i at f263fae, the last commit before the nine). The 4,217 respondents new to the nine
get a tier the way pipeline/archive/stv_step2.assign_density_tiers_respondents made them: CES urbancity (city URBAN,
suburb and town SUBURBAN, rural RURAL), otherwise a draw from the state's Census urban share (rng seed 42).
Writes the checkpoint with density_tier in the new typology order; district_id is rewritten by run_house_canonical.
"""
import io
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))
from stv_config import DTA_PATH, STATE_URBAN_PCT, URBANCITY_TO_TIER  # noqa: E402

CKPT = ROOT / "data/outputs/canonical/ballots_checkpoint.parquet"
old_ids = pd.read_csv(io.BytesIO(subprocess.check_output(
    ["git", "show", "f263fae:data/processed/typology_cluster_assignments.csv"], cwd=ROOT)), usecols=["caseid"]).caseid.values
old = pd.read_parquet(io.BytesIO(subprocess.check_output(
    ["git", "show", "f263fae:data/outputs/canonical/ballots_checkpoint.parquet"], cwd=ROOT)))
assert len(old) == len(old_ids)
tier = pd.Series(old.density_tier.values, index=old_ids)

new = pd.read_csv(ROOT / "data/processed/typology_cluster_assignments.csv", usecols=["caseid", "inputstate"])
dta = pd.read_stata(DTA_PATH, columns=["caseid", "urbancity"], convert_categoricals=False).set_index("caseid")
out = tier.reindex(new.caseid.values).values.astype(object)
fresh = pd.isna(out)
rng = np.random.default_rng(42)
for i in np.where(fresh)[0]:
    t = URBANCITY_TO_TIER.get(dta.urbancity.get(new.caseid.values[i]))
    if t is None:
        u = STATE_URBAN_PCT.get(int(new.inputstate.values[i]), 70.0) / 100.0
        p = np.array([max(0.0, (u * 100 - 30) / 100.0), 0.30, max(0.0, 1.0 - u)])
        t = rng.choice(["URBAN", "SUBURBAN", "RURAL"], p=p / p.sum())
    out[i] = t
pd.DataFrame({"district_id": -1, "density_tier": out}).to_parquet(CKPT, index=False)
print(f"{len(out):,} rows; carried {int((~fresh).sum()):,}, new {int(fresh.sum()):,}; tiers {pd.Series(out).value_counts().to_dict()}")
