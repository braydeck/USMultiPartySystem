"""Pick one real draw that produces a given winner and is typical of such draws.

Averaging across draws is not an option: round 3 cannot be averaged across draws
that eliminated different candidates in round 2, because the active sets differ, so
the tallies are not commensurable and transfers would not sum. Instead: narrow to
the most common slate, then the most common elimination order within it, then take
the medoid of that bucket.
"""

import copy
from collections import Counter

import numpy as np


def pick_representative(draws: list, fips: str, winner_party: str):
    wins = [d for d in draws
            if fips in d["senate"]["irv"]
            and d["senate"]["irv"][fips].rsplit("_", 1)[0] == winner_party]
    if not wins:
        return None

    # contests.py populates "paths" and "irv" for the same states in one loop, so a
    # winning draw always has a path entry here — but nothing enforces that across
    # files, so make the dependency explicit instead of failing on a bare KeyError.
    for d in wins:
        assert fips in d["senate"]["paths"], (
            f"{fips}: draw has an IRV winner but no matching paths entry")

    def slate_of(d):
        return tuple(d["senate"]["paths"][fips]["slate"])

    def elim_of(d):
        return tuple(d["senate"]["paths"][fips]["elim"])

    top_slate = Counter(slate_of(d) for d in wins).most_common(1)[0][0]
    in_slate = [d for d in wins if slate_of(d) == top_slate]
    top_elim = Counter(elim_of(d) for d in in_slate).most_common(1)[0][0]
    bucket = [d for d in in_slate if elim_of(d) == top_elim]

    # Medoid: the draw whose round-1 vote vector is closest to the bucket mean.
    keys = top_slate  # already sorted by contests.py when it built "slate"
    def vec(d):
        r1 = {c["code"]: c["pct"] for c in d["senate"]["paths"][fips]["rounds"][0]["candidates"]}
        return np.array([r1.get(k, 0.0) for k in keys])
    M = np.vstack([vec(d) for d in bucket])
    medoid = bucket[int(np.argmin(((M - M.mean(axis=0)) ** 2).sum(axis=1)))]

    p = medoid["senate"]["paths"][fips]
    # Deep-copy rounds (unlike the list-copied slate/elim) since it nests per-candidate
    # dicts; without this the caller shares mutable state with the source draw.
    return {"rounds": copy.deepcopy(p["rounds"]), "slate": list(p["slate"]),
            "elim": list(p["elim"]), "share": len(bucket) / len(wins)}
