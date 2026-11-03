"""Tag every CES Stage A pool item with its battery (docs/EFA_ITEM_SELECTION_ROBUSTNESS.md §3c step 1).

Data: CES 2024 Common Content (efa_update.CES_PATH). Questionnaire order is taken from the variable order of the file,
which follows the codebook; the misnumbered CC24_323f sitting inside the CC24_328 tax grid (position 144) is the check
that variable order is questionnaire order. Pool: item_pool.POOL (Stage A, 69 items) plus the checkbox binaries item_pool.FP (their eligibility is an open
ruling in §3c; tagged so the foreign-policy pools can run). The exclusive "none" boxes are not pool items but are
asked inside the same grids, so they do not break adjacency.

Battery = items sharing one response scale and asked consecutively with no other question between them. Two pool
items are in the same battery when their file positions are adjacent (no variable between) and their answer labels
are identical. Every gap in position between pool items here is an asked question (e.g. CC24_330* between CC24_323f
and CC24_340a), so a gap always ends a battery.
Writes analysis/efa/ces_item_pool.csv.
"""
import pandas as pd

import item_pool as ip

HAND_DROPS = {"CC24_440a", "CC24_441a", "CC24_441b", "pew_bornagain"}


def main():
    r = pd.io.stata.StataReader(ip.eu.CES_PATH)
    labels = r.variable_labels()
    order = list(labels)
    allitems = ip.POOL + ip.FP
    NONE_BOXES = ["CC24_420_7", "CC24_308a_1", "CC24_308b_1"]
    lab = pd.read_stata(ip.eu.CES_PATH, columns=allitems + NONE_BOXES, convert_categoricals=True)
    scale = {c: "numeric 0-40 weeks" if c == "CC24_325" else " / ".join(x for x in lab[c].cat.categories if x != "Don't know")
             for c in allitems + NONE_BOXES}
    items = sorted(allitems + NONE_BOXES, key=order.index)
    groups, cur = [], [items[0]]
    for a, b in zip(items, items[1:]):
        if order.index(b) == order.index(a) + 1 and scale[a] == scale[b]:
            cur.append(b)
        else:
            groups.append(cur)
            cur = [b]
    groups.append(cur)
    rows = []
    for g in groups:
        bid = g[0] if len(g) == 1 else f"{g[0]}..{g[-1]}"
        for c in g:
            if c in NONE_BOXES:
                continue
            rows.append({"item_id": c, "label": labels[c], "questionnaire_position": order.index(c), "scale": scale[c],
                         "battery_id": bid, "production_24": c in ip.eu.ITEMS_24, "checkbox": c in ip.FP, "hand_drop_retested": c in HAND_DROPS})
    out = pd.DataFrame(rows)
    out.to_csv(ip.rl.ROOT / "analysis/efa/ces_item_pool.csv", index=False)
    print(out.groupby("battery_id", sort=False).item_id.apply(lambda s: f"{len(s)}: " + " ".join(s)).to_string())


if __name__ == "__main__":
    main()
