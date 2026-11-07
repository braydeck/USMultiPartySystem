#!/usr/bin/env python3
"""Party order from how often the nine parties vote together, and the issue-coalition review page.

Ruled 2026-11-06 (listwise_check DECISIONS.md "Party order = vote agreement"): the default left-right order is the
first dimension of classical MDS on bloc agreement over the Legislation tab's 37 bills.
  bloc agreement    share of bills on which two parties' majorities (support > 50%) land on the same side
  member agreement  mean chance that a random member of each party votes the same way, p_a p_b + (1-p_a)(1-p_b)
Orientation: dimension 1 is signed to correlate positively with the parties' mean Economic Conservatism (FS_F5), so
the right end is the economically conservative end; the order itself comes from the votes.

Inputs
  viz/src/data/houseVoteModelTurnoutL5.json   the 37 bills (variable, domain, question) and House free-vote P(pass)
  viz/src/data/clusterProfiles.json           each party's % support per bill (what the app shows)
  viz/src/data/uncertaintyTurnoutL5.json      published House seats at the default view (double, depth 7, 5% gap)
  data/processed/efa_factor_scores.csv + typology_cluster_assignments.csv   party means of FS_F5, for the sign only
  analysis/coalitions/outputs/house_draw_seats_l5.csv   per-draw House seats (house_draw_seats.py), optional
Writes
  data/processed/party_order.csv              party, rank, dim1, dim2 (bloc); read by pipeline/party_codes.py
  viz/src/constants/parties.ts F5_ORDER       rewritten to match when the order moves (the app and hex maps read it)
  analysis/coalitions/outputs/vote_agreement.html   local review page (never published)
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
DATA = BASE / "viz/src/data"
TOKENS = Path.home() / ".claude/skills/html-research-artifacts/assets/tokens.css"
DRAWS = HERE / "outputs/house_draw_seats_l5.csv"
NAMES = {0: "CON", 1: "LBR", 2: "STY", 3: "NAT", 5: "POP", 6: "CUP", 7: "OAO", 8: "DSA", 9: "PRG"}


def agreement(p, mode):
    n = p.shape[1]
    if mode == "bloc":
        y = p > 0.5
        return np.array([[np.mean(y[:, i] == y[:, j]) for j in range(n)] for i in range(n)])
    return np.array([[np.mean(p[:, i] * p[:, j] + (1 - p[:, i]) * (1 - p[:, j])) for j in range(n)] for i in range(n)])


def mds(A, sign_ref):
    """Classical MDS on 1 - agreement; returns 2 dims and each one's share of the positive eigenvalues."""
    D2 = (1 - A) ** 2
    J = np.eye(len(A)) - 1 / len(A)
    ev, V = np.linalg.eigh(-0.5 * J @ D2 @ J)
    o = ev.argsort()[::-1]
    ev, V = ev[o], V[:, o]
    X = V[:, :2] * np.sqrt(np.clip(ev[:2], 0, None))
    if np.corrcoef(X[:, 0], sign_ref)[0, 1] < 0:
        X[:, 0] *= -1
    return X, ev[:2] / ev[ev > 0].sum()


def main():
    bills = json.loads((DATA / "houseVoteModelTurnoutL5.json").read_text())
    prof = {NAMES[int(c["id"])]: c["variables"] for c in json.loads((DATA / "clusterProfiles.json").read_text())}
    parties = sorted(prof)
    P = np.array([[prof[q][b["variable"]]["pct"] / 100 for q in parties] for b in bills])

    fs = pd.read_csv(BASE / "data/processed/efa_factor_scores.csv", usecols=["caseid", "commonpostweight", "FS_F5"])
    ty = pd.read_csv(BASE / "data/processed/typology_cluster_assignments.csv", usecols=["caseid", "cluster"])
    assert (fs.caseid.values == ty.caseid.values).all()
    fs["party"] = ty.cluster.map(NAMES).values
    econ = fs.groupby("party").apply(lambda d: np.average(d.FS_F5, weights=d.commonpostweight)).loc[parties].values

    seats_pub = {q: v["observed"] for q, v in json.loads((DATA / "uncertaintyTurnoutL5.json").read_text())["house"]["seats"].items()}

    lines, share = {}, {}
    domains = ["All"] + sorted({b["domain"] for b in bills})
    for mode in ("bloc", "member"):
        Xall, sh = mds(agreement(P, mode), econ)
        share[mode] = [round(float(s), 3) for s in sh]
        for dom in domains:
            rows = [i for i, b in enumerate(bills) if dom == "All" or b["domain"] == dom]
            X, s = (Xall, sh) if dom == "All" else mds(agreement(P[rows], mode), Xall[:, 0])
            lines[f"{mode}|{dom}"] = {"n": len(rows), "share1": round(float(s[0]), 3),
                                      "dim1": {q: round(float(v), 4) for q, v in zip(parties, X[:, 0])},
                                      "dim2": {q: round(float(v), 4) for q, v in zip(parties, X[:, 1])}}

    main_line = lines["bloc|All"]
    order = sorted(parties, key=lambda q: main_line["dim1"][q])
    pd.DataFrame({"party": order, "rank": range(1, len(order) + 1),
                  "dim1": [main_line["dim1"][q] for q in order],
                  "dim2": [main_line["dim2"][q] for q in order]}).to_csv(BASE / "data/processed/party_order.csv", index=False)
    print("order (bloc agreement):", " ".join(order), f"dim1 {share['bloc'][0]:.0%}, dim2 {share['bloc'][1]:.0%}")
    print("order (member agreement):", " ".join(sorted(parties, key=lambda q: lines['member|All']['dim1'][q])))
    ts_path = BASE / "viz/src/constants/parties.ts"
    ts_src = ts_path.read_text()
    lit = "export const F5_ORDER = [" + ",".join(f"'{q}'" for q in order) + "] as const;"
    cur = re.search(r"export const F5_ORDER = \[.*?\] as const;", ts_src).group(0)
    if cur != lit:
        ts_path.write_text(ts_src.replace(cur, lit))
        print(f"party order moved: rewrote F5_ORDER in {ts_path.relative_to(BASE)}; rerun rebuild_from_typology step 14")

    draws = None
    if DRAWS.exists():
        d = pd.read_csv(DRAWS)
        obs = d[d.draw == -1].iloc[0]
        assert all(int(obs.get(q, 0)) == seats_pub.get(q, 0) for q in parties), "draw anchor differs from the published seats"
        d = d[d.draw >= 0]
        draws = {q: d[q].astype(int).tolist() if q in d else [0] * len(d) for q in parties}

    ts = (BASE / "viz/src/constants/parties.ts").read_text()

    def ts_map(name):
        block = re.search(rf"export const {name}[^=]*=\s*\{{(.*?)\n\}};", ts, re.S).group(1)
        return dict(re.findall(r"^\s*(\w+):\s*'([^']*)'", block, re.M))

    colors, names = ts_map("PARTY_COLORS"), ts_map("PARTY_NAMES")
    payload = {
        "parties": parties, "order": order, "names": {q: names[q] for q in parties},
        "colors": {q: colors[q] for q in parties}, "seats": seats_pub, "chamber": 873, "majority": 437, "share": share, "lines": lines,
        "domains": domains, "draws": draws,
        "bills": [{"v": b["variable"], "domain": b["domain"], "q": b["question"], "overall": round(b["overallPct"], 1),
                   "pFree": b["houseRawMultiProbPass"], "pct": {q: round(float(P[i, k]) * 100, 1) for k, q in enumerate(parties)}}
                  for i, b in enumerate(bills)],
    }
    tpl = (HERE / "vote_agreement_template.html").read_text()
    out = HERE / "outputs/vote_agreement.html"
    out.write_text(tpl.replace("/*TOKENS*/", TOKENS.read_text()).replace("/*DATA*/", json.dumps(payload, allow_nan=False)))
    print(f"wrote {out}" + ("" if draws else " (no per-draw seats yet: majority odds hidden)"))


if __name__ == "__main__":
    sys.exit(main())
