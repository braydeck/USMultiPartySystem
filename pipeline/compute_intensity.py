#!/usr/bin/env python3
"""Full response distributions for the multi-point items the app otherwise
collapses to a single 0/1.

The Compare/Platform views show these as one number (spending → "% increase",
agree scales → "% agree"), which throws away the compromise/neutral middle
("Maintain", "Neither") and the strong-vs-somewhat intensity. This emits the
complete weighted per-category distribution per cluster + nation so the viz can
show the real shape. Same listwise-alignment trick as add_compare_items.py.

Emits viz/src/data/clusterIntensity.json.
"""
import json
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DTA = ROOT / "CCES24_Common_OUTPUT_vv_topost_final (2).dta"
TYPO = ROOT / "data" / "processed" / "typology_cluster_assignments.csv"
STATS = ROOT / "data" / "outputs" / "profiles" / "cluster_stats.csv"
OUT = ROOT / "viz" / "src" / "data" / "clusterIntensity.json"

CLUSTER_TO_PARTY = {0: "CON", 1: "LBR", 2: "STY", 3: "NAT", 4: "LIB", 5: "POP", 6: "CUP", 7: "OAO", 8: "DSA", 9: "PRG"}

ITEMS_25 = ['pew_churatd','CC24_302','CC24_303','CC24_341a','CC24_341c','CC24_341d','CC24_323a','CC24_323b','CC24_323d','CC24_321b','CC24_321d','CC24_321e','CC24_325','CC24_324b','CC24_340a','CC24_340b','CC24_340c','CC24_340e','CC24_340f','CC24_440b','CC24_440c','CC24_421_1','CC24_421_2','CC24_423','CC24_424']
ITEMS = [x for x in ITEMS_25 if x != 'CC24_340a']  # 24 EFA anchor (row alignment)

# Multi-point items to surface, with display order + kind.
# kind: 'diverging' has a neutral middle; 'freq' is a sequential frequency scale.
SPEND = ['CC24_443_1','CC24_443_2','CC24_443_3','CC24_443_4','CC24_443_5']
AGREE = ['CC24_440a','CC24_440b','CC24_440c','CC24_440d','CC24_441a','CC24_441b','CC24_441e','CC24_441f','CC24_441g','CC24_421_1','CC24_421_2']
ECON = ['CC24_302','CC24_303']
FREQ = ['pew_churatd']
KIND = {**{v: 'diverging' for v in SPEND + AGREE + ECON}, **{v: 'freq' for v in FREQ}}
ORDER = SPEND + ECON + AGREE + FREQ

# label text that marks a code as non-substantive (dropped before shares)
DROP = ('skipped', 'not asked', 'not sure', "don't know", 'dk')


def main():
    reader = pd.io.stata.StataReader(str(DTA))
    varlabels = reader.variable_labels()
    vallabels = reader.value_labels()
    setname = dict(zip(reader._varlist, reader._lbllist))

    stats = pd.read_csv(STATS).drop_duplicates('variable').set_index('variable')

    load = list(dict.fromkeys(ITEMS + ORDER + ['commonpostweight']))
    df = pd.read_stata(DTA, columns=load, convert_categoricals=False)
    mask = df[ITEMS + ['commonpostweight']].notna().all(axis=1)
    dc = df[mask].reset_index(drop=True)
    typo = pd.read_csv(TYPO)
    assert len(dc) == len(typo), f"row mismatch {len(dc)} vs {len(typo)}"
    cl = typo['cluster'].values
    w = dc['commonpostweight'].values.astype(float)

    def substantive_codes(var):
        labs = vallabels.get(setname.get(var, ''), {})
        codes = []
        for c in sorted(int(k) for k in labs.keys()):
            txt = str(labs[c]).strip().lower()
            if any(d in txt for d in DROP) or c in (8, 9, 98, 99):
                continue
            codes.append((c, str(labs[c])))
        return codes

    def shares(var, codes, m):
        r = dc[var].values.astype(float)
        codeset = [c for c, _ in codes]
        ok = m & np.isin(r, codeset)
        tot = w[ok].sum()
        if tot <= 0:
            return [0.0] * len(codes)
        return [round(w[ok & (r == c)].sum() / tot * 100, 1) for c, _ in codes]

    items = []
    for var in ORDER:
        codes = substantive_codes(var)
        if len(codes) < 3:
            print(f"skip {var}: {len(codes)} substantive codes")
            continue
        labels = [lab for _, lab in codes]
        kind = KIND[var]
        middle = len(codes) // 2 if kind == 'diverging' else None
        meta = stats.loc[var] if var in stats.index else None
        items.append({
            "variable": var,
            "question": (meta["question"] if meta is not None else varlabels.get(var, var)),
            "domain": (meta["domain"] if meta is not None else "Other"),
            "kind": kind,
            "labels": labels,
            "middleIndex": middle,
            "national": shares(var, codes, np.ones(len(dc), bool)),
            "parties": {CLUSTER_TO_PARTY[k]: shares(var, codes, cl == k) for k in range(10)},
        })

    OUT.write_text(json.dumps({"items": items}, indent=2))
    print(f"wrote {OUT.relative_to(ROOT)} — {len(items)} items")
    for it in items:
        sty = it["parties"]["STY"]
        mid = it["middleIndex"]
        midtxt = f" · STY {it['labels'][mid]}={sty[mid]}%" if mid is not None else ""
        print(f"  {it['domain'][:18]:18} {it['question'][:44]:44}{midtxt}")


if __name__ == '__main__':
    main()
