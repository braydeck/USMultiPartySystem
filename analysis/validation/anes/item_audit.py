"""Coding audit of the ANES independent pool: every substantive code, its codebook label, the value it is mapped to,
and its weighted share, so direction, ordering and missing-code handling can be read item by item.

Data: ANES 2024 Time Series CSV and codebook PDF (2025-08-08 release), post weight V240108a.
Pool: config/anes_independent_pool.csv. Items in the Stage C fit: outputs/stage_c/loadings_k10.csv.

Flags per item:
  unmapped_substantive  codes >= 1 with a codebook label that the map sends to NaN (fine for DK / haven't thought /
                        other; anything else is a coding loss)
  unlabeled_in_data     codes >= 1 present in the data with no codebook label and no map entry
  nonmonotone           mapped values do not rise or fall with the code order (expected for some scales; read it)
  has_summary           a codebook summary variable lists this source as a component, i.e. a direction + strength
                        version may exist that the pool does not use
Writes outputs/item_audit/{audit.txt, flags.csv}.
"""
import numpy as np
import pandas as pd

import independent_efa as ie
import recode_matched as rm
import tag_batteries as tb

OUT = ie.me.OUT / "item_audit"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cw = pd.read_csv(ie.POOL)
    fit = set(pd.read_csv(ie.me.OUT / "stage_c" / "loadings_k10.csv", index_col=0).index)
    order, labels, sq = tb.parse()
    summaries = {}
    for v in order:
        if v.endswith("x"):
            for comp in sq[v]:
                summaries.setdefault(comp.split()[0], []).append(v)
    srcs = sorted({s for x in cw.anes_sources for s in x.split("|")})
    raw = pd.read_csv(rm.ANES_CSV, usecols=srcs + [rm.WEIGHT], low_memory=False).apply(pd.to_numeric, errors="coerce")
    w = raw[rm.WEIGHT].fillna(0).values
    lines, flags = [], []
    for r in cw.itertuples():
        parts = r.anes_sources.split("|")
        maps = dict(p.strip().split(":", 1) for p in r.anes_map.split(" / ")) if len(parts) > 1 else {parts[0]: r.anes_map}
        lines.append(f"\n{r.item_id}  [{'FIT' if r.item_id in fit else 'out'}]  {r.label}")
        f = {"item_id": r.item_id, "in_fit": r.item_id in fit, "label": r.label}
        for s in parts:
            m = rm.parse_map(maps[s])
            lab = labels.get(s, {})
            x = raw[s].values
            codes = sorted(set(lab) | {int(c) for c in np.unique(x[~np.isnan(x)]) if c >= 1})
            tot = w[~np.isnan(x) & (x >= 1)].sum() or 1
            segs = []
            for c in codes:
                share = w[x == c].sum() / tot
                segs.append(f"{c}:{lab.get(c, '??')[:38]}→{m.get(c, 'NaN')} ({share:.0%})")
                if c not in m and c in lab:
                    f.setdefault("unmapped_substantive", []).append(f"{c}:{lab[c][:30]}")
                if c not in lab and c not in m:
                    f.setdefault("unlabeled_in_data", []).append(str(c))
            mapped = [m[c] for c in sorted(m)]
            if len(mapped) > 2 and not (all(np.diff(mapped) >= 0) or all(np.diff(mapped) <= 0)):
                f["nonmonotone"] = True
            if s in summaries:
                f.setdefault("has_summary", []).extend(summaries[s])
            lines.append(f"   {s}: " + " | ".join(segs))
        flags.append({k: ("; ".join(v) if isinstance(v, list) else v) for k, v in f.items()})
    (OUT / "audit.txt").write_text("\n".join(lines))
    fl = pd.DataFrame(flags)
    fl.to_csv(OUT / "flags.csv", index=False)
    print(fl.drop(columns="label").notna().sum().to_string())


if __name__ == "__main__":
    main()
