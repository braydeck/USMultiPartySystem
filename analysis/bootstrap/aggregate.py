"""Turn a list of draw results into the uncertainty payload the viz reads.

Three statistics per party, and they answer different questions:
  observed  the deterministic run on the real sample (regression anchor)
  modal     the most likely winner in each state, doubled — sums to chamber size
  expected  mean seat count across draws — also sums to chamber size, by linearity
"""

import math
from collections import Counter

import numpy as np

from .representative import pick_representative

SENATE_MULTIPLIER = 2  # one winner per state fills both of that state's seats


def _party(code):
    return code.rsplit("_", 1)[0] if code else ""


def _rounded_to_total(values: dict, places: int, total: float, on=None) -> dict:
    """Round each value to `places` while keeping the group's exact total.

    Rounding independently breaks both sums the viz relies on: a state's `dist` reading as
    a probability distribution, and expected seats summing to the chamber size by linearity
    of expectation. With 12 draws, 15 of 102 senate races round to 0.9999 or 1.0001. Park
    the residual on `on` (default: the largest value), where a rounding unit is invisible.
    """
    out = {k: round(v, places) for k, v in values.items()}
    if out:
        sink = on if on in out else max(out, key=lambda k: out[k])
        # Re-round to clear the binary-float dust the correction leaves behind. The residual
        # is itself a multiple of 10**-places whenever `total` is (1.0, or an integer
        # chamber size), so the corrected value stays at `places` decimals.
        out[sink] = round(out[sink] + (total - sum(out.values())), 10)
    return out


def _seat_stats(per_draw_counts, parties, observed_counts, multiplier=1):
    out, means, series = {}, {}, {}
    for p in parties:
        series[p] = np.array([c.get(p, 0) * multiplier for c in per_draw_counts], dtype=float)
        means[p] = float(series[p].mean())
    expected = _rounded_to_total(means, 2, sum(means.values()))
    for p in parties:
        # Floor the low end and ceil the high end: truncating both with int() narrows every
        # interval at the top by up to a seat. Then widen `hi` to cover `expected`, because
        # a party winning seats in under 2.5% of draws gets lo=hi=0 with expected>0, and the
        # viz draws `expected` as the centre dot of this span.
        # `modal` may still legitimately fall outside [lo, hi]: the modal chamber is
        # assembled from independent per-state argmaxes, so it is not a sampled chamber and
        # has no reason to lie inside a sampled interval. The viz shows it as its own tick —
        # do not "fix" this by clamping modal into the interval.
        out[p] = {
            "lo": int(np.floor(np.percentile(series[p], 2.5))),
            "hi": max(int(np.ceil(np.percentile(series[p], 97.5))), math.ceil(expected[p])),
            "observed": int(observed_counts.get(p, 0) * multiplier),
            "expected": expected[p],
        }
    return out


def _senate_block(draws, observed, method):
    fips_list = sorted(observed["senate"][method])
    states, modal_counts = {}, Counter()
    for fips in fips_list:
        winners = [_party(d["senate"][method][fips]) for d in draws if fips in d["senate"][method]]
        dist = Counter(winners)
        n = sum(dist.values())
        obs_code = observed["senate"][method][fips]
        # Tie-break toward the observed winner so real data wins where draws are indifferent.
        best = max(dist.items(), key=lambda kv: (kv[1], kv[0] == _party(obs_code)))
        modal_party = best[0]
        modal_counts[modal_party] += 1
        # Read pModal/pObserved back out of the corrected dist so the three cannot disagree.
        raw = {k: v / n for k, v in dist.most_common()}
        shares = _rounded_to_total(raw, 4, 1.0, on=modal_party)
        if shares[modal_party] < max(shares.values()):
            # A negative rounding residual can push the sink below a tied peer, and the viz
            # reads pModal as the peak of dist. Park the residual on the next party that
            # keeps the modal maximal.
            for alt in sorted(raw, key=lambda k: -raw[k]):
                cand = _rounded_to_total(raw, 4, 1.0, on=alt)
                if cand[modal_party] >= max(cand.values()):
                    shares = cand
                    break
        entry = {
            "observed": obs_code,
            "modal": modal_party,
            "pModal": shares[modal_party],
            "pObserved": shares.get(_party(obs_code), 0.0),
            "dist": shares,
            "substituted": _party(obs_code) != modal_party,
        }
        if entry["substituted"] and method == "irv":
            rep = pick_representative(draws, fips, modal_party)
            if rep:
                entry["repRounds"] = rep["rounds"]
                entry["repShare"] = round(rep["share"], 4)
        # Decomposition for close races: how often each party makes the slate,
        # reaches the last round, wins, and wins given it got there. IRV only, like
        # repRounds: it reads the recorded IRV elimination path, so pairing it with the
        # Condorcet winner would splice two elimination models.
        if entry["pModal"] < 0.70 and method == "irv":
            entry["decomp"] = _decomp(draws, fips, method)
        states[fips] = entry

    # Count seats over the observed fips set only, the same set `states`/`modal_counts` use:
    # a draw carrying an extra state would otherwise inflate `expected` past the chamber.
    per_draw = [Counter(_party(d["senate"][method][f]) for f in fips_list
                        if f in d["senate"][method]) for d in draws]
    obs_counts = Counter(_party(c) for c in observed["senate"][method].values())
    parties = sorted({p for c in per_draw for p in c} | set(obs_counts) | set(modal_counts))
    seats = _seat_stats(per_draw, parties, obs_counts, SENATE_MULTIPLIER)
    for p in parties:
        seats[p]["modal"] = modal_counts.get(p, 0) * SENATE_MULTIPLIER
    return {
        "seats": seats,
        "states": states,
        "nSubstituted": sum(1 for s in states.values() if s["substituted"]),
        "nBelow50": sum(1 for s in states.values() if s["pModal"] < 0.50),
    }


def _decomp(draws, fips, method):
    slate = Counter(); final = Counter(); win = Counter(); win_given = Counter()
    n = 0
    for d in draws:
        p = d["senate"]["paths"].get(fips)
        if not p:
            continue
        n += 1
        w = _party(d["senate"][method][fips])
        win[w] += 1
        for c in {_party(x) for x in p["slate"]}:
            slate[c] += 1
        last = {_party(c["code"]) for c in p["rounds"][-1]["candidates"]}
        for c in last:
            final[c] += 1
        if w in last:
            win_given[w] += 1
    out = {}
    # Emit in descending win probability. `slate` is filled by iterating sets of party codes,
    # so its own insertion order follows randomised string hashing — sorting is what makes the
    # payload byte-reproducible across processes, and it puts the likely winner first for a
    # viz that reads these positionally.
    for c in sorted(slate, key=lambda k: (-win.get(k, 0), -slate[k], k)):
        out[c] = {
            "slate": round(slate[c] / n, 4),
            "final": round(final.get(c, 0) / n, 4),
            "win": round(win.get(c, 0) / n, 4),
            "winIfFinal": round(win_given.get(c, 0) / final[c], 4) if final.get(c) else None,
        }
    return out


def build_uncertainty(draws, observed, n_draws, seed):
    out = {"nDraws": n_draws, "seed": seed, "senate": {}}
    for method in ("cond", "irv"):
        out["senate"][method] = _senate_block(draws, observed, method)

    hp = [Counter(d["house"]) for d in draws]
    ho = Counter(observed["house"])
    parties = sorted({p for c in hp for p in c} | set(ho))
    hseats = _seat_stats(hp, parties, ho)
    # House modal: per-party mode of its own seat-count distribution. Modes of marginals
    # need not sum to the chamber, and because skewed marginals systematically undershoot
    # their means the shortfall is large (~20 seats). Apportion it by largest remainder over
    # `expected` rather than dumping it all on the largest party: over synthetic 1000-draw
    # chambers that single sink landed 16-22 seats above its own mode, which no longer
    # describes anything "most likely".
    for p in parties:
        series = [c.get(p, 0) for c in hp]
        hseats[p]["modal"] = Counter(series).most_common(1)[0][0]
    residual = sum(ho.values()) - sum(hseats[p]["modal"] for p in parties)
    step = 1 if residual > 0 else -1
    for _ in range(abs(residual)):
        cands = [p for p in parties if step > 0 or hseats[p]["modal"] > 0]
        if not cands:
            break
        # Give the seat to the party whose mode most understates its mean (or take it from
        # the one that most overstates it), so no party moves far from its own mode.
        pick = max(cands, key=lambda p: step * (hseats[p]["expected"] - hseats[p]["modal"]))
        hseats[pick]["modal"] += step
    out["house"] = {"seats": hseats}

    slate = Counter()
    for d in draws:
        for c in d["primary"]:
            slate[c] += 1
    out["primary"] = {"slate": {k: round(v / len(draws), 4) for k, v in slate.most_common()},
                      "observedSlate": observed["primary"]}

    out["president"] = {}
    for method in ("irv", "cond"):
        c = Counter(_party(d["president"][method]) for d in draws if d["president"][method])
        tot = sum(c.values())
        modal = c.most_common(1)[0][0] if c else ""
        # `dist` is conditional on the contest resolving — a Condorcet cycle leaves `cond`
        # empty — so publish the denominator too, or a cycle rate reads as certainty.
        out["president"][method] = {
            "dist": _rounded_to_total({k: v / tot for k, v in c.most_common()}, 4, 1.0, on=modal)
                    if c else {},
            "observed": _party(observed["president"][method]),
            "modal": modal,
            "nResolved": tot}
    return out
