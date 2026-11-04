"""Revised-rule clusters at 5 and 10, side by side: factor positions, policy views, demographics (party ID last), how
the two solutions nest, and which clusters trade members under resampling. Local page only.

Data: CES 2024 Common Content (efa_update.CES_PATH), weight commonpostweight.
  Clusters: outputs/stage_c_v2/labels.npz, modal seed solution (best lower bound within it) at caps 5 and 10, on
  outputs/stage_c_v2/scores.csv (n = 49,431; the four clustering scores, residualized and in-power adjusted as
  clustered).
Stability per cluster: mean best Jaccard against each of the 30 resample fits stored with the cap scan (fits predicted
back onto everyone). "Unstable" = below 0.75, the §3c stable line; none falls below 0.5 (dissolved).
Resample swaps: for each resample fit, each of its clusters is mapped to the modal cluster it overlaps most (weighted);
cell (i, j) = weighted share of modal cluster i's members whose fit cluster maps to j, averaged over the 30 fits.
Names: five clusters A-E by policy similarity; each of the ten is named for the five-cluster most of its members sit
in (A.1, A.2 ...), numbered by size.
Writes outputs/profile_v2/{names,factors,policy,demographics,nesting,swaps_5,swaps_10,stability}.csv and index.html.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import compare_typologies as ct
import loading_draws as ld
import reestimate_loadings as rl

FINE = int(sys.argv[1]) if len(sys.argv) > 1 else 10  # the finer solution profiled against the five
WORD = {9: "nine", 10: "ten"}[FINE]
OUT = rl.OUT / ("profile_v2" if FINE == 10 else f"profile_v2_k{FINE}")
V2 = rl.OUT / "stage_c_v2"
STABLE = 0.75
FACTORS = [("RT", "Cultural conservatism (RT slot)", "CC24_445b", ["Agree", "Strongly agree", "Somewhat agree"]),
           ("TR", "Distrust", "CC24_423", ["Not very much", "None at all"]),
           ("SO", "Security & Order", "CC24_323b", ["Support"]),
           ("PC", "Economic right (PC slot)", "CC24_328e", ["Oppose"])]


def jaccard_mean(lab, boots):
    return np.mean([ct_best(lab, b) for b in boots], axis=0)


def ct_best(ref, other):
    out = []
    for c in np.unique(ref):
        a = ref == c
        out.append(max((a & (other == d)).sum() / (a | (other == d)).sum() for d in np.unique(other)))
    return np.array(out)


def swaps(lab, boots, w):
    ks = np.unique(lab)
    M = np.zeros((len(ks), len(ks)))
    for b in boots:
        mp = {}
        for d in np.unique(b):
            ov = [w[(b == d) & (lab == c)].sum() for c in ks]
            mp[d] = ks[int(np.argmax(ov))]
        mb = np.vectorize(mp.get)(b)
        for i, c in enumerate(ks):
            m = lab == c
            for j, c2 in enumerate(ks):
                M[i, j] += w[m & (mb == c2)].sum() / w[m].sum()
    return M / len(boots)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    S = pd.read_csv(V2 / "scores.csv")
    z = np.load(V2 / "labels.npz")
    w_all = S.commonpostweight.values
    sol = {}
    for K in (5, FINE):
        lab, n_sol, share = ld.modal_solution(list(zip(range(42, 62), z[f"{K}_seed"], z[f"{K}_seed_bounds"])))
        boots = list(z[f"{K}_boot"])
        sol[K] = {"lab": lab, "jac": jaccard_mean(lab, boots), "swap": swaps(lab, boots, w_all), "n_sol": n_sol, "share": share}
        print(f"cap {K}: {n_sol} solutions (modal {share:.2f}); per-cluster mean Jaccard {np.round(sol[K]['jac'], 3).tolist()}")

    items = list(dict.fromkeys(it for _, rows in ct.TOPICS for it, _, _ in rows))
    demo_cols = ["birthyr", "gender4", "sexuality", "race", "educ", "faminc_new", "investor", "child18", "marstat",
                 "employ", "union", "ownhome", "urbancity", "region", "religpew", "pid3", "ideo5", "CC24_410"]
    meta = pd.read_stata(rl.eu.CES_PATH, columns=["caseid", "commonpostweight"], convert_categoricals=False)
    lab_df = pd.read_stata(rl.eu.CES_PATH, columns=items + demo_cols, convert_categoricals=True)
    lab_df.insert(0, "caseid", meta.caseid.values)
    D = lab_df.set_index("caseid").loc[S.caseid.values]
    w = w_all

    # orient factors so high = the name, then standardize (weighted, everyone in the sample)
    F = pd.DataFrame(index=D.index)
    for c, name, it, ans in FACTORS:
        v = S[c].values.copy()
        ok = D[it].notna().values
        r = np.corrcoef(v[ok], D[it].astype(str).isin(ans).values[ok].astype(float))[0, 1]
        v = -v if r < 0 else v
        mu = np.average(v, weights=w)
        F[name] = (v - mu) / np.sqrt(np.average((v - mu) ** 2, weights=w))
        print(f"{name}: r with {it} {r:+.2f} -> {'flipped' if r < 0 else 'kept'}")

    # names: five by policy similarity, ten by parent five + size
    def pol_matrix(lab):
        ks = np.unique(lab)
        rows = []
        for _, trs in ct.TOPICS:
            for it, _, ans in trs:
                ind, ok = D[it].astype(str).isin(ans).values, D[it].notna().values
                rows.append([ct.wshare(ind, ok, lab == k, w) for k in ks])
        P = np.array(rows)
        return ks, (P - np.nanmean(P, axis=1, keepdims=True)) / (np.nanstd(P, axis=1, keepdims=True) + 1e-9)
    ks5, Pz5 = pol_matrix(sol[5]["lab"])
    order5 = [ks5[i] for i in ct.seriate(np.nan_to_num(Pz5.T), "euclidean")]
    econ = F["Economic right (PC slot)"].values
    if np.average(econ[sol[5]["lab"] == order5[0]], weights=w[sol[5]["lab"] == order5[0]]) < \
       np.average(econ[sol[5]["lab"] == order5[-1]], weights=w[sol[5]["lab"] == order5[-1]]):
        order5 = order5[::-1]
    name5 = {k: "ABCDE"[i] for i, k in enumerate(order5)}
    l5 = np.array([name5[k] for k in sol[5]["lab"]])
    parent, name10 = {}, {}
    for k in np.unique(sol[FINE]["lab"]):
        m = sol[FINE]["lab"] == k
        sh = pd.Series(w[m]).groupby(l5[m]).sum() / w[m].sum()
        parent[k] = (sh.idxmax(), float(sh.max() * 100))
    for p in "ABCDE":
        kids = sorted([k for k in parent if parent[k][0] == p], key=lambda k: -w[sol[FINE]["lab"] == k].sum())
        for i, k in enumerate(kids):
            name10[k] = f"{p}.{i + 1}"
    l10 = np.array([name10[k] for k in sol[FINE]["lab"]])
    pd.DataFrame([{"cap": K, "cluster": int(k), "name": nm[k]} for K, nm in ((5, name5), (FINE, name10)) for k in nm]).to_csv(OUT / "names.csv", index=False)
    stab = {}
    for K, nm in ((5, name5), (FINE, name10)):
        for i, k in enumerate(np.unique(sol[K]["lab"])):
            stab[nm[k]] = float(sol[K]["jac"][i])

    groups = []
    for p in "ABCDE":
        groups.append(("five", p))
        groups += [("ten", n) for n in sorted([v for v in name10.values() if v.startswith(p + ".")], key=lambda s: int(s.split(".")[1]))]
    groups.append(("all", "Everyone"))
    masks = {g: (l5 == g) if k == "five" else (l10 == g) if k == "ten" else np.ones(len(D), bool) for k, g in groups}

    nest = pd.crosstab(l10, l5, values=w, aggfunc="sum").fillna(0)
    gmeta = []
    for k, g in groups:
        row = {"key": k, "id": g, "share": round(float(w[masks[g]].sum() / w.sum() * 100), 1), "n": int(masks[g].sum())}
        if k != "all":
            row["jac"] = round(stab[g], 2)
            row["unstable"] = stab[g] < STABLE
        if k == "ten":
            r = nest.loc[g] / nest.loc[g].sum() * 100
            row["from"] = ", ".join(f"{c} {v:.0f}%" for c, v in r.sort_values(ascending=False).items() if v >= 10)
        if k == "five":
            r = nest[g] / nest[g].sum() * 100
            row["into"] = ", ".join(f"{c} {v:.0f}%" for c, v in r.sort_values(ascending=False).items() if v >= 10)
        gmeta.append(row)
    pd.DataFrame(gmeta).to_csv(OUT / "stability.csv", index=False)

    fac = pd.DataFrame({g: [float(np.average(F[c].values[masks[g]], weights=w[masks[g]])) for c in F.columns] for _, g in groups},
                       index=F.columns)
    fac.round(3).to_csv(OUT / "factors.csv")
    inputs = set(pd.read_csv(V2 / "loadings.csv", index_col=0).index)
    pol_rows = []
    for topic, rows in ct.TOPICS:
        for it, label, ans in rows:
            ind, ok = D[it].astype(str).isin(ans).values, D[it].notna().values
            pol_rows.append({"topic": topic, "item": it, "label": label, "input": it in inputs,
                             **{g: round(ct.wshare(ind, ok, masks[g], w), 1) for _, g in groups}})
    pol = pd.DataFrame(pol_rows)
    pol.to_csv(OUT / "policy.csv", index=False)
    dem_rows = []
    for sec, label, ind, ok in ct.demo_rows(D[demo_cols]):
        ind, ok = ind.fillna(False).values.astype(bool), ok.values.astype(bool)
        dem_rows.append({"section": sec, "label": label, **{g: round(ct.wshare(ind, ok, masks[g], w), 1) for _, g in groups}})
    age = 2024 - D.birthyr.astype(float).values
    dem_rows.insert(0, {"section": "Age and gender", "label": "Median age", "median": True,
                        **{g: float(np.median(age[masks[g]])) for _, g in groups}})
    dem = pd.DataFrame(dem_rows)
    dem.drop(columns="median").to_csv(OUT / "demographics.csv", index=False)

    gids = [g for k, g in groups if k != "all"]
    P = pol[gids].values
    Pz = (P - np.nanmean(P, axis=1, keepdims=True)) / (np.nanstd(P, axis=1, keepdims=True) + 1e-9)
    sim_order = [gids[i] for i in ct.seriate(np.nan_to_num(Pz.T), "euclidean")]
    if fac.loc["Economic right (PC slot)", sim_order[0]] < fac.loc["Economic right (PC slot)", sim_order[-1]]:
        sim_order = sim_order[::-1]
    pol_order = ct.seriate(np.nan_to_num(P - pol["Everyone"].values[:, None]), "correlation")
    ctx = (dem.section == "Party and vote (context)").values
    mi = np.where(~ctx)[0]
    dem_order = [int(mi[i]) for i in ct.seriate(np.nan_to_num(dem[gids].values[mi].astype(float) - dem["Everyone"].values[mi, None]), "correlation")] \
        + [int(i) for i in np.where(ctx)[0]]

    nest_rows = sorted(nest.index, key=lambda s: (s[0], int(s.split(".")[1])))
    nest_r = (nest.div(nest.sum(axis=1), axis=0) * 100).loc[nest_rows, list("ABCDE")]
    nest_c = (nest.div(nest.sum(axis=0), axis=1) * 100).loc[nest_rows, list("ABCDE")]
    nest_r.round(1).to_csv(OUT / "nesting.csv")
    sw = {}
    for K, nm in ((5, name5), (FINE, name10)):
        ks = np.unique(sol[K]["lab"])
        names = [nm[k] for k in ks]
        order = [i for i in sorted(range(len(ks)), key=lambda i: (names[i][0], names[i]))]
        M = pd.DataFrame(sol[K]["swap"] * 100, index=names, columns=names).iloc[order, order]
        M.round(1).to_csv(OUT / f"swaps_{K}.csv")
        off = [(M.index[i], M.columns[j], M.iloc[i, j]) for i in range(len(M)) for j in range(len(M)) if i != j]
        print(f"cap {K} largest swaps:", [(a, b, round(v, 1)) for a, b, v in sorted(off, key=lambda t: -t[2])[:6]])
        sw[K] = {"names": list(M.index), "v": M.values.round(1).tolist()}

    data = {"groups": gmeta, "sim_order": sim_order, "row_order": {"policy": pol_order, "demo": dem_order},
            "factors": [{"label": c, "values": {g: round(fac.loc[c, g], 2) for _, g in groups}} for c in F.columns],
            "policy": pol.to_dict(orient="records"),
            "demo": [{k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in r.items()} for r in dem.to_dict(orient="records")],
            "nest": {"rows": nest_rows, "cols": list("ABCDE"), "r": nest_r.round(1).values.tolist(), "c": nest_c.round(1).values.tolist()},
            "swaps": sw, "stable": STABLE, "n": int(len(D)),
            "solutions": {str(K): {"n_sol": int(sol[K]["n_sol"]), "share": float(sol[K]["share"])} for K in (5, FINE)}, "fine": FINE, "word": WORD}
    tpl = Path(__file__).with_name("profile_v2_template.html").read_text()
    if FINE != 10:
        for a, b in (("5 and 10", f"5 and {FINE}"), ("of 10", f"of {FINE}"), ("10 clusters", f"{FINE} clusters"), ("5, then 10", f"5, then {FINE}"),
                     ("10 \\\\ 5", f"{FINE} \\\\ 5"), ("Ten clusters", WORD.capitalize() + " clusters"), ("ten clusters", WORD + " clusters"),
                     ("the ten", "the " + WORD), ("ten-cluster", WORD + "-cluster")):
            tpl = tpl.replace(a, b)
    html = (tpl
            .replace("/*TOKENS*/", ct.TOKENS.read_text()).replace("/*DATA*/", json.dumps(data, allow_nan=False)))
    (OUT / "index.html").write_text(html)
    print(f"wrote {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
