"""Tie-breaking for every STV and IRV count, after the Scottish local-government rules
(SSI 2007/42, Schedule 1).

  Exclusion (rule 51): among candidates tied for fewest votes, exclude the one with fewest votes at
  the most recent preceding stage at which they had unequal numbers of votes; if they were equal
  at every stage, decide by lot.
  Surplus order (rule 49): among candidates tied for the largest surplus, the one with more votes at
  the most recent preceding stage at which they were unequal goes first; otherwise by lot.

A "stage" is one count of continuing candidates' totals; each counter appends its totals to a
History before deciding, so history[-1] is the current stage.

The lot is a seeded draw (base seed 42) keyed on the count's own label (a district or state id)
and the stage number, so a run reproduces exactly. The tied candidates are put in a fixed order
by party cluster id and slate position before the draw, never by name, so renaming a party
cannot change who wins.
"""
import zlib

import numpy as np

from party_codes import ALL_PARTIES

LOT_SEED = 42
_CLUSTER_OF = {p: k for k, p in ALL_PARTIES.items()}


def stable_key(code: str) -> tuple:
    """Name-independent order for a candidate code like 'LP_2' or a bare party code 'LP'."""
    party, _, rest = str(code).partition("_")
    slate = int(rest) if rest.isdigit() else 0
    return (_CLUSTER_OF.get(party, 99), slate, rest if not rest.isdigit() else "")


class History:
    """Totals of every continuing candidate at each stage of one count."""

    def __init__(self, label: str = "", key=stable_key):
        """`key` orders tied candidates before a lot; pass one that maps an index to its code
        when a counter works on candidate indices."""
        self.label = str(label)
        self.key = key
        self.stages: list = []

    def push(self, totals: dict):
        self.stages.append(dict(totals))

    def _lot(self, tied: list, pick_max: bool):
        rng = np.random.default_rng([LOT_SEED, zlib.crc32(self.label.encode()), len(self.stages),
                                     int(pick_max)])
        ordered = sorted(tied, key=self.key)
        return ordered[int(rng.integers(len(ordered)))]

    def _resolve(self, tied: list, pick_max: bool):
        """Walk back from the stage before the current one to the most recent stage at which the
        tied candidates' votes differ; keep the extreme there, and repeat if that still ties."""
        tied = list(tied)
        for stage in reversed(self.stages[:-1]):
            vals = {c: stage.get(c, 0.0) for c in tied}
            if len(set(vals.values())) > 1:
                best = (max if pick_max else min)(vals.values())
                tied = [c for c in tied if vals[c] == best]
                if len(tied) == 1:
                    return tied[0]
        return tied[0] if len(tied) == 1 else self._lot(tied, pick_max)

    def exclude(self, candidates, totals: dict):
        """The candidate to exclude: fewest votes now, ties by rule 51."""
        candidates = list(candidates)
        low = min(totals.get(c, 0.0) for c in candidates)
        tied = [c for c in candidates if totals.get(c, 0.0) == low]
        return tied[0] if len(tied) == 1 else self._resolve(tied, pick_max=False)

    def order_desc(self, candidates, totals: dict) -> list:
        """Candidates from most to fewest votes, each run of equal totals ordered by rule 49."""
        remaining = list(candidates)
        out = []
        while remaining:
            high = max(totals.get(c, 0.0) for c in remaining)
            tied = [c for c in remaining if totals.get(c, 0.0) == high]
            first = tied[0] if len(tied) == 1 else self._resolve(tied, pick_max=True)
            out.append(first)
            remaining.remove(first)
        return out
