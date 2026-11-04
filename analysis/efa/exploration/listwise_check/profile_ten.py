"""Profile of the revised-rule ten clusters: a card per cluster (factor positions, most distinctive policy views and
demographics, party ID last), full tables, and two overlap matrices (resampled respondents, redrawn factors).
Local page only.

Data: CES 2024 Common Content, weight commonpostweight, n = 49,431 (outputs/stage_c_v2/scores.csv).
Inputs (no refit here):
  outputs/profile_v2/{names,factors,policy,demographics,stability,swaps_10}.csv  (profile_v2.py)
  outputs/v2_draws/{summary,parties}.csv, draw_labels.npz                         (v2_draws.py, 50 factor redraws)
  outputs/stage_c_v2/labels.npz                                                    (cap-10 modal seed solution)
Unstable = mean resample Jaccard below 0.75 (the §3c stable line), as on the 5-and-10 page.
Redraw overlap: in each of the 50 redraws, each redraw cluster is mapped to the reference cluster it overlaps most
(weighted); cell (i, j) = weighted share of reference cluster i's members landing in a cluster mapped to j, averaged.
Distinctive rows: the policy items and demographic rows (party and vote excluded) with the largest absolute gap from
everyone, in points.
Writes outputs/profile_ten/{index.html, redraw_swaps.csv, distinctive.csv}.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import compare_typologies as ct
import loading_draws as ld
import reestimate_loadings as rl

CAP = int(sys.argv[1]) if len(sys.argv) > 1 else 10
WORD = {9: "nine", 10: "ten"}[CAP]
OUT = rl.OUT / f"profile_{WORD}"
P2 = rl.OUT / ("profile_v2" if CAP == 10 else f"profile_v2_k{CAP}")
REDRAWS = CAP == 10  # outputs/v2_draws/ holds redraws of the ten only
STABLE = 0.75
N_POLICY, N_DEMO = 6, 4
FACTOR_LABELS = {"Cultural conservatism (RT slot)": "Cultural conservatism", "Distrust": "Distrust of government",
                 "Security & Order": "Security & order", "Economic right (PC slot)": "Economic right"}


def redraw_swaps(ref, names, w):
    D = np.load(rl.OUT / "v2_draws/draw_labels.npz")
    draws = sorted(int(k[1:]) for k in D.files if k[1:].isdigit())
    ks = sorted(names, key=lambda k: names[k])
    M = np.zeros((len(ks), len(ks)))
    for d in draws:
        lab = D[f"d{d}"]
        mp = {c: ks[int(np.argmax([w[(lab == c) & (ref == k)].sum() for k in ks]))] for c in np.unique(lab)}
        mb = np.vectorize(mp.get)(lab)
        for i, k in enumerate(ks):
            m = ref == k
            for j, k2 in enumerate(ks):
                M[i, j] += w[m & (mb == k2)].sum() / w[m].sum()
    lbl = [names[k] for k in ks]
    return pd.DataFrame(M / len(draws) * 100, index=lbl, columns=lbl), len(draws)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    S = pd.read_csv(rl.OUT / "stage_c_v2/scores.csv")
    w = S.commonpostweight.values
    z = np.load(rl.OUT / "stage_c_v2/labels.npz")
    ref = ld.modal_solution(list(zip(range(42, 62), z[f"{CAP}_seed"], z[f"{CAP}_seed_bounds"])))[0]
    nm = pd.read_csv(P2 / "names.csv")
    names = dict(zip(nm[nm.cap == CAP].cluster, nm[nm.cap == CAP].name))
    ten = sorted(names.values())

    stab = pd.read_csv(P2 / "stability.csv").set_index("id")
    fac = pd.read_csv(P2 / "factors.csv", index_col=0)
    pol = pd.read_csv(P2 / "policy.csv")
    dem = pd.read_csv(P2 / "demographics.csv")
    if REDRAWS:
        red = pd.read_csv(rl.OUT / "v2_draws/summary.csv").set_index("party")
        parties = pd.read_csv(rl.OUT / "v2_draws/parties.csv")
        n_draws = parties.draw.nunique()
        under = parties[parties.kept < 0.5].groupby("party").size().reindex(ten, fill_value=0)
        RS, nd = redraw_swaps(ref, names, w)
        assert nd == n_draws
        RS = RS.loc[ten, ten]
        RS.round(1).to_csv(OUT / "redraw_swaps.csv")
    else:
        n_draws = 0
    SW = pd.read_csv(P2 / f"swaps_{CAP}.csv", index_col=0)
    if CAP == 9:  # working letters A-I from compare_typologies.py v2 9 (production order of each cluster's largest source party)
        let = pd.read_csv(rl.OUT / "compare_typologies_k9/letters.csv")
        mp = {names[c]: l for c, l in zip(let.cluster, let.label)}
        names = {c: mp[n] for c, n in names.items()}
        # drop the five-cluster columns first: their ids A-E would collide with the letters
        stab = stab[stab.key.isin(["ten", "all"])].rename(index=mp)
        stab["from"] = ""
        keep = list(mp) + ["Everyone"]
        fac = fac[keep].rename(columns=mp)
        pol = pol[[c for c in pol.columns if c not in list("ABCDE")]].rename(columns=mp)
        dem = dem[[c for c in dem.columns if c not in list("ABCDE")]].rename(columns=mp)
        SW = SW.rename(index=mp, columns=mp)
        ten = sorted(names.values())
    SW = SW.loc[ten, ten]

    groups = []
    for g in ten:
        groups.append({"id": g, "share": float(stab.loc[g, "share"]), "n": int(stab.loc[g, "n"]),
                       "jac": float(stab.loc[g, "jac"]), "unstable": bool(stab.loc[g, "unstable"]),
                       "from": stab.loc[g, "from"] if isinstance(stab.loc[g, "from"], str) else "",
                       "stay_resample": round(float(SW.loc[g, g]), 1),
                       **({"kept": round(float(red.loc[g, "kept_median"]), 2), "under": int(under[g]),
                           "stay_redraw": round(float(RS.loc[g, g]), 1)} if REDRAWS else {})})
    groups.append({"id": "Everyone", "n": int(stab.loc["Everyone", "n"]), "share": 100.0})

    dist = []
    ctx = dem.section == "Party and vote (context)"
    for g in ten:
        gp = (pol[g] - pol["Everyone"]).abs().sort_values(ascending=False).head(N_POLICY).index
        gd = (dem.loc[~ctx & (dem.label != "Median age"), g] - dem.loc[~ctx & (dem.label != "Median age"), "Everyone"]).abs().sort_values(ascending=False).head(N_DEMO).index
        dist += [{"cluster": g, "kind": "policy", "label": pol.label[i], "topic": pol.topic[i], "value": pol[g][i], "everyone": pol["Everyone"][i]} for i in gp]
        dist += [{"cluster": g, "kind": "demo", "label": dem.label[i], "topic": dem.section[i], "value": dem[g][i], "everyone": dem["Everyone"][i]} for i in gd]
    dist = pd.DataFrame(dist)
    dist.to_csv(OUT / "distinctive.csv", index=False)

    keep_cols = ten + ["Everyone"]
    party_rows = dem[ctx & dem.label.isin(["Democrat", "Republican", "Independent or other", "Voted Harris", "Voted Trump"])]
    data = {
        "groups": groups, "n": int(stab.loc["Everyone", "n"]), "n_draws": int(n_draws), "stable": STABLE, "word": WORD,
        "factors": [{"label": FACTOR_LABELS.get(r, r), "values": {c: round(float(fac.loc[r, c]), 2) for c in keep_cols}} for r in fac.index],
        "policy": [{"topic": r.topic, "item": r["item"], "label": r["label"], "input": bool(r["input"]), **{c: r[c] for c in keep_cols}} for _, r in pol.iterrows()],
        "demo": [{"section": r.section, "label": r.label, "median": r.label == "Median age", **{c: r[c] for c in keep_cols}} for _, r in dem.iterrows()],
        "distinct": {g: {"policy": dist[(dist.cluster == g) & (dist.kind == "policy")].drop(columns=["cluster", "kind"]).to_dict(orient="records"),
                         "demo": dist[(dist.cluster == g) & (dist.kind == "demo")].drop(columns=["cluster", "kind"]).to_dict(orient="records"),
                         "median_age": float(dem.loc[dem.label == "Median age", g].iloc[0]),
                         "party": {r.label: r[g] for _, r in party_rows.iterrows()}} for g in ten},
        "row_order": {"policy": ct.seriate(np.nan_to_num(pol[ten].values - pol["Everyone"].values[:, None]), "correlation")},
        "swaps": {"names": ten, "resample": SW.values.round(1).tolist(), "redraw": RS.values.round(1).tolist() if REDRAWS else None},
    }
    data = json.loads(json.dumps(data, default=lambda o: None if o is None else float(o)).replace("NaN", "null"))
    html = (Path(__file__).with_name("profile_ten_template.html").read_text()
            .replace("/*TOKENS*/", ct.TOKENS.read_text()).replace("/*DATA*/", json.dumps(data, allow_nan=False)))
    (OUT / "index.html").write_text(html)
    print(f"wrote {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
