#!/usr/bin/env python3
"""Run a wave's native + common-subset EFA/cluster fits.

Usage:  python run_wave.py <2018|2020|2022|2024>

Native  fit: all crosswalk items usable in this wave (coverage exact|equivalent|weak), k=5.
Common  fit: the 7 all-wave backbone items (F1/F4/F5), k=3 — the apples-to-apples basis
             for cross-wave congruence, clustering, and the 2024 prior-lens projection.
Artifacts land in outputs/<wave>/.  Both fits also pickle their full result dict for
the compare step.
"""
import sys, pickle, warnings
warnings.filterwarnings("ignore")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import wave_pipeline as wp, crosswalk as cwmod, io_paths as io

NATIVE_K = 5
COMMON_K = 4


def main(wave):
    assert wave in io.WAVES, wave
    print(f"\n########## WAVE {wave} ({io.KIND[wave]}) ##########", flush=True)
    cw = cwmod.load()

    # load the union of native items once (common items are a subset)
    items_df, w, pid3, meta = wp.load_wave_items(wave, levels=cwmod.USABLE)
    native_ids = list(items_df.columns)
    common_ids = [c for c in cwmod.common_constructs(cw=cw)["construct_id"] if c in native_ids]

    print(f"native items ({len(native_ids)}): {native_ids}")
    print(f"common items ({len(common_ids)}): {common_ids}")

    results = {}
    results["native"] = wp.fit_efa(items_df, w, pid3, native_ids, NATIVE_K, wave, "native")
    results["common"] = wp.fit_efa(items_df, w, pid3, common_ids, COMMON_K, wave, "common")

    # pickle for compare step (drop the sklearn model to keep it light/portable)
    for r in results.values():
        r.pop("model", None)
    with open(io.out_dir(wave) / "fit_results.pkl", "wb") as f:
        pickle.dump(results, f)
    print(f"\nsaved outputs/{wave}/  (loadings/phi/parallel/cluster_shares/diagnostics + fit_results.pkl)")


if __name__ == "__main__":
    main(sys.argv[1])
