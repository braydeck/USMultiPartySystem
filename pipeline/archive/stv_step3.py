"""
stv_step3.py
------------
STV engine: run one STV election per district using Gregory fractional
surplus transfer, weighted by commonpostweight.

Algorithm:
  - Droop quota: floor(sum_weights / (seats + 1)) + 1
  - Each voter carries a transfer_weight (starts at commonpostweight)
  - When a candidate reaches quota:
      surplus_factor = (tally - quota) / tally
      All ballots currently pointing at the winner are multiplied by surplus_factor
      Those voters' pointers advance to their next active preference
  - When no candidate reaches quota:
      Lowest-tally candidate is eliminated; their voters advance at full weight
  - Termination: last seats filled by default if remaining active == remaining seats
  - Transfer recording: every pointer advance logs {from_party, to_party, weight_moved}
"""

import numpy as np
import pandas as pd
from stv_config import OUTPUT_DIR, PARTY_LABELS, N_PARTIES


# ── STV engine for a single district ─────────────────────────────────────────

def run_stv_district(
    ballots:       np.ndarray,      # (N, 10) int8 — position i = rank i, value = party index
    weights:       np.ndarray,      # (N,) float64 — survey transfer weights
    seats:         int,
    district_id:   str,
    pre_dissolved: list = None,     # party indices to eliminate before round 1 (dissolution)
) -> dict:
    """
    Run fractional STV for one district.

    Returns dict:
        district_id : str
        seats       : int
        quota       : float
        total_weight: float
        n_ballots   : int
        elected     : list of int (party indices in election order)
        elim_order  : list of int (elimination order)
        transfers   : list of dicts {round, from_party, to_party, weight}
        round_log   : list of dicts (per-round tallies)
    """
    N = len(ballots)
    if N == 0:
        return {
            "district_id": district_id, "seats": seats, "quota": 0,
            "total_weight": 0, "n_ballots": 0,
            "elected": [], "elim_order": [], "transfers": [], "round_log": [],
        }

    total_wt = float(weights.sum())
    quota    = float(int(total_wt / (seats + 1)) + 1)

    # Working transfer weights (float copy)
    tw      = weights.astype(np.float64).copy()
    # Pointer: index into ballot row for each voter's current preference
    # -1 means exhausted
    pointer = np.zeros(N, dtype=np.int16)   # value = current rank position (0..9)

    # STATUS: 0=active, 1=elected, 2=eliminated
    status  = np.zeros(N_PARTIES, dtype=np.int8)

    # Pre-dissolution: mark specified parties as eliminated before any round.
    # advance_all_pointers() will cascade through them correctly on the first call
    # since it iterates positions 0→9 sequentially in a single pass.
    if pre_dissolved:
        for p in pre_dissolved:
            if 0 <= p < N_PARTIES:
                status[p] = 2

    elected    = []
    elim_order = []
    transfers  = []
    round_log  = []

    # ── Helper: advance each voter's pointer past non-active parties ──────────
    def advance_all_pointers():
        """
        For every voter, advance pointer until it points at an active party
        or runs off the end (exhausted = pointer >= N_PARTIES).
        Vectorized: iterate over rank positions.
        """
        for pos in range(N_PARTIES):
            # Which voters are currently at this position?
            at_pos = (pointer == pos)
            if not at_pos.any():
                continue
            # Check which of those voters' current party is still active
            current_party = ballots[at_pos, pos]      # shape (k,)
            is_active     = status[current_party] == 0
            # Voters pointing at an inactive party need to advance
            need_advance  = at_pos.copy()
            need_advance[at_pos] = ~is_active
            pointer[need_advance] = pos + 1

        # One more pass: voters at position 9 pointing at inactive party → exhaust
        at_9   = (pointer == N_PARTIES - 1)
        if at_9.any():
            parties_at_9 = ballots[at_9, N_PARTIES - 1]
            exhausted_9  = at_9.copy()
            exhausted_9[at_9] = status[parties_at_9] != 0
            pointer[exhausted_9] = N_PARTIES

    def compute_tallies() -> np.ndarray:
        """Sum transfer weights for each active party from current pointers."""
        tally = np.zeros(N_PARTIES, dtype=np.float64)
        not_exhausted = pointer < N_PARTIES
        if not not_exhausted.any():
            return tally
        valid_pos   = np.where(not_exhausted, pointer, 0)
        # Guard: clip pointer to [0, 9] for indexing
        safe_pos    = np.clip(valid_pos, 0, N_PARTIES - 1)
        curr_party  = ballots[np.arange(N), safe_pos]   # shape (N,)
        for j in range(N_PARTIES):
            if status[j] == 0:
                mask = not_exhausted & (curr_party == j)
                tally[j] = tw[mask].sum()
        return tally

    def record_and_advance_transfers(from_party: int, surplus_factor: float, rnd: int):
        """
        For voters currently pointing at from_party:
          1. Apply surplus_factor to their weights (if < 1.0, this is an election surplus)
          2. Advance pointer past from_party
          3. Re-advance past any newly eliminated/elected party
          4. Record the weight that flowed to each destination party
        """
        not_exhausted = pointer < N_PARTIES
        safe_pos      = np.clip(pointer, 0, N_PARTIES - 1)
        curr_party    = ballots[np.arange(N), safe_pos]
        from_mask     = not_exhausted & (curr_party == from_party)

        if not from_mask.any():
            return

        # Apply surplus factor to these voters' weights
        if surplus_factor < 1.0:
            tw[from_mask] *= surplus_factor

        # Advance these voters past from_party
        pointer[from_mask] += 1

        # Re-advance past any now-inactive parties (newly elected/eliminated)
        for pos in range(N_PARTIES):
            at_pos = from_mask & (pointer == pos)
            if not at_pos.any():
                continue
            party_here = ballots[at_pos, np.clip(pos, 0, N_PARTIES-1)]
            inactive   = status[party_here] != 0
            # Mark voters at an inactive party as needing further advance
            still_needs = at_pos.copy()
            still_needs[at_pos] = inactive
            pointer[still_needs] = pos + 1

        # Record where weight ended up
        not_ex2    = pointer < N_PARTIES
        safe_pos2  = np.clip(pointer, 0, N_PARTIES - 1)
        new_party  = ballots[np.arange(N), safe_pos2]

        for j in range(N_PARTIES):
            if j == from_party:
                continue
            if status[j] != 0:
                continue
            dest_mask = from_mask & not_ex2 & (new_party == j)
            if dest_mask.any():
                weight_moved = tw[dest_mask].sum()
                if weight_moved > 1e-9:
                    transfers.append({
                        "round":       rnd,
                        "district_id": district_id,
                        "from_party":  int(from_party),
                        "to_party":    int(j),
                        "weight":      float(weight_moved),
                    })

    # ── MAIN STV LOOP ─────────────────────────────────────────────────────────
    round_num = 0

    while len(elected) < seats:
        round_num += 1

        # Advance all pointers past any inactive parties
        advance_all_pointers()

        tally          = compute_tallies()
        active_parties = np.where(status == 0)[0]
        remaining_seats = seats - len(elected)

        # Termination: elect all remaining if active == remaining seats
        if len(active_parties) <= remaining_seats:
            for j in active_parties:
                elected.append(int(j))
                status[j] = 1
            break

        round_log.append({
            "round":  round_num,
            "tally":  {int(j): float(tally[j]) for j in active_parties},
            "quota":  quota,
            "n_active": int(len(active_parties)),
        })

        # Check for parties at or above quota
        at_quota = [(j, tally[j]) for j in active_parties if tally[j] >= quota]

        if at_quota:
            # Elect highest tally; tie-break: lower party index wins
            winner = max(at_quota, key=lambda x: (x[1], -x[0]))[0]
            surplus = tally[winner] - quota
            surplus_factor = (surplus / tally[winner]) if tally[winner] > 1e-12 else 0.0
            surplus_factor = max(0.0, min(1.0, surplus_factor))

            status[winner] = 1
            elected.append(int(winner))

            # Record transfers and advance pointers
            record_and_advance_transfers(winner, surplus_factor, round_num)

        else:
            # Eliminate lowest tally; tie-break: higher party index eliminated
            loser = min(active_parties, key=lambda j: (tally[j], -j))
            status[loser] = 2
            elim_order.append(int(loser))

            # Full-weight transfer (surplus_factor = 1.0)
            record_and_advance_transfers(loser, 1.0, round_num)

    return {
        "district_id":  district_id,
        "seats":        seats,
        "quota":        quota,
        "total_weight": total_wt,
        "n_ballots":    N,
        "elected":      elected,
        "elim_order":   elim_order,
        "transfers":    transfers,
        "round_log":    round_log,
    }


# ── Run all districts ─────────────────────────────────────────────────────────

def run_all_districts(
    df: pd.DataFrame,
    apportionment: pd.DataFrame,
    pre_dissolved: list = None,
) -> list:
    """
    Run STV for every district. Returns list of result dicts.
    Skips districts with zero respondents (logs warning).
    """
    results = []

    # Pre-extract arrays for speed
    ballots_array  = np.stack(df["ballot"].values)        # (N, 10)
    weights_array  = df["commonpostweight"].values         # (N,)
    district_array = df["district_id"].values              # (N,)

    n_districts  = len(apportionment)
    n_empty      = 0
    n_processed  = 0

    for _, district_row in apportionment.iterrows():
        did   = district_row["district_id"]
        seats = int(district_row["seat_count"])

        # Respondents assigned to this district
        idx = np.where(district_array == did)[0]

        if len(idx) == 0:
            n_empty += 1
            print(f"  WARNING: No respondents in district {did} — skipping")
            continue

        d_ballots = ballots_array[idx]
        d_weights = weights_array[idx]

        result = run_stv_district(d_ballots, d_weights, seats, did,
                                  pre_dissolved=pre_dissolved)
        result["density_tier"] = district_row["density_tier"]
        result["state_fips"]   = int(district_row["state_fips"])
        result["state_abbr"]   = district_row["state_abbr"]

        results.append(result)
        n_processed += 1

        if n_processed % 50 == 0:
            print(f"  ... {n_processed}/{n_districts} districts processed")

    print(f"  Districts processed: {n_processed}")
    if n_empty:
        print(f"  Districts skipped (no respondents): {n_empty}")

    return results


# ── Flatten results to DataFrame ─────────────────────────────────────────────

def results_to_dataframe(all_results: list, max_seats: int = 7) -> pd.DataFrame:
    """Flatten the list of STV result dicts into a tidy DataFrame."""
    rows = []
    for r in all_results:
        row = {
            "district_id":  r["district_id"],
            "state_fips":   r["state_fips"],
            "state_abbr":   r.get("state_abbr", ""),
            "density_tier": r["density_tier"],
            "seat_count":   r["seats"],
            "quota":        round(r["quota"], 4),
            "total_weight": round(r["total_weight"], 4),
            "n_ballots":    r["n_ballots"],
        }

        # Elected parties (up to max_seats columns)
        for k in range(max_seats):
            row[f"elected_party_{k}"] = (
                r["elected"][k] if k < len(r["elected"]) else None
            )

        # Round when each cluster was eliminated (-1 = elected, None = never competed)
        elim_round = {}
        for rnd_data in r.get("round_log", []):
            pass   # will compute from elim_order

        elim_order_list = r.get("elim_order", [])
        elected_set     = set(r.get("elected", []))

        for c in range(N_PARTIES):
            if c in elected_set:
                row[f"round_elim_c{c}"] = -1    # -1 = elected
            elif c in elim_order_list:
                row[f"round_elim_c{c}"] = elim_order_list.index(c) + 1
            else:
                row[f"round_elim_c{c}"] = None  # never appeared (zero weight)

        rows.append(row)

    return pd.DataFrame(rows)


# ── Standalone run ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    from stv_step1 import run_apportionment
    from stv_step2 import load_and_prepare

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("STEP 1: DISTRICT APPORTIONMENT")
    print("=" * 60)
    apportionment = run_apportionment()

    print("\n" + "=" * 60)
    print("STEP 2: BALLOT GENERATION")
    print("=" * 60)
    df = load_and_prepare(apportionment)

    print("\n" + "=" * 60)
    print("STEP 3: STV PER DISTRICT")
    print("=" * 60)
    all_results = run_all_districts(df, apportionment)

    df_results = results_to_dataframe(all_results)
    out_path   = OUTPUT_DIR / "stv_results_by_district.csv"
    df_results.to_csv(out_path, index=False)
    print(f"\n  Saved: {out_path}")
    print(f"  Shape: {df_results.shape}")

    # Quick summary
    total_seats_won = 0
    for r in all_results:
        total_seats_won += len(r["elected"])
    print(f"  Total seats filled: {total_seats_won}")
