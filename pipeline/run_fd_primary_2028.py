#!/usr/bin/env python3
"""
run_fd_primary_2028.py
-----------------------
2028 Presidential Primary simulation using 71 factor-deviation candidates.

Requires:
  data/outputs/factor_deviation/ballots.csv
  data/outputs/factor_deviation/candidate_factor_centroids.csv
  data/processed/efa_factor_scores.csv  (for inputstate + weights)

Phases (same pod structure as LF primary):
  Phase 1: Retail Six   → 12 survivors
  Phase 2: + Pod A      → 10 survivors
  Phase 3: + Pod C      →  8 survivors
  Phase 4: + Pod B+D    →  5 finalists  (→ Ranked Pairs winner)

Outputs:
  data/outputs/factor_deviation/primary_results_2028.csv
  data/outputs/factor_deviation/primary_diagnostics_2028.csv
  data/outputs/factor_deviation/state_pod_assignments.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict

BASE_DIR        = Path(__file__).parent.parent
BALLOTS_PATH    = BASE_DIR / "data" / "outputs" / "factor_deviation" / "ballots.csv"
CANDIDATES_PATH = BASE_DIR / "data" / "outputs" / "factor_deviation" / "candidate_factor_centroids.csv"
EFA_SCORES_PATH = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
OUTPUT_DIR      = BASE_DIR / "data" / "outputs" / "factor_deviation"

FIPS_TO_ABBR = {
     1:"AL",  2:"AK",  4:"AZ",  5:"AR",  6:"CA",  8:"CO",  9:"CT",
    10:"DE", 11:"DC", 12:"FL", 13:"GA", 15:"HI", 16:"ID", 17:"IL",
    18:"IN", 19:"IA", 20:"KS", 21:"KY", 22:"LA", 23:"ME", 24:"MD",
    25:"MA", 26:"MI", 27:"MN", 28:"MS", 29:"MO", 30:"MT", 31:"NE",
    32:"NV", 33:"NH", 34:"NJ", 35:"NM", 36:"NY", 37:"NC", 38:"ND",
    39:"OH", 40:"OK", 41:"OR", 42:"PA", 44:"RI", 45:"SC", 46:"SD",
    47:"TN", 48:"TX", 49:"UT", 50:"VT", 51:"VA", 53:"WA", 54:"WV",
    55:"WI", 56:"WY", 72:"PR",
}

RETAIL_SIX  = {32, 28, 10, 19, 33, 72}
POD_A_MAIN  = {48, 17, 53, 51, 49,  9}
POD_A_BENCH = {50, 54, 35, 15, 38, 11}
POD_B_MAIN  = {12, 42, 25, 47,  8, 24}
POD_B_BENCH = {16, 44,  5,  2, 21, 22, 40}
POD_C_MAIN  = {36, 13, 39,  4, 27, 18}
POD_C_BENCH = {31, 30, 23}
POD_D_MAIN  = { 6, 37, 26, 34, 29, 45}
POD_D_BENCH = {20, 46, 56,  1, 41, 55}

STATE_POD: dict[int, dict] = {}
for fips in RETAIL_SIX:  STATE_POD[fips] = {"pod": "Retail", "bench": False, "retail_2028": True}
for fips in POD_A_MAIN:  STATE_POD[fips] = {"pod": "A",      "bench": False, "retail_2028": False}
for fips in POD_A_BENCH: STATE_POD[fips] = {"pod": "A",      "bench": True,  "retail_2028": False}
for fips in POD_B_MAIN:  STATE_POD[fips] = {"pod": "B",      "bench": False, "retail_2028": False}
for fips in POD_B_BENCH: STATE_POD[fips] = {"pod": "B",      "bench": True,  "retail_2028": False}
for fips in POD_C_MAIN:  STATE_POD[fips] = {"pod": "C",      "bench": False, "retail_2028": False}
for fips in POD_C_BENCH: STATE_POD[fips] = {"pod": "C",      "bench": True,  "retail_2028": False}
for fips in POD_D_MAIN:  STATE_POD[fips] = {"pod": "D",      "bench": False, "retail_2028": False}
for fips in POD_D_BENCH: STATE_POD[fips] = {"pod": "D",      "bench": True,  "retail_2028": False}


# ── STV helpers ──────────────────────────────────────────────────────────────

def first_surviving_choice(ballots_arr: np.ndarray, active_set: set) -> np.ndarray:
    N      = len(ballots_arr)
    result = np.empty(N, dtype=object)
    for i in range(N):
        for code in ballots_arr[i]:
            if code in active_set:
                result[i] = code
                break
    return result


def compute_vote_totals(fsc: np.ndarray, weights: np.ndarray, active_set: set) -> dict:
    totals = {c: 0.0 for c in active_set}
    for code, w in zip(fsc, weights):
        if code in totals:
            totals[code] += w
    return totals


def droop_quota(total_votes: float, n_survivors: int) -> float:
    return total_votes / (n_survivors + 1) + 1


def winnow(ballots_arr, weights, active_set, survivors_target, label, cand_names):
    """
    True STV with Gregory fractional surplus transfer.
    Returns (finalists, results_rows, transfer_rows).
    """
    active         = set(active_set)
    all_codes      = list(active_set)
    total_votes    = float(weights.sum())
    quota          = droop_quota(total_votes, survivors_target)
    ballot_weights = weights.astype(float).copy()

    elected:               list = []
    elected_via_quota:     list = []
    survived_default:      list = []
    eliminated_this_round: list = []
    results_rows:          list = []
    transfer_rows:         list = []

    while len(elected) < survivors_target and active:
        remaining_seats = survivors_target - len(elected)
        if len(active) <= remaining_seats:
            survived_default.extend(sorted(active))
            elected.extend(sorted(active))
            active.clear()
            break

        fsc    = first_surviving_choice(ballots_arr, active)
        totals = compute_vote_totals(fsc, ballot_weights, active)

        over_quota = sorted(
            [c for c in active if totals[c] >= quota],
            key=lambda c: (-totals[c], c),
        )
        if over_quota:
            winner         = over_quota[0]
            winner_votes   = totals[winner]
            surplus_factor = (winner_votes - quota) / winner_votes
            elected.append(winner)
            elected_via_quota.append(winner)

            temp_active = active - {winner}
            transfer_targets: dict = defaultdict(float)
            for i in range(len(fsc)):
                if fsc[i] == winner:
                    ballot_weights[i] *= surplus_factor
                    for ranked_code in ballots_arr[i]:
                        if ranked_code in temp_active:
                            transfer_targets[ranked_code] += ballot_weights[i]
                            break

            active.discard(winner)
            for dest, votes in sorted(transfer_targets.items(), key=lambda x: -x[1]):
                transfer_rows.append({
                    "eliminated_code":         winner,
                    "eliminated_name":         cand_names.get(winner, winner),
                    "winnowing_point":         label,
                    "transfer_type":           "surplus",
                    "dest_code":               dest,
                    "dest_name":               cand_names.get(dest, dest),
                    "transferred_votes":       round(votes, 4),
                    "pct_of_eliminated_total": round(votes / winner_votes * 100, 2)
                                               if winner_votes > 0 else 0.0,
                })

        else:
            loser       = min(active, key=lambda c: (totals[c], c))
            loser_votes = totals[loser]
            eliminated_this_round.append(loser)
            active.discard(loser)

            transfer_targets = defaultdict(float)
            for i in range(len(fsc)):
                if fsc[i] == loser:
                    for ranked_code in ballots_arr[i]:
                        if ranked_code in active:
                            transfer_targets[ranked_code] += ballot_weights[i]
                            break

            for dest, votes in sorted(transfer_targets.items(), key=lambda x: -x[1]):
                transfer_rows.append({
                    "eliminated_code":         loser,
                    "eliminated_name":         cand_names.get(loser, loser),
                    "winnowing_point":         label,
                    "transfer_type":           "elimination",
                    "dest_code":               dest,
                    "dest_name":               cand_names.get(dest, dest),
                    "transferred_votes":       round(votes, 4),
                    "pct_of_eliminated_total": round(votes / loser_votes * 100, 2)
                                               if loser_votes > 0 else 0.0,
                })

    finalists = set(elected)

    # Any candidates still in active were never formally eliminated (STV loop exited
    # once quota filled all seats).  Eliminate them now so transfers are recorded.
    while active:
        all_remaining  = active | finalists
        cleanup_fsc    = first_surviving_choice(ballots_arr, all_remaining)
        cleanup_totals = compute_vote_totals(cleanup_fsc, ballot_weights, active)
        loser          = min(active, key=lambda c: (cleanup_totals.get(c, 0.0), c))
        loser_votes    = cleanup_totals.get(loser, 0.0)
        eliminated_this_round.append(loser)
        active.discard(loser)
        transfer_targets_cl: dict = defaultdict(float)
        for i in range(len(cleanup_fsc)):
            if cleanup_fsc[i] == loser:
                for ranked_code in ballots_arr[i]:
                    if ranked_code in (active | finalists):
                        transfer_targets_cl[ranked_code] += ballot_weights[i]
                        break
        for dest, votes in sorted(transfer_targets_cl.items(), key=lambda x: -x[1]):
            transfer_rows.append({
                "eliminated_code":         loser,
                "eliminated_name":         cand_names.get(loser, loser),
                "winnowing_point":         label,
                "transfer_type":           "elimination",
                "dest_code":               dest,
                "dest_name":               cand_names.get(dest, dest),
                "transferred_votes":       round(votes, 4),
                "pct_of_eliminated_total": round(votes / loser_votes * 100, 2)
                                           if loser_votes > 0 else 0.0,
            })

    if finalists:
        final_fsc    = first_surviving_choice(ballots_arr, finalists)
        final_totals = compute_vote_totals(final_fsc, ballot_weights, finalists)
    else:
        final_totals = {}

    for code in all_codes:
        is_finalist = code in finalists
        vote_total  = final_totals.get(code, 0.0) if is_finalist else 0.0
        if code in finalists:
            status = "surviving"
        elif code in eliminated_this_round:
            status = "eliminated_this_round"
        else:
            status = "previously_eliminated"
        results_rows.append({
            "winnowing_point":       label,
            "candidate_code":        code,
            "candidate_name":        cand_names.get(code, code),
            "vote_total":            round(vote_total, 4),
            "vote_pct":              round(vote_total / total_votes * 100, 4) if total_votes else 0.0,
            "status":                status,
            "quota_threshold":       round(quota, 4),
            "accumulated_pool_size": round(total_votes, 4),
        })

    print(f"\n  ── {label} (→ {survivors_target} survivors) ──")
    print(f"     Total weighted votes: {total_votes:,.1f}   Droop quota: {quota:,.2f}")
    print(f"     Elected via quota:  {', '.join(elected_via_quota) or 'none'}")
    print(f"     Survived (default): {', '.join(survived_default) or 'none'}")
    print(f"     Eliminated ({len(eliminated_this_round)}): "
          f"{', '.join(eliminated_this_round[:10])}"
          + (f" … +{len(eliminated_this_round) - 10}" if len(eliminated_this_round) > 10 else ""))
    print(f"     Survivors ({len(finalists)}): {', '.join(sorted(finalists))}")

    return finalists, results_rows, transfer_rows


def ranked_pairs_winner(matchups, candidates, cand_names):
    """Ranked Pairs (Tideman) algorithm."""
    defeats = []
    for idx, m in enumerate(matchups):
        a, b = m["candidate_a"], m["candidate_b"]
        if m["votes_a_beats_b"] != m["votes_b_beats_a"]:
            winner = a if m["votes_a_beats_b"] > m["votes_b_beats_a"] else b
            loser  = b if winner == a else a
            margin = abs(m["votes_a_beats_b"] - m["votes_b_beats_a"])
            defeats.append({"winner": winner, "loser": loser, "margin": margin, "orig_idx": idx})
    defeats.sort(key=lambda d: -d["margin"])

    def creates_cycle(locked_edges, new_winner, new_loser):
        reachable: set = set()
        frontier = {new_loser}
        while frontier:
            node = frontier.pop()
            if node == new_winner:
                return True
            if node in reachable:
                continue
            reachable.add(node)
            for w, l in locked_edges:
                if w == node and l not in reachable:
                    frontier.add(l)
        return False

    locked_edges: list = []
    lock_meta = {d["orig_idx"]: {"lock_order": None, "locked": False} for d in defeats}

    for order, defeat in enumerate(defeats, start=1):
        idx = defeat["orig_idx"]
        lock_meta[idx]["lock_order"] = order
        if not creates_cycle(locked_edges, defeat["winner"], defeat["loser"]):
            locked_edges.append((defeat["winner"], defeat["loser"]))
            lock_meta[idx]["locked"] = True

    losers     = {l for _, l in locked_edges}
    undefeated = [c for c in candidates if c not in losers]
    rp_winner  = undefeated[0] if len(undefeated) == 1 else "none"

    annotated = []
    for idx, m in enumerate(matchups):
        total_v    = m["votes_a_beats_b"] + m["votes_b_beats_a"]
        raw_margin = abs(m["votes_a_beats_b"] - m["votes_b_beats_a"])
        annotated.append({
            **m,
            "margin":            round(raw_margin, 4),
            "margin_pct":        round(raw_margin / total_v * 100, 4) if total_v else 0.0,
            "lock_order":        lock_meta.get(idx, {}).get("lock_order"),
            "locked":            lock_meta.get(idx, {}).get("locked", False),
            "rp_winner_overall": rp_winner,
        })

    return rp_winner, annotated


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sep  = "=" * 70
    thin = "-" * 70

    print(sep)
    print("FD PRESIDENTIAL PRIMARY 2028  —  71 factor-deviation candidates")
    print(sep)

    # ── Load candidates ──────────────────────────────────────────────────────
    print("\nLoading FD candidates…")
    cand_df   = pd.read_csv(CANDIDATES_PATH)
    CAND_CODES = cand_df["candidate_code"].tolist()
    CAND_NAMES = {row["candidate_code"]: row["candidate_code"] for _, row in cand_df.iterrows()}
    CAND_META  = {row["candidate_code"]: {"party": row["party"], "axis": row["axis"],
                                           "direction": row["direction"]}
                  for _, row in cand_df.iterrows()}
    N_CANDIDATES = len(CAND_CODES)
    print(f"  {N_CANDIDATES} candidates across {cand_df['party'].nunique()} parties")

    # ── Load ballots ──────────────────────────────────────────────────────────
    print("Loading FD presidential ballots…")
    ballot_df   = pd.read_csv(BALLOTS_PATH, index_col="respondent_id")
    N           = len(ballot_df)
    rank_cols   = [f"rank_{k+1}" for k in range(N_CANDIDATES)]
    ballots_arr = ballot_df[rank_cols].values
    print(f"  {N:,} ballots × {N_CANDIDATES} candidates")

    # ── Load EFA scores for state + weights ───────────────────────────────────
    print("Loading EFA scores…")
    efa        = pd.read_csv(EFA_SCORES_PATH)
    inputstate = efa["inputstate"].values.astype(int)
    weights    = efa["commonpostweight"].values.astype(float)
    assert len(efa) == N

    def pod_mask(pods: list) -> np.ndarray:
        mask = np.zeros(N, dtype=bool)
        for i, fips in enumerate(inputstate):
            info = STATE_POD.get(fips)
            if info and info["pod"] in pods:
                mask[i] = True
        return mask

    retail_mask = pod_mask(["Retail"])
    poda_mask   = pod_mask(["A"])
    podc_mask   = pod_mask(["C"])
    podb_mask   = pod_mask(["B"])
    podd_mask   = pod_mask(["D"])
    pod_bd_mask = podb_mask | podd_mask

    all_results   = []
    all_transfers = []
    trajectory    = []

    active = set(CAND_CODES)

    def snapshot(phase_label, mask, current_active):
        fsc     = first_surviving_choice(ballots_arr[mask], current_active)
        totals  = compute_vote_totals(fsc, weights[mask], current_active)
        total_w = weights[mask].sum()
        for code in CAND_CODES:
            v = totals.get(code, 0.0)
            trajectory.append({
                "phase":          phase_label,
                "candidate_code": code,
                "candidate_name": CAND_NAMES[code],
                "party":          CAND_META[code]["party"],
                "axis":           CAND_META[code]["axis"],
                "direction":      CAND_META[code]["direction"],
                "raw_votes":      round(v, 4),
                "vote_pct":       round(v / total_w * 100, 4) if total_w else 0.0,
                "status":         "active" if code in current_active else "eliminated",
            })

    # ── Phase 1: Retail Six → 12 survivors ────────────────────────────────────
    print(f"\n{'='*60}")
    print("PHASE 1: Retail Six")
    cum_mask = retail_mask.copy()
    active, r_rows, t_rows = winnow(
        ballots_arr[cum_mask], weights[cum_mask], active,
        survivors_target=12, label="After_Retail_Six", cand_names=CAND_NAMES,
    )
    all_results   += r_rows
    all_transfers += t_rows
    snapshot("After_Retail_Six", cum_mask, active)

    # ── Phase 2: + Pod A → 10 survivors ───────────────────────────────────────
    print(f"\n{'='*60}")
    print("PHASE 2: Pod A")
    cum_mask = retail_mask | poda_mask
    active, r_rows, t_rows = winnow(
        ballots_arr[cum_mask], weights[cum_mask], active,
        survivors_target=10, label="After_Pod_A", cand_names=CAND_NAMES,
    )
    all_results   += r_rows
    all_transfers += t_rows
    snapshot("After_Pod_A", cum_mask, active)

    # ── Phase 3: + Pod C → 8 survivors ────────────────────────────────────────
    print(f"\n{'='*60}")
    print("PHASE 3: Pod C")
    cum_mask = retail_mask | poda_mask | podc_mask
    active, r_rows, t_rows = winnow(
        ballots_arr[cum_mask], weights[cum_mask], active,
        survivors_target=8, label="After_Pod_C", cand_names=CAND_NAMES,
    )
    all_results   += r_rows
    all_transfers += t_rows
    snapshot("After_Pod_C", cum_mask, active)

    # ── Phase 4: + Pod B+D → 5 finalists ──────────────────────────────────────
    print(f"\n{'='*60}")
    print("PHASE 4: Pod B + Pod D")
    cum_mask = retail_mask | poda_mask | podc_mask | pod_bd_mask
    active, r_rows, t_rows = winnow(
        ballots_arr[cum_mask], weights[cum_mask], active,
        survivors_target=5, label="After_Pod_BD", cand_names=CAND_NAMES,
    )
    all_results   += r_rows
    all_transfers += t_rows
    snapshot("After_Pod_BD", cum_mask, active)

    finalists     = sorted(active)
    finalist_meta = [(c, CAND_META[c]["party"], CAND_META[c]["axis"], CAND_META[c]["direction"])
                     for c in finalists]
    print(f"\n{'='*60}")
    print(f"FINALISTS (5):")
    for code, party, axis, dirn in finalist_meta:
        print(f"  {code:<20}  party={party}  axis={axis}  direction={dirn}")

    # ── Save primary results ──────────────────────────────────────────────────
    results_df  = pd.DataFrame(all_results)
    results_out = OUTPUT_DIR / "primary_results_2028.csv"
    results_df.to_csv(results_out, index=False)
    print(f"\nSaved primary results → {results_out.relative_to(BASE_DIR)}  ({len(results_df)} rows)")

    # ── Diagnostics ────────────────────────────────────────────────────────────
    diag_sheets = {}

    traj_df = pd.DataFrame(trajectory)
    diag_sheets["trajectories"] = traj_df

    # Variant analysis: compare each FD variant to its base party candidate
    variant_rows = []
    full_mask    = cum_mask
    for code in CAND_CODES:
        meta = CAND_META[code]
        if meta["axis"] == "base":
            continue
        base_code = meta["party"]
        for pod_label, pmask in [
            ("Retail", retail_mask), ("A", poda_mask),
            ("C", podc_mask), ("B", podb_mask), ("D", podd_mask),
        ]:
            if pmask.sum() == 0:
                continue
            fsc_pod    = first_surviving_choice(ballots_arr[pmask], set(CAND_CODES))
            w_pod      = weights[pmask]
            totals_pod = compute_vote_totals(fsc_pod, w_pod, set(CAND_CODES))
            total_w    = w_pod.sum()
            var_pct    = totals_pod.get(code, 0.0) / total_w * 100 if total_w else 0.0
            base_pct   = totals_pod.get(base_code, 0.0) / total_w * 100 if total_w else 0.0
            variant_rows.append({
                "variant_code":   code,
                "party":          meta["party"],
                "axis":           meta["axis"],
                "direction":      meta["direction"],
                "base_code":      base_code,
                "pod":            pod_label,
                "variant_pct":    round(var_pct, 4),
                "base_pct":       round(base_pct, 4),
                "delta_vs_base":  round(var_pct - base_pct, 4),
            })
    diag_sheets["variant_analysis"] = pd.DataFrame(variant_rows)

    # Transfer analysis — top 5 destinations per candidate per stage
    transfer_df = pd.DataFrame(all_transfers)
    if not transfer_df.empty:
        transfer_top5 = (
            transfer_df
            .sort_values(["eliminated_code", "winnowing_point", "transferred_votes"],
                         ascending=[True, True, False])
            .groupby(["eliminated_code", "winnowing_point"])
            .head(5)
            .reset_index(drop=True)
        )
    else:
        transfer_top5 = transfer_df
    diag_sheets["transfer_analysis"] = transfer_top5

    # Ranked Pairs among 5 finalists
    print(f"\n{thin}")
    print("Running Ranked Pairs (Tideman) among 5 finalists…")
    raw_matchups = []
    for i, ca in enumerate(finalists):
        for cb in finalists[i + 1:]:
            votes_a, votes_b = 0.0, 0.0
            for ballot, w in zip(ballots_arr, weights):
                for code in ballot:
                    if code == ca:
                        votes_a += w; break
                    elif code == cb:
                        votes_b += w; break
            pairwise_winner = (ca if votes_a > votes_b else (cb if votes_b > votes_a else "tie"))
            raw_matchups.append({
                "candidate_a":     ca,
                "candidate_b":     cb,
                "votes_a_beats_b": round(votes_a, 4),
                "votes_b_beats_a": round(votes_b, 4),
                "winner":          pairwise_winner,
            })
    rp_winner, annotated_matchups = ranked_pairs_winner(raw_matchups, finalists, CAND_NAMES)
    condorcet_df = pd.DataFrame(annotated_matchups).sort_values("lock_order").reset_index(drop=True)
    diag_sheets["condorcet"] = condorcet_df
    print(f"  Ranked Pairs winner: {rp_winner}")

    # Save combined diagnostics
    diag_out = OUTPUT_DIR / "primary_diagnostics_2028.csv"
    combined_parts = []
    for sheet_name, df in diag_sheets.items():
        df2 = df.copy()
        df2.insert(0, "diagnostic", sheet_name)
        combined_parts.append(df2)
    diag_combined = pd.concat(combined_parts, ignore_index=True)
    diag_combined.to_csv(diag_out, index=False)
    print(f"Saved diagnostics → {diag_out.relative_to(BASE_DIR)}  ({len(diag_combined)} rows)")

    # Save pod assignments
    pod_rows = []
    for fips, info in sorted(STATE_POD.items()):
        pod_rows.append({
            "state_fips":  fips,
            "state_abbr":  FIPS_TO_ABBR.get(fips, f"FIPS{fips}"),
            "pod":         info["pod"],
            "bench":       info["bench"],
            "retail_2028": info["retail_2028"],
        })
    pd.DataFrame(pod_rows).to_csv(OUTPUT_DIR / "state_pod_assignments.csv", index=False)

    print(f"\n{sep}")
    print("FD primary simulation complete.")
    print(f"  Finalists: {', '.join(finalists)}")
    print(f"  Ranked Pairs winner: {rp_winner}")
    print(sep)


if __name__ == "__main__":
    main()
