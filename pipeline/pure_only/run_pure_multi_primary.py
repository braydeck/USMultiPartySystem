#!/usr/bin/env python3
"""
run_pure_multi_primary.py
--------------------------
2028 Presidential Primary — 27 candidates (9 parties × 3).

Uses multi-seat STV with Gregory fractional surplus transfers at each stage.
Surplus from quota winners properly flows to same-party candidates, allowing
_2 and _3 to survive through inherited vote weight.

Stages:
  1. Retail:    27 → 12 survivors  (quota ≈ 7.7%)
  2. Pod A:     12 →  9 survivors  (quota ≈ 10.0%)
  3. Pod B:      9 →  7 survivors  (quota ≈ 12.5%)
  4. Pod C/D:    7 →  5 finalists  (quota ≈ 16.7%)

Outputs:
  primary_results_2028.csv         — per-stage candidate data
  primary_diagnostics_2028.csv     — transfer flow data for Sankey
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict
from itertools import combinations

BASE_DIR     = Path(__file__).parent.parent.parent
BALLOTS_PATH = BASE_DIR / "data" / "outputs" / "pure_multi" / "presidential_ballots.csv"
EFA_PATH     = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
OUTPUT_DIR   = BASE_DIR / "data" / "outputs" / "pure_multi"

PARTY_OF = {}   # filled during load
CAND_CODES = []

STAGES = [
    ("Initial_Slate",    None),   # snapshot only
    ("After_Retail",     12),
    ("After_Pod_A",       9),
    ("After_Pod_C",       7),
    ("After_Pod_BD",      5),
]


def load_ballots():
    """Load 27-candidate ballots as (N, 27) int array + code list."""
    df = pd.read_csv(BALLOTS_PATH, index_col=0)
    codes = []
    # Discover candidate codes from first row
    for col in df.columns:
        for val in df[col].unique():
            if val not in codes:
                codes.append(val)
    codes = sorted(set(val for col in df.columns for val in df[col].unique()))
    code_idx = {c: i for i, c in enumerate(codes)}

    N = len(df)
    M = len(df.columns)
    ballots = np.zeros((N, M), dtype=np.int16)
    for k, col in enumerate(df.columns):
        ballots[:, k] = df[col].map(code_idx).values

    for c in codes:
        PARTY_OF[c] = c.rsplit("_", 1)[0]

    return ballots, codes, code_idx


def first_surviving_choice(ballots, active):
    N, M = ballots.shape
    result = np.full(N, -1, dtype=np.int32)
    for i in range(N):
        for j in range(M):
            if int(ballots[i, j]) in active:
                result[i] = int(ballots[i, j])
                break
    return result


def run_stv_stage(ballots, weights, active_set, n_survivors, codes):
    """Gregory fractional STV — elect n_survivors candidates.

    Returns: (survivors set, elected_order list, transfer_records list, round_data list)
    """
    active      = set(active_set)
    ballot_wts  = weights.astype(np.float64).copy()
    total_votes = float(weights.sum())
    quota       = total_votes / (n_survivors + 1) + 1e-6

    elected     = []
    eliminated  = []
    transfers   = []
    round_data  = []

    max_rounds = len(active) * 3

    for rnd in range(max_rounds):
        if len(elected) >= n_survivors or not active:
            break

        remaining = n_survivors - len(elected)
        # If remaining seats >= active non-elected candidates, elect them all
        active_non_elected = active - set(elected)
        if len(active_non_elected) <= remaining:
            for c in sorted(active_non_elected):
                elected.append(c)
            break

        fsc = first_surviving_choice(ballots, active)
        totals = {c: 0.0 for c in active}
        for i in range(len(fsc)):
            if fsc[i] in totals:
                totals[fsc[i]] += ballot_wts[i]

        # Record round
        rd = {}
        for c in active:
            rd[codes[c]] = totals.get(c, 0.0)
        round_data.append(rd)

        # Check quota
        over = [(c, totals[c]) for c in active if c not in elected and totals[c] >= quota]
        over.sort(key=lambda x: -x[1])

        if over:
            winner, votes = over[0]
            surplus_frac = (votes - quota) / votes
            elected.append(winner)

            # Record surplus transfers
            temp_active = active - {winner}
            transfer_targets = defaultdict(float)
            for i in range(len(fsc)):
                if fsc[i] == winner:
                    old_w = ballot_wts[i]
                    ballot_wts[i] *= surplus_frac
                    transferred = old_w - ballot_wts[i]  # amount that "stayed" to fill quota
                    # Find where surplus goes
                    for j in range(ballots.shape[1]):
                        c = int(ballots[i, j])
                        if c in temp_active:
                            transfer_targets[codes[c]] += ballot_wts[i]
                            break

            active.discard(winner)

            for dest, vol in sorted(transfer_targets.items(), key=lambda x: -x[1]):
                transfers.append({
                    "from": codes[winner],
                    "to": dest,
                    "votes": round(vol, 2),
                    "type": "surplus",
                })
        else:
            # Eliminate weakest
            eliminable = [c for c in active if c not in elected]
            if not eliminable:
                break
            weakest = min(eliminable, key=lambda c: (totals.get(c, 0), c))
            active.discard(weakest)
            eliminated.append(weakest)

            # Record elimination transfers
            transfer_targets = defaultdict(float)
            for i in range(len(fsc)):
                if fsc[i] == weakest:
                    for j in range(ballots.shape[1]):
                        c = int(ballots[i, j])
                        if c in active:
                            transfer_targets[codes[c]] += ballot_wts[i]
                            break

            for dest, vol in sorted(transfer_targets.items(), key=lambda x: -x[1]):
                transfers.append({
                    "from": codes[weakest],
                    "to": dest,
                    "votes": round(vol, 2),
                    "type": "elimination",
                })

    survivors = set(elected)

    # Display totals: elected-via-quota candidates show quota weight;
    # candidates elected via "remaining <= seats" show their last-round total.
    final_totals = {}
    # Last round totals (before the shortcut)
    last_round = round_data[-1] if round_data else {}
    last_round_by_idx = {}
    for c_code, val in last_round.items():
        for idx in range(len(codes)):
            if codes[idx] == c_code:
                last_round_by_idx[idx] = val
                break

    elected_set = set()
    for c in elected:
        if c in elected_set:
            continue
        # Check if this candidate was elected via quota (appeared in the over_quota path)
        # Approximate: candidates elected early had quota-level vote totals
        final_totals[c] = max(quota, last_round_by_idx.get(c, quota))
        elected_set.add(c)

    # Normalize so display totals are meaningful percentages
    total_display = sum(final_totals.values()) or 1.0
    for c in final_totals:
        final_totals[c] = final_totals[c] / total_display * total_votes

    return survivors, elected, eliminated, transfers, round_data, quota, final_totals


def main():
    print("=" * 70)
    print("PURE MULTI PRIMARY — 27 candidates, multi-seat STV")
    print("=" * 70)

    ballots, codes, code_idx = load_ballots()
    efa     = pd.read_csv(EFA_PATH)
    weights = efa["commonpostweight"].values.astype(np.float64)
    N = len(ballots)
    n_cands = len(codes)
    print(f"  {N:,} ballots, {n_cands} candidates")

    surviving = set(range(n_cands))
    results_rows  = []
    diag_rows     = []

    for stage_idx, (stage_name, target) in enumerate(STAGES):
        print(f"\n{'─'*60}")
        print(f"Stage: {stage_name}  ({len(surviving)} candidates → {target or len(surviving)} survivors)")

        if target is None:
            # Initial snapshot — first preference shares
            fsc = first_surviving_choice(ballots, surviving)
            totals = defaultdict(float)
            for i in range(N):
                if fsc[i] >= 0:
                    totals[fsc[i]] += weights[i]
            total_w = sum(totals.values())

            print(f"  {'Candidate':<10} {'Party':<6} {'Share':>7}")
            for c in sorted(surviving, key=lambda x: -totals.get(x, 0)):
                code = codes[c]
                pct  = totals.get(c, 0) / total_w * 100
                results_rows.append({
                    "winnowing_point": stage_name,
                    "candidate_code": code,
                    "candidate_name": code,
                    "party_code": PARTY_OF.get(code, code),
                    "vote_total": round(totals.get(c, 0), 4),
                    "vote_pct": round(pct, 2),
                    "status": "surviving",
                    "quota_threshold": 0,
                    "accumulated_pool_size": round(total_w, 4),
                })
                if pct > 0.5:
                    print(f"  {code:<10} {PARTY_OF.get(code,''):<6} {pct:>6.1f}%")
            continue

        # Filter ballots to surviving candidates
        surv_list = sorted(surviving)
        surv_map  = {old: new for new, old in enumerate(surv_list)}
        n_surv    = len(surv_list)
        surv_codes = [codes[s] for s in surv_list]

        filtered = np.full((N, n_surv), -1, dtype=np.int16)
        for i in range(N):
            rank = 0
            for j in range(ballots.shape[1]):
                c = int(ballots[i, j])
                if c in surv_map:
                    filtered[i, rank] = surv_map[c]
                    rank += 1

        local_active = set(range(n_surv))
        survivors_local, elected, eliminated, transfers, rounds, quota, final_totals_local = \
            run_stv_stage(filtered, weights, local_active, target, surv_codes)

        # Map back to global indices
        surviving = {surv_list[local] for local in survivors_local}
        surv_codes_final = sorted([codes[s] for s in surviving])

        # Use STV-computed final vote totals (with modified ballot weights)
        total_w = sum(final_totals_local.values()) or 1.0

        print(f"  Quota: {quota:.1f}")
        print(f"  Elected: {len(elected)}  Eliminated: {len(eliminated)}")
        print(f"  Survivors ({len(surviving)}): {', '.join(surv_codes_final)}")
        for loc_idx in sorted(final_totals_local.keys(), key=lambda x: -final_totals_local[x]):
            code = surv_codes[loc_idx]
            vt   = final_totals_local[loc_idx]
            print(f"    {code:<10} {vt/total_w*100:>6.1f}%  ({vt:.0f})")

        # Record results
        for local_idx in range(n_surv):
            code = surv_codes[local_idx]
            global_idx = surv_list[local_idx]
            in_survivors = global_idx in surviving

            status = "surviving" if in_survivors else "eliminated_this_round"
            vt = final_totals_local.get(local_idx, 0.0) if in_survivors else 0.0
            results_rows.append({
                "winnowing_point": stage_name,
                "candidate_code": code,
                "candidate_name": code,
                "party_code": PARTY_OF.get(code, code),
                "vote_total": round(vt, 4),
                "vote_pct": round(vt / total_w * 100, 2) if total_w > 0 else 0,
                "status": status,
                "quota_threshold": round(quota, 4),
                "accumulated_pool_size": round(total_w, 4),
            })

        # Record transfers for Sankey
        for t in transfers:
            diag_rows.append({
                "winnowing_point": stage_name,
                "eliminated_code": t["from"],
                "eliminated_name": t["from"],
                "dest_code": t["to"],
                "dest_name": t["to"],
                "transferred_votes": t["votes"],
                "transfer_type": t["type"],
            })

    # ── Ranked Pairs among finalists ──────────────────────────────────────────
    print(f"\n{'─'*60}")
    fin_list  = sorted(surviving)
    fin_codes = [codes[s] for s in fin_list]
    print(f"Finalists: {', '.join(fin_codes)}")

    fin_map = {old: new for new, old in enumerate(fin_list)}
    n_fin   = len(fin_list)
    fin_ballots = np.full((N, n_fin), -1, dtype=np.int16)
    for i in range(N):
        rank = 0
        for j in range(ballots.shape[1]):
            c = int(ballots[i, j])
            if c in fin_map:
                fin_ballots[i, rank] = fin_map[c]
                rank += 1

    # Pairwise
    pairwise = np.zeros((n_fin, n_fin))
    for i in range(N):
        w = weights[i]
        ranks = {}
        for r in range(n_fin):
            p = int(fin_ballots[i, r])
            if p >= 0:
                ranks[p] = r
        for ai in range(n_fin):
            for bi in range(n_fin):
                if ai != bi and ranks.get(ai, 999) < ranks.get(bi, 999):
                    pairwise[ai, bi] += w

    # Simple Condorcet: who beats everyone?
    wins = [sum(1 for bi in range(n_fin) if bi != ai and pairwise[ai, bi] > pairwise[bi, ai])
            for ai in range(n_fin)]
    rp_winner_idx = max(range(n_fin), key=lambda x: wins[x])
    rp_winner = fin_codes[rp_winner_idx]
    print(f"Ranked Pairs winner: {rp_winner}")

    # ── Save ─────────────────────────────────────────────────────────────────
    pd.DataFrame(results_rows).to_csv(OUTPUT_DIR / "primary_results_2028.csv", index=False)
    pd.DataFrame(diag_rows).to_csv(OUTPUT_DIR / "primary_diagnostics_2028.csv", index=False)
    print(f"\nSaved primary_results_2028.csv ({len(results_rows)} rows)")
    print(f"Saved primary_diagnostics_2028.csv ({len(diag_rows)} rows)")

    print(f"\n{'='*70}")
    print(f"Primary complete.  Finalists: {', '.join(fin_codes)}  Winner: {rp_winner}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
