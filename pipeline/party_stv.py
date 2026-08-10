"""
party_stv.py
------------
Multi-seat STV engine where parties can win multiple seats.

In standard STV, elected candidates are removed. Here, elected parties
stay active — their surplus transfers but they can win additional seats
if they accumulate enough votes again. This models party-slate STV where
a dominant party earns proportional representation.

Also provides single-seat IRV and Condorcet utilities for general elections.
"""

import numpy as np
from collections import defaultdict


def first_surviving_choice(ballots: np.ndarray, active: set,
                           party_codes: list) -> np.ndarray:
    """For each ballot, find the first party in the ranking that's still active.

    ballots: (N, M) int8 array of party indices
    active: set of party indices (ints)
    Returns: (N,) array of party indices (-1 = exhausted)
    """
    N, M = ballots.shape
    result = np.full(N, -1, dtype=np.int32)
    for i in range(N):
        for j in range(M):
            if int(ballots[i, j]) in active:
                result[i] = int(ballots[i, j])
                break
    return result


def run_multi_seat_stv(ballots: np.ndarray, weights: np.ndarray,
                       n_parties: int, n_seats: int,
                       party_codes: list = None) -> dict:
    """Run Weighted Inclusive Gregory STV where parties can win multiple seats.

    Every ballot the winner holds transfers, each scaled by its own current value, so a
    ballot's weight only ever shrinks and no ballot exceeds the one vote it started with.

    Args:
        ballots:     (N, M) int8 array — party indices at each rank
        weights:     (N,) float — voter weights
        n_parties:   number of parties (M)
        n_seats:     target seat count
        party_codes: list of party code strings (for labeling)

    Returns dict with:
        seats:        {party_idx: n_seats_won}
        eliminated:   list of party indices in elimination order
        rounds:       list of {party_idx: vote_total} per round
    """
    if party_codes is None:
        party_codes = [str(i) for i in range(n_parties)]

    active      = set(range(n_parties))
    ballot_wts  = weights.astype(np.float64).copy()
    total_votes = float(weights.sum())
    quota       = total_votes / (n_seats + 1) + 1e-6
    seats_won   = defaultdict(int)
    total_elected = 0
    eliminated  = []
    rounds      = []
    won_seat    = set()  # parties that have won at least 1 seat

    max_rounds = n_parties * n_seats + 100  # safety limit

    for _ in range(max_rounds):
        if total_elected >= n_seats or not active:
            break

        remaining = n_seats - total_elected

        # Only shortcut when remaining seats ≤ remaining eliminable parties
        # (i.e., every remaining party gets at least 1 seat, no more eliminations possible)
        eliminable = [p for p in active if p not in won_seat]
        if remaining <= len(active) and len(eliminable) == 0:
            # All active parties already have seats — distribute remaining to strongest
            fsc = first_surviving_choice(ballots, active, party_codes)
            totals = {p: 0.0 for p in active}
            for i in range(len(fsc)):
                if fsc[i] in totals:
                    totals[fsc[i]] += ballot_wts[i]
            for p, _ in sorted(totals.items(), key=lambda x: -x[1]):
                if total_elected >= n_seats:
                    break
                seats_won[p] += 1
                total_elected += 1
            break
        if remaining <= len(eliminable) and remaining <= len(active):
            # Give remaining eliminable parties 1 seat each
            for p in sorted(active, key=lambda x: x):
                if seats_won[p] == 0:
                    seats_won[p] = 1
                    total_elected += 1
                    if total_elected >= n_seats:
                        break
            break

        # Count first-surviving-choice votes
        fsc = first_surviving_choice(ballots, active, party_codes)
        totals = {p: 0.0 for p in active}
        for i in range(len(fsc)):
            p = fsc[i]
            if p in totals:
                totals[p] += ballot_wts[i]

        rounds.append({party_codes[p]: totals.get(p, 0.0) for p in active})

        # Check for quota winners
        over = sorted(
            [(p, totals[p]) for p in active if totals[p] >= quota],
            key=lambda x: -x[1]
        )

        if over:
            winner, votes = over[0]
            surplus_frac = (votes - quota) / votes
            seats_won[winner] += 1
            won_seat.add(winner)
            total_elected += 1

            # Apply surplus transfer
            for i in range(len(fsc)):
                if fsc[i] == winner:
                    ballot_wts[i] *= surplus_frac
        else:
            # Eliminate weakest party (only from parties with 0 seats)
            eliminable = [p for p in active if p not in won_seat]
            if not eliminable:
                # All active parties have seats — give remaining seats to strongest
                for p, _ in sorted(totals.items(), key=lambda x: -x[1]):
                    if total_elected >= n_seats:
                        break
                    seats_won[p] += 1
                    total_elected += 1
                break

            weakest = min(eliminable, key=lambda p: (totals.get(p, 0), p))
            active.discard(weakest)
            eliminated.append(weakest)

    return {
        "seats": dict(seats_won),
        "eliminated": eliminated,
        "rounds": rounds,
        "quota": quota,
    }


def expand_slots(seats: dict, party_codes: list) -> list:
    """Expand {party_idx: n_seats} into a list of slot labels.

    E.g., {0: 2, 1: 1} → ["CON_1", "CON_2", "LBR_1"]
    """
    slots = []
    for p_idx in sorted(seats.keys()):
        n = seats[p_idx]
        code = party_codes[p_idx]
        if n == 1:
            slots.append(code)
        else:
            for k in range(1, n + 1):
                slots.append(f"{code}_{k}")
    return slots


# ── Single-winner IRV (for general elections) ────────────────────────────────

def run_irv(ballots: np.ndarray, weights: np.ndarray,
            candidates: set, party_codes: list) -> dict:
    """Run IRV among a set of candidate party indices. Returns winner and rounds."""
    active      = set(candidates)
    ballot_wts  = weights.astype(np.float64).copy()
    total_votes = float(weights.sum())
    rounds_data = []
    eliminated  = []

    while len(active) > 1:
        fsc = first_surviving_choice(ballots, active, party_codes)
        totals = {p: 0.0 for p in active}
        for i in range(len(fsc)):
            p = fsc[i]
            if p in totals:
                totals[p] += ballot_wts[i]

        rounds_data.append({party_codes[p]: totals[p] for p in active})

        # Check majority
        for p, v in totals.items():
            if v > total_votes / 2:
                return {"winner": p, "rounds": rounds_data, "eliminated": eliminated}

        # Eliminate weakest
        weakest = min(active, key=lambda p: (totals[p], p))
        active.discard(weakest)
        eliminated.append(weakest)

    winner = active.pop() if active else -1
    return {"winner": winner, "rounds": rounds_data, "eliminated": eliminated}


# ── Condorcet (Ranked Pairs / Tideman) ───────────────────────────────────────

def condorcet_matchups(ballots: np.ndarray, weights: np.ndarray,
                       candidates: list, party_codes: list) -> dict:
    """Compute pairwise matchups among candidate party indices.

    Returns dict with 'matchups' (list of dicts) and 'winner' (party index or None).
    """
    n = len(candidates)
    cand_set = set(candidates)

    # Build rank lookup per ballot
    N, M = ballots.shape
    # For each ballot, which rank does each candidate have?
    pairwise = np.zeros((n, n), dtype=np.float64)

    for i in range(N):
        w = weights[i]
        ranks = {}
        for r in range(M):
            p = int(ballots[i, r])
            if p in cand_set:
                ranks[p] = r
        for ai, a in enumerate(candidates):
            for bi, b in enumerate(candidates):
                if a == b:
                    continue
                ra = ranks.get(a, M)
                rb = ranks.get(b, M)
                if ra < rb:  # a ranked higher (lower number = better)
                    pairwise[ai, bi] += w

    # Ranked Pairs (Tideman)
    margins = []
    matchups = []
    for ai, a in enumerate(candidates):
        for bi, b in enumerate(candidates):
            if ai >= bi:
                continue
            va = pairwise[ai, bi]
            vb = pairwise[bi, ai]
            margins.append((ai, bi, va - vb, va, vb))
            matchups.append({
                "a": party_codes[a],
                "b": party_codes[b],
                "votes_a": float(va),
                "votes_b": float(vb),
                "margin": float(va - vb),
            })

    # Sort by absolute margin descending
    margins.sort(key=lambda x: -abs(x[2]))

    # Lock pairs (simple cycle detection via graph reachability)
    locked = set()
    graph = defaultdict(set)

    def has_path(start, end):
        visited = set()
        stack = [start]
        while stack:
            node = stack.pop()
            if node == end:
                return True
            if node in visited:
                continue
            visited.add(node)
            stack.extend(graph[node])
        return False

    for ai, bi, margin, va, vb in margins:
        if margin > 0:
            winner_i, loser_i = ai, bi
        elif margin < 0:
            winner_i, loser_i = bi, ai
        else:
            continue
        if not has_path(loser_i, winner_i):
            graph[winner_i].add(loser_i)
            locked.add((winner_i, loser_i))

    # Winner = candidate with no losses in locked set
    losers = {loser for _, loser in locked}
    winners = [i for i in range(n) if i not in losers]
    rp_winner = candidates[winners[0]] if len(winners) == 1 else None

    return {
        "matchups": matchups,
        "winner": rp_winner,
        "pairwise": pairwise,
    }
