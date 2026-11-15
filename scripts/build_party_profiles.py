#!/usr/bin/env python3
"""
build_party_profiles.py → PARTY_PROFILES.md

Per-party profiles of the current typology, built from the same payloads as
docs/AGENT_SUMMARY.md (see scripts/sim_data.py). Prose comes from the app's own copy in
viz/src/constants/parties.ts; every number is read from the JSON the site renders.

    python3 scripts/build_party_profiles.py
"""

from __future__ import annotations

import datetime as dt

import sim_data as S
from sim_data import f1, f2

OUT = S.ROOT / "PARTY_PROFILES.md"


def main() -> None:
    d = S.app_defaults()
    depth, stop, mag = d["depth"], d["stop"], d["magnitude"]
    order = S.parties()
    names, tag, blurb = S.party_names(), S.taglines(), S.blurbs()
    cp, pop, fmeta = S.cluster_profiles(), S.population(), S.factor_meta()
    h, mm = S.house(depth, mag, stop), S.mmp(mag, stop)
    t_h = sum(h["stvSeats"].values())
    us = S.uncertainty(stop)["senate"]
    sen = {m: S.delegation_seats(us[m]["states"]) for m in ("cond", "irv")}
    n_sen = sum(sen["cond"].values())
    g = S.general(depth, stop)
    fc = S.national_first_choice(g["irvRounds"])
    pr = S.primary(depth, stop)
    last = pr["stagesOrder"][-1]
    pos, whip = S.agreement_matrices(order)
    aff = S.load(S.src("crossPartyAffinity.json"))

    def h2h(code: str) -> tuple[int, int]:
        wins = losses = 0
        for m in g["condorcetMatchups"]:
            if code in (m["candidateA"], m["candidateB"]):
                wins += m["winner"] == code
                losses += m["winner"] != code
        return wins, losses

    def primary_fate(p: str) -> str:
        best = None
        for c in pr["candidates"]:
            if c["party"] != p:
                continue
            if c["stages"].get(last, {}).get("status") == "surviving":
                return f"{c['code']} reaches the general"
            for s in pr["stagesOrder"]:
                if c["stages"].get(s, {}).get("status") == "eliminated_this_round":
                    idx = pr["stagesOrder"].index(s)
                    if best is None or idx > best[0]:
                        best = (idx, f"best candidate {c['code']} cut at {pr['stageLabels'][s]}")
        return best[1] if best else "no candidate"

    out: list[str] = []
    w = out.append
    w("# Party profiles: the nine parties")
    w("")
    w(f"Generated {dt.date.today().isoformat()} by `scripts/build_party_profiles.py`. Do not edit by hand. "
      f"{S.n_respondents():,} CES 2024 respondents, {len(order)} parties from a DPGMM on {len(fmeta)} EFA factors. "
      f"Scenario: field {d['field']}, depth {depth}, turnout gap {stop}%, {mag} magnitude "
      f"({t_h} House seats, {n_sen} Senate seats). Parties run left to right by how often they vote together.")
    w("")
    w("Prose is the app's copy (`viz/src/constants/parties.ts`). Numbers: shares from "
      "`partyPopulation.json`, factors from `clusterProfiles.json` and `factorLoadings.json`, House from "
      "`houseDepthNational.json` and `houseMmpNational.json`, Senate from `uncertainty*.json` (two-per-state "
      "delegations), presidency from `generalDepth.json` and `primaryDepth.json`, agreement from "
      "`candidateVoteModel.json`, partial fit from `crossPartyAffinity.json`. For the full tables see "
      "`docs/AGENT_SUMMARY.md`.")
    w("")
    w("## At a glance")
    w("")
    rows = []
    for p in order:
        code = f"{p}_1"
        rows.append([f"**{p}** {names[p]}", f1(pop[p]["popShare"]), f1(pop[p]["voteShare"]),
                     h["stvSeats"].get(p, 0), h["listSeats"].get(p, 0), mm["mmpSeats"].get(p, 0),
                     sen["cond"].get(p, 0), sen["irv"].get(p, 0),
                     f1(fc[code]) if code in fc else "—"])
    w(S.table(["Party", "Pop %", "Voter %", "House STV", "House list", "House MMP", "Senate Cond",
               "Senate IRV", "Pres. first choice %"], rows))
    w("")
    w(S.table(["Factor", "η²", "High pole", "Low pole"],
              [[f"{f['label']} ({f['factor']})", f"{f['eta']:.3f}", f["hi"], f["lo"]] for f in fmeta], "lrll"))
    w("")
    w("---")
    for p in order:
        c = cp[p]
        w("")
        w(f"## {p}: {names[p]}")
        w("")
        w(f"*{tag[p]}.*")
        w("")
        w(blurb[p])
        w("")
        w(S.table(["Factor", "z", "Percentile"],
                  [[f["label"], f2(c[f"z_{f['factor']}"]), f"{c[f'pctile_' + f['factor']]:.0f}"] for f in fmeta],
                  "lrr"))
        w("")
        w("Signature positions (% of members who support; gap vs the nation in points):")
        w("")
        w(S.table(["Position", "Support %", "Gap"],
                  [[k["question"], f1(k["pct"]), f"{k['diffPp']:+.1f}"] for k in c["keyPositions"]], "lrr"))
        w("")
        code = f"{p}_1"
        wl = h2h(code) if code in fc else None
        partners = sorted((q for q in order if q != p), key=lambda q: -pos[p][q])[:2]
        flows = {q: v for q, v in aff["matrix"][p].items() if q != p}
        top_flow = sorted(flows, key=lambda q: -flows[q])[:2]
        retained = aff["parties"][p]["retained"] / aff["parties"][p]["hardShare"] * 100
        w(S.table(["Measure", "Value"], [
            ["Population / 2024 voter share", f"{f1(pop[p]['popShare'])}% / {f1(pop[p]['voteShare'])}%"],
            [f"House seats ({mag}, {stop}% gap): STV / list / MMP",
             f"{h['stvSeats'].get(p, 0)} / {h['listSeats'].get(p, 0)} / {mm['mmpSeats'].get(p, 0)} of {t_h}"],
            [f"Senate seats ({stop}% gap): Condorcet / IRV",
             f"{sen['cond'].get(p, 0)} / {sen['irv'].get(p, 0)} of {n_sen}"],
            ["Presidential primary", primary_fate(p)],
            ["General: first choice %, head-to-head W–L",
             f"{f1(fc[code])}%, {wl[0]}–{wl[1]}" if wl else "not a finalist"],
            ["Closest on bills (free vote / whipped)",
             ", ".join(f"{q} {pos[p][q]:.0f} / {whip[p][q]:.0f}" for q in partners)],
            ["Own-party share of members' posterior", f"{retained:.0f}%"],
            ["Members' partial fit goes mostly to", ", ".join(top_flow)],
        ], "ll"))
        w("")

    OUT.write_text("\n".join(out))
    print(f"wrote {S.rel(OUT)} ({len(out)} lines)")


if __name__ == "__main__":
    main()
