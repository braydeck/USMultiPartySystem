#!/usr/bin/env python3
"""Per-cluster internal cohesion metrics for the viz.

Two questions this answers, from respondent-level CES data (not cluster means):
  1. Does a cluster cohere by *consistency* (members share strong positions) or by
     *cross-pressure* (members are individually mixed)?  → overdispersion + the
     distribution of each member's "liberal share" across binary items.
  2. Does it seek *compromise*?  → how often it picks the middle option on ordinal
     batteries that offer one (spending "Maintain", agree "Neither").

Emits viz/src/data/clusterCohesion.json. Aligns the listwise EFA sample (notna on
the 24 items + weight → N=45,707, same order as the typology file) to
typology_cluster_assignments.csv by row position, exactly like add_compare_items.py.
"""
import json
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DTA = ROOT / "CCES24_Common_OUTPUT_vv_topost_final (2).dta"
TYPO = ROOT / "data" / "processed" / "typology_cluster_assignments.csv"
OUT = ROOT / "viz" / "src" / "data" / "clusterCohesion.json"

CLUSTER_TO_PARTY = {0: "CON", 1: "LBR", 2: "STY", 3: "NAT", 4: "LIB", 5: "POP", 6: "CUP", 7: "OAO", 8: "DSA", 9: "PRG"}

ITEMS_25 = ['pew_churatd','CC24_302','CC24_303','CC24_341a','CC24_341c','CC24_341d','CC24_323a','CC24_323b','CC24_323d','CC24_321b','CC24_321d','CC24_321e','CC24_325','CC24_324b','CC24_340a','CC24_340b','CC24_340c','CC24_340e','CC24_340f','CC24_440b','CC24_440c','CC24_421_1','CC24_421_2','CC24_423','CC24_424']
ITEMS = [x for x in ITEMS_25 if x != 'CC24_340a']  # 24 EFA input items (listwise anchor)

# Binary support/oppose items (coded 1/2) for the consistency measure.
BIN = ['CC24_341a','CC24_341c','CC24_341d','CC24_323a','CC24_323b','CC24_323d','CC24_321b','CC24_321d','CC24_321e','CC24_324b','CC24_340b','CC24_340c','CC24_340e','CC24_340f']
# Ordinal batteries with a genuine middle/compromise category (code 3).
SPEND = ['CC24_443_1','CC24_443_2','CC24_443_3','CC24_443_4','CC24_443_5']  # 3 = Maintain
AGREE = ['CC24_440b','CC24_440c','CC24_441a','CC24_441b','CC24_441e','CC24_441f','CC24_441g']  # 3 = Neither
COMPROMISE = SPEND + AGREE

NBINS = 10


def main():
    cols = list(dict.fromkeys(ITEMS + BIN + COMPROMISE + ['pid3', 'commonpostweight']))
    df = pd.read_stata(DTA, columns=cols, convert_categoricals=False)
    mask = df[ITEMS + ['commonpostweight']].notna().all(axis=1)
    dc = df[mask].reset_index(drop=True)
    typo = pd.read_csv(TYPO)
    assert len(dc) == len(typo), f"row mismatch {len(dc)} vs {len(typo)}"
    cl = typo['cluster'].values
    w = dc['commonpostweight'].values.astype(float)
    pid = dc['pid3'].values

    # Liberal direction per binary item = the code Democrats favor over Republicans.
    libcode = {}
    for it in BIN:
        r = dc[it].values
        d1, d2 = ((r == 1) & (pid == 1)).sum(), ((r == 2) & (pid == 1)).sum()
        r1, r2 = ((r == 1) & (pid == 2)).sum(), ((r == 2) & (pid == 2)).sum()
        libcode[it] = 1 if d1 / (d1 + r1 + 1e-9) > d2 / (d2 + r2 + 1e-9) else 2
    L = np.column_stack([(dc[it].values == libcode[it]).astype(float) for it in BIN])
    frac = L.mean(axis=1)
    N = len(BIN)

    def middle_share(m):
        vals = []
        for it in COMPROMISE:
            r = dc[it].values.astype(float)
            ok = m & np.isin(r, [1, 2, 3, 4, 5])
            if w[ok].sum() > 0:
                vals.append(w[ok & (r == 3)].sum() / w[ok].sum() * 100)
        return float(np.mean(vals))

    edges = np.linspace(0, 1, NBINS + 1)

    def summarize(m):
        f, ww = frac[m], w[m]
        p = float((ww * f).sum() / ww.sum())
        var = float((ww * (f - p) ** 2).sum() / ww.sum())
        sd_chance = np.sqrt(p * (1 - p) / N)
        hist = []
        for i in range(NBINS):
            lo, hi = edges[i], edges[i + 1]
            sel = (f >= lo) & (f < hi if i < NBINS - 1 else f <= hi)
            hist.append(round(ww[sel].sum() / ww.sum() * 100, 2))
        return {
            "mean": round(p, 3),
            "overdispersion": round(np.sqrt(var) / sd_chance, 3) if sd_chance > 0 else None,
            "hist": hist,
            "middleShare": round(middle_share(m), 1),
            "n": int(m.sum()),
        }

    out = {
        "binCenters": [round((edges[i] + edges[i + 1]) / 2, 3) for i in range(NBINS)],
        "nItems": N,
        "nation": summarize(np.ones(len(dc), bool)),
        "parties": {CLUSTER_TO_PARTY[k]: summarize(cl == k) for k in range(10)},
    }
    OUT.write_text(json.dumps(out, indent=2))
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"{'party':7}{'mean':>6}{'overdisp':>10}{'middle%':>9}")
    for code, s in out["parties"].items():
        print(f"{code:7}{s['mean']:6.2f}{s['overdispersion']:10.2f}{s['middleShare']:9.1f}")


if __name__ == '__main__':
    main()
