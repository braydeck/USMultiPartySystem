#!/usr/bin/env python3
"""
run_light_fusion_primary_2028.py
-----------------------------------
2028 Presidential Primary simulation using 25 light-fusion candidates:
  9 pure party candidates + 16 "slight deviant" variants at 80/20 weights.

Light fusion candidates (e.g. STY_sd) represent voters who would caucus
with their primary party but lean slightly toward an adjacent party.
Distinct from "blended" midpoints used in the senate-derived scenario.

Requires:
  data/outputs/light_fusion/presidential_ballots.csv   (from generate_light_fusion_ballots.py)
  data/efa_factor_scores.csv                           (for inputstate + commonpostweight)

Outputs:
  data/outputs/light_fusion/primary_results_2028.csv
  data/outputs/light_fusion/primary_diagnostics_2028.csv
  data/outputs/light_fusion/state_pod_assignments.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict

BASE_DIR      = Path(__file__).parent.parent
BALLOTS_PATH  = BASE_DIR / "data" / "outputs" / "light_fusion" / "presidential_ballots.csv"
EFA_SCORES_PATH = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
OUTPUT_DIR    = BASE_DIR / "data" / "outputs" / "light_fusion"

# ── 25 Light Fusion Presidential Candidates ────────────────────────────────────
CANDIDATES = [
    # ── Pure Party Candidates ──
    {"code": "RH",      "name": "CON",     "primary": 0, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "MW",      "name": "SD",      "primary": 1, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "MRJ",     "name": "STY",     "primary": 2, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "BE",      "name": "NAT",     "primary": 3, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "CO",      "name": "LIB",     "primary": 4, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "DH",      "name": "REF",     "primary": 5, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "LK",      "name": "CTR",     "primary": 6, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "ZN",      "name": "DSA",     "primary": 8, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "JR",      "name": "PRG",     "primary": 9, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    # ── Light Fusion (80/20) ──
    {"code": "PRG_dsa", "name": "PRG_dsa", "primary": 9, "secondary": 8, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "DSA_prg", "name": "DSA_prg", "primary": 8, "secondary": 9, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "DSA_lib", "name": "DSA_lib", "primary": 8, "secondary": 4, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "LIB_dsa", "name": "LIB_dsa", "primary": 4, "secondary": 8, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "LIB_sd",  "name": "LIB_sd",  "primary": 4, "secondary": 1, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "SD_lib",  "name": "SD_lib",  "primary": 1, "secondary": 4, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "SD_sty",  "name": "SD_sty",  "primary": 1, "secondary": 2, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "STY_sd",  "name": "STY_sd",  "primary": 2, "secondary": 1, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "STY_ctr", "name": "STY_ctr", "primary": 2, "secondary": 6, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "CTR_sty", "name": "CTR_sty", "primary": 6, "secondary": 2, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "CTR_con", "name": "CTR_con", "primary": 6, "secondary": 0, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "CON_ctr", "name": "CON_ctr", "primary": 0, "secondary": 6, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "CON_ref", "name": "CON_ref", "primary": 0, "secondary": 5, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "REF_con", "name": "REF_con", "primary": 5, "secondary": 0, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "REF_nat", "name": "REF_nat", "primary": 5, "secondary": 3, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "NAT_ref", "name": "NAT_ref", "primary": 3, "secondary": 5, "w_primary": 0.80, "w_secondary": 0.20},
]

CAND_CODES = [c["code"] for c in CANDIDATES]
CAND_NAMES = {c["code"]: c["name"] for c in CANDIDATES}
N_CANDIDATES = len(CANDIDATES)

PLATONIC_CODES  = {c["code"] for c in CANDIDATES if c["secondary"] is None}
STRADDLER_CODES = {c["code"] for c in CANDIDATES if c["secondary"] is not None}

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


# ── Helpers ────────────────────────────────────────────────────────────────────

def first_surviving_choice(ballots_arr: np.ndarray, active_set: set[str]) -> np.ndarray:
    N = len(ballots_arr)
    result = np.empty(N, dtype=object)
    for i in range(N):
        for code in ballots_arr[i]:
            if code in active_set:
                result[i] = code
                break
    return result


def compute_vote_totals(fsc: np.ndarray, weights: np.ndarray, active_set: set[str]) -> dict[str, float]:
    totals = {c: 0.0 for c in active_set}
    for code, w in zip(fsc, weights):
        if code in totals:
            totals[code] += w
    return totals


def droop_quota(total_votes: float, n_survivors: int) -> float:
    return total_votes / (n_survivors + 1) + 1


def pod_vote_shares(ballots_arr, weights, pod_mask, active_set, pod_label):
    fsc     = first_surviving_choice(ballots_arr[pod_mask], active_set)
    w_pod   = weights[pod_mask]
    totals  = compute_vote_totals(fsc, w_pod, active_set)
    total_w = w_pod.sum()
    rows = []
    for code, votes in totals.items():
        rows.append({
            "candidate_code":  code,
            "pod":             pod_label,
            "votes_from_pod":  round(votes, 4),
            "pod_total_votes": round(total_w, 4),
            "pct_of_pod":      round(votes / total_w * 100, 4) if total_w else 0.0,
        })
    return rows


def winnow(ballots_arr, weights, active_set, survivors_target, label):
    """
    True STV primary with Gregory fractional surplus transfer.
    Returns (finalists, results_rows, transfer_rows).
    transfer_rows include both 'surplus' and 'elimination' types.
    """
    active         = set(active_set)
    total_votes    = float(weights.sum())
    quota          = droop_quota(total_votes, survivors_target)
    ballot_weights = weights.astype(float).copy()

    elected:               list[str] = []
    elected_via_quota:     list[str] = []
    survived_default:      list[str] = []
    eliminated_this_round: list[str] = []
    results_rows:          list[dict] = []
    transfer_rows:         list[dict] = []

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
            transfer_targets: dict[str, float] = defaultdict(float)
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
                    "eliminated_name":         CAND_NAMES[winner],
                    "winnowing_point":         label,
                    "transfer_type":           "surplus",
                    "dest_code":               dest,
                    "dest_name":               CAND_NAMES.get(dest, dest),
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
                    "eliminated_name":         CAND_NAMES[loser],
                    "winnowing_point":         label,
                    "transfer_type":           "elimination",
                    "dest_code":               dest,
                    "dest_name":               CAND_NAMES.get(dest, dest),
                    "transferred_votes":       round(votes, 4),
                    "pct_of_eliminated_total": round(votes / loser_votes * 100, 2)
                                               if loser_votes > 0 else 0.0,
                })

    finalists = set(elected)
    if finalists:
        final_fsc    = first_surviving_choice(ballots_arr, finalists)
        final_totals = compute_vote_totals(final_fsc, ballot_weights, finalists)
    else:
        final_totals = {}

    for code in CAND_CODES:
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
            "candidate_name":        CAND_NAMES[code],
            "vote_total":            round(vote_total, 4),
            "vote_pct":              round(vote_total / total_votes * 100, 4) if total_votes else 0.0,
            "status":                status,
            "quota_threshold":       round(quota, 4),
            "accumulated_pool_size": round(total_votes, 4),
        })

    print(f"\n  ── {label} winnowing (→ {survivors_target} survivors) ──")
    print(f"     Total weighted votes: {total_votes:,.1f}   Droop quota: {quota:,.2f}")
    print(f"     Elected via quota:  {', '.join(elected_via_quota) or 'none'}")
    print(f"     Survived (default): {', '.join(survived_default) or 'none'}")
    print(f"     Eliminated:         {', '.join(eliminated_this_round) or 'none'}")
    print(f"     Survivors ({len(finalists)}):     {', '.join(sorted(finalists))}")

    return finalists, results_rows, transfer_rows


def ranked_pairs_winner(matchups, candidates):
    """Ranked Pairs (Tideman) algorithm among finalists."""
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
        reachable: set[str] = set()
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

    locked_edges: list[tuple] = []
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

    print("Loading light fusion presidential ballots…")
    ballot_df = pd.read_csv(BALLOTS_PATH, index_col="respondent_id")
    N = len(ballot_df)
    rank_cols    = [f"rank_{k+1}" for k in range(N_CANDIDATES)]
    ballots_arr  = ballot_df[rank_cols].values
    print(f"  {N:,} ballots loaded  ({N_CANDIDATES} candidates)")

    print("Loading EFA scores…")
    efa        = pd.read_csv(EFA_SCORES_PATH)
    inputstate = efa["inputstate"].values.astype(int)
    weights    = efa["commonpostweight"].values.astype(float)

    def pod_mask(pods: list[str]) -> np.ndarray:
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
    geo_rows      = []

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
                "raw_votes":      round(v, 4),
                "vote_pct":       round(v / total_w * 100, 4) if total_w else 0.0,
                "status":         "active" if code in current_active else "eliminated",
            })

    # ── Phase 1: Retail Six → 12 survivors ──
    print("\n" + "="*60)
    print("PHASE 1: Retail Six")
    cum_mask = retail_mask.copy()
    active, r_rows, t_rows = winnow(
        ballots_arr[cum_mask], weights[cum_mask], active,
        survivors_target=12, label="After_Retail_Six"
    )
    all_results   += r_rows
    all_transfers += t_rows
    snapshot("After_Retail_Six", cum_mask, active)

    # ── Phase 2: Pod A → 10 survivors ──
    print("\n" + "="*60)
    print("PHASE 2: Pod A")
    cum_mask = retail_mask | poda_mask
    active, r_rows, t_rows = winnow(
        ballots_arr[cum_mask], weights[cum_mask], active,
        survivors_target=10, label="After_Pod_A"
    )
    all_results   += r_rows
    all_transfers += t_rows
    snapshot("After_Pod_A", cum_mask, active)

    # ── Phase 3: Pod C → 8 survivors ──
    print("\n" + "="*60)
    print("PHASE 3: Pod C")
    cum_mask = retail_mask | poda_mask | podc_mask
    active, r_rows, t_rows = winnow(
        ballots_arr[cum_mask], weights[cum_mask], active,
        survivors_target=8, label="After_Pod_C"
    )
    all_results   += r_rows
    all_transfers += t_rows
    snapshot("After_Pod_C", cum_mask, active)

    # ── Phase 4: Pod B+D → 5 survivors ──
    print("\n" + "="*60)
    print("PHASE 4: Pod B + Pod D")
    cum_mask = retail_mask | poda_mask | podc_mask | pod_bd_mask
    active, r_rows, t_rows = winnow(
        ballots_arr[cum_mask], weights[cum_mask], active,
        survivors_target=5, label="After_Pod_BD"
    )
    all_results   += r_rows
    all_transfers += t_rows
    snapshot("After_Pod_BD", cum_mask, active)

    finalists = sorted(active)
    print(f"\n{'='*60}")
    print(f"FINALISTS (5): {', '.join(finalists)}")

    # ── Save primary results ──
    results_df  = pd.DataFrame(all_results)
    results_out = OUTPUT_DIR / "primary_results_2028.csv"
    results_df.to_csv(results_out, index=False)
    print(f"\nSaved primary results → {results_out}  ({len(results_df)} rows)")

    # ── DIAGNOSTICS ──
    diag_sheets = {}

    traj_df = pd.DataFrame(trajectory)
    diag_sheets["trajectories"] = traj_df

    # Geographic breakdown for finalists
    full_mask = retail_mask | poda_mask | podc_mask | pod_bd_mask
    for pod_label, pmask in [
        ("Retail", retail_mask), ("A", poda_mask), ("C", podc_mask),
        ("B", podb_mask), ("D", podd_mask),
    ]:
        geo_rows += pod_vote_shares(ballots_arr, weights, pmask, set(finalists), pod_label)
    geo_df = pd.DataFrame(geo_rows)
    finalist_totals = geo_df.groupby("candidate_code")["votes_from_pod"].sum().rename("finalist_national_total")
    geo_df = geo_df.merge(finalist_totals, on="candidate_code")
    geo_df["pct_of_finalist_total"] = (
        geo_df["votes_from_pod"] / geo_df["finalist_national_total"] * 100
    ).round(2)
    diag_sheets["geo_breakdown"] = geo_df

    # Straddler analysis: light fusion vs. pure parent
    platonic_by_cluster = {c["primary"]: c["code"] for c in CANDIDATES if c["secondary"] is None}
    straddler_rows = []
    for cand in CANDIDATES:
        if cand["secondary"] is None:
            continue
        straddler  = cand["code"]
        platonic_p = platonic_by_cluster.get(cand["primary"])
        platonic_s = platonic_by_cluster.get(cand["secondary"])
        for pod_label, pmask in [
            ("Retail", retail_mask), ("A", poda_mask),
            ("C", podc_mask), ("B", podb_mask), ("D", podd_mask),
        ]:
            if pmask.sum() == 0:
                continue
            all_active = set(CAND_CODES)
            fsc_pod    = first_surviving_choice(ballots_arr[pmask], all_active)
            w_pod      = weights[pmask]
            totals_pod = compute_vote_totals(fsc_pod, w_pod, all_active)
            total_w_pod = w_pod.sum()
            s_pct  = totals_pod.get(straddler, 0.0) / total_w_pod * 100 if total_w_pod else 0
            p_pct  = totals_pod.get(platonic_p, 0.0) / total_w_pod * 100 if (total_w_pod and platonic_p) else None
            ps_pct = totals_pod.get(platonic_s, 0.0) / total_w_pod * 100 if (total_w_pod and platonic_s) else None
            straddler_rows.append({
                "straddler_code":            straddler,
                "straddler_name":            CAND_NAMES[straddler],
                "platonic_code":             platonic_p or "",
                "platonic_name":             CAND_NAMES.get(platonic_p, "") if platonic_p else "",
                "platonic_secondary_code":   platonic_s or "",
                "pod":                       pod_label,
                "straddler_pct":             round(s_pct, 4),
                "platonic_pct":              round(p_pct, 4) if p_pct is not None else None,
                "platonic_secondary_pct":    round(ps_pct, 4) if ps_pct is not None else None,
                "delta_vs_primary":          round(s_pct - p_pct, 4) if p_pct is not None else None,
            })
    diag_sheets["straddler_analysis"] = pd.DataFrame(straddler_rows)

    # Transfer analysis — top 3 destinations per candidate per stage
    transfer_df = pd.DataFrame(all_transfers)
    if not transfer_df.empty:
        transfer_top3 = (
            transfer_df
            .sort_values(["eliminated_code", "winnowing_point", "transferred_votes"],
                         ascending=[True, True, False])
            .groupby(["eliminated_code", "winnowing_point"])
            .head(3)
            .reset_index(drop=True)
        )
    else:
        transfer_top3 = transfer_df
    diag_sheets["transfer_analysis"] = transfer_top3

    # Ranked Pairs among 5 finalists
    print("\nRunning Ranked Pairs (Tideman) among 5 finalists…")
    finalist_list = sorted(finalists)
    raw_matchups  = []
    for i, ca in enumerate(finalist_list):
        for cb in finalist_list[i + 1:]:
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
    rp_winner, annotated_matchups = ranked_pairs_winner(raw_matchups, finalist_list)
    condorcet_df = pd.DataFrame(annotated_matchups).sort_values("lock_order").reset_index(drop=True)
    diag_sheets["condorcet"] = condorcet_df
    print(f"  Ranked Pairs winner: {rp_winner}  ({CAND_NAMES.get(rp_winner, rp_winner)})")

    # Save diagnostics
    diag_out = OUTPUT_DIR / "primary_diagnostics_2028.csv"
    combined_parts = []
    for sheet_name, df in diag_sheets.items():
        df2 = df.copy()
        df2.insert(0, "diagnostic", sheet_name)
        combined_parts.append(df2)
    diag_combined = pd.concat(combined_parts, ignore_index=True)
    diag_combined.to_csv(diag_out, index=False)
    print(f"Saved diagnostics → {diag_out}  ({len(diag_combined)} rows)")

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

    print("\n✓ Light fusion primary simulation complete.")
    print(f"  Finalists: {', '.join(CAND_NAMES[c] for c in finalist_list)}")


if __name__ == "__main__":
    main()
