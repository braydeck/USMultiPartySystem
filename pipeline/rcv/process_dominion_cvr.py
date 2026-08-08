#!/usr/bin/env python3
"""
Process a Dominion ``CVR_Export`` directory (Alaska Division of Elections) into
IRV rounds, a Condorcet pairwise matrix, the Ranked Pairs winner, and
multi-seat STV — all from ballot-level rankings.

Alaska publishes the full cast vote record for every RCV general election, so
every number this script emits is computed from real ballots rather than
reconstructed from published round summaries.

Data sources (download + unzip before running):
  2022 general  https://elections.alaska.gov/results/22GENR/rcv/CVR_Export.zip
  2024 general  https://www.elections.alaska.gov/results/24GENR/CVR_Export_20241130154411.zip

Usage:
    python pipeline/rcv/process_dominion_cvr.py \
        --cvr-dir data/raw/rcv/AK_2022_general \
        --contest "U.S. Representative" \
        --state AK --year 2022 --office US_HOUSE \
        --race-name "Alaska At-Large" --stv-seats 2

Output:
    data/outputs/rcv/AK_2022_US_HOUSE.json

Tabulation rules follow Alaska statute (AS 15.15.350) as implemented by the
Division of Elections: an overvote exhausts the ballot at that rank, a single
skipped rank is passed over, and two consecutive skipped ranks exhaust the
ballot. Duplicate rankings of the same candidate are ignored after the first.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidates import relabel  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = REPO_ROOT / "data" / "outputs" / "rcv"

Ballot = tuple[str, ...]


# ── Dominion CVR parsing ────────────────────────────────────────────────────

def load_contest(cvr_dir: Path, contest_desc: str) -> tuple[list[Ballot], list[str], int]:
    """Extract ranked ballots for one contest from a Dominion CVR export.

    Returns (ballots, candidate_names_by_first_choice_volume, ballots_containing_contest).
    A ballot is a tuple of candidate names in preference order; empty tuples are
    kept out of the returned list but still counted in the contest total, since
    undervoted ballots are part of the published denominator.
    """
    contests = json.loads((cvr_dir / "ContestManifest.json").read_text())["List"]
    match = [c for c in contests if c["Description"].strip().lower() == contest_desc.strip().lower()]
    if not match:
        available = sorted(c["Description"] for c in contests)
        raise SystemExit(f"Contest {contest_desc!r} not found. Available:\n  " + "\n  ".join(available))
    contest_id = match[0]["Id"]
    max_rank = match[0].get("NumOfRanks") or 5

    cand_names = {
        c["Id"]: c["Description"]
        for c in json.loads((cvr_dir / "CandidateManifest.json").read_text())["List"]
        if c["ContestId"] == contest_id
    }

    ballots: list[Ballot] = []
    n_with_contest = 0

    for path in sorted(cvr_dir.glob("CvrExport*.json")):
        for session in json.loads(path.read_text())["Sessions"]:
            # Adjudicated ballots carry a "Modified" record that supersedes "Original".
            record = session.get("Modified") or session["Original"]
            for card in record.get("Cards", []):
                for contest in card.get("Contests", []):
                    if contest["Id"] != contest_id:
                        continue
                    n_with_contest += 1
                    by_rank: dict[int, list[str]] = {}
                    for mark in contest.get("Marks", []):
                        if mark.get("IsAmbiguous"):
                            continue
                        name = cand_names.get(mark["CandidateId"])
                        if name is not None:
                            by_rank.setdefault(mark["Rank"], []).append(name)
                    ballots.append(_read_rankings(by_rank, max_rank))

    order = Counter(b[0] for b in ballots if b)
    for b in ballots:  # candidates appearing only as lower preferences
        for c in b:
            order.setdefault(c, 0)
    candidates = [c for c, _ in order.most_common()]
    return [b for b in ballots if b], candidates, n_with_contest


def _read_rankings(by_rank: dict[int, list[str]], max_rank: int) -> Ballot:
    out: list[str] = []
    consecutive_skips = 0
    for rank in range(1, max_rank + 1):
        marks = by_rank.get(rank, [])
        if len(marks) > 1:
            break  # overvote exhausts the ballot here
        if not marks:
            consecutive_skips += 1
            if consecutive_skips >= 2:
                break
            continue
        consecutive_skips = 0
        if marks[0] not in out:
            out.append(marks[0])
    return tuple(out)


# ── IRV ─────────────────────────────────────────────────────────────────────

def run_irv(ballots: list[Ballot], candidates: list[str],
            batch_eliminate: bool = False) -> tuple[Optional[str], list[dict]]:
    """Single-winner IRV.

    Alaska eliminates one candidate per round; Maine batch-eliminated the trailing
    candidates who could not mathematically overtake the next candidate up (2018
    CD2). ``batch_eliminate`` selects the latter so reported rounds match the
    state's own tabulation.
    """
    active = set(candidates)
    rounds: list[dict] = []

    while True:
        totals = {c: 0 for c in active}
        for b in ballots:
            top = next((c for c in b if c in active), None)
            if top is not None:
                totals[top] += 1
        continuing = sum(totals.values())
        if continuing == 0:
            return None, rounds

        ranked = sorted(active, key=lambda c: -totals[c])
        leader = ranked[0]
        pcts = {c: totals[c] / continuing * 100 for c in active}

        if pcts[leader] > 50 or len(active) <= 1:
            rounds.append(_round(len(rounds) + 1, totals, pcts, [], continuing))
            return leader, rounds

        doomed = _batch_eliminate(ranked, totals) if batch_eliminate else [ranked[-1]]
        rounds.append(_round(len(rounds) + 1, totals, pcts, doomed, continuing))
        active -= set(doomed)


def _batch_eliminate(ranked: list[str], totals: dict[str, int]) -> list[str]:
    """Largest suffix of the standing whose combined votes still trail the next
    candidate up. Falls back to eliminating the single last-place candidate."""
    for cut in range(1, len(ranked)):
        tail = ranked[cut:]
        if sum(totals[c] for c in tail) < totals[ranked[cut - 1]]:
            return tail
    return [ranked[-1]]


def _round(num: int, totals: dict[str, int], pcts: dict[str, float],
           eliminated: list[str], continuing: int) -> dict:
    return {
        "round": num,
        "totals": dict(sorted(totals.items(), key=lambda kv: -kv[1])),
        "pcts": {c: round(p, 2) for c, p in sorted(pcts.items(), key=lambda kv: -kv[1])},
        "eliminated": eliminated,
        "continuingBallots": continuing,
    }


# ── Condorcet ───────────────────────────────────────────────────────────────

def run_condorcet(ballots: list[Ballot], candidates: list[str]):
    """Pairwise preference matrix over ballots that express a preference between
    each pair. matrix[a][b] = share of those ballots ranking a above b."""
    prefer = {a: Counter() for a in candidates}
    for b in ballots:
        for i, a in enumerate(b):
            for c in b[i + 1:]:
                prefer[a][c] += 1
        # A ranked candidate beats every unranked one.
        ranked = set(b)
        for a in b:
            for c in candidates:
                if c not in ranked:
                    prefer[a][c] += 1

    matrix, counts = {}, {}
    for a in candidates:
        matrix[a], counts[a] = {}, {}
        for b in candidates:
            if a == b:
                continue
            ab, ba = prefer[a][b], prefer[b][a]
            matrix[a][b] = ab / (ab + ba) if ab + ba else 0.5
            counts[a][b] = ab

    winner = next(
        (a for a in candidates
         if all(matrix[a][b] > 0.5 for b in candidates if b != a)),
        None,
    )
    return winner, matrix, counts


def ranked_pairs_winner(matrix: dict[str, dict[str, float]], candidates: list[str]) -> Optional[str]:
    """Tideman Ranked Pairs: lock the strongest pairwise victories first, skipping
    any that would close a cycle."""
    pairs = []
    for i, a in enumerate(candidates):
        for b in candidates[i + 1:]:
            if matrix[a][b] > matrix[b][a]:
                pairs.append((matrix[a][b], a, b))
            elif matrix[b][a] > matrix[a][b]:
                pairs.append((matrix[b][a], b, a))
    pairs.sort(key=lambda p: -p[0])

    locked: dict[str, set[str]] = {c: set() for c in candidates}

    def reaches(src: str, dst: str) -> bool:
        seen, stack = set(), [src]
        while stack:
            node = stack.pop()
            if node == dst:
                return True
            if node in seen:
                continue
            seen.add(node)
            stack.extend(locked[node])
        return False

    for _, win, lose in pairs:
        if not reaches(lose, win):
            locked[win].add(lose)

    return next((c for c in candidates if not any(c in locked[w] for w in candidates)), None)


# ── STV (Weighted Inclusive Gregory) ────────────────────────────────────────

def run_stv(ballots: list[Ballot], candidates: list[str], seats: int) -> tuple[list[str], list[dict]]:
    """Droop-quota STV with Weighted Inclusive Gregory surplus transfers.
    Returns (elected_in_order, rounds) where each round records the standing."""
    quota = len(ballots) / (seats + 1)
    weighted = [[list(b), 1.0] for b in ballots]
    elected: list[str] = []
    active = set(candidates)
    rounds: list[dict] = []

    while len(elected) < seats and active:
        counts = {c: 0.0 for c in active}
        for ranking, weight in weighted:
            top = next((c for c in ranking if c in active), None)
            if top is not None:
                counts[top] += weight

        leader = max(counts, key=lambda c: counts[c])
        if counts[leader] >= quota or len(active) <= seats - len(elected):
            seated, surplus_ratio = leader, 0.0
            if counts[leader] > quota:
                surplus_ratio = (counts[leader] - quota) / counts[leader]
            rounds.append({
                "elected": seated,
                "votes": round(counts[seated], 1),
                "quota": round(quota, 1),
                "counts": {c: round(v, 1) for c, v in sorted(counts.items(), key=lambda kv: -kv[1])},
            })
            elected.append(seated)
            active.discard(seated)
            for entry in weighted:
                if next((c for c in entry[0] if c in active or c == seated), None) == seated:
                    entry[1] *= surplus_ratio
        else:
            loser = min(counts, key=lambda c: counts[c])
            rounds.append({
                "eliminated": loser,
                "votes": round(counts[loser], 1),
                "quota": round(quota, 1),
                "counts": {c: round(v, 1) for c, v in sorted(counts.items(), key=lambda kv: -kv[1])},
            })
            active.discard(loser)

    return elected, rounds


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cvr-dir", required=True, type=Path)
    ap.add_argument("--contest", required=True)
    ap.add_argument("--state", required=True, choices=["AK", "ME"])
    ap.add_argument("--year", required=True, type=int)
    ap.add_argument("--office", required=True, choices=["US_HOUSE", "US_SENATE", "GOVERNOR", "PRESIDENT"])
    ap.add_argument("--race-name", required=True)
    ap.add_argument("--race-id", default=None, help="Output filename stem (defaults to STATE_YEAR_OFFICE)")
    ap.add_argument("--stv-seats", type=int, default=None,
                    help="Actual seats; STV is run at double this (the simulation's doubled-House size)")
    ap.add_argument("--source", default="", help="URL of the CVR export, recorded in the output")
    ap.add_argument("--batch-eliminate", action="store_true",
                    help="Eliminate all mathematically-eliminated trailing candidates at once (Maine's rule)")
    args = ap.parse_args()

    ballots, candidates, n_contest = load_contest(args.cvr_dir, args.contest)
    print(f"{args.race_name}: {n_contest:,} ballots in contest, {len(ballots):,} with a valid first choice")
    print(f"  candidates: {candidates}")

    irv_winner, irv_rounds = run_irv(ballots, candidates, batch_eliminate=args.batch_eliminate)
    cond_winner, cond_matrix, cond_counts = run_condorcet(ballots, candidates)
    rp_winner = ranked_pairs_winner(cond_matrix, candidates)
    print(f"  IRV: {irv_winner} in {len(irv_rounds)} rounds | Condorcet: {cond_winner} | Ranked Pairs: {rp_winner}")
    for r in irv_rounds:
        print(f"    R{r['round']}: " + ", ".join(f"{c} {p}%" for c, p in r["pcts"].items())
              + (f"  ✗ {', '.join(r['eliminated'])}" if r["eliminated"] else ""))

    result = {
        "state": args.state,
        "year": args.year,
        "office": args.office,
        "contestType": "GENERAL",
        "raceName": args.race_name,
        "district": None,
        "candidates": candidates,
        "totalBallots": n_contest,
        "activeBallots": len(ballots),
        "irvRounds": irv_rounds,
        "irvWinner": irv_winner,
        "condorcetMatrix": {a: {b: round(v, 4) for b, v in row.items()} for a, row in cond_matrix.items()},
        "condorcetCounts": cond_counts,
        "condorcetWinner": cond_winner,
        "rankedPairsWinner": rp_winner,
        "irvMatchesCondorcet": irv_winner == cond_winner,
        "pluralityWinner": candidates[0],
        "irvMatchesPlurality": irv_winner == candidates[0],
        "provenance": args.source or "Dominion CVR export",
    }

    if args.stv_seats:
        doubled = args.stv_seats * 2
        stv_elected, stv_rounds = run_stv(ballots, candidates, doubled)
        result["stvSeats"] = doubled
        result["stvElected"] = stv_elected
        result["stvRounds"] = stv_rounds
        print(f"  STV at {doubled} seats: {stv_elected}")

    relabel(result)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = args.race_id or f"{args.state}_{args.year}_{args.office}"
    out = OUTPUT_DIR / f"{stem}.json"
    out.write_text(json.dumps(result, indent=2))
    print(f"  → {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
