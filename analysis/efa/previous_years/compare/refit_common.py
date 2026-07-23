#!/usr/bin/env python3
"""Refit the common-subset EFA at k=3 from stored item matrices (no dta reload).

The common set now excludes the state-spending battery (see crosswalk.EXCLUDE_FROM_COMMON),
so it maps to the 2024 named factors (Security & Order, Religious Traditionalism,
Populist Conservatism) rather than spinning off a spending/method factor. Rewrites
each wave's common fit + outputs from the previously-stored 15-item matrix.
"""
import sys, pickle, warnings
warnings.filterwarnings("ignore")
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import wave_pipeline as wp, crosswalk as cwmod, io_paths as io

K = 2


def main():
    common_ids = list(cwmod.common_constructs()["construct_id"])
    print(f"common set ({len(common_ids)}): {common_ids}\n")
    for wave in io.WAVES:
        pkl = io.out_dir(wave) / "fit_results.pkl"
        with open(pkl, "rb") as f:
            res = pickle.load(f)
        c = res["common"]
        items_df = pd.DataFrame(c["_Xitems"], columns=c["item_ids"])[common_ids]
        new = wp.fit_efa(items_df, c["w"], c["pid3"], common_ids, K, wave, "common", save=True)
        new.pop("model", None)
        res["common"] = new
        with open(pkl, "wb") as f:
            pickle.dump(res, f)
        print(f"  refit {wave} common k={K}: PA k={new['k_pa']}, eff clusters={new['n_eff']}")


if __name__ == "__main__":
    main()
