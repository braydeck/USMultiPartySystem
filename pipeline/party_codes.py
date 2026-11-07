"""
party_codes.py
--------------
Party codes for the typology's cluster IDs, and which IDs currently hold voters.

Cluster IDs are stable across typologies (pinned through data/processed/party_id_reference.csv),
so a typology with fewer parties leaves its slot empty: 4 (DAL) in the nine-party typology of 2026-11-04. A
slot is live when some respondent's first choice in data/processed/typology_cluster_assignments.csv
is that cluster.

The typology is read with the csv module, not pandas, because the bootstrap swaps pd.read_csv
for a resampling reader during a draw, and the live set must not change from draw to draw.

Use ALL_CLUSTERS only where every ID must exist positionally (the prob_cluster_0..9 columns).
Anything that fields, lists or reports parties uses CLUSTER_TO_PARTY / PARTIES, which hold the
live parties only.
"""

import csv
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
TYPOLOGY = BASE / "data" / "processed" / "typology_cluster_assignments.csv"

ALL_PARTIES = {0: "CON", 1: "LBR", 2: "STY", 3: "NAT", 4: "DAL",
               5: "POP", 6: "CUP", 7: "OAO", 8: "DSA", 9: "PRG"}
ALL_CLUSTERS = list(ALL_PARTIES)

with open(TYPOLOGY, newline="") as f:
    LIVE_CLUSTERS = sorted({int(float(r["cluster"])) for r in csv.DictReader(f)})
CLUSTER_TO_PARTY = {k: ALL_PARTIES[k] for k in LIVE_CLUSTERS}
PARTY_TO_CLUSTER = {p: k for k, p in CLUSTER_TO_PARTY.items()}
PARTIES = list(CLUSTER_TO_PARTY.values())
EMPTY_PARTIES = [p for k, p in ALL_PARTIES.items() if k not in CLUSTER_TO_PARTY]

# Left-to-right display order: how often the parties vote together (ruled 2026-11-06). First MDS
# dimension of party-majority agreement over the Legislation tab's bills, written to
# data/processed/party_order.csv by analysis/coalitions/vote_agreement.py. Mirrors F5_ORDER in
# viz/src/constants/parties.ts; the hex cartograms read that copy.
with open(BASE / "data" / "processed" / "party_order.csv", newline="") as f:
    LEFT_RIGHT = [r["party"] for r in sorted(csv.DictReader(f), key=lambda r: int(r["rank"]))
                  if r["party"] in PARTY_TO_CLUSTER]
assert sorted(LEFT_RIGHT) == sorted(PARTIES), f"party_order.csv {LEFT_RIGHT} != live parties {PARTIES}"
