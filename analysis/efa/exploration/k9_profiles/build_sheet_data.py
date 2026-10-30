"""Side-by-side party profiles: the live site's ten parties against the nine-party typology.

Old: main branch (pre-rescore ten-party typology, 45,707 respondents): `git show main:` of the
viz payloads and data/outputs/profiles/cluster_stats.csv. New: the working tree on
bd-nine-parties (nine parties, seed 59, 45,214 respondents): cluster_stats.csv from
pipeline/archive/cluster_profile_viz.py, factor z-scores and shares computed here from
data/processed/{efa_factor_scores,typology_cluster_assignments}.csv, House seats from
data/outputs/pure_multi_turnout_l5_top7/house/stv_seat_summary.csv. "Came from" and retention
use data/processed/party_id_reference.csv (the rescored ten-party seed-61 parties), by caseid.
All percentages are survey-weighted (commonpostweight). House seats are the default view:
double magnitude, rank-7, 5% turnout gap (houseSeatsTurnoutL5.json), 873 seats.
"""
import io
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).parent
PARTIES = ["CON", "LBR", "STY", "NAT", "LIB", "POP", "CUP", "OAO", "DSA", "PRG"]
ORDER = ["PRG", "DSA", "LIB", "LBR", "STY", "CUP", "CON", "POP", "NAT"]
POLICY_SKIP = {"Demographics", "Voting History", "Approval", "Household", "Faith", "Religion",
               "Civic Engagement"}


def old(path):
    return subprocess.run(["git", "show", f"main:{path}"], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def new(path):
    return (ROOT / path).read_text()


def ts_strings(src, name):
    body = re.search(rf"export const {name}[^{{]*{{(.*?)\n}};", src, re.S).group(1)
    return dict(re.findall(r"(\w+): '((?:[^'\\]|\\.)*)'", body))


def stats(text):
    d = pd.read_csv(io.StringIO(text))
    d["key"] = d.variable + " | " + d.stat_label
    return d.set_index("key")


def main():
    S = {"old": stats(old("data/outputs/profiles/cluster_stats.csv")),
         "new": stats(new("data/outputs/profiles/cluster_stats.csv"))}
    prof = {"old": {p["party"]: p for p in json.loads(old("viz/src/data/clusterProfiles.json"))}}
    pop = {"old": {p["party"]: p for p in json.loads(old("viz/src/data/partyPopulation.json"))}}
    seats = {"old": {PARTIES[r["party"]]: r["national"] for r in json.loads(old("viz/src/data/houseSeatsTurnoutL5.json"))}}
    fsn = pd.read_csv(ROOT / "data/processed/efa_factor_scores.csv")
    typn = pd.read_csv(ROOT / "data/processed/typology_cluster_assignments.csv", usecols=["cluster"])
    wn = fsn.commonpostweight.values
    prof["new"], pop["new"] = {}, {}
    for k, p in enumerate(PARTIES):
        m = typn.cluster.values == k
        if not m.any():
            continue
        zs = {}
        for i in range(1, 6):
            x = fsn[f"FS_F{i}"].values
            mu = np.average(x, weights=wn)
            sd = np.sqrt(np.average((x - mu) ** 2, weights=wn))
            zs[f"z_F{i}"] = round(float(np.average((x[m] - mu) / sd, weights=wn[m])), 2)
        prof["new"][p] = zs
        pop["new"][p] = {"popShare": round(float(wn[m].sum() / wn.sum() * 100), 2)}
    hs = pd.read_csv(ROOT / "data/outputs/pure_multi_turnout_l5_top7/house/stv_seat_summary.csv")
    seats["new"] = {PARTIES[int(r.party)]: int(r.NATIONAL) for r in hs.itertuples()}
    consts = new("viz/src/constants/parties.ts")
    names, tags, blurbs, colors = (ts_strings(consts, n) for n in ("PARTY_NAMES", "PARTY_TAGLINES", "PARTY_BLURBS", "PARTY_COLORS"))

    ref = pd.read_csv(ROOT / "data/processed/party_id_reference.csv")
    typ = pd.read_csv(ROOT / "data/processed/typology_cluster_assignments.csv", usecols=["caseid", "cluster", "commonpostweight"])
    j = typ.merge(ref, on="caseid")
    w = j.commonpostweight
    retention = {PARTIES[p]: float(w[(j.party_id == p) & (j.cluster == p)].sum() / w[j.party_id == p].sum()) for p in range(10)}
    origin = {PARTIES[c]: {PARTIES[p]: round(float(w[(j.cluster == c) & (j.party_id == p)].sum() / w[j.cluster == c].sum()) * 100, 1)
                           for p in range(10)} for c in range(10) if (j.cluster == c).any()}

    def val(v, key, p):
        s = S[v]
        return float(s.at[key, f"c{PARTIES.index(p)}"]) if key in s.index else None

    def ov(v, key):
        return float(S[v].at[key, "overall"]) if key in S[v].index else None

    demo_keys = [("race | % White", "White"), ("race | % Black", "Black"), ("race | % Hispanic", "Hispanic"),
                 ("age | Median", "Median age"), ("educ | % 4-year degree", "4-year degree"), ("educ | % Post-grad", "Post-grad"),
                 ("urbancity | % City", "City"), ("urbancity | % Rural area", "Rural"),
                 ("gender4 | % Woman", "Women"), ("pew_bornagain | % Supporting", "Born-again"),
                 ("pew_churatd | % Never", "Never attends church"), ("relig_none | % Supporting", "No religion"),
                 ("pid3 | % Democrat", "Democrat"), ("pid3 | % Republican", "Republican"), ("pid3 | % Independent", "Independent"),
                 ("vote24_harris | % Supporting", "Voted Harris"), ("vote24_trump | % Supporting", "Voted Trump"),
                 ("vote24_dnv | % Supporting", "Did not vote 2024"),
                 ("CC24_421_1 | % Strongly Agree", "US elections fair: strongly agree"),
                 ("CC24_421_1 | % Strongly Disagree", "US elections fair: strongly disagree"),
                 ("CC24_423 | % None at all", "Trust federal govt: none at all"),
                 ("CC24_424 | % None at all", "Trust state govt: none at all")]
    # income: share under $50k and $100k+
    inc = [k for k in S["new"].index if k.startswith("faminc_new | %")]
    low, high = inc[:5], inc[9:]

    # policy rows: binary "% Supporting" and the % rows of likert/trust/ordinal distributions
    pol_keys = [k for k in S["new"].index if S["new"].at[k, "domain"] not in POLICY_SKIP and k in S["old"].index
                and S["new"].at[k, "stat_label"].startswith("%")]

    def gaps(v):
        M = S[v].loc[pol_keys, [f"c{i}" for i in range(10)]].values
        return {(PARTIES[a], PARTIES[b]): float(np.mean(np.abs(M[:, a] - M[:, b]))) for a in range(10) for b in range(10) if a != b}
    G = {v: gaps(v) for v in ("old", "new")}

    out = []
    for p in ORDER:
        demo = []
        for k, lab in demo_keys:
            demo.append({"label": lab, "old": val("old", k, p), "new": val("new", k, p), "overall": ov("new", k)})
        for keys, lab in ((low, "Family income under $50k"), (high, "Family income $100k+")):
            demo.append({"label": lab, "old": sum(val("old", k, p) for k in keys), "new": sum(val("new", k, p) for k in keys),
                         "overall": sum(ov("new", k) for k in keys)})
        rows = []
        for k in pol_keys:
            o, n, a = val("old", k, p), val("new", k, p), ov("new", k)
            r = S["new"].loc[k]
            rows.append({"q": r.question, "stat": r.stat_label, "domain": r.domain, "old": o, "new": n, "overall": a,
                         "dev": n - a, "shift": n - o})
        rows = pd.DataFrame(rows)
        bin_rows = rows[rows.stat == "% Supporting"]
        distinct = bin_rows.reindex(bin_rows.dev.abs().sort_values(ascending=False).index).head(10)
        shifted = rows.reindex(rows["shift"].abs().sort_values(ascending=False).index).head(8)
        near = sorted(((q, G["new"][(p, q)], G["old"][(p, q)]) for q in ORDER if q != p), key=lambda t: t[1])[:3]
        out.append({
            "code": p, "name": names[p], "color": colors[p], "tagline": tags[p], "blurb": blurbs[p],
            "share": {"old": pop["old"][p]["popShare"], "new": pop["new"][p]["popShare"]},
            "seats": {"old": seats["old"][p], "new": seats["new"][p]},
            "retention": round(retention[p] * 100, 1),
            "origin": {q: v for q, v in sorted(origin[p].items(), key=lambda t: -t[1]) if v >= 5},
            "factors": {f: {"old": prof["old"][p][f"z_{f}"], "new": prof["new"][p][f"z_{f}"]} for f in ("F1", "F2", "F3", "F4", "F5")},
            "demo": demo,
            "distinct": distinct[["q", "domain", "old", "new", "overall", "dev"]].to_dict("records"),
            "shifted": shifted[["q", "stat", "old", "new", "shift"]].to_dict("records"),
            "nearest": [{"party": q, "new": round(g, 1), "old": round(go, 1)} for q, g, go in near],
            "median_shift": round(float(rows["shift"].abs().median()), 1),
        })
    meta = {"n_policy_rows": len(pol_keys), "seats_total": {v: sum(seats[v].values()) for v in seats}}
    (HERE / "sheet_data.json").write_text(json.dumps({"meta": meta, "parties": out}, indent=1, default=float))
    print(json.dumps(meta))
    for r in out:
        print(f"{r['code']}: share {r['share']['old']}->{r['share']['new']}  seats {r['seats']['old']}->{r['seats']['new']}  "
              f"ret {r['retention']}  med shift {r['median_shift']}  nearest {r['nearest'][0]}  origin {r['origin']}")


if __name__ == "__main__":
    main()
