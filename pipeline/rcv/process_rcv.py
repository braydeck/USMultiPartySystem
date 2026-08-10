#!/usr/bin/env python3
"""
Process a Cast Vote Record CSV from ME/AK election boards into IRV rounds,
Condorcet pairwise matrix, Ranked Pairs winner, and STV seats.

Usage:
    python pipeline/rcv/process_rcv.py \
        --cvr data/raw/rcv/AK_2022_house_general.csv \
        --race "US Representative" \
        --state AK --year 2022 --office US_HOUSE --seats 2

Output:
    data/outputs/rcv/AK_2022_US_HOUSE.json
"""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "outputs" / "rcv"


# ── Ballot parsing ──────────────────────────────────────────────────────────

def parse_cvr(path: Path, race_prefix: str) -> tuple[list[list[Optional[str]]], list[float]]:
    """Parse a CVR CSV into ballots + weights.
    rank columns are those whose header starts with race_prefix.
    Each ballot is a list of candidate names (None = skipped/overvote).
    """
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    rank_cols = [c for c in (rows[0].keys() if rows else []) if c.startswith(race_prefix)]
    if not rank_cols:
        raise ValueError(
            f"No rank columns found starting with '{race_prefix}'. "
            f"Available columns: {list(rows[0].keys())[:10]}"
        )

    ballots: list[list[Optional[str]]] = []
    weights: list[float] = []
    for row in rows:
        ballot: list[Optional[str]] = []
        for col in rank_cols:
            val = row.get(col, "").strip()
            if val.lower() in ("", "overvote", "undervote", "write-in"):
                ballot.append(None)
            else:
                ballot.append(val)
        # Trim trailing Nones
        while ballot and ballot[-1] is None:
            ballot.pop()
        if ballot:
            ballots.append(ballot)
            weights.append(1.0)

    return ballots, weights


# ── IRV ─────────────────────────────────────────────────────────────────────

def run_irv(ballots: list[list[Optional[str]]], weights: list[float]):
    """Run IRV (instant-runoff voting) to a single winner.
    Returns (winner, rounds) where each round = {round, totals, pcts, eliminated}.
    """
    active = list({c for b in ballots for c in b if c})
    if not active:
        return None, []

    current = [list(b) for b in ballots]  # mutable copy
    rounds = []
    round_num = 1

    while True:
        # Count first preferences
        totals: dict[str, float] = {c: 0.0 for c in active}
        total_weight = 0.0
        for b, w in zip(current, weights):
            for cand in b:
                if cand in totals:
                    totals[cand] += w
                    total_weight += w
                    break

        if total_weight == 0:
            break

        pcts = {c: t / total_weight for c, t in totals.items()}
        winner_cand = max(pcts, key=lambda c: pcts[c])

        if pcts[winner_cand] > 0.5 or len(active) == 1:
            rounds.append({
                "round": round_num,
                "totals": totals,
                "pcts": {c: round(p * 100, 2) for c, p in pcts.items()},
                "eliminated": None,
            })
            return winner_cand, rounds

        # Eliminate candidate with fewest votes
        loser = min(active, key=lambda c: totals.get(c, 0))
        rounds.append({
            "round": round_num,
            "totals": totals,
            "pcts": {c: round(p * 100, 2) for c, p in pcts.items()},
            "eliminated": loser,
        })

        active = [c for c in active if c != loser]
        for b in current:
            while loser in b:
                b.remove(loser)

        round_num += 1

    return None, rounds


# ── Condorcet ───────────────────────────────────────────────────────────────

def run_condorcet(ballots: list[list[Optional[str]]], weights: list[float], candidates: list[str]):
    """Compute pairwise win percentages. Returns (winner_or_None, matrix).
    matrix[a][b] = fraction of ballots ranking a above b.
    """
    n = len(candidates)
    wins = {a: {b: 0.0 for b in candidates} for a in candidates}
    total_w = sum(weights)

    for ballot, w in zip(ballots, weights):
        ranked = [c for c in ballot if c in candidates]
        for i, a in enumerate(ranked):
            for b in ranked[i + 1:]:
                wins[a][b] += w

    matrix = {
        a: {b: wins[a][b] / (wins[a][b] + wins[b][a]) if (wins[a][b] + wins[b][a]) > 0 else 0.5
            for b in candidates if b != a}
        for a in candidates
    }

    # Find Condorcet winner: beats all others head-to-head
    winner = None
    for a in candidates:
        if all(matrix[a].get(b, 0) > 0.5 for b in candidates if b != a):
            winner = a
            break

    return winner, matrix


# ── Ranked Pairs ────────────────────────────────────────────────────────────

def ranked_pairs_winner(matrix: dict[str, dict[str, float]], candidates: list[str]) -> Optional[str]:
    """Tideman Ranked Pairs: lock pairs from strongest to weakest, skip cycles."""
    pairs = []
    for a in candidates:
        for b in candidates:
            if a < b:
                pct_ab = matrix.get(a, {}).get(b, 0)
                pct_ba = matrix.get(b, {}).get(a, 0)
                if pct_ab > pct_ba:
                    pairs.append((pct_ab, a, b))
                elif pct_ba > pct_ab:
                    pairs.append((pct_ba, b, a))
    pairs.sort(reverse=True)

    locked: dict[str, set[str]] = {c: set() for c in candidates}

    def creates_cycle(winner_: str, loser_: str) -> bool:
        visited: set[str] = set()
        stack = [loser_]
        while stack:
            node = stack.pop()
            if node == winner_:
                return True
            if node in visited:
                continue
            visited.add(node)
            stack.extend(locked[node])
        return False

    for _, w, l in pairs:
        if not creates_cycle(w, l):
            locked[w].add(l)

    # Source node = no one locks over it
    for c in candidates:
        if not any(c in locked[w] for w in candidates):
            return c
    return None


# ── STV (BROKEN legacy — do not use) ────────────────────────────────────────

def run_stv(ballots: list[list[Optional[str]]], weights: list[float], candidates: list[str], seats: int):
    """BROKEN. Unused legacy routine, kept only pending a decision to delete it.

    Nothing imports this module; the live RCV path is process_dominion_cvr.run_stv,
    which is a correct Droop-quota Weighted Inclusive Gregory count. Three defects
    here, so do not resurrect it without a rewrite:

      - eliminated candidates are appended to `elected`, so losers appear as winners;
      - `active.discard(top)` runs on the elimination branch too, dropping the
        current leader alongside the eliminated candidate;
      - the loop runs exactly `seats` times, so every elimination consumes a seat.

    The surplus arithmetic itself is the right shape (scale each contributing
    ballot's current weight by (votes - quota) / votes), but the surrounding
    round structure is not.
    """
    if seats >= len(candidates):
        return candidates[:]

    n_ballots = sum(weights)
    quota = n_ballots / (seats + 1) + 1  # Droop quota

    # Each ballot has a weight (starts at 1.0)
    current = [(list(b), w) for b, w in zip(ballots, weights)]
    elected: list[str] = []
    active = set(candidates)

    for _ in range(seats):
        if not active:
            break
        # Count
        counts: dict[str, float] = {c: 0.0 for c in active}
        for b, w in current:
            for c in b:
                if c in active:
                    counts[c] += w
                    break

        top = max(counts, key=lambda c: counts[c])

        if counts[top] >= quota:
            elected.append(top)
            surplus_ratio = (counts[top] - quota) / counts[top] if counts[top] > 0 else 0
            new_current = []
            for b, w in current:
                idx = next((i for i, c in enumerate(b) if c in active), None)
                if idx is not None and b[idx] == top:
                    new_b = b[idx + 1:]
                    new_w = w * surplus_ratio
                    if new_b:
                        new_current.append((new_b, new_w))
                else:
                    new_current.append((b, w))
            current = new_current
        else:
            # Eliminate lowest
            loser = min(active, key=lambda c: counts.get(c, 0))
            elected.append(loser)  # still records them
            active.remove(loser)
            current = [(b, w) for b, w in current]

        active.discard(top)

    return elected[:seats]


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cvr",   required=True,  help="Path to CVR CSV file")
    parser.add_argument("--race",  required=True,  help="Race column prefix in CVR headers")
    parser.add_argument("--state", required=True,  choices=["AK", "ME"])
    parser.add_argument("--year",  required=True,  type=int)
    parser.add_argument("--office", required=True, choices=["US_HOUSE", "US_SENATE", "GOVERNOR"])
    parser.add_argument("--seats", type=int, default=None, help="Seats for STV (House races only)")
    args = parser.parse_args()

    print(f"Parsing {args.cvr} …")
    cvr_path = Path(args.cvr)
    ballots, weights = parse_cvr(cvr_path, args.race)
    print(f"  {len(ballots):,} ballots loaded")

    # Collect all candidates (non-None names seen in ballots)
    cand_counts: Counter = Counter()
    for b in ballots:
        for c in b:
            if c:
                cand_counts[c] += 1
    candidates = [c for c, _ in cand_counts.most_common()]
    print(f"  Candidates: {candidates}")

    # IRV
    irv_winner, irv_rounds = run_irv(ballots, weights)
    print(f"  IRV winner: {irv_winner}")

    # Condorcet
    cond_winner, cond_matrix = run_condorcet(ballots, weights, candidates)
    rp_winner = ranked_pairs_winner(cond_matrix, candidates)
    print(f"  Condorcet winner: {cond_winner} (Ranked Pairs: {rp_winner})")

    # STV (house races only)
    stv_seats = args.seats
    stv_elected = None
    if stv_seats and args.office == "US_HOUSE":
        doubled = stv_seats * 2
        stv_elected = run_stv(ballots, weights, candidates, doubled)
        print(f"  STV ({doubled} seats): {stv_elected}")

    # Serialize rounds (convert float keys to strings for JSON)
    def serialize_rounds(rounds):
        out = []
        for r in rounds:
            out.append({
                "round":      r["round"],
                "totals":     {k: round(v) for k, v in r["totals"].items()},
                "pcts":       r["pcts"],
                "eliminated": r["eliminated"],
            })
        return out

    result = {
        "state":          args.state,
        "year":           args.year,
        "office":         args.office,
        "candidates":     candidates,
        "totalBallots":   len(ballots),
        "irvRounds":      serialize_rounds(irv_rounds),
        "irvWinner":      irv_winner,
        "condorcetMatrix": {
            a: {b: round(v, 4) for b, v in row.items()}
            for a, row in cond_matrix.items()
        },
        "condorcetWinner":    cond_winner,
        "rankedPairsWinner":  rp_winner,
        "irvMatchesCondorcet": irv_winner == cond_winner,
    }
    if stv_seats is not None:
        result["stvSeats"] = stv_seats * 2 if args.office == "US_HOUSE" else stv_seats
        result["stvElected"] = stv_elected or []

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{args.state}_{args.year}_{args.office}.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"  Written → {out_path}")


if __name__ == "__main__":
    main()
