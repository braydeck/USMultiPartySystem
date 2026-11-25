#!/usr/bin/env python3
"""
build_agent_summary.py → docs/AGENT_SUMMARY.md

One compact, table-only reference to the simulation for agents: parties, House, presidency,
Senate and legislation, at the app's default scenario (plus every turnout stop where the
payloads carry one). Every figure is read from the JSON the site renders; see scripts/sim_data.py.

    python3 scripts/build_agent_summary.py
"""

from __future__ import annotations

import datetime as dt
import math

import sim_data as S
from sim_data import f1, f2

OUT = S.ROOT / "docs" / "AGENT_SUMMARY.md"


def main() -> None:
    d = S.app_defaults()
    depth, stop, mag = d["depth"], d["stop"], d["magnitude"]
    order = S.parties()
    names = S.party_names()
    cp = S.cluster_profiles()
    pop = S.population()
    fmeta = S.factor_meta()
    tag = S.taglines()
    out: list[str] = []
    w = out.append

    # ── Header ───────────────────────────────────────────────────────────────
    h_def = S.house(depth, mag, stop)
    seats_def = sum(h_def["stvSeats"].values())
    weights = S.ec_weights()
    w("# Agent summary: the nine-party simulation")
    w("")
    w(f"Generated {dt.date.today().isoformat()} by `scripts/build_agent_summary.py` from the site's "
      "payloads. Do not edit by hand; rerun the script after the pipeline. Party order is left to right "
      f"(`pipeline/party_codes.LEFT_RIGHT`, from `data/processed/party_order.csv`).")
    w("")
    w(S.table(["Setting", "Value", "Source"], [
        ["Respondents", f"{S.n_respondents():,}", "`viz/src/data/crossPartyAffinity.json` nVoters"],
        ["Parties", len(order), "`pipeline/party_codes.py`"],
        ["Field", d["field"], "app default (`scenario` URL param)"],
        ["Ballot depth", d["depth"], "app default (`depth`)"],
        ["Turnout gap stop", f"{stop}%", "app default (`part`)"],
        ["Turnout stops in payloads", ", ".join(s + "%" for s in d["stops"]), "tab sources"],
        ["Magnitude", mag, "app default (`wyoming`)"],
        [f"House seats ({mag})", seats_def, "`viz/src/data/houseDepthNational.json`"],
        ["House seats (triple)", sum(S.house(depth, "triple", stop)["stvSeats"].values()), "same"],
        ["Electors", sum(weights.values()), "`viz/src/data/houseStateMap.json` seats + 2 per state"],
        ["Senate races / seats", f"{len(S.senate('cond', stop))} / {2 * len(S.senate('cond', stop))}",
         "`viz/src/data/pureMultiSenate*.json` (one race per state); chamber seats two per state"],
        ["Legislation bills", len(S.bills()), "`viz/src/data/candidateVoteModel.json`"],
        ["Legislation default vote model", d["voteModel"], "app default (`voteModel`)"],
    ], "lll"))
    w("")
    w("Sections: [Parties](#parties) · [House](#house) · [Presidency](#presidency) · "
      "[Senate](#senate) · [Legislation](#legislation) · [Coalitions by domain](#coalitions-by-domain) · "
      "[Budget priorities](#budget-priorities)")
    w("")

    # ── Parties ──────────────────────────────────────────────────────────────
    w("## Parties")
    w("")
    w("Sources: `viz/src/data/partyPopulation.json` (shares), `viz/src/data/clusterProfiles.json` "
      "(factor z-scores, key positions), `viz/src/data/factorLoadings.json` (η²), "
      "`viz/src/constants/parties.ts` (names, taglines).")
    w("")
    w("Population share is each party's first-choice share of adults (post-weighted). Voter share "
      "re-weights the same head count by validated 2024 turnout (the 2024 electorate as cast). "
      "Factor z-scores are SDs from the national mean; high = more of the named trait.")
    w("")
    fac_hdr = [f"{f['label']} z ({f['factor']}, η² {f['eta']:.2f})" for f in fmeta]
    rows = []
    for p in order:
        rows.append([f"**{p}** {names.get(p, cp[p]['partyName'])}", f1(pop[p]["popShare"]),
                     f1(pop[p]["voteShare"])] + [f2(cp[p][f"z_{f['factor']}"]) for f in fmeta])
    w(S.table(["Party", "Pop %", "Voter % (2024)"] + fac_hdr, rows))
    w("")
    w(S.table(["Factor", "Key", "η²", "Between/within", "High pole", "Low pole"],
              [[f["label"], f["factor"], f"{f['eta']:.3f}", f["bw"], f["hi"], f["lo"]] for f in fmeta],
              "llrrll"))
    w("")
    w("Profiles (tagline from the app; positions are the party's top differentiators: % of members who support, "
      "and the gap vs the nation in points):")
    w("")
    rows = []
    for p in order:
        kp = cp[p]["keyPositions"][:3]
        pos = "; ".join(f"{k['question']} {k['pct']:.0f}% ({k['diffPp']:+.0f})" for k in kp)
        rows.append([f"**{p}**", tag.get(p, ""), pos])
    w(S.table(["Party", "Tagline", "Top positions"], rows, "lll"))
    w("")

    # ── House ────────────────────────────────────────────────────────────────
    w("## House")
    w("")
    w(f"Sources: STV and party list from `viz/src/data/houseDepthNational.json` [{depth}][magnitude][stop] "
      "(what the House tab shows at a ranked depth); MMP from `viz/src/data/houseMmpNational.json` "
      "(MMP uses the 436 real districts plus a per-state top-off; it has no depth setting). "
      f"Turnout stop {stop}%.")
    w("")
    for m in ["double", "triple"]:
        h = S.house(depth, m, stop)
        mm = S.mmp(m, stop)
        t_stv, t_list, t_mmp = (sum(x.values()) for x in (h["stvSeats"], h["listSeats"], mm["mmpSeats"]))
        rows = []
        for p in order:
            s, l, x = h["stvSeats"].get(p, 0), h["listSeats"].get(p, 0), mm["mmpSeats"].get(p, 0)
            rows.append([p, f1(h["voteShare"].get(p, 0)), s, f1(s / t_stv * 100), l, f1(l / t_list * 100),
                         x, f1(x / t_mmp * 100)])
        rows.append(["**Total**", "", t_stv, "", t_list, "", t_mmp, ""])
        w(f"### {m.capitalize()} magnitude")
        w("")
        w(S.table(["Party", "Vote %", "STV seats", "STV %", "List seats", "List %", "MMP seats", "MMP %"], rows))
        w("")
        w(S.table(["Metric", "STV", "Party list", "MMP"], [
            ["Gallagher index", h["gallagher"]["stv"], h["gallagher"]["list"], mm["gallagher"]["mmp"]],
            ["Unrepresented voters %", h["unrepresented"]["stv"], h["unrepresented"]["list"], mm["unrepresented"]],
            ["Wasted votes %", h["wasted"]["stv"], h["wasted"]["list"], ""],
            ["MMP district / top-off / overhang seats", "", "", f"{mm['districtTotal']} / {mm['topoffTotal']} / {mm['overhang']}"],
        ], "lrrr"))
        w("")
    w(f"STV seats by turnout stop ({mag}, {depth}):")
    w("")
    rows = []
    for p in order:
        rows.append([p] + [S.house(depth, mag, s)["stvSeats"].get(p, 0) for s in d["stops"]])
    w(S.table(["Party"] + [f"{s}%" for s in d["stops"]], rows))
    w("")

    # ── Presidency ───────────────────────────────────────────────────────────
    w("## Presidency")
    w("")
    w(f"Sources: primary from `viz/public/data/primaryDepth.json` [{depth}]; general from "
      f"`viz/public/data/generalDepth.json` [{depth}] (identical to `rawMultiPresidentialElection{S.stop_suffix(stop)}.json` "
      "at the default); top-two reduction from `viz/public/data/topTwo.json`; per-state elector rules "
      "computed here with a port of `viz/src/lib/ecAllocation.ts` over `irvStateWinners`, weights "
      "`houseStateMap.json` seats + 2.")
    w("")
    # Primary at default
    pr = S.primary(depth, stop)
    last = pr["stagesOrder"][-1]
    survivors = [c["code"] for c in pr["candidates"] if c["stages"].get(last, {}).get("status") == "surviving"]
    w(f"### Primary ({len(pr['candidates'])} candidates, stages "
      + " → ".join(pr["stageLabels"][s] for s in pr["stagesOrder"]) + f"; turnout {stop}%)")
    w("")
    w(f"Finalists: {', '.join(sorted(survivors, key=lambda c: order.index(S.party_of(c))))}. "
      "Cells are the vote % held after each stage's STV count; survivors are elected at the quota, so they "
      "tie by construction. ✗ marks the stage a candidate was cut.")
    w("")

    def reach(c):
        return sum(1 for s in pr["stagesOrder"] if c["stages"].get(s, {}).get("status") in ("surviving", "eliminated_this_round"))

    rows = []
    for c in sorted(pr["candidates"], key=lambda c: (-reach(c), -max(st["votePct"] for st in c["stages"].values()))):
        cells = []
        for s in pr["stagesOrder"]:
            st = c["stages"].get(s)
            if not st or st["status"] == "previously_eliminated":
                cells.append("")
            else:
                cells.append(f"{st['votePct']:.1f}" + (" ✗" if st["status"] == "eliminated_this_round" else ""))
        rows.append([c["code"]] + cells)
    w(S.table(["Candidate"] + [f"{pr['stageLabels'][s]} %" for s in pr["stagesOrder"]], rows))
    w("")

    # General per stop
    w("### General: winners and finalists by turnout stop")
    w("")
    rows = []
    for s in d["stops"]:
        g = S.general(depth, s)
        fc = S.national_first_choice(g["irvRounds"])
        fin = sorted(fc, key=lambda c: -fc[c])
        rows.append([f"{s}%", ", ".join(f"{c} {fc[c]:.1f}" for c in fin), g["condorcetWinner"], g["irvWinner"],
                     fin[0]])
    w(S.table(["Stop", "Finalists (national first-choice %)", "Condorcet", "IRV", "FPTP (first choice)"], rows, "lllll"))
    w("")

    g = S.general(depth, stop)
    fin = [c["code"] for c in g["irvRounds"][0]["candidates"]]
    fin.sort(key=lambda c: order.index(S.party_of(c)))
    beats = {a: {} for a in fin}
    for m in g["condorcetMatchups"]:
        a, b, pa = m["candidateA"], m["candidateB"], m["aWinsPct"]
        beats[a][b], beats[b][a] = pa, 100 - pa
    w(f"### Head-to-head matrix (turnout {stop}%): % of voters ranking row above column")
    w("")
    w(S.table(["", *fin], [[a] + [("—" if a == b else f1(beats[a][b])) for b in fin] for a in fin]))
    w("")
    w(f"### IRV rounds (turnout {stop}%)")
    w("")
    rows = []
    for c in fin:
        rows.append([c] + [next((f1(x["pct"]) + (" ✗" if x["eliminated"] else "") for x in r["candidates"]
                                 if x["code"] == c), "") for r in g["irvRounds"]])
    w(S.table(["Candidate"] + [f"R{r['round']}" for r in g["irvRounds"]], rows))
    w("")

    w("### Electors by rule and turnout stop")
    w("")
    w(f"Total electors {sum(weights.values())}, majority {sum(weights.values()) // 2 + 1}. "
      "Top-2 rules: every ballot counts for whichever of the two national finalists it ranks higher "
      "(pair from the Condorcet or the IRV route), then each state allocates proportionally or "
      "winner-take-all. Per-state rules ignore the national result. A blank winner means no majority "
      "(the House decides).")
    w("")
    rows = []
    for s in d["stops"]:
        t2 = S.top_two(depth, s)
        g = S.general(depth, s)
        for route in ["condorcet", "irv"]:
            c = t2[route]
            for alloc in ["prop", "wta"]:
                ev = c[alloc]
                rows.append([f"{s}%", f"Top-2 {'proportional' if alloc == 'prop' else 'WTA'} ({route} pair)",
                             ", ".join(f"{k} {v}" for k, v in sorted(ev.items(), key=lambda kv: -kv[1])),
                             c[f"{alloc}Winner"] or "", f"pop {c['a']} {c['popA']:.1f}%"])
        for meth, label in [("prop", "Per-state proportional to first choice"), ("fptp", "Per-state WTA, first choice"),
                            ("irv", "Per-state IRV, WTA"), ("condorcet", "Per-state Condorcet, WTA")]:
            t = S.allocate_ec(g["irvStateWinners"], weights, meth)
            rows.append([f"{s}%", label, ", ".join(f"{k} {v}" for k, v in sorted(t["byParty"].items(), key=lambda kv: -kv[1])),
                         t["winner"] or "", ""])
    w(S.table(["Stop", "Rule", "Electors", "Winner", "Note"], rows, "lllll"))
    w("")

    # ── Senate ───────────────────────────────────────────────────────────────
    thr = S.split_threshold_pp()
    w("## Senate")
    w("")
    w("Sources: `viz/src/data/uncertainty<stop>.json` senate (re-clustering bootstrap; the Senate map "
      "and chamber read this) and `viz/src/data/pureMultiSenate{Condorcet,IRV}<stop>.json` (the single "
      "observed run, the map's fallback fill). Delegations computed with a port of "
      "`viz/src/lib/senateDelegations.ts`. Rank-7 ballots, one modelled race per state (51).")
    w("")
    w(f"The chamber is two senators per state ({2 * len(S.senate('cond', stop))} seats). Each state sends "
      "its bootstrap-modal winner twice, unless the runner-up is within "
      f"{thr:g} points of resample win share, in which case it splits one each.")
    w("")
    w("Chamber seats by turnout stop (split states in the last column):")
    w("")
    rows = []
    for s in d["stops"]:
        us = S.uncertainty(s)["senate"]
        for meth, lab in [("cond", "Condorcet"), ("irv", "IRV")]:
            ds = S.delegation_seats(us[meth]["states"])
            n_split = sum(1 for x in S.delegations(us[meth]["states"]).values() if x["split"])
            rows.append([f"{s}%", lab] + [ds.get(p, 0) or "" for p in order] + [sum(ds.values()), n_split])
    w(S.table(["Stop", "Method", *order, "Total", "Splits"], rows, "ll" + "r" * (len(order) + 2)))
    w("")
    w("Single observed run, one winner per state (51 races):")
    w("")
    rows = []
    for s in d["stops"]:
        for meth, lab in [("cond", "Condorcet"), ("irv", "IRV")]:
            cnt: dict[str, int] = {}
            for r in S.senate(meth, s):
                cnt[r["senatorParty"]] = cnt.get(r["senatorParty"], 0) + 1
            rows.append([f"{s}%", lab] + [cnt.get(p, 0) or "" for p in order])
    w(S.table(["Stop", "Method", *order], rows, "ll" + "r" * len(order)))
    w("")
    U = S.uncertainty(stop)
    u = U["senate"]
    w(f"Bootstrap at turnout {stop}% ({U['nDraws']} draws), on the {2 * len(S.senate('cond', stop))}-seat "
      "basis with each state's winner doubled: expected [95% range]")
    w("")
    rows = []
    for p in order:
        r = [p]
        for meth in ["cond", "irv"]:
            sp = u[meth]["seats"].get(p)
            r.append(f"{sp['expected']:.1f} [{sp['lo']}–{sp['hi']}]" if sp else "")
        rows.append(r)
    w(S.table(["Party", "Condorcet", "IRV"], rows, "lll"))
    w("")
    cond = {r["stateFips"]: r for r in S.senate("cond", stop)}
    irv = {r["stateFips"]: r for r in S.senate("irv", stop)}
    dc, di = S.delegations(u["cond"]["states"]), S.delegations(u["irv"]["states"])
    w(f"By state (turnout {stop}%): observed winner · resample leader and its share · delegation")
    w("")
    rows = []
    for fips in sorted(cond, key=lambda f: cond[f]["stateAbbr"]):
        row = [cond[fips]["stateAbbr"]]
        for obs, dl in [(cond, dc), (irv, di)]:
            x = dl[fips]
            row += [obs[fips]["senatorParty"], f"{x['top']} {x['topPct']:.0f}%"
                    + (f", {x['runner']} {x['runnerPct']:.0f}%" if x["runner"] else ""),
                    "/".join(x["seats"]) + (" (split)" if x["split"] else "")]
        rows.append(row)
    w(S.table(["State", "Cond observed", "Cond resample", "Cond seats", "IRV observed", "IRV resample", "IRV seats"],
              rows, "lllllll"))
    w("")

    # ── Legislation ──────────────────────────────────────────────────────────
    pos, binm = S.agreement_matrices(order)
    w("## Legislation")
    w("")
    w(f"Source: `viz/src/data/candidateVoteModel.json` ({len(S.bills())} bills, each party's observed "
      "support), computed with a port of `viz/src/components/legislation/PartyAgreement.tsx`. "
      "Position-based, so it does not move with seats or turnout.")
    w("")
    for title, M, note in [("Free vote", pos, "100 − average gap in support across the bills"),
                           ("Whipped", binm, "% of bills where both parties' majorities fall on the same side")]:
        w(f"### {title}: {note}")
        w("")
        w(S.table(["", *order], [[a] + [("—" if a == b else ("" if math.isnan(M[a][b]) else f"{M[a][b]:.0f}"))
                                         for b in order] for a in order]))
        w("")

    hv = {r["variable"]: r for r in S.load(S.src(f"houseVoteModel{S.stop_suffix(stop)}.json"))}
    sv = {r["variable"]: r for r in S.load(S.src(f"senateVoteModel{S.stop_suffix(stop)}.json"))}
    w(f"### Bills at turnout {stop}% (pass probability; president from the party-line field)")
    w("")
    w(f"Sources: `houseVoteModel{S.stop_suffix(stop)}.json` (houseRawMultiProbPass = STV double, "
      "houseListProbPass = party list double), "
      f"`senateVoteModel{S.stop_suffix(stop)}.json` (cond/irvRawMultiProbPass, presRawMultiCond/IRVSigns).")
    w("")
    rows = []
    for b in S.bills():
        h, s_ = hv[b["variable"]], sv[b["variable"]]
        rows.append([b["question"], f"{float(h['overallPct']):.0f}",
                     f"{float(h['houseRawMultiProbPass']):.2f}", f"{float(h['houseListProbPass']):.2f}",
                     f"{float(s_['condRawMultiProbPass']):.2f}", f"{float(s_['irvRawMultiProbPass']):.2f}",
                     s_.get("presRawMultiCondSigns", ""), s_.get("presRawMultiIRVSigns", "")])
    w(S.table(["Bill", "Nation %", "House STV", "House list", "Senate Cond", "Senate IRV", "Pres (Cond)", "Pres (IRV)"],
              rows, "lrrrrrll"))
    w("")

    # ── Coalitions by domain ─────────────────────────────────────────────────
    meth = "cond" if d["senateMethod"] == "condorcet" else "irv"
    chambers = [("House", h_def["stvSeats"]),
                ("Senate", S.delegation_seats(S.uncertainty(stop)["senate"][meth]["states"]))]
    budget = S.budget_rows()
    w("## Coalitions by domain")
    w("")
    w("### Parties that vote the same way on every item in the domain (port of `votingGroups`)")
    w("")
    doms: dict[str, list] = {}
    for b in S.bills() + budget:
        doms.setdefault(b["domain"], []).append(b)
    w(S.table(["Domain", "Items", "Bundles"],
              [[dm, len(rs), " | ".join(" ".join(g) for g in S.voting_groups(rs, order))] for dm, rs in doms.items()], "lrl"))
    w("")
    w("### Winning side and needed, by chamber")
    w("")
    w(f"Which parties form the majority on each kind of issue, at the app defaults (House STV {mag} "
      f"magnitude, depth {depth}, turnout {stop}%; Senate {d['senateMethod']} delegations), with every "
      "party casting all its seats the way its majority leans (support > 50%). Port of "
      "`domainCoalitions` / `coalitionSegments` in `viz/src/components/legislation/voteBloc.ts`, over the "
      f"{len(S.bills())} bills plus the {len(budget)} Budget items. Each cell: % of the domain's items on "
      "which the party is on the winning side (yes on a pass, no on a defeat), then in brackets % that pass "
      "only with its seats (without them the yes side falls to half the chamber or less). The grid always "
      "counts party-line votes, whatever the Vote Model toggle says.")
    w("")
    for cname, seats in chambers:
        total = sum(seats.get(p, 0) for p in order)
        w(f"### {cname}: {total} seats, majority {total // 2 + 1}")
        w("")
        w(S.table(["Party", *order], [["Seats", *[seats.get(p, 0) for p in order]]]))
        w("")
        rows, typ = [], []
        for r in S.domain_coalitions(S.bills() + budget, seats, order):
            n = len(r["bills"])
            rows.append([r["domain"], n, f"{r['passed']}/{n}"] + [
                "" if p not in r["membership"] else
                f"{r['membership'][p] * 100:.0f}" + (f" ({r['needed'][p] * 100:.0f})" if r["needed"][p] else "")
                for p in order])
            t = r["typical"]
            typ.append([r["domain"], " ".join(t["parties"]) or "(none)", "yes" if t["pass"] else "no",
                        f"{t['count']}/{n}", "; ".join(b["question"] for b in r["failed"]) or "none"])
        w(S.table(["Domain", "Items", "Pass", *order], rows))
        w("")
        w(S.table(["Domain", "Most common winning side", "Votes", "Items", "Items that fail"], typ, "llrrl"))
        w("")

    # ── Budget priorities ────────────────────────────────────────────────────
    w("## Budget priorities")
    w("")
    w("Source: `viz/src/data/budgetPriorities.json` (`pipeline/build_budget_priorities.py`), CES "
      "CC24_443_1..5: should the respondent's state legislature increase or decrease spending on each "
      "category. Each cell is the weighted % choosing slightly or greatly increase, against maintain or "
      "decrease. These are state spending preferences, not federal bills; they are not in the bill set "
      "the party order is computed from. Port of `viz/src/components/legislation/BudgetPriorities.tsx`.")
    w("")
    cats = [r["category"] for r in budget]
    level = {p: sum(r["parties"][p]["observedPct"] for r in budget) / len(budget) for p in order}
    nat = sum(r["overallPct"] for r in budget) / len(budget)
    by_level = sorted(order, key=lambda p: -level[p])
    w(f"### Level and share by category (% wanting more; level = mean of the {len(budget)}, national {nat:.0f})")
    w("")
    w(S.table(["Party", "Level", *cats],
              [[p, f"{level[p]:.0f}", *[f"{r['parties'][p]['observedPct']:.0f}" for r in budget]] for p in by_level]
              + [["National", f"{nat:.0f}", *[f"{r['overallPct']:.0f}" for r in budget]]]))
    w("")
    w("### Mix: category minus the party's own level, in points")
    w("")
    w(S.table(["Party", *cats],
              [[p, *[f"{r['parties'][p]['observedPct'] - level[p]:+.0f}" for r in budget]] for p in by_level]))
    w("")
    w(f"### Chamber outcome at the defaults (free vote: P(pass), port of `passProbability`; whipped: pass/fail)")
    w("")
    rows = []
    for r in budget:
        row = [r["category"], f"{r['overallPct']:.0f}"]
        for _, seats in chambers:
            pp = S.pass_probability(r, seats, order)
            c = S.coalition_segments_whipped(r, seats, order)
            row += [f"{pp:.2f}", ("passes" if c["pass"] else "fails")
                    + (f", pivotal {c['pivotal']}" if c["pivotal"] else ""), " ".join(c["yes"])]
        rows.append(row)
    w(S.table(["Category", "Nation %", "House free", "House whipped", "House yes side",
               "Senate free", "Senate whipped", "Senate yes side"], rows, "lrrllrll"))
    w("")

    OUT.write_text("\n".join(out))
    print(f"wrote {S.rel(OUT)} ({len(out)} lines)")


if __name__ == "__main__":
    main()
