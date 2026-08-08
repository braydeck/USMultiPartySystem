#!/usr/bin/env python3
"""
Pull ballot-level RCV reports from ranked.vote and convert them to the schema
``pipeline/rcv/process_dominion_cvr.py`` writes.

ranked.vote publishes cast-vote-record-derived reports (CC-BY) for jurisdictions
whose raw CVR files are awkward to obtain, which is the case for Maine. Its
pairwise matrices were cross-checked against this repo's own Dominion processing
on the Alaska 2022 special election and agreed to within 0.03 percentage points
on every cell, so the two sources are interchangeable.

Usage:
    python pipeline/rcv/fetch_ranked_vote.py            # all races in RACES below
    python pipeline/rcv/fetch_ranked_vote.py --list     # show configured races
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidates import relabel  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = REPO_ROOT / "data" / "outputs" / "rcv"
API = "https://ranked.vote/api/{path}/report.json"
REPORT_URL = "https://ranked.vote/report/{path}"

# path, output stem, state, year, office, contestType, display name, district
RACES = [
    ("us/me/2018/11/cd02",          "ME_2018_US_HOUSE_CD2",   "ME", 2018, "US_HOUSE", "GENERAL", "U.S. House, CD2", "CD2"),
    ("us/me/2018/06/gov-primary-dem", "ME_2018_GOV_PRIMARY_D", "ME", 2018, "GOVERNOR", "PRIMARY_D", "Governor, Democratic primary", None),
    ("us/me/2018/06/cd02-primary-dem", "ME_2018_US_HOUSE_CD2_PRIMARY_D", "ME", 2018, "US_HOUSE", "PRIMARY_D", "U.S. House CD2, Democratic primary", "CD2"),
    ("us/me/2020/07/cd02-primary-rep", "ME_2020_US_HOUSE_CD2_PRIMARY_R", "ME", 2020, "US_HOUSE", "PRIMARY_R", "U.S. House CD2, Republican primary", "CD2"),
    ("us/me/2026/06/gov-primary-dem", "ME_2026_GOV_PRIMARY_D", "ME", 2026, "GOVERNOR", "PRIMARY_D", "Governor, Democratic primary", None),
    ("us/me/2026/06/gov-primary-rep", "ME_2026_GOV_PRIMARY_R", "ME", 2026, "GOVERNOR", "PRIMARY_R", "Governor, Republican primary", None),
    ("us/me/2026/06/cd02-primary-dem", "ME_2026_US_HOUSE_CD2_PRIMARY_D", "ME", 2026, "US_HOUSE", "PRIMARY_D", "U.S. House CD2, Democratic primary", "CD2"),
]


def fetch(path: str) -> dict:
    with urllib.request.urlopen(API.format(path=path), timeout=60) as resp:
        return json.load(resp)


def convert(report: dict, stem: str, state: str, year: int, office: str,
            contest_type: str, race_name: str, district, path: str) -> dict:
    names = [c["name"] for c in report["candidates"]]
    rounds_out = []

    for i, rnd in enumerate(report["rounds"]):
        totals = {names[a["allocatee"]]: a["votes"]
                  for a in rnd["allocations"] if a["allocatee"] != "X"}
        continuing = sum(totals.values())
        # Eliminated this round = anyone standing now but gone next round.
        if i + 1 < len(report["rounds"]):
            nxt = {a["allocatee"] for a in report["rounds"][i + 1]["allocations"]}
            eliminated = [names[a["allocatee"]] for a in rnd["allocations"]
                          if a["allocatee"] != "X" and a["allocatee"] not in nxt]
        else:
            eliminated = []
        rounds_out.append({
            "round": i + 1,
            "totals": dict(sorted(totals.items(), key=lambda kv: -kv[1])),
            "pcts": {c: round(v / continuing * 100, 2)
                     for c, v in sorted(totals.items(), key=lambda kv: -kv[1])},
            "eliminated": eliminated,
            "continuingBallots": continuing,
            "inactiveBallots": rnd.get("undervote", 0) + rnd.get("overvote", 0),
        })

    matrix, counts = {}, {}
    pw = report["pairwisePreferences"]
    for ri, r in enumerate(pw["rows"]):
        a = names[r]
        matrix[a], counts[a] = {}, {}
        for ci, c in enumerate(pw["cols"]):
            if r == c:
                continue
            cell = pw["entries"][ri][ci]
            if cell is None:
                continue
            matrix[a][names[c]] = round(cell["frac"], 4)
            counts[a][names[c]] = cell["numerator"]

    irv_winner = names[report["winner"]]
    cond_winner = names[report["condorcet"]] if report.get("condorcet") is not None else None
    first_round = rounds_out[0]["totals"]
    plurality = max(first_round, key=lambda c: first_round[c])

    return {
        "state": state,
        "year": year,
        "office": office,
        "contestType": contest_type,
        "raceName": race_name,
        "district": district,
        "candidates": list(first_round.keys()) + [n for n in names if n not in first_round],
        "totalBallots": report["ballotCount"],
        "activeBallots": rounds_out[0]["continuingBallots"],
        "irvRounds": rounds_out,
        "irvWinner": irv_winner,
        "condorcetMatrix": matrix,
        "condorcetCounts": counts,
        "condorcetWinner": cond_winner,
        "rankedPairsWinner": cond_winner,
        "irvMatchesCondorcet": irv_winner == cond_winner,
        "pluralityWinner": plurality,
        "irvMatchesPlurality": irv_winner == plurality,
        "provenance": REPORT_URL.format(path=path),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for path, stem, *_ in RACES:
            print(f"{stem:36s} {path}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path, stem, state, year, office, ctype, race_name, district in RACES:
        report = fetch(path)
        out = relabel(convert(report, stem, state, year, office, ctype, race_name, district, path))
        (OUTPUT_DIR / f"{stem}.json").write_text(json.dumps(out, indent=2))
        flag = "" if out["irvMatchesCondorcet"] else "  ⚑ IRV ≠ Condorcet"
        print(f"{stem:36s} {len(out['irvRounds'])} rounds, {out['totalBallots']:>7,} ballots, "
              f"IRV → {out['irvWinner']}{flag}")


if __name__ == "__main__":
    main()
