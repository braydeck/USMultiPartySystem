#!/usr/bin/env python3
"""Compare independently-clustered prior waves to the 2024 party typology.

Matching based on policy-profile distance (shared items) + factor-space positions
+ demographics. No partisan composition in verdict logic.

Usage:  .venv/bin/python analysis/efa/previous_years/independent/match_to_2024.py
"""
import sys, warnings, pickle
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import io_paths as io, crosswalk as cwmod

CODES = ["CON", "LBR", "STY", "NAT", "LIB", "POP", "CUP", "OAO", "DSA", "PRG"]
NAMES = {"CON": "Conservative", "LBR": "Labor", "STY": "Solidarity", "NAT": "Nationalist",
         "LIB": "Liberal", "POP": "Populist", "CUP": "Civic Union", "OAO": "Order & Opp.",
         "DSA": "Dem. Socialist", "PRG": "Progressive"}
PID3_LABEL = {"Democrat": 1, "Republican": 2, "Independent": 3, "Other": 4, "Not sure": 5}
CANONICAL_24 = [
    "pew_churatd", "CC24_302", "CC24_303", "CC24_341a", "CC24_341c", "CC24_341d",
    "CC24_323a", "CC24_323b", "CC24_323d", "CC24_321b", "CC24_321d", "CC24_321e",
    "CC24_325", "CC24_324b", "CC24_340b", "CC24_340c", "CC24_340e", "CC24_340f",
    "CC24_440b", "CC24_440c", "CC24_421_1", "CC24_421_2", "CC24_423", "CC24_424",
]
DEMO_COLS = ["birthyr", "educ", "race", "gender4", "faminc_new", "religpew",
             "pew_bornagain", "urbancity", "votereg", "newsint"]
FCOLS = ["FS_F1", "FS_F2", "FS_F3", "FS_F4_resid", "FS_F5_resid"]


def load_2024_reference(shared_cids):
    """Build 2024 party profiles, factor centroids, and demographics."""
    tp = pd.read_csv(io.ROOT / "data/processed/typology_cluster_assignments.csv")
    n_tp = len(tp)

    cw = cwmod.load()
    cw24 = cw[cw["construct_id"].isin(shared_cids) & cw["var_2024"].notna()]
    vars_needed = list(set(cw24["var_2024"]))
    all_vars = list(set(CANONICAL_24 + vars_needed + [io.WEIGHT_COL, "pid3"] + DEMO_COLS))
    all_cols = pd.read_stata(str(io.dta_path("2024")), iterator=True).variable_labels()
    all_vars = [v for v in all_vars if v in all_cols]

    df24 = pd.read_stata(str(io.dta_path("2024")), columns=all_vars,
                         convert_categoricals=True, convert_missing=False, convert_dates=False)
    w_full = pd.to_numeric(df24[io.WEIGHT_COL], errors="coerce").values.astype(float)
    canon_mask = ~np.isnan(w_full)
    for var in CANONICAL_24:
        col = df24[var]
        if col.dtype.name == "category":
            canon_mask &= col.notna().values
        else:
            canon_mask &= pd.to_numeric(col, errors="coerce").notna().values
    assert canon_mask.sum() == n_tp, f"Listwise mask gives {canon_mask.sum()}, expected {n_tp}"
    cluster_full = np.full(len(df24), -1, dtype=int)
    cluster_full[canon_mask] = tp["cluster"].values

    items24 = cwmod.recode_wave(df24, "2024", levels={"exact", "equivalent"}, cw=cw24)
    pid3_raw = df24["pid3"].astype("object").map(PID3_LABEL)
    pid3_full = pd.to_numeric(pid3_raw, errors="coerce").values.astype(float)

    profiles, partisan, factor_centroids, demographics = {}, {}, {}, {}
    for k in range(10):
        m = cluster_full == k
        wk = w_full[m]; tot = wk.sum()
        prof = {}
        for cid in shared_cids:
            if cid in items24.columns:
                vals = items24.loc[items24.index[m], cid].values
                valid = ~np.isnan(vals)
                if valid.sum() > 0:
                    prof[cid] = np.average(vals[valid], weights=wk[valid])
        profiles[CODES[k]] = prof
        partisan[CODES[k]] = {
            "share": 100 * tot / w_full[cluster_full >= 0].sum(),
            "Dem": 100 * wk[pid3_full[m] == 1].sum() / tot,
            "Rep": 100 * wk[pid3_full[m] == 2].sum() / tot,
        }
        fc = {}
        for j, col in enumerate(FCOLS):
            fc[col] = float(tp.loc[tp["cluster"] == k, col].mean())
        factor_centroids[CODES[k]] = fc

        demo = {}
        if "birthyr" in df24.columns:
            by = pd.to_numeric(df24.loc[df24.index[m], "birthyr"], errors="coerce")
            valid = by.notna()
            if valid.sum() > 0:
                ages = 2024 - by[valid].values
                demo["mean_age"] = round(float(np.average(ages, weights=wk[valid.values])), 1)
        for dc in ["educ", "race", "religpew", "urbancity"]:
            if dc in df24.columns:
                cats = df24.loc[df24.index[m], dc].astype("object")
                for val in cats.unique():
                    if pd.isna(val) or str(val).strip() in ("", "Skipped", "Not Asked"):
                        continue
                    pct = 100 * wk[cats.values == val].sum() / tot
                    if pct > 3.0:
                        demo[f"{dc}:{str(val).strip()}"] = round(pct, 1)
        demographics[CODES[k]] = demo
    return profiles, partisan, factor_centroids, demographics


def find_shared_items(wave_item_ids):
    cw = cwmod.load()
    has_2024 = set(cw.loc[cw["var_2024"].notna(), "construct_id"])
    return [cid for cid in wave_item_ids if cid in has_2024]


def compute_distance_matrix(wave_profiles, ref_profiles, shared_cids):
    cluster_ids = sorted(wave_profiles.keys())
    all_vectors = []
    for c in cluster_ids:
        all_vectors.append([wave_profiles[c].get(cid, np.nan) for cid in shared_cids])
    for p in CODES:
        all_vectors.append([ref_profiles[p].get(cid, np.nan) for cid in shared_cids])
    M = np.array(all_vectors)
    mu = np.nanmean(M, axis=0); sig = np.nanstd(M, axis=0)
    sig[sig < 1e-10] = 1.0
    Z = np.nan_to_num((M - mu) / sig, nan=0.0)
    n_wave = len(cluster_ids)
    cost = np.zeros((n_wave, len(CODES)))
    for i in range(n_wave):
        for j in range(len(CODES)):
            cost[i, j] = np.sqrt(np.sum((Z[i] - Z[n_wave + j]) ** 2))
    return cost, cluster_ids


def assign_verdicts(cost, cluster_ids, n_shared):
    """Verdicts based purely on policy-profile distance. No partisan."""
    scale = np.sqrt(n_shared)
    row_ind, col_ind = linear_sum_assignment(cost)
    assignment = {}
    for r, c in zip(row_ind, col_ind):
        cid = cluster_ids[r]
        party = CODES[c]
        dist = cost[r, c]
        norm = dist / scale
        if norm < 0.45:
            verdict = "SURVIVES"
        elif norm < 0.65:
            verdict = "WEAK"
        else:
            verdict = "ABSENT"
        assignment[party] = {"matched_cluster": cid, "match_dist": round(dist, 3),
                             "norm_dist": round(norm, 3), "verdict": verdict}

    # detect MERGED: multiple parties' closest cluster is the same
    for j, party in enumerate(CODES):
        closest = cluster_ids[int(np.argmin(cost[:, j]))]
        if party not in assignment:
            min_d = float(np.min(cost[:, j]))
            assignment[party] = {"matched_cluster": None, "match_dist": round(min_d, 3),
                                 "norm_dist": round(min_d / scale, 3), "verdict": "ABSENT"}
        assignment[party]["closest_cluster"] = closest

    cluster_claims = {}
    for party in CODES:
        cl = assignment[party]["closest_cluster"]
        cluster_claims.setdefault(cl, []).append(party)
    for cl, parties in cluster_claims.items():
        if len(parties) > 1:
            for party in parties:
                others = [p for p in parties if p != party]
                assignment[party].setdefault("notes", "")
                assignment[party]["notes"] += f"closest shared w/ {','.join(others)}"
    return assignment


def item_diff_table(wave_prof, ref_prof, shared_cids):
    """Per-item absolute differences between matched profiles."""
    diffs = {}
    for cid in shared_cids:
        wv = wave_prof.get(cid, np.nan)
        rv = ref_prof.get(cid, np.nan)
        if not np.isnan(wv) and not np.isnan(rv):
            diffs[cid] = round(wv - rv, 3)
    return diffs


def demo_comparison(wave_demo, ref_demo):
    """Find shared demographic keys and compute differences."""
    shared_keys = set(wave_demo.keys()) & set(ref_demo.keys())
    comp = {}
    for k in sorted(shared_keys):
        if k == "mean_age":
            comp[k] = f"{wave_demo[k]:.0f} vs {ref_demo[k]:.0f}"
        else:
            comp[k] = f"{wave_demo[k]:.0f}% vs {ref_demo[k]:.0f}%"
    return comp


def process_wave(wave, ref_profiles, ref_partisan, ref_factor, ref_demo):
    outdir = io.out_dir(wave)
    pkl_path = outdir / "independent_fit.pkl"
    if not pkl_path.exists():
        print(f"  {wave}: no independent fit found, skipping")
        return None

    print(f"\n{'='*80}")
    print(f"  {wave} ({io.KIND[wave]})")
    print(f"{'='*80}")

    with open(pkl_path, "rb") as f:
        fit = pickle.load(f)

    item_ids = fit["item_ids"]
    shared_cids = find_shared_items(item_ids)
    k = fit["k"]
    k_pa = fit["k_pa"]
    n_eff = fit["n_eff"]
    print(f"  items: {len(item_ids)}  shared w/ 2024: {len(shared_cids)}  k={k} (PA={k_pa})  clusters: {n_eff}")

    # factor structure summary
    L = fit["L"]
    fnames = [f"F{j+1}" for j in range(k)]
    print(f"\n  Factor structure (k={k}):")
    ss = np.sum(L ** 2, axis=0)
    pv = ss / len(item_ids) * 100
    for j in range(k):
        top = np.argsort(np.abs(L[:, j]))[::-1][:4]
        items_str = ", ".join(f"{item_ids[i]}({L[i,j]:+.2f})" for i in top)
        print(f"    F{j+1} ({pv[j]:.1f}%): {items_str}")

    wave_profiles = fit["profiles"]
    wave_partisan = fit["partisan"]
    wave_demo = fit.get("demographics", {})

    cost, cluster_ids = compute_distance_matrix(wave_profiles, ref_profiles, shared_cids)
    assignment = assign_verdicts(cost, cluster_ids, len(shared_cids))

    # enrich with partisan + demographics for display
    for party in CODES:
        a = assignment[party]
        mc = a["matched_cluster"]
        if mc is not None:
            wp = wave_partisan[mc]
            a["wave_share"] = round(wp["share"], 1)
            a["wave_D_R"] = f"{wp['Dem']:.0f}/{wp['Rep']:.0f}"
        else:
            a["wave_share"] = None
            a["wave_D_R"] = "-"
        rp = ref_partisan[party]
        a["ref_share"] = round(rp["share"], 1)
        a["ref_D_R"] = f"{rp['Dem']:.0f}/{rp['Rep']:.0f}"

    # print results
    scale = np.sqrt(len(shared_cids))
    print(f"\n  SURVIVES < {0.45:.2f} norm | WEAK < {0.65:.2f} norm | (√{len(shared_cids)}={scale:.2f})")
    print(f"\n  {'party':>5} {'name':>14} {'2024%':>5} {wave+'%':>5} {'norm':>5} {'2024mix':>8} {'wavemix':>8} {'verdict':>10}")
    print(f"  {'-'*5} {'-'*14} {'-'*5} {'-'*5} {'-'*5} {'-'*8} {'-'*8} {'-'*10}")
    for party in CODES:
        a = assignment[party]
        name = NAMES[party]
        ws = f"{a['wave_share']}" if a['wave_share'] is not None else "---"
        notes = f"  ({a['notes']})" if a.get('notes') else ""
        print(f"  {party:>5} {name:>14} {a['ref_share']:>5.1f} {ws:>5} {a['norm_dist']:>5.2f} "
              f"{a['ref_D_R']:>8} {a['wave_D_R']:>8} {a['verdict']:>10}{notes}")

    # top item differences for each match
    print(f"\n  Largest item differences (wave - 2024) for each match:")
    for party in CODES:
        mc = assignment[party]["matched_cluster"]
        if mc is None:
            continue
        diffs = item_diff_table(wave_profiles[mc], ref_profiles[party], shared_cids)
        sorted_diffs = sorted(diffs.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
        diff_str = "  ".join(f"{cid}({d:+.2f})" for cid, d in sorted_diffs)
        print(f"    {party}: {diff_str}")

    # demographics comparison
    if wave_demo:
        print(f"\n  Demographics (wave cluster vs 2024 party):")
        for party in CODES:
            mc = assignment[party]["matched_cluster"]
            if mc is None or mc not in wave_demo:
                continue
            wd = wave_demo[mc]
            rd = ref_demo.get(party, {})
            age_w = wd.get("mean_age", "?")
            age_r = rd.get("mean_age", "?")
            print(f"    {party} (c{mc}): age {age_w} vs {age_r}", end="")
            # key demo diffs
            for key in ["educ:4-year", "educ:Post-grad", "race:White", "race:Black",
                        "race:Hispanic", "religpew:Protestant", "religpew:Nothing in particular",
                        "urbancity:Rural"]:
                wv = wd.get(key)
                rv = rd.get(key)
                if wv and rv:
                    short = key.split(":")[-1][:12]
                    print(f"  {short}:{wv:.0f}/{rv:.0f}", end="")
            print()

    # 2024 factor centroids for reference
    print(f"\n  2024 factor centroids (for reference):")
    print(f"    {'party':>5} {'F1Sec':>6} {'F2Dis':>6} {'F3Gov':>6} {'F4Rel':>6} {'F5Pop':>6}")
    for party in CODES:
        fc = ref_factor[party]
        print(f"    {party:>5} {fc['FS_F1']:>+6.2f} {fc['FS_F2']:>+6.2f} {fc['FS_F3']:>+6.2f} "
              f"{fc['FS_F4_resid']:>+6.2f} {fc['FS_F5_resid']:>+6.2f}")

    return {"wave": wave, "assignment": assignment, "cost": cost,
            "cluster_ids": cluster_ids, "shared_cids": shared_cids}


def save_results(all_results):
    outdir = io.compare_dir()
    rows = []
    for res in all_results:
        if res is None:
            continue
        wave = res["wave"]
        for party in CODES:
            a = res["assignment"][party]
            rows.append({
                "party": party, "wave": wave,
                "matched_cluster": a["matched_cluster"],
                "match_dist": a["match_dist"], "norm_dist": a["norm_dist"],
                "2024_share": a["ref_share"], "wave_share": a["wave_share"],
                "2024_D_R": a["ref_D_R"], "wave_D_R": a["wave_D_R"],
                "verdict": a["verdict"],
                "notes": a.get("notes", ""),
            })
    df = pd.DataFrame(rows)
    df.to_csv(outdir / "party_survival_matrix.csv", index=False)
    print(f"\nSaved: {outdir / 'party_survival_matrix.csv'}")


def main():
    print("PARTY SURVIVAL: independent clustering → match to 2024 parties")
    print("Verdicts based on policy-profile distance only (no partisan in thresholds)\n")

    # find shared items across all waves
    all_shared = set()
    for wave in ["2022", "2020", "2018"]:
        pkl = io.out_dir(wave) / "independent_fit.pkl"
        if pkl.exists():
            with open(pkl, "rb") as f:
                fit = pickle.load(f)
            all_shared.update(find_shared_items(fit["item_ids"]))

    ref_profiles, ref_partisan, ref_factor, ref_demo = load_2024_reference(list(all_shared))

    results = []
    for wave in ["2022", "2020", "2018"]:
        res = process_wave(wave, ref_profiles, ref_partisan, ref_factor, ref_demo)
        results.append(res)
    save_results(results)


if __name__ == "__main__":
    main()
