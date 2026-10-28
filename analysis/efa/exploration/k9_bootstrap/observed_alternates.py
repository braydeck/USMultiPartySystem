#!/usr/bin/env python3
"""The election under each of the three full-data K = 9 solution families, and which family each
bootstrap draw lands in.

PROVENANCE
  A 20-seed K = 9 fit (seeds 42-61, n_init 5, full data; run by the coordinating session) splits into three
  families by lower bound: ~697 (11 seeds, including 42-46; seed 45 is observed.csv), ~757 (seeds 51, 52,
  54, 56, 60, 61) and ~360 (seeds 49, 57, 58). The seed-51 typology (best bound overall) was supplied as
  a CSV with IDs already matched to seed 61. Seed 49 is fit here with dpgmm_clustering.py.
  Bootstrap fits: the 200 cached draws from run_k9_bootstrap.py. Run 2026-10-28.

WHAT IT DOES
  For seed 51 and seed 49: install the typology, run run_k9_bootstrap.lean_rebuild (validated against the
  full rebuild), record the same metrics as observed.csv -> observed_families.csv (seed 45 row copied in).
  Draw families: a draw's lower bound comes from a fit to its own resample, so it is not on the full-data
  scale (duplicated respondents raise the bound). Each draw is therefore assigned to the family whose
  full-data typology it agrees with most (ARI on hard labels over all 45,214) -> draw_families.csv.

USAGE
  python3 analysis/efa/exploration/k9_bootstrap/observed_alternates.py --work-dir <run_k9 work dir> \
      --seed51 <typ_k9_seed51.csv>
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import adjusted_rand_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_k9_bootstrap import (HERE, OBSERVED, PER_DRAW, PROC, TYPO, dpgmm, lean_rebuild,  # noqa: E402
                              metrics, REF)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work-dir", type=Path, required=True)
    ap.add_argument("--seed51", type=Path, required=True)
    a = ap.parse_args()
    fs = pd.read_csv(PROC / "efa_factor_scores.csv", usecols=["caseid"])
    ref_cluster = fs.merge(pd.read_csv(REF), on="caseid", how="left")["party_id"].values
    saved = a.work_dir / "typology_before_alternates.csv"
    shutil.copy(TYPO, saved)

    seed49 = a.work_dir / "typ_k9_seed49.csv"
    if not seed49.exists():
        dpgmm(["--seed", "49"], seed49, a.work_dir / "seed49_dpgmm.log")
    bound49 = float(re.search(r"lower bound=([\d.-]+)", (a.work_dir / "seed49_dpgmm.log").read_text()).group(1))

    obs = pd.read_csv(OBSERVED).assign(draw="seed 45", family="697", lower_bound=697.6289)
    rows = [obs.drop(columns=["sec"]).iloc[0].to_dict()]
    for label, family, bound, path in (("seed 51", "757", None, a.seed51), ("seed 49", "360", bound49, seed49)):
        shutil.copy(path, TYPO)
        lean_rebuild(a.work_dir / f"alt_{label.replace(' ', '')}.log")
        typ = pd.read_csv(TYPO)
        assert (typ.caseid.values == fs.caseid.values).all()
        rows.append({"draw": label, "family": family, "lower_bound": bound, **metrics(typ, ref_cluster)})
    shutil.copy(saved, TYPO)
    pd.DataFrame(rows).to_csv(HERE / "observed_families.csv", index=False)

    fam = {"697": a.work_dir / "observed_typology.csv", "757": a.seed51, "360": seed49}
    fam_labels = {k: pd.read_csv(p, usecols=["cluster"])["cluster"].values for k, p in fam.items()}
    print("ARI between families: " + ", ".join(
        f"{x}-{y} {adjusted_rand_score(fam_labels[x], fam_labels[y]):.3f}"
        for x, y in (("697", "757"), ("697", "360"), ("757", "360"))))
    out = []
    tdir = a.work_dir / "typologies"
    for b in pd.read_csv(PER_DRAW)["draw"]:
        lab = pd.read_csv(tdir / f"draw_{b:03d}.csv.gz", usecols=["cluster"])["cluster"].values
        aris = {k: adjusted_rand_score(v, lab) for k, v in fam_labels.items()}
        bound = float(re.search(r"lower bound=([\d.-]+)", (tdir / f"draw_{b:03d}.log").read_text()).group(1))
        best = max(aris, key=aris.get)
        out.append({"draw": b, "resample_lower_bound": bound, "family": best,
                    **{f"ari_{k}": round(v, 4) for k, v in aris.items()}})
    pd.DataFrame(out).to_csv(HERE / "draw_families.csv", index=False)


if __name__ == "__main__":
    main()
