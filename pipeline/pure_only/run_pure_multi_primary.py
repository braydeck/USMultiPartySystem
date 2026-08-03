#!/usr/bin/env python3
"""
run_pure_multi_primary.py
--------------------------
2028 Presidential Primary — 27 candidates (10 parties × 3).

Uses multi-seat STV with Gregory fractional surplus transfers at each stage.
Surplus from quota winners properly flows to same-party candidates, allowing
_2 and _3 to survive through inherited vote weight.

Cumulative rolling electorate: each stage counts only the states that have voted by then,
and their ballots stay in the pool for every later stage. A state votes once; the field
narrows around it. Quotas below are 1/(survivors+1) of *that* pool, so the retail quota is a
share of six states rather than of the country.

  1. Retail:    27 → 12 survivors  (quota ≈ 7.7% of the retail states)
  2. Pod A:     12 →  9 survivors  (quota ≈ 10.0% of retail + A)
  3. Pod C:      9 →  7 survivors  (quota ≈ 12.5% of retail + A + C)
  4. Pod B/D:    7 →  5 finalists  (quota ≈ 16.7% of the country)

Outputs:
  primary_results_2028.csv         — per-stage candidate data
  primary_diagnostics_2028.csv     — transfer flow data for Sankey
"""

import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict
from itertools import combinations

sys.path.insert(0, str(Path(__file__).parent))
from turnout_weights import turnout_multiplier, output_tree

BASE_DIR     = Path(__file__).parent.parent.parent
_BALLOT_TREE = "pure_multi_nosty" if os.environ.get("NO_STY") == "1" else "pure_multi"
_OUT_TREE    = output_tree(_BALLOT_TREE)  # turnout-weighted output → parallel _turnout tree
BALLOTS_PATH = BASE_DIR / "data" / "outputs" / _BALLOT_TREE / "presidential_ballots.csv"
EFA_PATH     = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
POD_PATH     = BASE_DIR / "data" / "outputs" / _BALLOT_TREE / "state_pod_assignments.csv"
OUTPUT_DIR   = BASE_DIR / "data" / "outputs" / _OUT_TREE

PARTY_OF = {}   # filled during load
CAND_CODES = []

# (stage, survivors, pods that have voted by this stage). The pod list is cumulative: a
# state votes once and its ballots stay in the pool for every later stage, which is what
# makes the calendar mean anything. Retail cuts 27 to 12 on six states' ballots, not on the
# country's — the whole point of a sequential primary is that early states winnow the field
# before the rest have voted.
STAGES = [
    ("Initial_Slate",    None, None),                            # pre-voting snapshot
    ("After_Retail",     12,   ("Retail",)),
    ("After_Pod_A",       9,   ("Retail", "A")),
    ("After_Pod_C",       7,   ("Retail", "A", "C")),
    ("After_Pod_BD",      5,   ("Retail", "A", "C", "B", "D")),
]


def load_pod_masks(n_ballots):
    """Boolean respondent mask per stage, from the state pod assignments.

    Rows of `efa_factor_scores.csv` and of the ballot file are the same respondents in the
    same order, so a mask built from `inputstate` indexes both. Ported from
    `run_presidential_primary_pure.py`, which had this right; the 27-candidate rebuild lost
    it and counted the whole country at every stage.
    """
    efa = pd.read_csv(EFA_PATH)
    if len(efa) != n_ballots:
        raise SystemExit(f"efa rows ({len(efa)}) != ballots ({n_ballots}); masks would misalign")
    inputstate = efa["inputstate"].values.astype(int)
    pod_df = pd.read_csv(POD_PATH)
    pod_of_fips = {int(r.state_fips): r.pod for r in pod_df.itertuples()}

    unassigned = sorted({f for f in np.unique(inputstate) if f not in pod_of_fips})
    if unassigned:
        raise SystemExit(f"states with ballots but no pod: {unassigned}")
    # Pod entries with no respondents are fine and expected: Puerto Rico holds a retail
    # primary but the CES does not sample it, so it contributes no ballots.
    empty = sorted({f for f in pod_of_fips if f not in set(inputstate.tolist())})

    pod_by_row = np.array([pod_of_fips[f] for f in inputstate])
    masks = {}
    for stage_name, _target, pods in STAGES:
        masks[stage_name] = (None if pods is None
                             else np.isin(pod_by_row, np.array(pods)))
    return masks, empty


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

    # Record transfers for implicitly eliminated leftovers (candidates still
    # active but not elected when the loop exits — they were passed over).
    # Leftover candidates hold votes via surplus transfers (modified ballot_wts).
    # Since survivors already used surplus to shed weight, leftover voters are
    # those who rank leftovers above survivors on the MODIFIED-weight ballots.
    # We simulate elimination rounds: weakest leftover eliminated, votes transfer
    # to survivors (recorded) or remaining leftovers (cascade continues).
    leftover = list(active - set(elected))
    remaining_left = set(leftover)
    while remaining_left:
        # First choice among only leftovers (not survivors — those already elected)
        fsc_left = first_surviving_choice(ballots, remaining_left)
        totals_left = {c: 0.0 for c in remaining_left}
        for i in range(len(fsc_left)):
            if fsc_left[i] in totals_left:
                totals_left[fsc_left[i]] += ballot_wts[i]
        # Eliminate weakest leftover
        weakest_left = min(remaining_left, key=lambda c: (totals_left.get(c, 0), c))
        remaining_left.discard(weakest_left)
        # Find where weakest_left's voters go (to remaining leftovers or survivors)
        dest_set = remaining_left | survivors
        transfer_targets = defaultdict(float)
        for i in range(len(fsc_left)):
            if fsc_left[i] == weakest_left:
                found = False
                for j in range(ballots.shape[1]):
                    c = int(ballots[i, j])
                    if c == weakest_left:
                        found = True
                    elif found and c in dest_set:
                        transfer_targets[codes[c]] += ballot_wts[i]
                        break
        eliminated.append(weakest_left)
        for dest, vol in sorted(transfer_targets.items(), key=lambda x: -x[1]):
            if vol > 0.01:
                transfers.append({
                    "from": codes[weakest_left],
                    "to": dest,
                    "votes": round(vol, 2),
                    "type": "elimination",
                })

    # Display totals: every elected candidate retains exactly quota.
    # Surplus above quota was shed via Gregory fractional transfers.
    # No normalization — retained values should reflect the true Droop quota
    # as a share of the total pool (e.g., 7.69% for 12 survivors).
    final_totals = {}
    for c in elected:
        if c not in final_totals:
            final_totals[c] = quota

    return survivors, elected, eliminated, transfers, round_data, quota, final_totals


def main():
    print("=" * 70)
    print("PURE MULTI PRIMARY — 27 candidates, multi-seat STV")
    print("=" * 70)

    # Ballot depth: 0 = full ranking; N = voters rank only their top N (truncated ballots
    # exhaust when all ranked candidates are eliminated). Output goes to a parallel _topN tree.
    ballot_depth = int(os.environ.get("BALLOT_DEPTH", "0"))
    out_dir = OUTPUT_DIR if not ballot_depth else OUTPUT_DIR.parent / (OUTPUT_DIR.name + f"_top{ballot_depth}")
    out_dir.mkdir(parents=True, exist_ok=True)
    ballots, codes, code_idx = load_ballots()
    if ballot_depth:
        ballots = ballots[:, :ballot_depth]
    efa     = pd.read_csv(EFA_PATH)
    weights = efa["commonpostweight"].values.astype(np.float64) * turnout_multiplier(len(efa))
    N = len(ballots)
    n_cands = len(codes)
    print(f"  {N:,} ballots, {n_cands} candidates (depth={ballot_depth or 'full'})")

    stage_masks, empty_pods = load_pod_masks(N)
    if empty_pods:
        print(f"  pod states with no ballots (not sampled by CES): {sorted(empty_pods)}")
    for stage_name, _t, pods in STAGES:
        if pods is None:
            continue
        m = stage_masks[stage_name]
        print(f"  {stage_name:<14} {m.sum():>6,} ballots  "
              f"{weights[m].sum():>12,.1f} weighted  ({100*m.sum()/N:>5.1f}% of the country)")

    surviving = set(range(n_cands))
    results_rows  = []
    diag_rows     = []

    for stage_idx, (stage_name, target, stage_pods) in enumerate(STAGES):
        print(f"\n{'─'*60}")
        print(f"Stage: {stage_name}  ({len(surviving)} candidates → {target or len(surviving)} survivors)")

        if target is None:
            # Initial snapshot — national first preferences before anyone has voted. This is
            # a description of the field, not a count, so it is the only stage that looks at
            # the whole country.
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

        # The electorate is every state that has voted by this stage, and only those.
        mask = stage_masks[stage_name]
        stage_ballots = ballots[mask]
        stage_weights = weights[mask]
        n_stage = len(stage_ballots)
        print(f"  Electorate: {n_stage:,} ballots from pods {'+'.join(stage_pods)}"
              f"  ({stage_weights.sum():,.1f} weighted)")

        # Filter ballots to surviving candidates
        surv_list = sorted(surviving)
        surv_map  = {old: new for new, old in enumerate(surv_list)}
        n_surv    = len(surv_list)
        surv_codes = [codes[s] for s in surv_list]

        filtered = np.full((n_stage, n_surv), -1, dtype=np.int16)
        for i in range(n_stage):
            rank = 0
            for j in range(stage_ballots.shape[1]):
                c = int(stage_ballots[i, j])
                if c in surv_map:
                    filtered[i, rank] = surv_map[c]
                    rank += 1

        local_active = set(range(n_surv))
        survivors_local, elected, eliminated, transfers, rounds, quota, final_totals_local = \
            run_stv_stage(filtered, stage_weights, local_active, target, surv_codes)

        # Map back to global indices
        surviving = {surv_list[local] for local in survivors_local}
        surv_codes_final = sorted([codes[s] for s in surviving])

        # Percentages are of the ballots cast by this stage — the same pool the quota came
        # from — so a retail-round share is a share of the retail states, not of the country.
        total_w = float(stage_weights.sum())

        print(f"  Quota: {quota:.1f}")
        print(f"  Elected: {len(elected)}  Eliminated: {len(eliminated)}")
        print(f"  Survivors ({len(surviving)}): {', '.join(surv_codes_final)}")
        for loc_idx in sorted(final_totals_local.keys(), key=lambda x: -final_totals_local[x]):
            code = surv_codes[loc_idx]
            vt   = final_totals_local[loc_idx]
            print(f"    {code:<10} {vt/total_w*100:>6.1f}%  ({vt:.0f})")

        # First-choice tallies (round 1 of STV, before surplus/elimination)
        first_choice = rounds[0] if rounds else {}

        # Record results
        for local_idx in range(n_surv):
            code = surv_codes[local_idx]
            global_idx = surv_list[local_idx]
            in_survivors = global_idx in surviving

            status = "surviving" if in_survivors else "eliminated_this_round"
            vt = final_totals_local.get(local_idx, 0.0) if in_survivors else 0.0
            fc = first_choice.get(code, 0.0)
            results_rows.append({
                "winnowing_point": stage_name,
                "candidate_code": code,
                "candidate_name": code,
                "party_code": PARTY_OF.get(code, code),
                "vote_total": round(vt, 4),
                "vote_pct": round(vt / total_w * 100, 2) if total_w > 0 else 0,
                "first_choice_total": round(fc, 4),
                "first_choice_pct": round(fc / total_w * 100, 2) if total_w > 0 else 0,
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
    # The electorate after the last pod: every state has voted by then, so this is the whole
    # sample — but derive it from the mask rather than assuming, in case pods change.
    final_mask = stage_masks[STAGES[-1][0]]
    fin_input  = ballots[final_mask]
    fin_weights = weights[final_mask]
    n_final = len(fin_input)
    fin_ballots = np.full((n_final, n_fin), -1, dtype=np.int16)
    for i in range(n_final):
        rank = 0
        for j in range(fin_input.shape[1]):
            c = int(fin_input[i, j])
            if c in fin_map:
                fin_ballots[i, rank] = fin_map[c]
                rank += 1

    # Pairwise
    pairwise = np.zeros((n_fin, n_fin))
    for i in range(n_final):
        w = fin_weights[i]
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
    pd.DataFrame(results_rows).to_csv(out_dir / "primary_results_2028.csv", index=False)
    pd.DataFrame(diag_rows).to_csv(out_dir / "primary_diagnostics_2028.csv", index=False)
    print(f"\nSaved primary_results_2028.csv ({len(results_rows)} rows)")
    print(f"Saved primary_diagnostics_2028.csv ({len(diag_rows)} rows)")

    print(f"\n{'='*70}")
    print(f"Primary complete.  Finalists: {', '.join(fin_codes)}  Winner: {rp_winner}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
