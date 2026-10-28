"""Apply the frozen matched crosswalk to ANES 2024 and report coverage and marginals.

Data: ANES 2024 Time Series, CSV release 2025-08-08
(UNTRACKED/anes_timeseries_2024_csv_20250808/), n = 5,521. Weight V240108a (post-election
full sample), PSU V240108c, strata V240108d.

Deliberately computes no correlations: the crosswalk is frozen before any ANES item
correlation is seen (analysis/validation/DECISIONS.md). Marginals only, to verify recodes.
Every recoded item is oriented so higher = the same pole as the CES item.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
ANES_CSV = ROOT / "UNTRACKED" / "anes_timeseries_2024_csv_20250808" / "anes_timeseries_2024_csv_20250808.csv"
CROSSWALK = Path(__file__).parent / "config" / "anes_matched_crosswalk.csv"
OUT = Path(__file__).parent / "outputs"
WEIGHT, PSU, STRATUM = "V240108a", "V240108c", "V240108d"


def parse_map(spec):
    return {int(a): float(b) for a, b in (pair.split("=") for pair in spec.split(","))}


def recode_row(df, sources, spec):
    """Unlisted codes (negative missing codes, 99 'haven't thought', 'Other') become NaN.
    For a splice, the first source with a valid value wins."""
    srcs = sources.split("|")
    maps = dict(part.strip().split(":", 1) for part in spec.split(" / ")) if len(srcs) > 1 else {srcs[0]: spec}
    out = pd.Series(np.nan, index=df.index)
    for s in srcs:
        out = out.fillna(df[s].map(parse_map(maps[s])))
    return out


def load_matched():
    cw = pd.read_csv(CROSSWALK)
    cw = cw[cw.fidelity != "none"]
    cols = sorted({s for src in cw.anes_sources for s in src.split("|")} | {WEIGHT, PSU, STRATUM, "V240001"})
    raw = pd.read_csv(ANES_CSV, usecols=cols, low_memory=False)
    for c in (WEIGHT, PSU, STRATUM):
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    items = pd.DataFrame({r.ces_var: recode_row(raw, r.anes_sources, r.anes_map) for r in cw.itertuples()})
    return raw, items, cw


def main():
    raw, items, cw = load_matched()
    w = raw[WEIGHT]
    has_w = w.notna() & (w > 0)
    rows = []
    for r in cw.itertuples():
        x = items[r.ces_var]
        ok = x.notna() & has_w
        dist = (w[ok].groupby(x[ok]).sum() / w[ok].sum()).round(3)
        rows.append({
            "ces_var": r.ces_var, "anes": r.anes_sources, "n_valid": int(ok.sum()),
            "wmean": round(float(np.average(x[ok], weights=w[ok])), 2),
            "modal_share": float(dist.max()), "weighted_dist": dict(dist),
        })
    report = pd.DataFrame(rows)
    listwise = items.notna().all(axis=1) & has_w
    OUT.mkdir(exist_ok=True)
    report.to_csv(OUT / "matched_marginals.csv", index=False)
    pd.set_option("display.width", 200, "display.max_colwidth", 80)
    print(report.to_string(index=False))
    print(f"\nrespondents with post weight: {int(has_w.sum())}")
    print(f"listwise complete on {items.shape[1]} matched items: {int(listwise.sum())}")


if __name__ == "__main__":
    main()
