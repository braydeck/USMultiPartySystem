#!/usr/bin/env python3
"""
RCV contests whose round-by-round tally is published but whose cast vote record
is not released, transcribed from the state's own summary report.

Only Maine's 2022 CD2 general falls in this category: the Secretary of State
published the RCV Summary Report but no ballot-level export, so the pairwise
matrix cannot be computed and ``condorcetAvailable`` is false. Every other race
in this project is derived from ballots.

Usage:
    python pipeline/rcv/official_reports.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidates import relabel  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = REPO_ROOT / "data" / "outputs" / "rcv"

ME_2022_CD2_SOURCE = (
    "https://www.maine.gov/sos/sites/maine.gov.sos/files/inline-files/"
    "Rep%20to%20Congress%20Dist%202%20RCV%20results.pdf"
)

RACES = [
    {
        "stem": "ME_2022_US_HOUSE_CD2",
        "state": "ME",
        "year": 2022,
        "office": "US_HOUSE",
        "contestType": "GENERAL",
        "raceName": "U.S. House, CD2",
        "district": "CD2",
        "candidates": ["Jared Forrest Golden", "Bruce Poliquin", "Tiffany Bond", "Write-in"],
        "totalBallots": 322778,
        "irvRounds": [
            {
                "round": 1,
                "totals": {"Jared Forrest Golden": 153074, "Bruce Poliquin": 141260,
                           "Tiffany Bond": 21655, "Write-in": 393},
                "continuingBallots": 316382,
                "inactiveBallots": 6396,
                "eliminated": ["Tiffany Bond", "Write-in"],
            },
            {
                "round": 2,
                "totals": {"Jared Forrest Golden": 165136, "Bruce Poliquin": 146142},
                "continuingBallots": 311278,
                "inactiveBallots": 11500,
                "eliminated": [],
            },
        ],
        "irvWinner": "Jared Forrest Golden",
        "provenance": ME_2022_CD2_SOURCE,
    },
]


def build(race: dict) -> dict:
    stem = race.pop("stem")
    for rnd in race["irvRounds"]:
        continuing = rnd["continuingBallots"]
        rnd["pcts"] = {c: round(v / continuing * 100, 2) for c, v in rnd["totals"].items()}
    first = race["irvRounds"][0]["totals"]
    race.update({
        "activeBallots": race["irvRounds"][0]["continuingBallots"],
        "condorcetMatrix": {},
        "condorcetWinner": None,
        "condorcetAvailable": False,
        "irvMatchesCondorcet": None,
        "pluralityWinner": max(first, key=lambda c: first[c]),
    })
    race["irvMatchesPlurality"] = race["irvWinner"] == race["pluralityWinner"]
    return stem, relabel(race)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for race in RACES:
        stem, out = build(dict(race))
        (OUTPUT_DIR / f"{stem}.json").write_text(json.dumps(out, indent=2))
        print(f"{stem:36s} {len(out['irvRounds'])} rounds, {out['totalBallots']:>7,} ballots, "
              f"IRV → {out['irvWinner']}  (no CVR: Condorcet unavailable)")


if __name__ == "__main__":
    main()
