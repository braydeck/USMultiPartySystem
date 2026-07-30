"""Turn a list of draw results into the uncertainty payload the viz reads.

Three statistics per party, and they answer different questions:
  observed  the deterministic run on the real sample (regression anchor)
  modal     the most likely winner in each state, doubled — sums to chamber size
  expected  mean seat count across draws — also sums to chamber size, by linearity
"""

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
    out, means = {}, {}
    for p in parties:
        series = np.array([c.get(p, 0) * multiplier for c in per_draw_counts], dtype=float)
        means[p] = float(series.mean())
        out[p] = {
            "lo": int(np.percentile(series, 2.5)),
            "hi": int(np.percentile(series, 97.5)),
            "observed": int(observed_counts.get(p, 0) * multiplier),
        }
    for p, exp in _rounded_to_total(means, 2, sum(means.values())).items():
        out[p]["expected"] = exp
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
        shares = _rounded_to_total({k: v / n for k, v in dist.most_common()}, 4, 1.0,
                                   on=modal_party)
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
        # reaches the last round, wins, and wins given it got there.
        if entry["pModal"] < 0.70:
            entry["decomp"] = _decomp(draws, fips, method)
        states[fips] = entry

    per_draw = [Counter(_party(c) for c in d["senate"][method].values()) for d in draws]
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
    for c in slate:
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
    # House modal: per-party mode of its own seat-count distribution, then rescale the
    # largest party so the chamber sums exactly (modes of marginals need not sum).
    for p in parties:
        series = [c.get(p, 0) for c in hp]
        hseats[p]["modal"] = Counter(series).most_common(1)[0][0]
    total = sum(hseats[p]["modal"] for p in parties)
    target = sum(ho.values())
    if total != target and parties:
        biggest = max(parties, key=lambda p: hseats[p]["modal"])
        hseats[biggest]["modal"] += target - total
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
        tot = sum(c.values()) or 1
        modal = c.most_common(1)[0][0] if c else ""
        out["president"][method] = {
            "dist": _rounded_to_total({k: v / tot for k, v in c.most_common()}, 4, 1.0, on=modal)
                    if c else {},
            "observed": _party(observed["president"][method]),
            "modal": modal}
    return out
