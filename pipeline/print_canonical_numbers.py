#!/usr/bin/env python3
"""Print the canonical, published simulation numbers straight from the viz data files.

WHY THIS EXISTS
---------------
Write-ups kept drifting from the simulation because authors hand-transcribed numbers
from the wrong file. The most common mistake: using `clusterProfiles.json` -> `seatsHouse`
(a cluster *population baseline*, where SD=166 looks "largest") instead of the actual STV
election result the viz displays (`houseSeats.json`, where CON=202 is the largest party).

The viz's data files are the single source of truth for anything public-facing. Run this
script and copy numbers from its output instead of reading the JSON by hand.

    python pipeline/print_canonical_numbers.py

See docs/DATA_SOURCES.md for the full map of which file backs which claim.
"""
import json
from collections import Counter
from pathlib import Path

VIZ_DATA = Path(__file__).resolve().parent.parent / "viz" / "src" / "data"


def load(name):
    return json.loads((VIZ_DATA / name).read_text())


def house_party_line():
    rows = sorted(load("houseSeats.json"), key=lambda r: -r["national"])
    print("HOUSE — party-line / pure_multi (the viz default 'party-line' view)")
    print("  source: viz/src/data/houseSeats.json  (<- data/outputs/pure_multi/house/stv_seat_summary.csv)")
    print(f"  {'Party':18s} {'Seats':>5s} {'Seat%':>6s} {'Pop%':>6s}")
    for r in rows:
        print(f"  {r['partyName']:18s} {r['national']:5d} {r['pctNational']:6.1f} {r['pctPopulation']:6.1f}")
    print(f"  TOTAL {sum(r['national'] for r in rows)} seats. Largest = {rows[0]['partyName']} ({rows[0]['national']}).")
    print()


def senate():
    files = [
        ("Crossover x Condorcet", "fdSenateCondorcet.json"),
        ("Crossover x IRV", "fdSenateIRV.json"),
        ("Pure-partisan x Condorcet", "pureMultiSenateCondorcet.json"),
        ("Pure-partisan x IRV", "pureMultiSenateIRV.json"),
    ]
    print("SENATE — 51 seats, four scenarios (party totals)")
    for label, fname in files:
        c = Counter(r["senatorParty"] for r in load(fname))
        totals = "  ".join(f"{k}={v}" for k, v in c.most_common())
        print(f"  {label:28s} ({fname}): {totals}")
    print()


def caveats():
    print("DO NOT USE for 'seats won':")
    print("  - clusterProfiles.json -> seatsHouse : cluster POPULATION baseline (SD=166), not an election result.")
    print("  - data/outputs/No_C7_canonical/stv_seat_summary.csv : outdated 850-seat summary, not the canonical result.")
    print("    (But the No_C7_* DIRS are kept on purpose: pure_multi/factor_deviation read their")
    print("     ballots_checkpoint + district_apportionment, and the viz transfer matrix sources from them.)")
    print()
    print("PARTY POLICY %s and demographics: read live from viz/src/data/clusterProfiles.json")
    print("  (variables[*].pct per party; variables[*].overall = national average). These were")
    print("  regenerated at least once, so older write-ups are stale. Re-pull before quoting.")


if __name__ == "__main__":
    house_party_line()
    senate()
    caveats()
