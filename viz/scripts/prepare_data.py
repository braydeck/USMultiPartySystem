#!/usr/bin/env python3
"""Prepare CSV data from simulation outputs into JSON files for the React viz app."""

import csv
import json
import os
from pathlib import Path
from collections import defaultdict

OUTPUTS          = Path(__file__).parent.parent.parent / "data" / "outputs"
PURE_DIR         = OUTPUTS / "pure_only"
LIGHT_FUSION_DIR = OUTPUTS / "light_fusion"
FD_DIR           = OUTPUTS / "factor_deviation"
PURE_MULTI_DIR   = OUTPUTS / "pure_multi"
RESULTS          = Path(__file__).parent.parent.parent / "results"
DATA_OUT = Path(__file__).parent.parent / "src" / "data"
DATA_OUT.mkdir(parents=True, exist_ok=True)

CLUSTER_TO_PARTY = {
    "0": "CON", "1": "SD", "2": "STY", "3": "NAT",
    "4": "LIB", "5": "REF", "6": "CTR", "8": "DSA", "9": "PRG",
}

# Soft-weighted national population shares per cluster (excluding C7/Blue Dogs, renormalized to 100%)
# Derived from: np.average(prob_cluster_k, weights=commonpostweight), then renormalized.
# Matches the GMM posterior scoring used in ballot generation.
NATIONAL_POP_SHARES = {
    0: 18.73,   # CON
    1: 15.63,   # SD
    2: 15.04,   # STY
    3:  9.19,   # NAT
    4:  9.30,   # LIB
    5: 11.01,   # REF
    6:  9.86,   # CTR
    8:  6.27,   # DSA
    9:  4.96,   # PRG
}

# Map platonic candidate short codes to party abbreviations
CANDIDATE_TO_PARTY = {
    "RH": "CON", "MW": "SD", "MRJ": "STY", "BE": "NAT",
    "CO": "LIB", "DH": "REF", "LK": "CTR", "ZN": "DSA", "JR": "PRG",
}

def normalize_candidate_code(code: str) -> str:
    """Convert candidate code to display code.
    - Short pure codes (RH, MW…) → party abbreviation (CON, SD…)
    - Light fusion codes (STY_sd, CON_ref…) → kept as-is (lowercase suffix)
    - Blended codes (SD_STY, CON_CTR…) → slash-separated (SD/STY, CON/CTR)
    """
    code = code.strip()
    if code in CANDIDATE_TO_PARTY:
        return CANDIDATE_TO_PARTY[code]
    # Light fusion: underscore with lowercase suffix — keep unchanged
    if "_" in code:
        suffix = code.split("_", 1)[1]
        if suffix == suffix.lower():
            return code
    return code.replace("_", "/")

PARTY_NAMES = {
    "CON": "Conservative", "SD": "Social Democrat", "STY": "Solidarity",
    "NAT": "Nationalist", "LIB": "Liberal", "REF": "Reform",
    "CTR": "Center", "DSA": "Democratic Socialists", "PRG": "Progressive",
}

def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_json(data, name):
    path = DATA_OUT / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    print(f"  Wrote {path.name} ({os.path.getsize(path):,} bytes)")


# ---------- primary.json ----------
def build_primary():
    rows = read_csv(OUTPUTS / "primary_results_2028.csv")
    centroids = {r["candidate_code"]: r for r in read_csv(OUTPUTS / "candidate_factor_centroids.csv")}

    stages_order = ["After_Retail_Six", "After_Pod_A", "After_Pod_C", "After_Pod_BD"]
    stage_labels = {
        "After_Retail_Six": "Retail + Bench States",
        "After_Pod_A": "After Pod A (West)",
        "After_Pod_C": "After Pod C (South)",
        "After_Pod_BD": "After Pods B+D (Final)",
    }

    by_candidate = defaultdict(dict)
    quota_by_stage = {}
    for row in rows:
        stage = row["winnowing_point"]
        code = row["candidate_code"]
        by_candidate[code][stage] = {
            "voteTotal": float(row["vote_total"]),
            "votePct": float(row["vote_pct"]),
            "status": row["status"],
            "quotaThreshold": float(row["quota_threshold"]),
        }
        quota_by_stage[stage] = float(row["quota_threshold"])

    candidates = []
    for raw_code, stages in by_candidate.items():
        display_code = normalize_candidate_code(raw_code)
        c = centroids.get(raw_code, {})
        name = c.get("candidate_name", display_code) or display_code
        entry = {
            "code": display_code,
            "name": name,
            "F1": float(c.get("F1_security_order", 0)),
            "F2": float(c.get("F2_electoral_skepticism", 0)),
            "F3": float(c.get("F3_government_distrust", 0)),
            "F4": float(c.get("F4_religious_traditionalism", 0)),
            "F5": float(c.get("F5_populist_conservatism", 0)),
            "stages": {s: stages.get(s, {"voteTotal": 0, "votePct": 0, "status": "previously_eliminated", "quotaThreshold": quota_by_stage.get(s, 0)}) for s in stages_order},
        }
        candidates.append(entry)

    output = {
        "stagesOrder": stages_order,
        "stageLabels": stage_labels,
        "quotaByStage": quota_by_stage,
        "candidates": candidates,
    }
    write_json(output, "primary.json")


# ---------- primaryStateWinners.json ----------
# Maps each state's presidential primary winner to pods so the map can reveal by stage.
STAGE_TO_PODS = {
    "After_Retail_Six": {"Retail"},
    "After_Pod_A":       {"Retail", "A"},
    "After_Pod_C":       {"Retail", "A", "C"},
    "After_Pod_BD":      {"Retail", "A", "B", "C", "D"},
}

def build_primary_state_winners():
    state_rows = read_csv(OUTPUTS / "irv" / "irv_presidential_states_2028.csv")
    pod_rows = read_csv(OUTPUTS / "state_pod_assignments.csv")
    profile_rows = read_csv(OUTPUTS / "state_candidate_profiles.csv")

    pod_by_fips = {r["state_fips"].zfill(2): r["pod"] for r in pod_rows}

    # Build per-state first-choice shares from all ~20 primary candidates
    first_choice_by_fips = {}
    for r in profile_rows:
        fips = r["state_fips"].zfill(2)
        fc_cols = [k for k in r.keys() if k.startswith("first_choice_")]
        shares = {}
        for col in fc_cols:
            raw_code = col.replace("first_choice_", "")
            display_code = normalize_candidate_code(raw_code)
            val = float(r.get(col) or 0)
            if val > 0:
                shares[display_code] = shares.get(display_code, 0) + val
        total = sum(shares.values())
        if total > 0:
            first_choice_by_fips[fips] = {k: round(v / total, 4) for k, v in shares.items()}

    out = {}
    for r in state_rows:
        fips = r["state_fips"].zfill(2)
        winner = r["winner_code"].replace("_", "/")
        runner_up = r["runner_up_code"].replace("_", "/")
        pod = pod_by_fips.get(fips, "D")
        out[fips] = {
            "stateAbbr": r["state_abbr"],
            "winnerCode": winner,
            "runnerUpCode": runner_up,
            "pod": pod,
            "nRespondents": int(r["n_respondents"]),
            "shares": first_choice_by_fips.get(fips, {}),
        }
    write_json(out, "primaryStateWinners.json")


# ---------- senate*.json ----------
def _extract_senate_condorcet(rows):
    out = []
    for r in rows:
        out.append({
            "stateFips": r["state_fips"].zfill(2),
            "stateAbbr": r["state_abbr"],
            "senatorCode": r.get("senator_code", ""),
            "senatorLabel": r.get("senator_label", ""),
            "senatorType": r.get("senator_type", ""),
            "primaryCluster": r.get("primary_cluster", ""),
            "secondaryCluster": r.get("secondary_cluster", ""),
        })
    return out


def _extract_senate_irv(rows):
    out = []
    for r in rows:
        out.append({
            "stateFips": r["state_fips"].zfill(2),
            "stateAbbr": r["state_abbr"],
            "senatorCode": r.get("winner_code", ""),
            "senatorLabel": r.get("winner_label", ""),
            "senatorType": r.get("winner_type", ""),
            "primaryCluster": r.get("winner_primary_cluster", ""),
            "secondaryCluster": r.get("winner_secondary_cluster", ""),
        })
    return out


def build_senate():
    cond_rows = read_csv(OUTPUTS / "senate" / "senate_composition.csv")
    irv_rows  = read_csv(OUTPUTS / "senate" / "senate_irv_composition.csv")
    write_json(_extract_senate_condorcet(cond_rows), "senateCondorcet.json")
    write_json(_extract_senate_irv(irv_rows), "senateIRV.json")


def build_senate_pure():
    cond_rows = read_csv(PURE_DIR / "senate" / "senate_composition.csv")
    irv_rows  = read_csv(PURE_DIR / "senate" / "senate_irv_composition.csv")
    write_json(_extract_senate_condorcet(cond_rows), "senateCondorcetPure.json")
    write_json(_extract_senate_irv(irv_rows), "senateIRVPure.json")


def build_senate_light_fusion():
    """Senate compositions from the 25-candidate light fusion simulation.
    Both Condorcet and IRV outputs use senator_code/senator_label columns.
    """
    cond_rows = read_csv(LIGHT_FUSION_DIR / "senate" / "senate_composition.csv")
    irv_rows  = read_csv(LIGHT_FUSION_DIR / "senate" / "senate_irv_composition.csv")
    write_json(_extract_senate_condorcet(cond_rows), "senateCondorcetLightFusion.json")
    write_json(_extract_senate_condorcet(irv_rows),  "senateIRVLightFusion.json")


# ── LF senate vote model helpers ─────────────────────────────────────────────

_LF_CLUSTER_MAP: dict = {
    "PRG_dsa": (9, 8), "DSA_prg": (8, 9), "DSA_lib": (8, 4),
    "LIB_dsa": (4, 8), "LIB_sd":  (4, 1), "SD_lib":  (1, 4),
    "SD_sty":  (1, 2), "STY_sd":  (2, 1), "STY_ctr": (2, 6),
    "CTR_sty": (6, 2), "CTR_con": (6, 0), "CON_ctr": (0, 6),
    "CON_ref": (0, 5), "REF_con": (5, 0), "REF_nat": (5, 3),
    "NAT_ref": (3, 5),
}
_PURE_CLUSTER: dict = {
    "CON": 0, "SD": 1, "STY": 2, "NAT": 3, "LIB": 4,
    "REF": 5, "CTR": 6, "DSA": 8, "PRG": 9,
}

def _lf_senator_support(code: str, cluster_row: dict) -> float:
    """Return the % supporting a bill for a given LF senator, using cluster stats row."""
    def _c(k: int) -> float:
        return float(cluster_row.get(f"c{k}") or 0)
    if code in _PURE_CLUSTER:
        return _c(_PURE_CLUSTER[code])
    if code in _LF_CLUSTER_MAP:
        p, s = _LF_CLUSTER_MAP[code]
        return 0.80 * _c(p) + 0.20 * _c(s)
    return 0.0

def _fd_prob_pass(seat_counts: dict, fd_by_var: dict, majority: int = 26) -> dict:
    """Compute prob_pass/verdict for FD senate using Normal approximation.
    seat_counts: {senator_code: n_seats}
    fd_by_var: {variable: fd_stats_row}  — % Supporting rows for FD candidates
    Returns: {variable: {"prob_pass": float, "verdict": str}}
    """
    import math
    results = {}
    for var, row in fd_by_var.items():
        mu = 0.0
        var_sum = 0.0
        for code, n in seat_counts.items():
            p = float(row.get(code) or 0) / 100.0
            mu += n * p
            var_sum += n * p * (1 - p)
        sigma = math.sqrt(var_sum) if var_sum > 0 else 1e-6
        z = (majority - 0.5 - mu) / sigma
        def _ncdf(x: float) -> float:
            if x > 6: return 1.0
            if x < -6: return 0.0
            t = 1.0 / (1.0 + 0.2316419 * abs(x))
            d = 0.3989422803 * math.exp(-0.5 * x * x)
            p_approx = d * t * (0.3193815 + t * (-0.3565638 + t * (1.7814779 + t * (-1.8212560 + t * 1.3302744))))
            return p_approx if x < 0 else 1.0 - p_approx
        prob = 1.0 - _ncdf(z)
        verdict = "PASS" if prob >= 0.7 else "FAIL" if prob <= 0.3 else "TOSS-UP"
        results[var] = {"prob_pass": round(prob, 4), "verdict": verdict}
    return results


def _lf_prob_pass(seat_counts: dict, cluster_by_var: dict, majority: int = 26) -> tuple:
    """Compute prob_pass and verdict for LF senate using Normal approximation.
    seat_counts: {senator_code: n_seats}
    cluster_by_var: {variable: cluster_row_dict}
    Returns: {variable: {"prob_pass": float, "verdict": str}}
    """
    import math
    results = {}
    for var, crow in cluster_by_var.items():
        mu = 0.0
        var_sum = 0.0
        for code, n in seat_counts.items():
            p = _lf_senator_support(code, crow) / 100.0
            mu += n * p
            var_sum += n * p * (1 - p)
        sigma = math.sqrt(var_sum) if var_sum > 0 else 1e-6
        # Continuity-corrected P(Y >= majority)
        z = (majority - 0.5 - mu) / sigma
        # Normal CDF approximation (Abramowitz & Stegun 26.2.17)
        def _ncdf(x: float) -> float:
            if x > 6:
                return 1.0
            if x < -6:
                return 0.0
            t = 1.0 / (1.0 + 0.2316419 * abs(x))
            d = 0.3989422803 * math.exp(-0.5 * x * x)
            p_approx = d * t * (0.3193815 + t * (-0.3565638 + t * (1.7814779 + t * (-1.8212560 + t * 1.3302744))))
            return p_approx if x < 0 else 1.0 - p_approx
        prob = 1.0 - _ncdf(z)
        if prob >= 0.7:
            verdict = "PASS"
        elif prob <= 0.3:
            verdict = "FAIL"
        else:
            verdict = "TOSS-UP"
        results[var] = {"prob_pass": round(prob, 4), "verdict": verdict}
    return results


# ---------- senateVoteModel.json ----------
def build_senate_vote_model():
    rows = read_csv(RESULTS / "vote_model.csv")

    # Load cluster stats for LF vote model computation
    cluster_rows = read_csv(OUTPUTS / "profiles" / "cluster_stats.csv")
    cluster_by_var = {
        r["variable"]: r
        for r in cluster_rows
        if r.get("stat_label") == "% Supporting" and r.get("type") == "binary"
    }

    cond_lf_seats = {}
    irv_lf_seats = {}
    for r in read_csv(LIGHT_FUSION_DIR / "senate" / "senate_composition.csv"):
        cond_lf_seats[r["senator_code"]] = cond_lf_seats.get(r["senator_code"], 0) + 1
    for r in read_csv(LIGHT_FUSION_DIR / "senate" / "senate_irv_composition.csv"):
        irv_lf_seats[r["senator_code"]] = irv_lf_seats.get(r["senator_code"], 0) + 1

    lf_cond_results = _lf_prob_pass(cond_lf_seats, cluster_by_var)
    lf_irv_results  = _lf_prob_pass(irv_lf_seats,  cluster_by_var)

    # STY_ctr (LF president) signing = 80% STY (c2) + 20% CTR (c6)
    lf_pres_signs = {}
    lf_pres_pct = {}
    for var, crow in cluster_by_var.items():
        support = 0.80 * float(crow.get("c2") or 0) + 0.20 * float(crow.get("c6") or 0)
        lf_pres_signs[var] = "SIGN" if support > 50 else "VETO"
        lf_pres_pct[var] = round(support, 2)

    # ── Factor Deviation senate vote model ──────────────────────────────────
    fd_stats_rows = read_csv(FD_DIR / "profiles" / "factor_deviation_stats.csv")
    fd_by_var = {
        r["variable"]: r
        for r in fd_stats_rows
        if r.get("stat_label") == "% Supporting" and r.get("type") == "binary"
           and r.get("variable", "").startswith("CC24_")
    }

    cond_fd_seats = {}
    irv_fd_seats = {}
    for r in read_csv(FD_DIR / "senate" / "senate_composition.csv"):
        cond_fd_seats[r["senator_code"]] = cond_fd_seats.get(r["senator_code"], 0) + 1
    for r in read_csv(FD_DIR / "senate" / "senate_irv_composition.csv"):
        irv_fd_seats[r["senator_code"]] = irv_fd_seats.get(r["senator_code"], 0) + 1

    fd_cond_results = _fd_prob_pass(cond_fd_seats, fd_by_var)
    fd_irv_results  = _fd_prob_pass(irv_fd_seats,  fd_by_var)

    # FD presidential winners — read dynamically from simulation outputs
    fd_irv_winner = None
    for r in read_csv(FD_DIR / "irv" / "irv_presidential_national_2028.csv"):
        if r.get("winner") == "True":
            fd_irv_winner = r["candidate_code"]
    fd_cond_winner = None
    _cm_rows = list(read_csv(FD_DIR / "irv" / "condorcet_matchups_2028.csv"))
    if _cm_rows:
        fd_cond_winner = _cm_rows[0].get("condorcet_winner") or None

    fd_pres_irv_signs = {}
    fd_pres_irv_pct   = {}
    fd_pres_cond_signs = {}
    fd_pres_cond_pct   = {}
    for var, row in fd_by_var.items():
        irv_sup  = float(row.get(fd_irv_winner)  or 0) if fd_irv_winner  else 0.0
        cond_sup = float(row.get(fd_cond_winner) or 0) if fd_cond_winner else 0.0
        fd_pres_irv_signs[var]   = "SIGN" if irv_sup  > 50 else "VETO"
        fd_pres_irv_pct[var]     = round(irv_sup, 2)
        fd_pres_cond_signs[var]  = "SIGN" if cond_sup > 50 else "VETO"
        fd_pres_cond_pct[var]    = round(cond_sup, 2)
    # Alias for backwards compat — IRV winner is the "default" FD president
    fd_pres_signs = fd_pres_irv_signs
    fd_pres_pct   = fd_pres_irv_pct

    # ── Raw Multi presidential winners ───────────────────────────────────────
    rm_irv_winner = None
    for r in read_csv(PURE_MULTI_DIR / "irv" / "irv_presidential_national_2028.csv"):
        if r.get("winner", "").strip() == "True":
            rm_irv_winner = r["candidate_code"]   # e.g. "SD_1"
    rm_cond_winner = None
    _rm_cm = list(read_csv(PURE_MULTI_DIR / "irv" / "condorcet_matchups_2028.csv"))
    if _rm_cm:
        rm_cond_winner = _rm_cm[0].get("condorcet_winner") or None   # e.g. "CTR_1"

    def _rm_party(code):
        return code.rsplit("_", 1)[0] if code else ""

    presRawMultiIRV_signs,  presRawMultiIRV_pct  = {}, {}
    presRawMultiCond_signs, presRawMultiCond_pct = {}, {}
    for var, crow in cluster_by_var.items():
        irv_party  = _rm_party(rm_irv_winner)
        cond_party = _rm_party(rm_cond_winner)
        irv_sup  = _lf_senator_support(irv_party,  crow)
        cond_sup = _lf_senator_support(cond_party, crow)
        presRawMultiIRV_signs[var]  = "SIGN" if irv_sup  > 50 else "VETO"
        presRawMultiIRV_pct[var]    = round(irv_sup, 2)
        presRawMultiCond_signs[var] = "SIGN" if cond_sup > 50 else "VETO"
        presRawMultiCond_pct[var]   = round(cond_sup, 2)

    # Raw Multi senate seat counts (strip _N suffix to aggregate by pure party)
    cond_rm_seats, irv_rm_seats = {}, {}
    for r in read_csv(PURE_MULTI_DIR / "senate" / "senate_composition.csv"):
        party = r["senator_code"].rsplit("_", 1)[0]
        cond_rm_seats[party] = cond_rm_seats.get(party, 0) + 1
    for r in read_csv(PURE_MULTI_DIR / "senate" / "senate_irv_composition.csv"):
        party = r["senator_code"].rsplit("_", 1)[0]
        irv_rm_seats[party] = irv_rm_seats.get(party, 0) + 1

    rm_cond_results = _lf_prob_pass(cond_rm_seats, cluster_by_var)
    rm_irv_results  = _lf_prob_pass(irv_rm_seats,  cluster_by_var)

    # Corrected pure presidential signing — actual winner is SD, not STY as in legacy vote_model.csv
    presPure_signs, presPure_pct = {}, {}
    for var, crow in cluster_by_var.items():
        sd_sup = _lf_senator_support("SD", crow)
        presPure_signs[var] = "SIGN" if sd_sup > 50 else "VETO"
        presPure_pct[var]   = round(sd_sup, 2)

    # State STV house (873 seats, majority = 437) — for LegislationTab house column
    stv_house_seat_counts = {}
    stv_house_total = 0
    for r in read_csv(OUTPUTS / "house" / "house_seat_summary.csv"):
        stv_house_seat_counts[r["party"]] = int(r["seats"])
        stv_house_total += int(r["seats"])
    stv_house_majority = stv_house_total // 2 + 1
    stv_house_results = _lf_prob_pass(stv_house_seat_counts, cluster_by_var, majority=stv_house_majority)

    # Compute SD/CON (Condorcet blended president) signing decisions from chamber profile
    senate_prof_rows = read_csv(OUTPUTS / "senate" / "senate_chamber_profile.csv")
    sdcon_pct = {}
    for r in senate_prof_rows:
        if r.get("stat_label") == "% Supporting" and r.get("variable", "").startswith("CC24_"):
            try:
                sdcon_pct[r["variable"]] = float(r["SD/CON"])
            except (KeyError, ValueError):
                pass

    out = []
    for r in rows:
        var = r["variable"]
        sdcon_support = sdcon_pct.get(var)
        pres_mixed_cond_pct = round(sdcon_support, 2) if sdcon_support is not None else float(r.get("pres_mixed_support_pct", 0))
        pres_mixed_cond_signs = ("SIGN" if sdcon_support > 50 else "VETO") if sdcon_support is not None else r["pres_mixed_signs"]

        lf_cond = lf_cond_results.get(var, {"prob_pass": 0.0, "verdict": "N/A"})
        lf_irv  = lf_irv_results.get(var, {"prob_pass": 0.0, "verdict": "N/A"})

        out.append({
            "variable": var,
            "domain": r["domain"],
            "question": r["question"],
            "overallPct": float(r["overall_pct"]),
            # Mixed senate scenarios (new keys + legacy aliases for UnifiedBillTable)
            "condMixedProbPass": float(r["senate_cond_prob_pass"]),
            "condMixedVerdict": r["senate_cond_verdict"],
            "irvMixedProbPass": float(r["senate_irv_prob_pass"]),
            "irvMixedVerdict": r["senate_irv_verdict"],
            # Legacy aliases (UnifiedBillTable reads these)
            "condProbPass": float(r["senate_cond_prob_pass"]),
            "condVerdict": r["senate_cond_verdict"],
            "irvProbPass": float(r["senate_irv_prob_pass"]),
            "irvVerdict": r["senate_irv_verdict"],
            # Pure senate scenarios
            "condPureProbPass": float(r["senate_cond_pure_prob_pass"]),
            "condPureVerdict": r["senate_cond_pure_verdict"],
            "irvPureProbPass": float(r["senate_irv_pure_prob_pass"]),
            "irvPureVerdict": r["senate_irv_pure_verdict"],
            # Light Fusion senate scenarios (kept for backwards compat)
            "condLFProbPass": lf_cond["prob_pass"],
            "condLFVerdict":  lf_cond["verdict"],
            "irvLFProbPass":  lf_irv["prob_pass"],
            "irvLFVerdict":   lf_irv["verdict"],
            # LF president (STY_ctr) — kept for backwards compat
            "presLFSigns": lf_pres_signs.get(var, "VETO"),
            "presLFPct":   lf_pres_pct.get(var, 0.0),
            # Factor Deviation senate scenarios
            "condFDProbPass": fd_cond_results.get(var, {}).get("prob_pass", 0.0),
            "condFDVerdict":  fd_cond_results.get(var, {}).get("verdict", "N/A"),
            "irvFDProbPass":  fd_irv_results.get(var, {}).get("prob_pass", 0.0),
            "irvFDVerdict":   fd_irv_results.get(var, {}).get("verdict", "N/A"),
            # FD president — separate fields for IRV and Condorcet winners
            "presFDSigns":     fd_pres_irv_signs.get(var, "VETO"),   # alias = IRV
            "presFDPct":       fd_pres_irv_pct.get(var, 0.0),
            "presFDIRVSigns":  fd_pres_irv_signs.get(var, "VETO"),
            "presFDIRVPct":    fd_pres_irv_pct.get(var, 0.0),
            "presFDCondSigns": fd_pres_cond_signs.get(var, "VETO"),
            "presFDCondPct":   fd_pres_cond_pct.get(var, 0.0),
            # Presidential sign + support pct
            "presMixedSigns": r["pres_mixed_signs"],         # CON/SD (blended IRV winner)
            "presMixedPct":   float(r.get("pres_mixed_support_pct", 0)),
            "presMixedCondSigns": pres_mixed_cond_signs,     # SD/CON (blended Condorcet)
            "presMixedCondPct": pres_mixed_cond_pct,
            "presPureSigns": presPure_signs.get(var, "VETO"),  # SD (actual pure winner)
            "presPurePct":   presPure_pct.get(var, 0.0),
            # Raw Multi senate scenarios
            "condRawMultiProbPass": rm_cond_results.get(var, {}).get("prob_pass", 0.0),
            "condRawMultiVerdict":  rm_cond_results.get(var, {}).get("verdict", "N/A"),
            "irvRawMultiProbPass":  rm_irv_results.get(var, {}).get("prob_pass", 0.0),
            "irvRawMultiVerdict":   rm_irv_results.get(var, {}).get("verdict", "N/A"),
            # Raw Multi president (SD_1 IRV, CTR_1 Condorcet)
            "presRawMultiIRVSigns":  presRawMultiIRV_signs.get(var, "VETO"),
            "presRawMultiIRVPct":    presRawMultiIRV_pct.get(var, 0.0),
            "presRawMultiCondSigns": presRawMultiCond_signs.get(var, "VETO"),
            "presRawMultiCondPct":   presRawMultiCond_pct.get(var, 0.0),
            # State STV house (for LegislationTab house column)
            "houseStvProbPass": stv_house_results.get(var, {}).get("prob_pass", 0.0),
            "houseStvVerdict":  stv_house_results.get(var, {}).get("verdict", "N/A"),
        })
    write_json(out, "senateVoteModel.json")


# ---------- houseSeats.json ----------
def build_house_seats():
    rows = read_csv(OUTPUTS / "pure_multi" / "house" / "stv_seat_summary.csv")
    out = []
    for r in rows:
        if int(r["party"]) == 7:  # skip Blue Dogs (C7 — merged into adjacent clusters)
            continue
        cluster = int(r["party"])
        out.append({
            "party": cluster,
            "partyName": r["party_name"],
            "urban": int(r["URBAN"]),
            "suburban": int(r["SUBURBAN"]),
            "rural": int(r["RURAL"]),
            "national": int(r["NATIONAL"]),
            "pctNational": float(r["pct_national"]),
            "pctPopulation": NATIONAL_POP_SHARES.get(cluster, 0.0),
        })
    write_json(out, "houseSeats.json")


def build_house_transfers():
    """Compute transfer preference matrix from party ballots."""
    ballot_path = PURE_MULTI_DIR / "party_ballots.csv"
    if not ballot_path.exists():
        ballot_path = PURE_MULTI_DIR / "presidential_ballots.csv"
    if not ballot_path.exists():
        write_json([], "houseTransfers.json")
        return

    # Read ballots and weights using csv reader
    ballot_rows = read_csv(str(ballot_path))
    weight_rows = read_csv(str(Path(__file__).parent.parent.parent / "data" / "processed" / "efa_factor_scores.csv"))

    def base_party(code):
        if "_" in code and code.rsplit("_", 1)[1].isdigit():
            return code.rsplit("_", 1)[0]
        return code

    # Discover base party codes
    base_codes = sorted(set(base_party(r["rank_1"]) for r in ballot_rows))

    transfers = {src: {dst: 0.0 for dst in base_codes} for src in base_codes}
    first_totals = {c: 0.0 for c in base_codes}

    for i, br in enumerate(ballot_rows):
        w = float(weight_rows[i]["commonpostweight"])
        first  = base_party(br["rank_1"])
        second = base_party(br["rank_2"])
        first_totals[first] += w
        transfers[first][second] += w

    out = []
    for src in base_codes:
        total = first_totals[src] or 1.0
        dests = []
        for dst in base_codes:
            if dst == src:
                continue
            pct = transfers[src][dst] / total * 100
            if pct > 0.5:
                dests.append({"party": dst, "pct": round(pct, 1)})
        dests.sort(key=lambda x: -x["pct"])
        out.append({
            "source": src,
            "totalVoters": round(first_totals[src], 0),
            "destinations": dests,
        })
    write_json(out, "houseTransfers.json")


def build_fd_variant_attraction():
    """For each FD variant, show where first-choice voters come from (home vs cross-party)."""
    ballot_path = FD_DIR / "ballots.csv"
    if not ballot_path.exists():
        write_json([], "fdVariantAttraction.json")
        return

    ballot_rows = read_csv(str(ballot_path))
    typology_rows = read_csv(str(Path(__file__).parent.parent.parent / "data" / "processed" / "typology_cluster_assignments.csv"))

    CLUSTER_TO_PARTY = {"0":"CON","1":"SD","2":"STY","3":"NAT","4":"LIB","5":"REF","6":"CTR","7":"C7","8":"DSA","9":"PRG"}

    # variant → {source_party: weighted_count}
    variant_sources: dict = {}
    variant_totals: dict = {}

    for i, br in enumerate(ballot_rows):
        variant = br.get("rank_1", "")
        cluster = typology_rows[i].get("cluster", "")
        home = CLUSTER_TO_PARTY.get(str(cluster), "")
        if home == "C7" or not home:
            continue
        w = float(typology_rows[i].get("commonpostweight", 1))
        if variant not in variant_sources:
            variant_sources[variant] = {}
            variant_totals[variant] = 0.0
        variant_sources[variant][home] = variant_sources[variant].get(home, 0.0) + w
        variant_totals[variant] += w

    out = []
    for variant in sorted(variant_sources.keys()):
        total = variant_totals[variant]
        if total < 50:
            continue
        parts = variant.split("_")
        party = parts[0]
        if len(parts) == 3:
            direction = parts[1]   # hi / lo
            axis = parts[2]        # so / ae / pc / rt
        else:
            axis = "base"
            direction = "base"

        home_pct = variant_sources[variant].get(party, 0) / total * 100
        sources = []
        for src_party, w in sorted(variant_sources[variant].items(), key=lambda x: -x[1]):
            pct = w / total * 100
            if pct >= 2:
                sources.append({"party": src_party, "pct": round(pct, 1)})

        out.append({
            "variant": variant,
            "party": party,
            "axis": axis,
            "direction": direction,
            "totalVoters": round(total, 0),
            "homePct": round(home_pct, 1),
            "crossPct": round(100 - home_pct, 1),
            "sources": sources,
        })

    out.sort(key=lambda x: -x["crossPct"])
    write_json(out, "fdVariantAttraction.json")


def build_house_seats_gauss():
    """Gaussian reference run — reads the _gauss suffix file."""
    rows = read_csv(OUTPUTS / "pure_multi" / "house" / "stv_seat_summary_gauss.csv")
    out = []
    for r in rows:
        if int(r["party"]) == 7:
            continue
        cluster = int(r["party"])
        out.append({
            "party": cluster,
            "partyName": r["party_name"],
            "urban": int(r["URBAN"]),
            "suburban": int(r["SUBURBAN"]),
            "rural": int(r["RURAL"]),
            "national": int(r["NATIONAL"]),
            "pctNational": float(r["pct_national"]),
            "pctPopulation": NATIONAL_POP_SHARES.get(cluster, 0.0),
        })
    write_json(out, "houseSeatsProbBased.json")


# ---------- houseVoteModel.json ----------
def build_house_vote_model():
    rows = read_csv(OUTPUTS / "house_vote_model.csv")

    # Load cluster stats for State STV house probability computation
    cluster_rows = read_csv(OUTPUTS / "profiles" / "cluster_stats.csv")
    cluster_by_var_h = {
        r["variable"]: r
        for r in cluster_rows
        if r.get("stat_label") == "% Supporting" and r.get("type") == "binary"
    }

    # State STV seat counts (from new house pipeline)
    stv_seat_counts = {}
    total_stv = 0
    for r in read_csv(OUTPUTS / "house" / "house_seat_summary.csv"):
        stv_seat_counts[r["party"]] = int(r["seats"])
        total_stv += int(r["seats"])
    stv_majority = total_stv // 2 + 1
    stv_results = _lf_prob_pass(stv_seat_counts, cluster_by_var_h, majority=stv_majority)

    # Raw Multi house seats (pure_multi — integer cluster id -> party code)
    _cluster_to_party = {v: k for k, v in _PURE_CLUSTER.items()}
    rm_house_seats: dict = {}
    rm_house_total = 0
    for r in read_csv(PURE_MULTI_DIR / "house" / "stv_seat_summary.csv"):
        cluster = int(r["party"])
        if cluster == 7:
            continue
        code = _cluster_to_party.get(cluster, str(cluster))
        rm_house_seats[code] = rm_house_seats.get(code, 0) + int(r["NATIONAL"])
        rm_house_total += int(r["NATIONAL"])
    rm_house_majority = rm_house_total // 2 + 1
    rm_house_results = _lf_prob_pass(rm_house_seats, cluster_by_var_h, majority=rm_house_majority)

    # FD house seats (factor_deviation — party column is already a code, group by base party)
    fd_house_seats: dict = {}
    fd_house_total = 0
    for r in read_csv(FD_DIR / "house" / "stv_seat_summary.csv"):
        code = r["party"]
        fd_house_seats[code] = fd_house_seats.get(code, 0) + int(r["NATIONAL"])
        fd_house_total += int(r["NATIONAL"])
    fd_house_majority = fd_house_total // 2 + 1
    fd_house_results = _lf_prob_pass(fd_house_seats, cluster_by_var_h, majority=fd_house_majority)

    out = []
    for r in rows:
        var = r["variable"]
        stv = stv_results.get(var, {"prob_pass": 0.0, "verdict": "N/A"})
        rm  = rm_house_results.get(var, {"prob_pass": 0.0, "verdict": "N/A"})
        fd  = fd_house_results.get(var, {"prob_pass": 0.0, "verdict": "N/A"})
        out.append({
            "variable": var,
            "domain": r["domain"],
            "question": r["question"],
            "overallPct": float(r["overall_pct"]),
            "probPass": float(r["house_prob_pass"]),
            "verdict": r["house_verdict"],
            "houseStvProbPass":      stv["prob_pass"],
            "houseStvVerdict":       stv["verdict"],
            "houseRawMultiProbPass": rm["prob_pass"],
            "houseRawMultiVerdict":  rm["verdict"],
            "houseFDProbPass":       fd["prob_pass"],
            "houseFDVerdict":        fd["verdict"],
        })
    write_json(out, "houseVoteModel.json")


# ---------- houseStateMap.json ----------
def build_house_state_map():
    """Aggregate house STV results by state to find plurality party per state."""
    rows = read_csv(OUTPUTS / "pure_multi" / "house" / "stv_results_by_district.csv")
    pod_rows = read_csv(OUTPUTS / "state_pod_assignments.csv")
    abbr_by_fips = {r["state_fips"].zfill(2): r["state_abbr"] for r in pod_rows}

    state_seats = defaultdict(lambda: defaultdict(int))
    for row in rows:
        fips = row["state_fips"].zfill(2)
        for i in range(9):
            v = row.get(f"elected_{i}", "").strip()
            if v:
                state_seats[fips][v] += 1

    out = {}
    for fips, counts in state_seats.items():
        total = sum(counts.values())
        plurality = max(counts, key=counts.get)
        out[fips] = {
            "stateAbbr": abbr_by_fips.get(fips, fips),
            "pluralityParty": plurality,
            "totalSeats": total,
            "seats": dict(counts),
        }
    write_json(out, "houseStateMap.json")


# ---------- coalitionProfiles.json ----------
def build_coalition_profiles():
    rows = read_csv(OUTPUTS / "coalitions" / "coalition_type_profiles.csv")
    out = []
    for r in rows:
        out.append({
            "type": r["type"],
            "chamber": r["chamber"],
            "F1": float(r["F1_security_order"]),
            "F2": float(r["F2_electoral_skepticism"]),
            "F3": float(r["F3_government_distrust"]),
            "F4": float(r["F4_religious_traditionalism"]),
            "F5": float(r["F5_populist_conservatism"]),
            "seatsHouse": int(r["seats_house"]),
            "seatsSenateCondorcet": int(r.get("seats_senate_cond", 0)),
            "seatsSenateIRV": int(r.get("seats_senate_irv", 0)),
        })
    write_json(out, "coalitionProfiles.json")


# ---------- transferMatrix.json ----------
def build_transfer_matrix():
    rows = read_csv(OUTPUTS / "No_C7_canonical" / "transfer_matrix_10party.csv")
    parties = [k for k in rows[0].keys() if k != "party_a"]
    matrix = {}
    for row in rows:
        src = row["party_a"]
        if not src:
            continue
        matrix[src] = {p: float(row[p]) for p in parties if row.get(p, "0") != "0"}
    write_json({"parties": parties, "matrix": matrix}, "transferMatrix.json")


# ---------- clusterProfiles.json ----------
def collect_cluster_variables(rows):
    """Build a variable dict for each cluster covering all binary/likert policy vars + demographics.

    Sources:
      - binary (% Supporting) and binary_agree (% Agreeing): included directly
      - likert5: agree-% computed as % Strongly Agree + % Agree
      - pew_churatd: weekly+ church attendance (% More than once/week + % Once/week)
      - race / gender4 categorical: specific buckets included as demographic facts
    """
    cluster_ids = [str(i) for i in range(10) if str(i) != "7"]
    result = {cid: {} for cid in cluster_ids}

    # Phase 1: binary and binary_agree
    for r in rows:
        typ = r.get("type", "")
        lbl = r.get("stat_label", "")
        if not ((typ == "binary" and lbl == "% Supporting") or
                (typ == "binary_agree" and lbl == "% Agreeing")):
            continue
        var = r["variable"]
        try:
            overall = float(r.get("overall", "") or 0)
        except (ValueError, TypeError):
            continue
        for cid in cluster_ids:
            try:
                val = float(r.get(f"c{cid}", "") or 0)
                result[cid][var] = {
                    "pct": round(val, 1),
                    "question": r.get("question", var),
                    "domain": r.get("domain", ""),
                    "diffPp": round(val - overall, 1),
                    "overall": round(overall, 1),
                }
            except (ValueError, TypeError):
                pass

    # Phase 2: Likert5 agree-% (% Strongly Agree + % Agree)
    likert_meta = {}   # var -> {question, domain}
    likert_sa   = {}   # var -> row for % Strongly Agree
    likert_ag   = {}   # var -> row for % Agree
    for r in rows:
        var = r["variable"]
        typ = r.get("type", "")
        lbl = r.get("stat_label", "")
        if typ == "likert5":
            likert_meta[var] = {"question": r.get("question", var), "domain": r.get("domain", "")}
        elif typ == "likert5_dist":
            if lbl == "% Strongly Agree":
                likert_sa[var] = r
            elif lbl == "% Agree":
                likert_ag[var] = r

    for var, meta in likert_meta.items():
        sa_row = likert_sa.get(var, {})
        ag_row = likert_ag.get(var, {})
        if not sa_row and not ag_row:
            continue
        try:
            overall_agree = round(
                float(sa_row.get("overall", 0) or 0) +
                float(ag_row.get("overall", 0) or 0), 1
            )
        except (ValueError, TypeError):
            overall_agree = 0
        agree_var = var + "_agree"
        for cid in cluster_ids:
            try:
                pct = round(
                    float(sa_row.get(f"c{cid}", 0) or 0) +
                    float(ag_row.get(f"c{cid}", 0) or 0), 1
                )
                result[cid][agree_var] = {
                    "pct": pct,
                    "question": meta["question"],
                    "domain": meta["domain"],
                    "diffPp": round(pct - overall_agree, 1),
                    "overall": round(overall_agree, 1),
                }
            except (ValueError, TypeError):
                pass

    # Phase 3: pew_churatd — weekly+ church attendance (needed by PartyCard)
    church_more = {}
    church_once = {}
    for r in rows:
        if r["variable"] != "pew_churatd":
            continue
        lbl = r.get("stat_label", "")
        if "More than once/week" in lbl:
            church_more = r
        elif "Once/week" in lbl and "More" not in lbl:
            church_once = r
    if church_more or church_once:
        try:
            overall_church = round(
                float(church_more.get("overall", 0) or 0) +
                float(church_once.get("overall", 0) or 0), 1
            )
        except (ValueError, TypeError):
            overall_church = 0
        for cid in cluster_ids:
            try:
                pct = round(
                    float(church_more.get(f"c{cid}", 0) or 0) +
                    float(church_once.get(f"c{cid}", 0) or 0), 1
                )
                result[cid]["pew_churatd"] = {
                    "pct": pct,
                    "question": "Weekly church attendance",
                    "domain": "Religion",
                    "diffPp": round(pct - overall_church, 1),
                    "overall": round(overall_church, 1),
                }
            except (ValueError, TypeError):
                pass

    # Phase 3.5: trust → % "Not very much" + % "None at all" (= % low trust)
    trust_meta_cv: dict = {}
    trust_not_much_cv: dict = {}
    trust_none_cv: dict = {}
    for r in rows:
        var = r["variable"]
        if r.get("type") == "trust":
            trust_meta_cv[var] = {"question": r.get("question", var), "domain": r.get("domain", "")}
        elif r.get("type") == "trust_dist":
            lbl = r.get("stat_label", "")
            if "Not very much" in lbl:
                trust_not_much_cv[var] = r
            elif "None at all" in lbl:
                trust_none_cv[var] = r

    TRUST_Q_CV = {
        "CC24_423": "Low trust in federal government (not very much or none at all)",
        "CC24_424": "Low trust in state government (not very much or none at all)",
    }
    for var, meta in trust_meta_cv.items():
        nm_row = trust_not_much_cv.get(var, {})
        na_row = trust_none_cv.get(var, {})
        if not nm_row and not na_row:
            continue
        try:
            overall = round(
                float(nm_row.get("overall", 0) or 0) +
                float(na_row.get("overall", 0) or 0), 1
            )
        except (ValueError, TypeError):
            overall = 0
        question = TRUST_Q_CV.get(var, meta["question"])
        for cid in cluster_ids:
            try:
                pct = round(
                    float(nm_row.get(f"c{cid}", 0) or 0) +
                    float(na_row.get(f"c{cid}", 0) or 0), 1
                )
                result[cid][var] = {
                    "pct": pct,
                    "question": question,
                    "domain": meta["domain"],
                    "diffPp": round(pct - overall, 1),
                    "overall": round(overall, 1),
                }
            except (ValueError, TypeError):
                pass

    # Phase 4: race and gender4 categorical breakdowns
    RACE_CATS   = {"% White", "% Black", "% Hispanic", "% Asian", "% Native American", "% Multiracial"}
    GENDER_CATS = {"% Man", "% Woman", "% Non-binary"}
    DEMO_VARS   = {"race": RACE_CATS, "gender4": GENDER_CATS}
    for base_var, cats in DEMO_VARS.items():
        for r in rows:
            if r["variable"] != base_var:
                continue
            lbl = r.get("stat_label", "")
            if lbl not in cats:
                continue
            suffix   = lbl.replace("% ", "").replace(" ", "_").lower()
            synth    = f"{base_var}_{suffix}"
            label_q  = f"Party base is {lbl.replace('% ', '').lower()}"
            try:
                overall = float(r.get("overall", 0) or 0)
            except (ValueError, TypeError):
                overall = 0
            for cid in cluster_ids:
                try:
                    val = float(r.get(f"c{cid}", 0) or 0)
                    result[cid][synth] = {
                        "pct": round(val, 1),
                        "question": label_q,
                        "domain": "Demographics",
                        "diffPp": round(val - overall, 1),
                        "overall": round(overall, 1),
                    }
                except (ValueError, TypeError):
                    pass

    # Phase 5: categorical_dist variables mapped to new demographic domains
    CAT_INCLUSIONS = [
        # (variable, stat_label, new_domain, new_question, synth_key)
        # --- Household ---
        ('marstat',   '% Married',        'Household', 'Married',                   'marstat_married'),
        ('marstat',   '% Never married',  'Household', 'Never married',             'marstat_never'),
        ('ownhome',   '% Own',            'Household', 'Owns home',                 'ownhome_own'),
        ('ownhome',   '% Rent',           'Household', 'Rents home',                'ownhome_rent'),
        ('urbancity', '% City',           'Household', 'Lives in: city',            'urbancity_city'),
        ('urbancity', '% Suburb',         'Household', 'Lives in: suburb',          'urbancity_suburb'),
        ('urbancity', '% Town',           'Household', 'Lives in: town/small city', 'urbancity_town'),
        ('urbancity', '% Rural area',     'Household', 'Lives in: rural area',      'urbancity_rural'),
        # --- Race & Ethnicity ---
        ('race', '% White',                       'Race & Ethnicity', 'White',                           'race_white'),
        ('race', '% Black',                       'Race & Ethnicity', 'Black',                           'race_black'),
        ('race', '% Hispanic',                    'Race & Ethnicity', 'Hispanic',                        'race_hispanic'),
        ('race', '% Asian',                       'Race & Ethnicity', 'Asian',                           'race_asian'),
        ('race', '% Multiracial',                 'Race & Ethnicity', 'Multiracial',                     'race_multiracial'),
        ('immstat', '% Immigrant, naturalized',   'Race & Ethnicity', 'Immigrant (naturalized citizen)', 'immstat_nat'),
        ('immstat', '% Immigrant, not citizen',   'Race & Ethnicity', 'Immigrant (not yet a citizen)',   'immstat_nc'),
        ('immstat', '% US-born, parent immigrant','Race & Ethnicity', 'US-born, parent was immigrant',   'immstat_parent'),
        # --- Gender & Sexuality ---
        ('gender4',   '% Man',                   'Gender & Sexuality', 'Identifies as man',              'gender4_man'),
        ('gender4',   '% Woman',                 'Gender & Sexuality', 'Identifies as woman',            'gender4_woman'),
        ('gender4',   '% Non-binary',            'Gender & Sexuality', 'Non-binary or other gender',     'gender4_nonbinary'),
        ('sexuality', '% Heterosexual/straight', 'Gender & Sexuality', 'Heterosexual / straight',        'sexuality_het'),
        ('sexuality', '% Lesbian/gay woman',     'Gender & Sexuality', 'Lesbian',                        'sexuality_lesbian'),
        ('sexuality', '% Gay man',               'Gender & Sexuality', 'Gay man',                        'sexuality_gay'),
        ('sexuality', '% Bisexual',              'Gender & Sexuality', 'Bisexual',                       'sexuality_bisexual'),
        # --- Education ---
        ('educ', '% No HS',         'Education', 'Less than high school',        'educ_no_hs'),
        ('educ', '% HS grad',       'Education', 'High school graduate',         'educ_hs'),
        ('educ', '% Some college',  'Education', 'Some college (no degree)',     'educ_some_college'),
        ('educ', '% 2-year degree', 'Education', "Associate's degree (2-year)",  'educ_2yr'),
        ('educ', '% 4-year degree', 'Education', "Bachelor's degree (4-year)",   'educ_4yr'),
        ('educ', '% Post-grad',     'Education', 'Post-graduate degree',         'educ_postgrad'),
        # --- Economics: employment ---
        ('employ', '% Full-time',  'Economics', 'Employed full-time',   'employ_ft'),
        ('employ', '% Part-time',  'Economics', 'Employed part-time',   'employ_pt'),
        ('employ', '% Unemployed', 'Economics', 'Currently unemployed', 'employ_unemployed'),
        ('employ', '% Retired',    'Economics', 'Retired',              'employ_retired'),
        ('employ', '% Homemaker',  'Economics', 'Homemaker',            'employ_homemaker'),
        # --- Economics: union membership ---
        ('union',   '% Current member',   'Economics', 'Current union member',       'union_current'),
        ('union',   '% Former member',    'Economics', 'Former union member',        'union_former'),
        ('unionhh', '% Currently member', 'Economics', 'Household has union member', 'unionhh_current'),
        # --- Voting History ---
        ('presvote20post', '% Biden',        'Voting History', 'Voted Biden (2020)',  'vote20_biden'),
        ('presvote20post', '% Trump',        'Voting History', 'Voted Trump (2020)',  'vote20_trump'),
        ('presvote20post', '% Did not vote', 'Voting History', 'Did not vote (2020)', 'vote20_dnv'),
        ('presvote16post', '% Did not vote', 'Voting History', 'Did not vote (2016)', 'vote16_dnv'),
        # --- Other ---
        ('gunown', '% No one in HH',    'Other', 'No gun in household',   'gunown_none'),
        ('gunown', '% Personally owns', 'Other', 'Personally owns a gun', 'gunown_personal'),
    ]

    cat_lookup = {(r['variable'], r.get('stat_label', '')): r for r in rows}
    for var, stat_lbl, domain, question, synth_key in CAT_INCLUSIONS:
        r = cat_lookup.get((var, stat_lbl))
        if not r:
            continue
        try:
            overall = float(r.get('overall', 0) or 0)
        except (ValueError, TypeError):
            overall = 0
        for cid in cluster_ids:
            try:
                val = float(r.get(f'c{cid}', 0) or 0)
                result[cid][synth_key] = {
                    'pct': round(val, 1),
                    'question': question,
                    'domain': domain,
                    'diffPp': round(val - overall, 1),
                    'overall': round(overall, 1),
                }
            except (ValueError, TypeError):
                pass

    # Phase 5b: income tier groupings from faminc_new ordinal distribution
    INCOME_TIERS = [
        ('income_under50k', 'Family income under $50k',
         ['% <$10k', '% $10k\u201320k', '% $20k\u201330k', '% $30k\u201340k', '% $40k\u201350k']),
        ('income_50k_100k', 'Family income $50k\u2013$100k',
         ['% $50k\u201360k', '% $60k\u201370k', '% $70k\u201380k', '% $80k\u2013100k']),
        ('income_over100k', 'Family income over $100k',
         ['% $100k\u2013120k', '% $120k\u2013150k', '% $150k\u2013200k', '% $200k\u2013250k',
          '% $250k\u2013350k', '% $350k\u2013500k', '% $500k+']),
    ]
    inc_rows = {r['stat_label']: r for r in rows if r['variable'] == 'faminc_new'}
    for synth_key, question, labels in INCOME_TIERS:
        matching = [inc_rows[lbl] for lbl in labels if lbl in inc_rows]
        if not matching:
            continue
        try:
            overall = sum(float(r.get('overall', 0) or 0) for r in matching)
        except Exception:
            overall = 0
        for cid in cluster_ids:
            try:
                val = sum(float(r.get(f'c{cid}', 0) or 0) for r in matching)
                result[cid][synth_key] = {
                    'pct': round(val, 1),
                    'question': question,
                    'domain': 'Economics',
                    'diffPp': round(val - overall, 1),
                    'overall': round(overall, 1),
                }
            except Exception:
                pass

    # Phase 5c: remap existing binary variables to new domains
    BINARY_REMAP = {
        'gigwork':   ('Economics',       'Gig / freelance worker'),
        'investor':  ('Economics',       'Owns stocks or mutual funds'),
        'child18':   ('Household',       'Has children under 18'),
        'CC24_323f': ('Taxes & Economy', 'Forgive up to $20k of student loan debt per person'),
    }
    for cid in cluster_ids:
        for var, (new_domain, new_question) in BINARY_REMAP.items():
            if var in result[cid]:
                result[cid][var]['domain'] = new_domain
                result[cid][var]['question'] = new_question

    # Phase 6: continuous variables with custom axis scale
    CONTINUOUS_VARS = [
        # (variable, stat_label, synth_key, domain, question, maxVal, unit)
        ('CC24_325', 'Median', 'CC24_325_median', 'Abortion',
         'Median abortion cutoff (weeks)', 40, 'wks'),
    ]
    for var, stat_lbl, synth_key, domain, question, max_val, unit in CONTINUOUS_VARS:
        r = cat_lookup.get((var, stat_lbl))
        if not r:
            continue
        try:
            overall = float(r.get('overall', 0) or 0)
        except (ValueError, TypeError):
            overall = 0
        for cid in cluster_ids:
            try:
                val = float(r.get(f'c{cid}', 0) or 0)
                result[cid][synth_key] = {
                    'pct': round(val, 1),
                    'question': question,
                    'domain': domain,
                    'diffPp': round(val - overall, 1),
                    'overall': round(overall, 1),
                    'maxVal': max_val,
                    'unit': unit,
                }
            except (ValueError, TypeError):
                pass

    return result

def compute_key_positions(rows, cid, n=4):
    """Return top-n data-driven policy positions that most differentiate this cluster."""
    binary_rows = [r for r in rows if r["type"] == "binary"]
    diffs = []
    for r in binary_rows:
        try:
            overall = float(r["overall"])
            val = float(r[f"c{cid}"]) if r.get(f"c{cid}") else overall
            diff = val - overall
            diffs.append((abs(diff), diff, r["question"], val))
        except (ValueError, KeyError):
            pass
    diffs.sort(reverse=True)
    out = []
    for _, diff, question, pct in diffs[:n]:
        out.append({
            "question": question,
            "pct": round(pct, 1),
            "direction": "supports" if diff > 0 else "opposes",
            "diffPp": round(diff, 1),
        })
    return out


def compute_key_positions_vs_neighbors(rows, cid, cluster_factors, n=4, min_diff=15):
    """Return top-n positions most distinguishing this cluster from its 2 nearest neighbors.
    Falls back to overall-diff approach if fewer than n positions pass the threshold."""
    me = cluster_factors.get(cid)
    if not me:
        return compute_key_positions(rows, cid, n)

    factor_keys = ["F1", "F2", "F3", "F4", "F5"]
    distances = []
    for other_cid, other in cluster_factors.items():
        if other_cid == cid:
            continue
        dist = sum((me[f] - other[f]) ** 2 for f in factor_keys) ** 0.5
        distances.append((dist, other_cid))
    distances.sort()
    neighbor_cids = [c2 for _, c2 in distances[:2]]

    binary_rows = [r for r in rows if r["type"] == "binary"]
    diffs = []
    for r in binary_rows:
        try:
            val = float(r[f"c{cid}"])
            neighbor_vals = [float(r[f"c{nc}"]) for nc in neighbor_cids if r.get(f"c{nc}")]
            if not neighbor_vals:
                continue
            avg_neighbor = sum(neighbor_vals) / len(neighbor_vals)
            diff = val - avg_neighbor
            if abs(diff) >= min_diff:
                diffs.append((abs(diff), diff, r["question"], val))
        except (ValueError, KeyError):
            pass
    diffs.sort(reverse=True)
    out = []
    for _, diff, question, pct in diffs[:n]:
        out.append({
            "question": question,
            "pct": round(pct, 1),
            "direction": "supports" if diff > 0 else "opposes",
            "diffPp": round(diff, 1),
        })
    # Fall back to overall-diff for any remaining slots
    if len(out) < n:
        seen = {p["question"] for p in out}
        fallback = compute_key_positions(rows, cid, n * 2)
        for pos in fallback:
            if pos["question"] not in seen:
                out.append(pos)
                seen.add(pos["question"])
            if len(out) >= n:
                break
    return out

def build_cluster_profiles():
    rows = read_csv(OUTPUTS / "profiles" / "cluster_stats.csv")
    clusters = {str(i): {"id": str(i), "variables": {}} for i in range(10) if str(i) != "7"}

    all_vars = collect_cluster_variables(rows)
    for cid in clusters:
        clusters[cid]["variables"] = all_vars.get(cid, {})

    coalition_rows = read_csv(OUTPUTS / "coalitions" / "coalition_type_profiles.csv")
    party_to_cluster = {v: k for k, v in CLUSTER_TO_PARTY.items()}
    cluster_factors = {}
    for r in coalition_rows:
        party = r["type"]
        cid = party_to_cluster.get(party)
        if cid and cid in clusters:
            clusters[cid]["party"] = party
            clusters[cid]["partyName"] = PARTY_NAMES.get(party, party)
            clusters[cid]["F1"] = float(r["F1_security_order"])
            clusters[cid]["F2"] = float(r["F2_electoral_skepticism"])
            clusters[cid]["F3"] = float(r["F3_government_distrust"])
            clusters[cid]["F4"] = float(r["F4_religious_traditionalism"])
            clusters[cid]["F5"] = float(r["F5_populist_conservatism"])
            clusters[cid]["seatsHouse"] = int(r["seats_house"])
            cluster_factors[cid] = {
                "F1": float(r["F1_security_order"]),
                "F2": float(r["F2_electoral_skepticism"]),
                "F3": float(r["F3_government_distrust"]),
                "F4": float(r["F4_religious_traditionalism"]),
                "F5": float(r["F5_populist_conservatism"]),
            }

    # Compute percentile ranks AND z-scores (SDs from population mean)
    efa_path = Path(__file__).parent.parent.parent / "data" / "processed" / "efa_factor_scores.csv"
    typo_path = Path(__file__).parent.parent.parent / "data" / "processed" / "typology_cluster_assignments.csv"
    if efa_path.exists() and typo_path.exists():
        efa_rows = read_csv(str(efa_path))
        typo_rows = read_csv(str(typo_path))
        factor_map = {"F1": "FS_F1", "F2": "FS_F2", "F3": "FS_F3", "F4": "FS_F4", "F5": "FS_F5"}
        if "FS_F4" not in (efa_rows[0] if efa_rows else {}):
            factor_map["F4"] = "FS_F4_resid"
            factor_map["F5"] = "FS_F5_resid"
        def get_factor_val(row_idx, factor_key):
            col = factor_map[factor_key]
            val = efa_rows[row_idx].get(col)
            if val is None or val == '':
                val = typo_rows[row_idx].get(col)
            return float(val or 0)

        N = len(efa_rows)
        for factor_key in ["F1", "F2", "F3", "F4", "F5"]:
            all_vals = [get_factor_val(i, factor_key) for i in range(N)]
            pop_mean = sum(all_vals) / N
            pop_sd = (sum((v - pop_mean) ** 2 for v in all_vals) / N) ** 0.5
            for cid in clusters:
                centroid = clusters[cid].get(factor_key, 0)
                below = sum(1 for v in all_vals if v < centroid)
                pctile = round(below / N * 100, 1)
                z_mean = round((centroid - pop_mean) / pop_sd, 2) if pop_sd > 0 else 0
                z_zero = round(centroid / pop_sd, 2) if pop_sd > 0 else 0
                clusters[cid][f"pctile_{factor_key}"] = pctile
                clusters[cid][f"z_{factor_key}"] = z_zero  # zero-based (factor model origin)

    # Add key positions vs nearest neighbors
    for cid in clusters:
        clusters[cid]["keyPositions"] = compute_key_positions_vs_neighbors(rows, cid, cluster_factors)

    write_json(list(clusters.values()), "clusterProfiles.json")


def _extract_policy_vars(rows, get_val, max_vars=None):
    """Build a variables dict from cluster_stats or blend_stats rows.
    Handles binary, binary_agree, and likert5 (summed as SA+A).
    get_val(row) -> float | None; return None to skip a row.
    """
    result = {}

    # Phase 1: binary + binary_agree
    for r in rows:
        typ = r.get("type", "")
        lbl = r.get("stat_label", "")
        if not ((typ == "binary" and lbl == "% Supporting") or
                (typ == "binary_agree" and lbl == "% Agreeing")):
            continue
        val = get_val(r)
        if val is None:
            continue
        try:
            overall = float(r.get("overall") or 0)
            result[r["variable"]] = {
                "pct": round(val, 1),
                "question": r.get("question", r["variable"]),
                "domain": r.get("domain", ""),
                "diffPp": round(val - overall, 1),
                "overall": round(overall, 1),
            }
        except (ValueError, KeyError):
            pass

    # Phase 2: likert5 → % Strongly Agree + % Agree
    likert_meta: dict = {}
    likert_sa: dict = {}
    likert_ag: dict = {}
    for r in rows:
        var = r["variable"]
        if r.get("type") == "likert5":
            likert_meta[var] = {"question": r.get("question", var), "domain": r.get("domain", "")}
        elif r.get("type") == "likert5_dist":
            if r.get("stat_label") == "% Strongly Agree":
                likert_sa[var] = r
            elif r.get("stat_label") == "% Agree":
                likert_ag[var] = r

    for var, meta in likert_meta.items():
        sa_row = likert_sa.get(var, {})
        ag_row = likert_ag.get(var, {})
        sa_val = get_val(sa_row) if sa_row else None
        ag_val = get_val(ag_row) if ag_row else None
        if sa_val is None and ag_val is None:
            continue
        try:
            val = (sa_val or 0) + (ag_val or 0)
            overall = (float(sa_row.get("overall") or 0) if sa_row else 0) + \
                      (float(ag_row.get("overall") or 0) if ag_row else 0)
            result[var + "_agree"] = {
                "pct": round(val, 1),
                "question": meta["question"],
                "domain": meta["domain"],
                "diffPp": round(val - overall, 1),
            }
        except (ValueError, TypeError):
            pass

    # Phase 3: trust → % "Not very much" + % "None at all" (= % low trust)
    trust_meta: dict = {}
    trust_not_much: dict = {}
    trust_none_at_all: dict = {}
    for r in rows:
        var = r["variable"]
        if r.get("type") == "trust":
            trust_meta[var] = {"question": r.get("question", var), "domain": r.get("domain", "")}
        elif r.get("type") == "trust_dist":
            lbl = r.get("stat_label", "")
            if "Not very much" in lbl:
                trust_not_much[var] = r
            elif "None at all" in lbl:
                trust_none_at_all[var] = r

    TRUST_Q = {
        "CC24_423": "Low trust in federal government (not very much or none at all)",
        "CC24_424": "Low trust in state government (not very much or none at all)",
    }
    for var, meta in trust_meta.items():
        nm_row = trust_not_much.get(var, {})
        na_row = trust_none_at_all.get(var, {})
        nm_val = get_val(nm_row) if nm_row else None
        na_val = get_val(na_row) if na_row else None
        if nm_val is None and na_val is None:
            continue
        try:
            val = (nm_val or 0) + (na_val or 0)
            overall = (float(nm_row.get("overall") or 0) if nm_row else 0) +                       (float(na_row.get("overall") or 0) if na_row else 0)
            result[var] = {
                "pct": round(val, 1),
                "question": TRUST_Q.get(var, meta["question"]),
                "domain": meta["domain"],
                "diffPp": round(val - overall, 1),
            }
        except (ValueError, TypeError):
            pass

    items = sorted(result.items(), key=lambda x: abs(x[1]["diffPp"]), reverse=True)
    return dict(items[:max_vars] if max_vars else items)


# ---------- blendProfiles.json ----------
def build_blend_profiles():
    """Build profiles for blended senator types that appear in the senate simulations."""
    blend_rows = read_csv(OUTPUTS / "profiles" / "blend_stats.csv")
    cluster_rows = read_csv(OUTPUTS / "profiles" / "cluster_stats.csv")
    centroid_rows = read_csv(OUTPUTS / "senate" / "senate_candidate_factor_centroids.csv")
    senate_prof_rows = read_csv(OUTPUTS / "senate" / "senate_chamber_profile.csv")
    cond_rows = read_csv(OUTPUTS / "senate" / "senate_composition.csv")
    irv_rows = read_csv(OUTPUTS / "senate" / "senate_irv_composition.csv")
    # Also read pure senate compositions to capture parties that only appear there (e.g. REF)
    pure_cond_rows = read_csv(PURE_DIR / "senate" / "senate_composition.csv")
    pure_irv_rows  = read_csv(PURE_DIR / "senate" / "senate_irv_composition.csv")

    # Cluster-to-party mapping for pure party key positions
    PARTY_TO_CID = {'CON': '0', 'SD': '1', 'STY': '2', 'NAT': '3',
                    'LIB': '4', 'REF': '5', 'CTR': '6', 'DSA': '8', 'PRG': '9'}

    # Factor scores indexed by blend label
    centroids = {r["candidate_label"]: r for r in centroid_rows}

    # Count senate seats per code (blended scenarios)
    seat_counts_cond = defaultdict(int)
    for r in cond_rows:
        seat_counts_cond[r["senator_code"]] += 1
    seat_counts_irv = defaultdict(int)
    for r in irv_rows:
        seat_counts_irv[r["winner_code"]] += 1

    # All unique blended codes (contain '/') across both chambers
    all_codes = set()
    for r in cond_rows:
        if "/" in r["senator_code"]:
            all_codes.add(r["senator_code"])
    for r in irv_rows:
        if "/" in r["winner_code"]:
            all_codes.add(r["winner_code"])

    # Blend stats has column names like 'CON/CTR', 'CON/SD', etc.
    blend_cols = [k for k in blend_rows[0].keys() if "/" in k] if blend_rows else []
    # Senate chamber profile binary rows — fallback for codes not in blend_stats
    senate_binary_rows = [r for r in senate_prof_rows
                          if r.get("stat_label") == "% Supporting"
                          and r.get("variable", "").startswith("CC24_")]

    def _diffs_from_rows(rows, col, overall_col="overall"):
        diffs = []
        for r in rows:
            try:
                overall = float(r[overall_col])
                val = float(r[col])
                diff = val - overall
                diffs.append((abs(diff), diff, r["question"], val))
            except (ValueError, KeyError):
                pass
        diffs.sort(reverse=True)
        return diffs

    def compute_blend_positions(blend_code, n=4):
        # Prefer blend_stats columns; fall back to senate_chamber_profile
        if blend_code in blend_cols:
            binary = [r for r in blend_rows if r["type"] == "binary"]
            diffs = _diffs_from_rows(binary, blend_code)
        elif senate_binary_rows and blend_code in (senate_binary_rows[0] if senate_binary_rows else {}):
            diffs = _diffs_from_rows(senate_binary_rows, blend_code)
        else:
            return []
        pos_out = []
        for _, diff, question, pct in diffs[:n]:
            pos_out.append({
                "question": question,
                "pct": round(pct, 1),
                "direction": "supports" if diff > 0 else "opposes",
                "diffPp": round(diff, 1),
            })
        return pos_out

    def compute_blend_variables(blend_code):
        """Return all policy variables for a blended party, sorted by |diffPp|."""
        if blend_code not in blend_cols:
            return {}
        def _get(r):
            try:
                return float(r[blend_code])
            except (ValueError, KeyError):
                return None
        return _extract_policy_vars(blend_rows, _get)

    def compute_pure_blend_variables(cid):
        """Return all policy variables for a pure-party cluster, sorted by |diffPp|."""
        def _get(r):
            try:
                return float(r[f"c{cid}"])
            except (ValueError, KeyError):
                return None
        return _extract_policy_vars(cluster_rows, _get)

    out = []
    for code in sorted(all_codes):
        c = centroids.get(code, {})
        profile = {
            "code": code,
            "seatsCond": seat_counts_cond.get(code, 0),
            "seatsIRV": seat_counts_irv.get(code, 0),
            "F1": float(c.get("F1_security_order", 0)) if c else 0,
            "F2": float(c.get("F2_electoral_skepticism", 0)) if c else 0,
            "F3": float(c.get("F3_government_distrust", 0)) if c else 0,
            "F4": float(c.get("F4_religious_traditionalism", 0)) if c else 0,
            "F5": float(c.get("F5_populist_conservatism", 0)) if c else 0,
            "keyPositions": compute_blend_positions(code),
            "variables": compute_blend_variables(code),
        }
        out.append(profile)

    # Collect all pure-party codes across blended AND pure senate compositions
    pure_codes = set()
    for r in cond_rows + pure_cond_rows:
        code = r.get("senator_code", "")
        if code and "/" not in code:
            pure_codes.add(code)
    for r in irv_rows + pure_irv_rows:
        code = r.get("winner_code", "")
        if code and "/" not in code:
            pure_codes.add(code)

    for code in sorted(pure_codes):
        c = centroids.get(code, {})
        cid = PARTY_TO_CID.get(code)
        key_positions = compute_key_positions(cluster_rows, cid) if cid else []
        out.append({
            "code": code,
            "isPure": True,
            "seatsCond": seat_counts_cond.get(code, 0),
            "seatsIRV": seat_counts_irv.get(code, 0),
            "F1": float(c.get("F1_security_order", 0)) if c else 0,
            "F2": float(c.get("F2_electoral_skepticism", 0)) if c else 0,
            "F3": float(c.get("F3_government_distrust", 0)) if c else 0,
            "F4": float(c.get("F4_religious_traditionalism", 0)) if c else 0,
            "F5": float(c.get("F5_populist_conservatism", 0)) if c else 0,
            "keyPositions": key_positions,
            "variables": compute_pure_blend_variables(cid) if cid else {},
        })

    # Add Light Fusion candidate profiles (16 LF codes)
    lf_centroid_rows = read_csv(OUTPUTS / "light_fusion_centroids.csv")
    lf_centroids = {
        r["candidate_code"]: r for r in lf_centroid_rows
        if "_" in r["candidate_code"] and r["candidate_code"].split("_")[1].islower()
    }

    lf_cond_counts: dict = {}
    lf_irv_counts: dict = {}
    for r in read_csv(LIGHT_FUSION_DIR / "senate" / "senate_composition.csv"):
        lf_cond_counts[r["senator_code"]] = lf_cond_counts.get(r["senator_code"], 0) + 1
    for r in read_csv(LIGHT_FUSION_DIR / "senate" / "senate_irv_composition.csv"):
        lf_irv_counts[r["senator_code"]] = lf_irv_counts.get(r["senator_code"], 0) + 1

    def _lf_weighted_pct(code: str, row: dict) -> float:
        def _c(k: int) -> float:
            return float(row.get(f"c{k}") or 0)
        if code in _PURE_CLUSTER:
            return _c(_PURE_CLUSTER[code])
        if code in _LF_CLUSTER_MAP:
            p, s = _LF_CLUSTER_MAP[code]
            return 0.80 * _c(p) + 0.20 * _c(s)
        return 0.0

    def compute_lf_variables(code: str, max_vars: int = None) -> dict:
        def _get(r):
            try:
                return _lf_weighted_pct(code, r)
            except Exception:
                return None
        return _extract_policy_vars(cluster_rows, _get, max_vars=max_vars)

    def compute_lf_key_positions(code: str, n: int = 4) -> list:
        vars_dict = compute_lf_variables(code, max_vars=n)
        return [
            {"question": v["question"], "pct": v["pct"], "direction": "supports" if v["diffPp"] > 0 else "opposes", "diffPp": v["diffPp"]}
            for v in vars_dict.values()
        ]

    lf_all_codes = set(lf_centroids.keys()) | {c for c in lf_cond_counts if "_" in c and c.split("_")[1].islower()} | {c for c in lf_irv_counts if "_" in c and c.split("_")[1].islower()}
    for code in sorted(lf_all_codes):
        c = lf_centroids.get(code, {})
        out.append({
            "code": code,
            "isLightFusion": True,
            "seatsCond": lf_cond_counts.get(code, 0),
            "seatsIRV": lf_irv_counts.get(code, 0),
            "F1": float(c.get("F1_security_order", 0)) if c else 0,
            "F2": float(c.get("F2_electoral_skepticism", 0)) if c else 0,
            "F3": float(c.get("F3_government_distrust", 0)) if c else 0,
            "F4": float(c.get("F4_religious_traditionalism", 0)) if c else 0,
            "F5": float(c.get("F5_populist_conservatism", 0)) if c else 0,
            "keyPositions": compute_lf_key_positions(code),
            "variables": compute_lf_variables(code),
        })

    out.sort(key=lambda x: -(x["seatsCond"] + x["seatsIRV"]))
    write_json(out, "blendProfiles.json")


# ---------- quizQuestions.json ----------
# Quiz variables: (variable, factor, row_selection_strategy)
# row_selection_strategy:
#   "binary"       → use type=="binary" row (% Supporting)
#   "likert_agree" → sum % Strongly Agree + % Agree rows
#   "trust_none"   → use % None at all row
#   "church_never" → use % Never row
QUIZ_VARS = [
    ("CC24_323b", "F1", "binary"),
    ("CC24_321d", "F1", "binary"),
    ("CC24_421_1", "F2", "likert_agree"),
    ("CC24_421_2", "F2", "likert_agree"),
    ("CC24_423",   "F3", "trust_none"),
    ("CC24_424",   "F3", "trust_none"),
    ("CC24_324b",  "F4", "binary"),
    ("pew_churatd","F4", "church_never"),
    ("CC24_323a",  "F5", "binary"),
    ("CC24_440a",  "F5", "likert_agree"),
]

QUIZ_QUESTION_OVERRIDES = {
    'CC24_423': 'I have very little trust in the federal government.',
    'CC24_424': 'I have very little trust in my state government.',
    'pew_churatd': 'I rarely or never attend religious services.',
}

CIDS = ["0","1","2","3","4","5","6","8","9"]

def build_quiz():
    rows = read_csv(OUTPUTS / "profiles" / "cluster_stats.csv")

    # Group rows by variable
    by_var = defaultdict(list)
    for r in rows:
        by_var[r["variable"]].append(r)

    questions = []
    for var, factor, strategy in QUIZ_VARS:
        var_rows = by_var.get(var, [])
        if not var_rows:
            print(f"  WARNING: quiz var {var} not found in cluster_stats.csv")
            continue

        cluster_pcts = {}
        question_text = QUIZ_QUESTION_OVERRIDES.get(var)
        domain = var_rows[0].get("domain", "")

        if strategy == "binary":
            row = next((r for r in var_rows if r.get("type") == "binary"), var_rows[0])
            if not question_text:
                question_text = row.get("question", var)
            for cid in CIDS:
                val = row.get(f"c{cid}", "")
                cluster_pcts[cid] = float(val) / 100 if val else 0.5

        elif strategy == "likert_agree":
            sa_row = next((r for r in var_rows if r.get("stat_label", "") == "% Strongly Agree"), None)
            a_row  = next((r for r in var_rows if r.get("stat_label", "") == "% Agree"), None)
            if not question_text:
                question_text = var_rows[0].get("question", var)
            for cid in CIDS:
                sa = float(sa_row.get(f"c{cid}", 0) or 0) if sa_row else 0
                a  = float(a_row.get(f"c{cid}", 0)  or 0) if a_row  else 0
                cluster_pcts[cid] = round((sa + a) / 100, 4)

        elif strategy == "trust_none":
            row = next((r for r in var_rows if "None at all" in r.get("stat_label", "")), var_rows[-1])
            if not question_text:
                question_text = row.get("question", var)
            for cid in CIDS:
                val = row.get(f"c{cid}", "")
                cluster_pcts[cid] = float(val) / 100 if val else 0.5

        elif strategy == "church_never":
            row = next((r for r in var_rows if r.get("stat_label", "") == "% Never"), var_rows[-1])
            if not question_text:
                question_text = row.get("question", var)
            for cid in CIDS:
                val = row.get(f"c{cid}", "")
                cluster_pcts[cid] = float(val) / 100 if val else 0.5

        questions.append({
            "variable": var,
            "factor": factor,
            "question": question_text or var,
            "domain": domain,
            "clusterSupport": cluster_pcts,
        })

    write_json(questions, "quizQuestions.json")


# ---------- presidentialElection.json ----------
def build_presidential_election():
    # IRV national rounds
    irv_rows = read_csv(OUTPUTS / "irv" / "irv_presidential_national_2028.csv")
    rounds_by_num = defaultdict(list)
    for r in irv_rows:
        rounds_by_num[int(r["round"])].append(r)

    irv_rounds = []
    irv_winner = None
    for rnum in sorted(rounds_by_num.keys()):
        candidates = []
        for r in rounds_by_num[rnum]:
            code = r["candidate_code"].replace("_", "/")
            eliminated = r["eliminated"].strip().lower() == "true"
            winner = r["winner"].strip().lower() == "true"
            if winner and not eliminated:
                irv_winner = code
            candidates.append({
                "code": code,
                "name": r["candidate_name"],
                "pct": round(float(r["vote_pct"]), 2),
                "votes": round(float(r["vote_total"]), 0),
                "eliminated": eliminated,
                "winner": winner,
            })
        irv_rounds.append({"round": rnum, "candidates": candidates})

    # Condorcet matchups from primary_diagnostics
    diag_rows = read_csv(OUTPUTS / "primary_diagnostics_2028.csv")
    condorcet_matchups = []
    condorcet_winner = None
    for r in diag_rows:
        if r.get("diagnostic") != "condorcet":
            continue
        a = r["candidate_a"].replace("_", "/")
        b = r["candidate_b"].replace("_", "/")
        votes_a = float(r["votes_a_beats_b"])
        votes_b = float(r["votes_b_beats_a"])
        total = votes_a + votes_b
        a_wins_pct = round(votes_a / total * 100, 3) if total > 0 else 50.0
        winner = r["winner"].replace("_", "/")
        margin_pct = round(float(r["margin_pct"]), 3)
        condorcet_matchups.append({
            "candidateA": a,
            "candidateB": b,
            "aWinsPct": a_wins_pct,
            "margin": margin_pct,
            "winner": winner,
        })
        if r.get("rp_winner_overall"):
            condorcet_winner = r["rp_winner_overall"].replace("_", "/")

    # State winners + shares
    state_rows = read_csv(OUTPUTS / "irv" / "irv_presidential_states_2028.csv")
    pod_rows = read_csv(OUTPUTS / "state_pod_assignments.csv")
    pod_by_fips = {r["state_fips"].zfill(2): r["pod"] for r in pod_rows}

    irv_state_winners = {}
    for r in state_rows:
        fips = r["state_fips"].zfill(2)
        winner = r["winner_code"].replace("_", "/")
        r1_cols = [k for k in r.keys() if k.startswith("r1_pct_")]
        raw_shares = {}
        for col in r1_cols:
            code = col.replace("r1_pct_", "").replace("_", "/")
            val = float(r.get(col) or 0)
            if val > 0:
                raw_shares[code] = val
        total = sum(raw_shares.values())
        shares = {k: round(v / total, 4) for k, v in raw_shares.items()} if total > 0 else {}
        irv_state_winners[fips] = {
            "stateAbbr": r["state_abbr"],
            "winner": winner,
            "pod": pod_by_fips.get(fips, "D"),
            "nRespondents": int(r["n_respondents"]),
            "shares": shares,
        }

    write_json({
        "irvRounds": irv_rounds,
        "irvWinner": irv_winner,
        "condorcetMatchups": condorcet_matchups,
        "condorcetWinner": condorcet_winner,
        "irvStateWinners": irv_state_winners,
    }, "presidentialElection.json")


# ---------- presidentialElectionPure.json ----------
def build_presidential_election_pure():
    # IRV national rounds
    irv_rows = read_csv(PURE_DIR / "irv" / "irv_presidential_national_2028.csv")
    rounds_by_num = defaultdict(list)
    for r in irv_rows:
        rounds_by_num[int(r["round"])].append(r)

    irv_rounds = []
    irv_winner = None
    for rnum in sorted(rounds_by_num.keys()):
        candidates = []
        for r in rounds_by_num[rnum]:
            code = normalize_candidate_code(r["candidate_code"])
            eliminated = r["eliminated"].strip().lower() == "true"
            winner = r["winner"].strip().lower() == "true"
            if winner and not eliminated:
                irv_winner = code
            candidates.append({
                "code": code,
                "name": normalize_candidate_code(r["candidate_name"]),
                "pct": round(float(r["vote_pct"]), 2),
                "votes": round(float(r["vote_total"]), 0),
                "eliminated": eliminated,
                "winner": winner,
            })
        irv_rounds.append({"round": rnum, "candidates": candidates})

    # Condorcet matchups from pure primary_diagnostics
    diag_rows = read_csv(PURE_DIR / "primary_diagnostics_2028.csv")
    condorcet_matchups = []
    condorcet_winner = None
    for r in diag_rows:
        if r.get("diagnostic") != "condorcet":
            continue
        a = normalize_candidate_code(r["candidate_a"])
        b = normalize_candidate_code(r["candidate_b"])
        votes_a = float(r["votes_a_beats_b"])
        votes_b = float(r["votes_b_beats_a"])
        total = votes_a + votes_b
        a_wins_pct = round(votes_a / total * 100, 3) if total > 0 else 50.0
        winner = normalize_candidate_code(r["winner"])
        margin_pct = round(float(r["margin_pct"]), 3)
        condorcet_matchups.append({
            "candidateA": a,
            "candidateB": b,
            "aWinsPct": a_wins_pct,
            "margin": margin_pct,
            "winner": winner,
        })
        if r.get("rp_winner_overall"):
            condorcet_winner = normalize_candidate_code(r["rp_winner_overall"])

    # State winners + shares
    state_rows = read_csv(PURE_DIR / "irv" / "irv_presidential_states_2028.csv")
    pod_rows = read_csv(OUTPUTS / "state_pod_assignments.csv")
    pod_by_fips = {r["state_fips"].zfill(2): r["pod"] for r in pod_rows}

    irv_state_winners = {}
    for r in state_rows:
        fips = r["state_fips"].zfill(2)
        winner = normalize_candidate_code(r["winner_code"])
        r1_cols = [k for k in r.keys() if k.startswith("r1_pct_")]
        raw_shares = {}
        for col in r1_cols:
            raw_code = col.replace("r1_pct_", "")
            code = normalize_candidate_code(raw_code)
            val = float(r.get(col) or 0)
            if val > 0:
                raw_shares[code] = raw_shares.get(code, 0) + val
        total = sum(raw_shares.values())
        shares = {k: round(v / total, 4) for k, v in raw_shares.items()} if total > 0 else {}
        irv_state_winners[fips] = {
            "stateAbbr": r["state_abbr"],
            "winner": winner,
            "pod": pod_by_fips.get(fips, "D"),
            "nRespondents": int(r["n_respondents"]),
            "shares": shares,
        }

    write_json({
        "irvRounds": irv_rounds,
        "irvWinner": irv_winner,
        "condorcetMatchups": condorcet_matchups,
        "condorcetWinner": condorcet_winner,
        "irvStateWinners": irv_state_winners,
    }, "presidentialElectionPure.json")


# ---------- presidentialElectionLightFusion.json ----------
def build_presidential_election_light_fusion():
    irv_dir = LIGHT_FUSION_DIR / "irv"
    irv_rows = read_csv(irv_dir / "irv_presidential_national_2028.csv")
    rounds_by_num = defaultdict(list)
    for r in irv_rows:
        rounds_by_num[int(r["round"])].append(r)

    irv_rounds = []
    irv_winner = None
    for rnum in sorted(rounds_by_num.keys()):
        candidates = []
        for r in rounds_by_num[rnum]:
            code = normalize_candidate_code(r["candidate_code"])
            eliminated = r["eliminated"].strip().lower() == "true"
            winner = r["winner"].strip().lower() == "true"
            if winner and not eliminated:
                irv_winner = code
            candidates.append({
                "code": code,
                "name": r["candidate_name"],
                "pct": round(float(r["vote_pct"]), 2),
                "votes": round(float(r["vote_total"]), 0),
                "eliminated": eliminated,
                "winner": winner,
            })
        irv_rounds.append({"round": rnum, "candidates": candidates})

    # Condorcet matchups from the light fusion IRV output
    condorcet_matchups = []
    condorcet_winner = None
    cond_rows = read_csv(irv_dir / "condorcet_matchups_2028.csv")
    for r in cond_rows:
        a = normalize_candidate_code(r["candidate_a"])
        b = normalize_candidate_code(r["candidate_b"])
        votes_a = float(r["votes_a_beats_b"])
        votes_b = float(r["votes_b_beats_a"])
        total = votes_a + votes_b
        a_wins_pct = round(votes_a / total * 100, 3) if total > 0 else 50.0
        winner = normalize_candidate_code(r["winner"])
        margin_pct = round(float(r["margin_pct"]), 3)
        condorcet_matchups.append({
            "candidateA": a,
            "candidateB": b,
            "aWinsPct": a_wins_pct,
            "margin": margin_pct,
            "winner": winner,
        })
        if r.get("rp_winner_overall"):
            condorcet_winner = normalize_candidate_code(r["rp_winner_overall"])

    # State winners + shares
    state_rows = read_csv(irv_dir / "irv_presidential_states_2028.csv")
    pod_rows = read_csv(LIGHT_FUSION_DIR / "state_pod_assignments.csv")
    pod_by_fips = {r["state_fips"].zfill(2): r["pod"] for r in pod_rows}

    irv_state_winners = {}
    for r in state_rows:
        fips = r["state_fips"].zfill(2)
        winner = normalize_candidate_code(r["winner_code"])
        r1_cols = [k for k in r.keys() if k.startswith("r1_pct_")]
        raw_shares = {}
        for col in r1_cols:
            code = normalize_candidate_code(col.replace("r1_pct_", ""))
            val = float(r.get(col) or 0)
            if val > 0:
                raw_shares[code] = raw_shares.get(code, 0) + val
        total = sum(raw_shares.values())
        shares = {k: round(v / total, 4) for k, v in raw_shares.items()} if total > 0 else {}
        irv_state_winners[fips] = {
            "stateAbbr": r["state_abbr"],
            "winner": winner,
            "pod": pod_by_fips.get(fips, "D"),
            "nRespondents": int(r["n_respondents"]),
            "shares": shares,
        }

    write_json({
        "irvRounds": irv_rounds,
        "irvWinner": irv_winner,
        "condorcetMatchups": condorcet_matchups,
        "condorcetWinner": condorcet_winner,
        "irvStateWinners": irv_state_winners,
    }, "presidentialElectionLightFusion.json")


# ---------- primaryTransfers.json ----------
def build_primary_transfers():
    diag_rows = read_csv(OUTPUTS / "primary_diagnostics_2028.csv")
    out = []
    for r in diag_rows:
        if r.get("diagnostic") != "transfer_analysis":
            continue
        elim_code = r.get("eliminated_code", "").strip()
        dest_code = r.get("dest_code", "").strip()
        transferred = r.get("transferred_votes", "").strip()
        pct = r.get("pct_of_eliminated_total", "").strip()
        winnowing = r.get("winnowing_point", "").strip()
        transfer_type = r.get("transfer_type", "").strip()
        if not elim_code or not dest_code or not transferred:
            continue
        out.append({
            "source": normalize_candidate_code(elim_code),
            "target": normalize_candidate_code(dest_code),
            "votes": round(float(transferred), 1),
            "pct": round(float(pct), 2) if pct else 0,
            "round": winnowing,
            "type": transfer_type,
        })
    write_json(out, "primaryTransfers.json")


# ---------- primarySankey.json ----------
def build_primary_sankey():
    """Build stage-by-stage Sankey: 5 columns (initial → retail → pod A → pod C → final 5)."""
    profiles = read_csv(OUTPUTS / "state_candidate_profiles.csv")
    diag_rows = read_csv(OUTPUTS / "primary_diagnostics_2028.csv")

    # First-choice national percentages for all 20 candidates (stage 0)
    fc_totals = {}
    for row in profiles:
        n = float(row.get("total_weighted_respondents") or 0)
        for k, v in row.items():
            if k.startswith("first_choice_"):
                raw = k.replace("first_choice_", "")
                code = normalize_candidate_code(raw)
                fc_totals[code] = fc_totals.get(code, 0) + n * float(v or 0)
    total_fc = sum(fc_totals.values())
    fc_pct = {code: round(v / total_fc * 100, 3) for code, v in fc_totals.items()}

    # Trajectory vote_pcts keyed by (norm_code, stageIdx)
    stage_order = ["After_Retail_Six", "After_Pod_A", "After_Pod_C", "After_Pod_BD"]
    stage_to_idx = {s: i + 1 for i, s in enumerate(stage_order)}
    traj_rows = [r for r in diag_rows if r["diagnostic"] == "trajectories"]

    active_at = {i: [] for i in range(1, 5)}  # stageIdx → [norm_code]
    vote_pct_at = {}  # (norm_code, stageIdx) → pct
    for r in traj_rows:
        stage_idx = stage_to_idx.get(r["phase"])
        if stage_idx is None:
            continue
        code = normalize_candidate_code(r["candidate_code"])
        pct = float(r["vote_pct"] or 0)
        if r["status"] in ("active", "surviving", "elected") and pct > 0:
            active_at[stage_idx].append(code)
            vote_pct_at[(code, stage_idx)] = pct

    # Elimination transfers: elim_xfers[stageIdx][eliminated_code] = [(dest_code, pct)]
    elim_xfers = {i: {} for i in range(1, 5)}
    for r in diag_rows:
        if r["diagnostic"] != "transfer_analysis" or r.get("transfer_type") != "elimination":
            continue
        stage_idx = stage_to_idx.get(r["winnowing_point"])
        if stage_idx is None:
            continue
        e_code = normalize_candidate_code(r["eliminated_code"])
        d_code = normalize_candidate_code(r["dest_code"])
        pct = float(r["pct_of_eliminated_total"] or 0)
        if e_code not in elim_xfers[stage_idx]:
            elim_xfers[stage_idx][e_code] = []
        elim_xfers[stage_idx][e_code].append((d_code, pct))

    # Build nodes
    nodes = []
    # Stage 0: all 20 initial candidates
    for code, pct in sorted(fc_pct.items(), key=lambda x: -x[1]):
        nodes.append({"id": f"{code}__0", "label": code, "stageIdx": 0, "pct": pct})

    # Stages 1–4: active candidates per stage
    for stage_idx in range(1, 5):
        for code in active_at[stage_idx]:
            pct = vote_pct_at.get((code, stage_idx), 0)
            nodes.append({"id": f"{code}__{stage_idx}", "label": code, "stageIdx": stage_idx, "pct": pct})

    # Collect all valid node ids
    node_ids = {n["id"] for n in nodes}

    # Build links
    links = []

    def add_link(src_id, tgt_id, value):
        if src_id in node_ids and tgt_id in node_ids and value > 0.01:
            links.append({"source": src_id, "target": tgt_id, "value": round(value, 3)})

    # Stage 0 → Stage 1 (Retail)
    retail_active = set(active_at[1])
    retail_elim_codes = set(elim_xfers[1].keys())

    for code, pct in fc_pct.items():
        src = f"{code}__0"
        if code in retail_active:
            add_link(src, f"{code}__1", pct)
        elif code in retail_elim_codes:
            for dest_code, xfer_pct in elim_xfers[1][code]:
                add_link(src, f"{dest_code}__1", pct * xfer_pct / 100)

    # Stages 1→2, 2→3, 3→4
    # Eliminations happen AT stage N+1 (winnowing_point=After_Pod_X)
    # So candidate is active in stage N and eliminated in stage N+1
    elim_stage_map = {
        2: 1,  # After_Pod_A elims happened between stage 1 and 2
        3: 2,
        4: 3,
    }
    for dst_idx in range(2, 5):
        src_idx = dst_idx - 1
        dst_active = set(active_at[dst_idx])

        # Survivors from src to dst
        for code in active_at[src_idx]:
            src_pct = vote_pct_at.get((code, src_idx), 0)
            if code in dst_active:
                add_link(f"{code}__{src_idx}", f"{code}__{dst_idx}", src_pct)
            elif code in elim_xfers[dst_idx]:
                # Eliminated between src and dst — transfer votes
                for dest_code, xfer_pct in elim_xfers[dst_idx][code]:
                    add_link(f"{code}__{src_idx}", f"{dest_code}__{dst_idx}", src_pct * xfer_pct / 100)
            # else: no links (exhausted/missing transfer data)

    stage_labels = [
        "Initial Slate (20)",
        "After Retail (12)",
        "After Pod A (10)",
        "After Pod C (8)",
        "Final Five",
    ]
    write_json({"stageLabels": stage_labels, "nodes": nodes, "links": links}, "primarySankey.json")


# ---------- primaryRaw.json ----------
def build_primary_raw():
    rows = read_csv(PURE_DIR / "primary_results_2028.csv")
    centroids = {r["candidate_code"]: r for r in read_csv(OUTPUTS / "candidate_factor_centroids.csv")}

    stages_order = ["After_Retail_Six", "After_Pod_A", "After_Pod_C", "After_Pod_BD"]
    stage_labels = {
        "After_Retail_Six": "Retail + Bench States",
        "After_Pod_A": "After Pod A (West)",
        "After_Pod_C": "After Pod C (South)",
        "After_Pod_BD": "After Pods B+D (Final)",
    }

    by_candidate = defaultdict(dict)
    quota_by_stage = {}
    for row in rows:
        stage = row["winnowing_point"]
        raw_code = row["candidate_code"]
        by_candidate[raw_code][stage] = {
            "voteTotal": float(row["vote_total"]),
            "votePct": float(row["vote_pct"]),
            "status": row["status"],
            "quotaThreshold": float(row["quota_threshold"]),
        }
        quota_by_stage[stage] = float(row["quota_threshold"])

    candidates = []
    for raw_code, stages in by_candidate.items():
        display_code = normalize_candidate_code(raw_code)
        c = centroids.get(raw_code, {})
        name = c.get("candidate_name", display_code) or display_code
        entry = {
            "code": display_code,
            "name": name,
            "F1": float(c.get("F1_security_order", 0)),
            "F2": float(c.get("F2_electoral_skepticism", 0)),
            "F3": float(c.get("F3_government_distrust", 0)),
            "F4": float(c.get("F4_religious_traditionalism", 0)),
            "F5": float(c.get("F5_populist_conservatism", 0)),
            "stages": {s: stages.get(s, {"voteTotal": 0, "votePct": 0, "status": "previously_eliminated", "quotaThreshold": quota_by_stage.get(s, 0)}) for s in stages_order},
        }
        candidates.append(entry)

    output = {
        "stagesOrder": stages_order,
        "stageLabels": stage_labels,
        "quotaByStage": quota_by_stage,
        "candidates": candidates,
    }
    write_json(output, "primaryRaw.json")


# ---------- primaryStateWinnersRaw.json ----------
def build_primary_state_winners_raw():
    state_rows = read_csv(PURE_DIR / "irv" / "irv_presidential_states_2028.csv")
    pod_rows = read_csv(OUTPUTS / "state_pod_assignments.csv")

    pod_by_fips = {r["state_fips"].zfill(2): r["pod"] for r in pod_rows}

    out = {}
    for r in state_rows:
        fips = r["state_fips"].zfill(2)
        winner = normalize_candidate_code(r["winner_code"].replace("_", "/"))
        runner_up = normalize_candidate_code(r["runner_up_code"].replace("_", "/"))
        # r1_pct_* columns are already party codes in the pure run
        r1_cols = [k for k in r.keys() if k.startswith("r1_pct_")]
        shares = {}
        for col in r1_cols:
            code = col.replace("r1_pct_", "")
            val = float(r.get(col) or 0)
            if val > 0:
                shares[code] = val
        total = sum(shares.values())
        if total > 0:
            shares = {k: round(v / total, 4) for k, v in shares.items()}
        pod = pod_by_fips.get(fips, "D")
        out[fips] = {
            "stateAbbr": r["state_abbr"],
            "winnerCode": winner,
            "runnerUpCode": runner_up,
            "pod": pod,
            "nRespondents": int(r["n_respondents"]),
            "shares": shares,
        }
    write_json(out, "primaryStateWinnersRaw.json")


# ---------- primarySankeyRaw.json ----------
def build_primary_sankey_raw():
    """Build stage-by-stage Sankey for pure (9-candidate) primary run.
    With only 9 candidates, all transfers are surplus (quota-based), not eliminations.
    Handles both cases: continuing candidates with surplus outflow, and eliminated candidates.
    """
    diag_rows = read_csv(PURE_DIR / "primary_diagnostics_2028.csv")

    # Stage 0: first-choice national pcts from state profiles (same approach as LF/blended)
    profiles = read_csv(PURE_DIR / "state_candidate_profiles.csv")
    fc_totals: dict = {}
    for row in profiles:
        n = float(row.get("total_weighted_respondents") or 0)
        for k, v in row.items():
            if k.startswith("first_choice_"):
                raw = k.replace("first_choice_", "")
                code = normalize_candidate_code(raw)
                fc_totals[code] = fc_totals.get(code, 0) + n * float(v or 0)
    total_fc = sum(fc_totals.values()) or 1
    fc_pct = {code: round(v / total_fc * 100, 3) for code, v in fc_totals.items()}

    stage_order = ["After_Retail_Six", "After_Pod_A", "After_Pod_C", "After_Pod_BD"]
    stage_to_idx = {s: i + 1 for i, s in enumerate(stage_order)}
    traj_rows = [r for r in diag_rows if r["diagnostic"] == "trajectories"]

    active_at = {i: [] for i in range(1, 5)}
    vote_pct_at = {}
    for r in traj_rows:
        stage_idx = stage_to_idx.get(r["phase"])
        if stage_idx is None:
            continue
        code = normalize_candidate_code(r["candidate_code"])
        pct = float(r["vote_pct"] or 0)
        if r["status"] in ("active", "surviving", "elected") and pct > 0:
            active_at[stage_idx].append(code)
            vote_pct_at[(code, stage_idx)] = pct

    # Collect ALL transfers (surplus + elimination)
    all_xfers = {i: {} for i in range(1, 5)}
    for r in diag_rows:
        if r["diagnostic"] != "transfer_analysis":
            continue
        stage_idx = stage_to_idx.get(r["winnowing_point"])
        if stage_idx is None:
            continue
        e_code = normalize_candidate_code(r["eliminated_code"])
        d_code = normalize_candidate_code(r["dest_code"])
        pct    = float(r["pct_of_eliminated_total"] or 0)
        if e_code not in all_xfers[stage_idx]:
            all_xfers[stage_idx][e_code] = []
        all_xfers[stage_idx][e_code].append((d_code, pct, r.get("transfer_type", "elimination")))

    nodes = []
    for code, pct in sorted(fc_pct.items(), key=lambda x: -x[1]):
        nodes.append({"id": f"{code}__0", "label": code, "stageIdx": 0, "pct": round(pct, 3)})
    for stage_idx in range(1, 5):
        for code in active_at[stage_idx]:
            pct = vote_pct_at.get((code, stage_idx), 0)
            nodes.append({"id": f"{code}__{stage_idx}", "label": code, "stageIdx": stage_idx, "pct": round(pct, 3)})

    # Pre-compute exhausted (ballot-exhaustion) totals so we can add Exhausted sink nodes
    def _exhausted_votes(code, src_pct, dst_active_set, stage_xfers):
        if code in dst_active_set:
            return 0.0
        xfer_sum = sum(p for _, p, _ in stage_xfers.get(code, []))
        return src_pct * max(0.0, 1.0 - xfer_sum / 100)

    exhausted_at = {i: 0.0 for i in range(1, 5)}
    for code, pct in fc_pct.items():
        exhausted_at[1] += _exhausted_votes(code, pct, set(active_at[1]), all_xfers[1])
    for dst_idx in range(2, 5):
        da = set(active_at[dst_idx])
        for code in active_at[dst_idx - 1]:
            exhausted_at[dst_idx] += _exhausted_votes(code, vote_pct_at.get((code, dst_idx - 1), 0), da, all_xfers[dst_idx])
    for stage_idx in range(1, 5):
        if exhausted_at[stage_idx] > 0.01:
            nodes.append({"id": f"exhausted__{stage_idx}", "label": "Exhausted", "stageIdx": stage_idx, "pct": round(exhausted_at[stage_idx], 3)})

    node_ids = {n["id"] for n in nodes}
    links = []

    def add_link(src_id, tgt_id, value, xfer_type="continuation"):
        if src_id in node_ids and tgt_id in node_ids and value > 0.01:
            links.append({"source": src_id, "target": tgt_id, "value": round(value, 3), "type": xfer_type})

    def draw_links_for_code(code, src_id, src_pct, dst_idx, dst_active, stage_xfers):
        """Draw continuation + any surplus/elimination/exhausted outgoing links."""
        xfers = stage_xfers.get(code, [])
        in_dst = code in dst_active

        if in_dst:
            surplus_out = sum(pct for _, pct, t in xfers if t == "surplus") / 100
            retained = src_pct * (1.0 - surplus_out)
            add_link(src_id, f"{code}__{dst_idx}", retained, "continuation")
            for dest_code, xfer_pct, _ in xfers:
                add_link(src_id, f"{dest_code}__{dst_idx}", src_pct * xfer_pct / 100, "surplus")
        else:
            xfer_sum = sum(p for _, p, _ in xfers)
            for dest_code, xfer_pct, _ in xfers:
                add_link(src_id, f"{dest_code}__{dst_idx}", src_pct * xfer_pct / 100, "elimination")
            exhausted = src_pct * max(0.0, 1.0 - xfer_sum / 100)
            if exhausted > 0.01:
                add_link(src_id, f"exhausted__{dst_idx}", exhausted, "exhausted")

    # Stage 0 → 1
    retail_active = set(active_at[1])
    for code, pct in fc_pct.items():
        draw_links_for_code(code, f"{code}__0", pct, 1, retail_active, all_xfers[1])

    # Stages 1 → 2 → 3 → 4
    for dst_idx in range(2, 5):
        src_idx = dst_idx - 1
        dst_active = set(active_at[dst_idx])
        for code in active_at[src_idx]:
            src_pct = vote_pct_at.get((code, src_idx), 0)
            draw_links_for_code(code, f"{code}__{src_idx}", src_pct, dst_idx, dst_active, all_xfers[dst_idx])

    # Count survivors per stage for labels
    n_survivors = [len(fc_pct), len(active_at[1]), len(active_at[2]), len(active_at[3]), len(active_at[4])]
    stage_labels = [
        f"Initial Slate ({n_survivors[0]})",
        f"After Retail ({n_survivors[1]})",
        f"After Pod A ({n_survivors[2]})",
        f"After Pod C ({n_survivors[3]})",
        f"Final ({n_survivors[4]})",
    ]
    write_json({"stageLabels": stage_labels, "nodes": nodes, "links": links}, "primarySankeyRaw.json")


# ---------- light fusion helpers ----------

def _build_trajectory_pcts(diag_rows):
    """Extract pod-relative first-choice % from 'trajectories' diagnostic rows.
    Returns dict: {(display_code, stage_key) → pct}  e.g. ('STY_ctr', 'After_Retail_Six') → 8.3
    """
    out = {}
    for r in diag_rows:
        if r.get("diagnostic") != "trajectories":
            continue
        raw_code = r.get("candidate_code", "")
        code = normalize_candidate_code(raw_code)
        stage = r.get("phase", "")
        try:
            pct = float(r.get("vote_pct") or 0)
        except (ValueError, TypeError):
            pct = 0.0
        out[(code, stage)] = pct
    return out


# ---------- primaryLightFusion.json ----------
def build_primary_light_fusion():
    """Build stage-by-stage data for 25-candidate light fusion primary run."""
    results_dir = LIGHT_FUSION_DIR
    rows = read_csv(results_dir / "primary_results_2028.csv")
    centroids = {r["candidate_code"]: r for r in read_csv(OUTPUTS / "light_fusion_centroids.csv")}
    diag_rows = read_csv(results_dir / "primary_diagnostics_2028.csv")
    traj_pcts = _build_trajectory_pcts(diag_rows)

    stages_order = ["After_Retail_Six", "After_Pod_A", "After_Pod_C", "After_Pod_BD"]
    stage_labels = {
        "After_Retail_Six": "Retail + Bench States",
        "After_Pod_A": "After Pod A (West)",
        "After_Pod_C": "After Pod C (South)",
        "After_Pod_BD": "After Pods B+D (Final)",
    }

    by_candidate = defaultdict(dict)
    quota_by_stage = {}
    for row in rows:
        stage = row["winnowing_point"]
        raw_code = row["candidate_code"]
        display_code = normalize_candidate_code(raw_code)
        by_candidate[raw_code][stage] = {
            "voteTotal":       float(row["vote_total"]),
            "votePct":         traj_pcts.get((display_code, stage), float(row["vote_pct"])),
            "status":          row["status"],
            "quotaThreshold":  float(row["quota_threshold"]),
        }
        quota_by_stage[stage] = float(row["quota_threshold"])

    candidates = []
    for raw_code, stages in by_candidate.items():
        display_code = normalize_candidate_code(raw_code)
        c = centroids.get(raw_code, {})
        name = c.get("candidate_name", display_code) or display_code
        entry = {
            "code": display_code,
            "name": name,
            "F1": float(c.get("F1_security_order", 0)),
            "F2": float(c.get("F2_electoral_skepticism", 0)),
            "F3": float(c.get("F3_government_distrust", 0)),
            "F4": float(c.get("F4_religious_traditionalism", 0)),
            "F5": float(c.get("F5_populist_conservatism", 0)),
            "stages": {s: stages.get(s, {
                "voteTotal": 0, "votePct": 0, "status": "previously_eliminated",
                "quotaThreshold": quota_by_stage.get(s, 0)
            }) for s in stages_order},
        }
        candidates.append(entry)

    write_json({
        "stagesOrder": stages_order,
        "stageLabels": stage_labels,
        "quotaByStage": quota_by_stage,
        "candidates": candidates,
    }, "primaryLightFusion.json")


# ---------- primaryStateWinnersLightFusion.json ----------
def build_primary_state_winners_light_fusion():
    """State-level first-choice winners derived from light fusion candidate profiles.
    Uses per-state first_choice_* proportions to determine winner and runner-up
    without needing a separate IRV state run. When IRV state data is available
    it will be used instead.
    """
    irv_path = LIGHT_FUSION_DIR / "irv" / "irv_presidential_states_2028.csv"
    if irv_path.exists():
        # Use proper IRV state winners if available
        state_rows = read_csv(irv_path)
        pod_rows = read_csv(LIGHT_FUSION_DIR / "state_pod_assignments.csv")
        pod_by_fips = {r["state_fips"].zfill(2): r["pod"] for r in pod_rows}
        out = {}
        for r in state_rows:
            fips = r["state_fips"].zfill(2)
            winner = normalize_candidate_code(r["winner_code"])
            runner_up = normalize_candidate_code(r["runner_up_code"])
            r1_cols = [k for k in r.keys() if k.startswith("r1_pct_")]
            shares = {}
            for col in r1_cols:
                code = normalize_candidate_code(col.replace("r1_pct_", ""))
                val = float(r.get(col) or 0)
                if val > 0:
                    shares[code] = val
            total = sum(shares.values())
            if total > 0:
                shares = {k: round(v / total, 4) for k, v in shares.items()}
            out[fips] = {
                "stateAbbr":    r["state_abbr"],
                "winnerCode":   winner,
                "runnerUpCode": runner_up,
                "pod":          pod_by_fips.get(fips, "D"),
                "nRespondents": int(r["n_respondents"]),
                "shares":       shares,
            }
        write_json(out, "primaryStateWinnersLightFusion.json")
        return

    # Derive state winners from first-choice proportions in state_candidate_profiles.csv
    profiles = read_csv(LIGHT_FUSION_DIR / "state_candidate_profiles.csv")
    pod_rows = read_csv(LIGHT_FUSION_DIR / "state_pod_assignments.csv")
    pod_by_fips = {r["state_fips"].zfill(2): r["pod"] for r in pod_rows}

    out = {}
    for r in profiles:
        fips = str(r["state_fips"]).zfill(2)
        n = float(r.get("total_weighted_respondents") or 0)

        # Collect first-choice proportions for all candidates
        shares = {}
        for k, v in r.items():
            if k.startswith("first_choice_"):
                raw = k.replace("first_choice_", "")
                code = normalize_candidate_code(raw)
                val = float(v or 0)
                if val > 0:
                    shares[code] = val

        if not shares:
            continue

        total = sum(shares.values())
        norm_shares = {k: round(v / total, 4) for k, v in shares.items()}

        # Sort descending by share to find winner and runner-up
        ranked = sorted(norm_shares.items(), key=lambda x: -x[1])
        winner = ranked[0][0] if ranked else ""
        runner_up = ranked[1][0] if len(ranked) > 1 else ""

        out[fips] = {
            "stateAbbr":    r["state_abbr"],
            "winnerCode":   winner,
            "runnerUpCode": runner_up,
            "pod":          pod_by_fips.get(fips, "D"),
            "nRespondents": round(n),
            "shares":       norm_shares,
        }
    write_json(out, "primaryStateWinnersLightFusion.json")


# ---------- primarySankeyLightFusion.json ----------
def build_primary_sankey_light_fusion():
    """Build stage-by-stage Sankey/alluvial data for light fusion (25-candidate) primary run.
    Includes both elimination and surplus transfer links.
    """
    diag_rows = read_csv(LIGHT_FUSION_DIR / "primary_diagnostics_2028.csv")

    # Stage 0: first-choice national pcts for all 25 candidates (same approach as build_primary_sankey)
    profiles = read_csv(LIGHT_FUSION_DIR / "state_candidate_profiles.csv")
    fc_totals: dict = {}
    for row in profiles:
        n = float(row.get("total_weighted_respondents") or 0)
        for k, v in row.items():
            if k.startswith("first_choice_"):
                raw = k.replace("first_choice_", "")
                code = normalize_candidate_code(raw)
                fc_totals[code] = fc_totals.get(code, 0) + n * float(v or 0)
    total_fc = sum(fc_totals.values()) or 1
    fc_pct = {code: round(v / total_fc * 100, 3) for code, v in fc_totals.items()}

    stage_order = ["After_Retail_Six", "After_Pod_A", "After_Pod_C", "After_Pod_BD"]
    stage_to_idx = {s: i + 1 for i, s in enumerate(stage_order)}

    traj_rows = [r for r in diag_rows if r.get("diagnostic") == "trajectories"]
    active_at = {i: [] for i in range(1, 5)}
    vote_pct_at = {}
    for r in traj_rows:
        stage_idx = stage_to_idx.get(r.get("phase"))
        if stage_idx is None:
            continue
        code = normalize_candidate_code(r["candidate_code"])
        pct  = float(r.get("vote_pct") or 0)
        if r.get("status") in ("active", "surviving", "elected") and pct > 0:
            active_at[stage_idx].append(code)
            vote_pct_at[(code, stage_idx)] = pct

    # Collect ALL transfers (elimination + surplus)
    all_xfers = {i: {} for i in range(1, 5)}
    for r in diag_rows:
        if r.get("diagnostic") != "transfer_analysis":
            continue
        stage_idx = stage_to_idx.get(r.get("winnowing_point"))
        if stage_idx is None:
            continue
        e_code = normalize_candidate_code(r.get("eliminated_code", ""))
        d_code = normalize_candidate_code(r.get("dest_code", ""))
        pct    = float(r.get("pct_of_eliminated_total") or 0)
        if e_code not in all_xfers[stage_idx]:
            all_xfers[stage_idx][e_code] = []
        all_xfers[stage_idx][e_code].append((d_code, pct))

    nodes = []
    for code, pct in sorted(fc_pct.items(), key=lambda x: -x[1]):
        nodes.append({"id": f"{code}__0", "label": code, "stageIdx": 0, "pct": round(pct, 3)})
    for stage_idx in range(1, 5):
        for code in active_at[stage_idx]:
            pct = vote_pct_at.get((code, stage_idx), 0)
            nodes.append({"id": f"{code}__{stage_idx}", "label": code, "stageIdx": stage_idx, "pct": round(pct, 3)})

    node_ids = {n["id"] for n in nodes}
    links = []

    def add_link(src_id, tgt_id, value, xfer_type="continuation"):
        if src_id in node_ids and tgt_id in node_ids and value > 0.01:
            links.append({"source": src_id, "target": tgt_id, "value": round(value, 3), "type": xfer_type})

    # Stage 0 → 1
    retail_active = set(active_at[1])
    retail_xfer_codes = set(all_xfers[1].keys())
    for code, pct in fc_pct.items():
        src = f"{code}__0"
        if code in retail_active:
            add_link(src, f"{code}__1", pct, "continuation")
        elif code in retail_xfer_codes:
            for dest_code, xfer_pct in all_xfers[1][code]:
                add_link(src, f"{dest_code}__1", pct * xfer_pct / 100, "elimination")

    # Stages 1 → 2 → 3 → 4
    for dst_idx in range(2, 5):
        src_idx = dst_idx - 1
        dst_active = set(active_at[dst_idx])
        for code in active_at[src_idx]:
            src_pct = vote_pct_at.get((code, src_idx), 0)
            if code in dst_active:
                add_link(f"{code}__{src_idx}", f"{code}__{dst_idx}", src_pct, "continuation")
            elif code in all_xfers[dst_idx]:
                xfer_type = "elimination"
                for dest_code, xfer_pct in all_xfers[dst_idx][code]:
                    add_link(f"{code}__{src_idx}", f"{dest_code}__{dst_idx}",
                             src_pct * xfer_pct / 100, xfer_type)

    stage_labels = [
        "Initial Slate (25)",
        "After Retail (12)",
        "After Pod A (10)",
        "After Pod C (8)",
        "Final (5)",
    ]
    write_json({"stageLabels": stage_labels, "nodes": nodes, "links": links}, "primarySankeyLightFusion.json")


# ---------- lightFusionProfiles.json ----------
def build_light_fusion_profiles():
    """Build viewpoint/position profiles for the 16 light fusion candidates."""
    lf_stats_path = OUTPUTS / "profiles" / "light_fusion_stats.csv"
    centroid_rows = read_csv(OUTPUTS / "light_fusion_centroids.csv")
    centroid_by_code = {r["candidate_code"]: r for r in centroid_rows}

    LIGHT_FUSION_CODES = [
        "PRG_dsa", "DSA_prg", "DSA_lib", "LIB_dsa", "LIB_sd",
        "SD_lib",  "SD_sty",  "STY_sd",  "STY_ctr", "CTR_sty",
        "CTR_con", "CON_ctr", "CON_ref", "REF_con",  "REF_nat", "NAT_ref",
    ]

    # Primary party for each light fusion candidate
    LF_PRIMARY = {
        "PRG_dsa": "PRG", "DSA_prg": "DSA", "DSA_lib": "DSA", "LIB_dsa": "LIB",
        "LIB_sd":  "LIB", "SD_lib":  "SD",  "SD_sty":  "SD",  "STY_sd":  "STY",
        "STY_ctr": "STY", "CTR_sty": "CTR", "CTR_con": "CTR", "CON_ctr": "CON",
        "CON_ref": "CON", "REF_con": "REF", "REF_nat": "REF", "NAT_ref": "NAT",
    }
    LF_LEAN = {
        "PRG_dsa": "DSA", "DSA_prg": "PRG", "DSA_lib": "LIB", "LIB_dsa": "DSA",
        "LIB_sd":  "SD",  "SD_lib":  "LIB", "SD_sty":  "STY", "STY_sd":  "SD",
        "STY_ctr": "CTR", "CTR_sty": "STY", "CTR_con": "CON", "CON_ctr": "CTR",
        "CON_ref": "REF", "REF_con": "CON", "REF_nat": "NAT", "NAT_ref": "REF",
    }

    # Load position stats
    try:
        lf_rows = read_csv(lf_stats_path)
    except FileNotFoundError:
        print(f"    [WARN] {lf_stats_path} not found; run generate_light_fusion_stats.py first")
        write_json({}, "lightFusionProfiles.json")
        return

    # Find key positions: rows where |lf_value - overall| is largest
    profiles = {}
    for code in LIGHT_FUSION_CODES:
        c = centroid_by_code.get(code, {})
        key_positions = []
        for row in lf_rows:
            if row.get("type") not in ("binary", "likert"):
                continue
            try:
                lf_val  = float(row.get(code, 0) or 0)
                overall = float(row.get("overall", 0) or 0)
                diff    = lf_val - overall
            except (ValueError, TypeError):
                continue
            if abs(diff) >= 3.0:
                key_positions.append({
                    "variable": row["variable"],
                    "question": row.get("question", ""),
                    "domain":   row.get("domain", ""),
                    "value":    round(lf_val, 1),
                    "overall":  round(overall, 1),
                    "diff":     round(diff, 1),
                })
        key_positions.sort(key=lambda x: -abs(x["diff"]))
        profiles[code] = {
            "code":        code,
            "primaryParty": LF_PRIMARY.get(code, ""),
            "lean":        LF_LEAN.get(code, ""),
            "F1": float(c.get("F1_security_order", 0)),
            "F2": float(c.get("F2_electoral_skepticism", 0)),
            "F3": float(c.get("F3_government_distrust", 0)),
            "F4": float(c.get("F4_religious_traditionalism", 0)),
            "F5": float(c.get("F5_populist_conservatism", 0)),
            "keyPositions": key_positions[:8],
        }

    write_json(profiles, "lightFusionProfiles.json")


# ---------- statePodAssignments.json ----------
def build_state_pods():
    rows = read_csv(OUTPUTS / "state_pod_assignments.csv")
    out = {}
    for r in rows:
        out[r["state_fips"].zfill(2)] = {
            "stateAbbr": r["state_abbr"],
            "pod": r["pod"],
            "bench": r["bench"] == "True",
            "retail": r["retail_2028"] == "True",
        }
    write_json(out, "statePodAssignments.json")


# ══════════════════════════════════════════════════════════════════════════════
# Factor Deviation (FD) builders
# ══════════════════════════════════════════════════════════════════════════════

# ---------- fdSenateCondorcet.json + fdSenateIRV.json ----------
_FD_PARTY_CLUSTER = {
    "CON": "0", "SD": "1", "STY": "2", "NAT": "3", "LIB": "4",
    "REF": "5", "CTR": "6", "DSA": "8", "PRG": "9",
}

def build_fd_senate():
    """FD senate compositions. CSV uses senator_party/axis/dir instead of label/cluster cols."""
    def _extract(rows):
        out = []
        for r in rows:
            party = r["senator_party"]
            out.append({
                "stateFips":   r["state_fips"].zfill(2),
                "stateAbbr":   r["state_abbr"],
                "senatorCode": r["senator_code"],
                "senatorParty": party,
                "senatorAxis": r["senator_axis"],
                "senatorDir":  r["senator_dir"],
                # SenateSeat-compatible fields for SenateMap / ParliamentChart
                "senatorLabel":     r["senator_code"],
                "senatorType":      "",
                "primaryCluster":   _FD_PARTY_CLUSTER.get(party, ""),
                "secondaryCluster": "",
            })
        return out

    cond_rows = read_csv(FD_DIR / "senate" / "senate_composition.csv")
    irv_rows  = read_csv(FD_DIR / "senate" / "senate_irv_composition.csv")
    write_json(_extract(cond_rows), "fdSenateCondorcet.json")
    write_json(_extract(irv_rows),  "fdSenateIRV.json")


# ---------- fdHouseSeats.json ----------
def build_fd_house_seats():
    """FD house seat summary. CSV uses candidate_code + party/axis/direction strings."""
    rows = read_csv(FD_DIR / "house" / "stv_seat_summary.csv")
    out = []
    for r in rows:
        out.append({
            "code":        r["candidate_code"],
            "party":       r["party"],
            "axis":        r["axis"],
            "direction":   r["direction"],
            "urban":       int(r["URBAN"]),
            "suburban":    int(r["SUBURBAN"]),
            "rural":       int(r["RURAL"]),
            "national":    int(r["NATIONAL"]),
            "pctNational": float(r["pct_national"]),
        })
    write_json(out, "fdHouseSeats.json")


# ---------- houseSeatsStateSTV.json ----------
def build_house_state_stv():
    """State-level proportional house: one entry per state×party with seats won."""
    rows = read_csv(OUTPUTS / "house" / "house_results_by_state.csv")
    out = []
    for r in rows:
        seats = int(r["party_seats"])
        if seats > 0:
            out.append({
                "state":      r["state_abbr"],
                "stateFips":  int(r["state_fips"]),
                "totalSeats": int(r["total_seats"]),
                "party":      r["party"],
                "seats":      seats,
                "voteShare":  float(r["vote_share"]),
            })
    write_json(out, "houseSeatsStateSTV.json")


# ---------- fdPrimary.json ----------
def build_fd_primary():
    """Stage-by-stage data for the 71-candidate FD primary run."""
    rows       = read_csv(FD_DIR / "primary_results_2028.csv")
    centroids  = {r["candidate_code"]: r for r in read_csv(FD_DIR / "candidate_factor_centroids.csv")}
    diag_rows  = read_csv(FD_DIR / "primary_diagnostics_2028.csv")
    traj_pcts  = _build_trajectory_pcts(diag_rows)

    stages_order = ["After_Retail_Six", "After_Pod_A", "After_Pod_C", "After_Pod_BD"]
    stage_labels = {
        "After_Retail_Six": "Retail + Bench States",
        "After_Pod_A":      "After Pod A (West)",
        "After_Pod_C":      "After Pod C (South)",
        "After_Pod_BD":     "After Pods B+D (Final)",
    }

    by_candidate  = defaultdict(dict)
    quota_by_stage = {}
    for row in rows:
        stage = row["winnowing_point"]
        code  = row["candidate_code"]
        by_candidate[code][stage] = {
            "voteTotal":      float(row["vote_total"]),
            "votePct":        traj_pcts.get((code, stage), float(row["vote_pct"])),
            "status":         row["status"],
            "quotaThreshold": float(row["quota_threshold"]),
        }
        quota_by_stage[stage] = float(row["quota_threshold"])

    candidates = []
    for code, stages in by_candidate.items():
        c = centroids.get(code, {})
        candidates.append({
            "code":      code,
            "name":      code,
            "party":     c.get("party", ""),
            "axis":      c.get("axis", "base"),
            "direction": c.get("direction", "base"),
            "F1": float(c.get("F1_security_order", 0)),
            "F2": float(c.get("F2_electoral_skepticism", 0)),
            "F3": float(c.get("F3_government_distrust", 0)),
            "F4": float(c.get("F4_religious_traditionalism", 0)),
            "F5": float(c.get("F5_populist_conservatism", 0)),
            "stages": {s: stages.get(s, {
                "voteTotal": 0, "votePct": 0,
                "status": "previously_eliminated",
                "quotaThreshold": quota_by_stage.get(s, 0),
            }) for s in stages_order},
        })

    write_json({
        "stagesOrder":  stages_order,
        "stageLabels":  stage_labels,
        "quotaByStage": quota_by_stage,
        "candidates":   candidates,
    }, "fdPrimary.json")


# ---------- fdPrimaryStateWinners.json ----------
def build_fd_primary_state_winners():
    """State-level IRV winners from the FD presidential general."""
    irv_path = FD_DIR / "irv" / "irv_presidential_states_2028.csv"
    pod_rows = read_csv(FD_DIR / "state_pod_assignments.csv")
    pod_by_fips = {r["state_fips"].zfill(2): r["pod"] for r in pod_rows}

    state_rows = read_csv(irv_path)
    out = {}
    for r in state_rows:
        fips       = r["state_fips"].zfill(2)
        winner     = r.get("irv_winner", r.get("winner_code", ""))
        runner_up  = r.get("irv_runner_up", r.get("runner_up_code", ""))
        r1_cols    = [k for k in r.keys() if k.startswith("r1_pct_") or k.startswith("fc_pct_")]
        shares = {}
        for col in r1_cols:
            code = col.replace("r1_pct_", "").replace("fc_pct_", "")
            val  = float(r.get(col) or 0)
            if val > 0:
                shares[code] = val
        total = sum(shares.values())
        if total > 0:
            shares = {k: round(v / total, 4) for k, v in shares.items()}
        n_resp = int(float(r.get("n_respondents", 0) or r.get("total_weight", 0) or 0))
        out[fips] = {
            "stateAbbr":    r["state_abbr"],
            "winnerCode":   winner,
            "runnerUpCode": runner_up,
            "pod":          pod_by_fips.get(fips, "D"),
            "nRespondents": n_resp,
            "shares":       shares,
        }
    write_json(out, "fdPrimaryStateWinners.json")


# ---------- pureMultiPrimaryStateWinners.json ----------
def build_pure_multi_primary_state_winners():
    """State-level IRV winners from the Raw Multi primary."""
    irv_path = PURE_MULTI_DIR / "irv" / "irv_presidential_states_2028.csv"
    pod_rows = read_csv(PURE_MULTI_DIR / "state_pod_assignments.csv")
    pod_by_fips = {r["state_fips"].zfill(2): r["pod"] for r in pod_rows}

    state_rows = read_csv(irv_path)
    out = {}
    for r in state_rows:
        fips       = r["state_fips"].zfill(2)
        winner     = r.get("irv_winner", r.get("winner_code", ""))
        runner_up  = r.get("irv_runner_up", r.get("runner_up_code", ""))
        r1_cols    = [k for k in r.keys() if k.startswith("r1_pct_") or k.startswith("fc_pct_")]
        shares = {}
        for col in r1_cols:
            code = col.replace("r1_pct_", "").replace("fc_pct_", "")
            val  = float(r.get(col) or 0)
            if val > 0:
                shares[code] = val
        total = sum(shares.values())
        if total > 0:
            shares = {k: round(v / total, 4) for k, v in shares.items()}
        n_resp = int(float(r.get("n_respondents", 0) or r.get("total_weight", 0) or 0))
        out[fips] = {
            "stateAbbr":    r["state_abbr"],
            "winnerCode":   winner,
            "runnerUpCode": runner_up,
            "pod":          pod_by_fips.get(fips, "D"),
            "nRespondents": n_resp,
            "shares":       shares,
        }
    write_json(out, "pureMultiPrimaryStateWinners.json")


# ---------- fdPrimarySankey.json ----------
def build_fd_primary_sankey():
    """Sankey/alluvial data for the 71-candidate FD primary.
    Stage 0 first-choice proportions come from state_candidate_profiles.csv.
    """
    diag_rows = read_csv(FD_DIR / "primary_diagnostics_2028.csv")
    profiles  = read_csv(FD_DIR / "state_candidate_profiles.csv")

    # Stage 0: aggregate first-choice totals across states
    fc_totals: dict = {}
    for row in profiles:
        n = float(row.get("total_weighted_respondents") or 0)
        for k, v in row.items():
            if k.startswith("first_choice_"):
                code = k.replace("first_choice_", "")
                fc_totals[code] = fc_totals.get(code, 0) + n * float(v or 0)
    total_fc = sum(fc_totals.values()) or 1
    fc_pct   = {code: round(v / total_fc * 100, 3) for code, v in fc_totals.items()}

    stage_order  = ["After_Retail_Six", "After_Pod_A", "After_Pod_C", "After_Pod_BD"]
    stage_to_idx = {s: i + 1 for i, s in enumerate(stage_order)}

    traj_rows    = [r for r in diag_rows if r.get("diagnostic") == "trajectories"]
    active_at    = {i: [] for i in range(1, 5)}
    vote_pct_at  = {}
    for r in traj_rows:
        stage_idx = stage_to_idx.get(r.get("phase"))
        if stage_idx is None:
            continue
        code = r["candidate_code"]
        pct  = float(r.get("vote_pct") or 0)
        if r.get("status") in ("active", "surviving", "elected") and pct > 0:
            active_at[stage_idx].append(code)
            vote_pct_at[(code, stage_idx)] = pct

    # Collect ALL transfers (surplus + elimination), keyed by (stage_idx, eliminated_code)
    all_xfers = {i: {} for i in range(1, 5)}
    for r in diag_rows:
        if r.get("diagnostic") != "transfer_analysis":
            continue
        stage_idx = stage_to_idx.get(r.get("winnowing_point"))
        if stage_idx is None:
            continue
        e_code = r.get("eliminated_code", "")
        d_code = r.get("dest_code", "")
        pct    = float(r.get("pct_of_eliminated_total") or 0)
        xtype  = r.get("transfer_type", "elimination")
        if e_code not in all_xfers[stage_idx]:
            all_xfers[stage_idx][e_code] = []
        all_xfers[stage_idx][e_code].append((d_code, pct, xtype))

    nodes = []
    for code, pct in sorted(fc_pct.items(), key=lambda x: -x[1]):
        nodes.append({"id": f"{code}__0", "label": code, "stageIdx": 0, "pct": round(pct, 3)})
    for stage_idx in range(1, 5):
        for code in active_at[stage_idx]:
            pct = vote_pct_at.get((code, stage_idx), 0)
            nodes.append({"id": f"{code}__{stage_idx}", "label": code, "stageIdx": stage_idx, "pct": round(pct, 3)})

    # Pre-compute exhausted (ballot-exhaustion) totals so we can add Exhausted sink nodes
    def _exhausted_votes(code, src_pct, dst_active_set, stage_xfers):
        if code in dst_active_set:
            return 0.0
        xfer_sum = sum(p for _, p, _ in stage_xfers.get(code, []))
        return src_pct * max(0.0, 1.0 - xfer_sum / 100)

    exhausted_at = {i: 0.0 for i in range(1, 5)}
    for code, pct in fc_pct.items():
        exhausted_at[1] += _exhausted_votes(code, pct, set(active_at[1]), all_xfers[1])
    for dst_idx in range(2, 5):
        da = set(active_at[dst_idx])
        for code in active_at[dst_idx - 1]:
            exhausted_at[dst_idx] += _exhausted_votes(code, vote_pct_at.get((code, dst_idx - 1), 0), da, all_xfers[dst_idx])
    for stage_idx in range(1, 5):
        if exhausted_at[stage_idx] > 0.01:
            nodes.append({"id": f"exhausted__{stage_idx}", "label": "Exhausted", "stageIdx": stage_idx, "pct": round(exhausted_at[stage_idx], 3)})

    node_ids = {n["id"] for n in nodes}
    links = []

    def add_link(src_id, tgt_id, value, xfer_type="continuation"):
        if src_id in node_ids and tgt_id in node_ids and value > 0.01:
            links.append({"source": src_id, "target": tgt_id, "value": round(value, 3), "type": xfer_type})

    def draw_links_for_code(code, src_id, src_pct, dst_idx, dst_active, stage_xfers):
        """Draw continuation (retained) + surplus/elimination/exhausted outgoing links."""
        xfers = stage_xfers.get(code, [])
        in_dst = code in dst_active
        if in_dst:
            surplus_out = sum(p for _, p, t in xfers if t == "surplus") / 100
            retained = src_pct * (1.0 - surplus_out)
            add_link(src_id, f"{code}__{dst_idx}", retained, "continuation")
            for dest_code, xfer_pct, _ in xfers:
                add_link(src_id, f"{dest_code}__{dst_idx}", src_pct * xfer_pct / 100, "surplus")
        else:
            xfer_sum = sum(p for _, p, _ in xfers)
            for dest_code, xfer_pct, _ in xfers:
                add_link(src_id, f"{dest_code}__{dst_idx}", src_pct * xfer_pct / 100, "elimination")
            exhausted = src_pct * max(0.0, 1.0 - xfer_sum / 100)
            if exhausted > 0.01:
                add_link(src_id, f"exhausted__{dst_idx}", exhausted, "exhausted")

    # Stage 0 → 1
    retail_active = set(active_at[1])
    for code, pct in fc_pct.items():
        draw_links_for_code(code, f"{code}__0", pct, 1, retail_active, all_xfers[1])

    # Stages 1 → 2 → 3 → 4
    for dst_idx in range(2, 5):
        src_idx   = dst_idx - 1
        dst_active = set(active_at[dst_idx])
        for code in active_at[src_idx]:
            src_pct = vote_pct_at.get((code, src_idx), 0)
            draw_links_for_code(code, f"{code}__{src_idx}", src_pct, dst_idx, dst_active, all_xfers[dst_idx])

    n_survivors = [len(fc_pct), len(active_at[1]), len(active_at[2]), len(active_at[3]), len(active_at[4])]
    stage_labels = [
        f"Initial Slate ({n_survivors[0]})",
        f"After Retail ({n_survivors[1]})",
        f"After Pod A ({n_survivors[2]})",
        f"After Pod C ({n_survivors[3]})",
        f"Final ({n_survivors[4]})",
    ]
    write_json({"stageLabels": stage_labels, "nodes": nodes, "links": links}, "fdPrimarySankey.json")


# ---------- fdPresidentialElection.json ----------
def build_fd_presidential_election():
    """FD general election: national IRV rounds, Condorcet matchups, per-state winners."""
    irv_dir = FD_DIR / "irv"

    irv_rows      = read_csv(irv_dir / "irv_presidential_national_2028.csv")
    rounds_by_num = defaultdict(list)
    for r in irv_rows:
        rounds_by_num[int(r["round"])].append(r)

    irv_rounds = []
    irv_winner = None
    for rnum in sorted(rounds_by_num.keys()):
        candidates = []
        for r in rounds_by_num[rnum]:
            code      = r["candidate_code"]
            eliminated = r["eliminated"].strip().lower() == "true"
            winner     = r["winner"].strip().lower() == "true"
            if winner and not eliminated:
                irv_winner = code
            candidates.append({
                "code":      code,
                "name":      r["candidate_name"],
                "pct":       round(float(r["vote_pct"]), 2),
                "votes":     round(float(r["vote_total"]), 0),
                "eliminated": eliminated,
                "winner":    winner,
            })
        irv_rounds.append({"round": rnum, "candidates": candidates})

    condorcet_matchups = []
    condorcet_winner   = None
    cond_rows = read_csv(irv_dir / "condorcet_matchups_2028.csv")
    for r in cond_rows:
        a       = r["candidate_a"]
        b       = r["candidate_b"]
        votes_a = float(r["votes_a_beats_b"])
        votes_b = float(r["votes_b_beats_a"])
        total   = votes_a + votes_b
        condorcet_matchups.append({
            "candidateA": a,
            "candidateB": b,
            "aWinsPct":   round(votes_a / total * 100, 3) if total > 0 else 50.0,
            "margin":     round(float(r["margin_pct"]), 3),
            "winner":     r["winner"],
        })
        if not condorcet_winner and r.get("condorcet_winner"):
            condorcet_winner = r["condorcet_winner"]

    state_rows  = read_csv(irv_dir / "irv_presidential_states_2028.csv")
    pod_rows    = read_csv(FD_DIR / "state_pod_assignments.csv")
    pod_by_fips = {r["state_fips"].zfill(2): r["pod"] for r in pod_rows}

    irv_state_winners = {}
    for r in state_rows:
        fips    = r["state_fips"].zfill(2)
        r1_cols = [k for k in r.keys() if k.startswith("r1_pct_")]
        shares  = {}
        for col in r1_cols:
            code = col.replace("r1_pct_", "")
            val  = float(r.get(col) or 0)
            if val > 0:
                shares[code] = val
        total = sum(shares.values())
        irv_state_winners[fips] = {
            "stateAbbr":    r["state_abbr"],
            "winner":       r["winner_code"],
            "pod":          pod_by_fips.get(fips, "D"),
            "nRespondents": int(r["n_respondents"]),
            "shares":       {k: round(v / total, 4) for k, v in shares.items()} if total > 0 else {},
        }

    write_json({
        "irvRounds":        irv_rounds,
        "irvWinner":        irv_winner,
        "condorcetMatchups": condorcet_matchups,
        "condorcetWinner":  condorcet_winner,
        "irvStateWinners":  irv_state_winners,
    }, "fdPresidentialElection.json")


# ---------- rawMultiPresidentialElection.json ----------
def build_raw_multi_presidential_election():
    """Raw Multi general election: national IRV rounds, Condorcet matchups, per-state winners."""
    irv_dir = PURE_MULTI_DIR / "irv"

    irv_rows      = read_csv(irv_dir / "irv_presidential_national_2028.csv")
    rounds_by_num = defaultdict(list)
    for r in irv_rows:
        rounds_by_num[int(r["round"])].append(r)

    irv_rounds = []
    irv_winner = None
    for rnum in sorted(rounds_by_num.keys()):
        candidates = []
        for r in rounds_by_num[rnum]:
            code       = r.get("candidate_code", r.get("candidate", ""))
            status     = r.get("status", "surviving")
            eliminated = (r.get("eliminated", "").strip().lower() == "true") or (status == "eliminated_this_round")
            winner     = (r.get("winner", "").strip().lower() == "true") or (status == "winner")
            if winner and not eliminated:
                irv_winner = code
            candidates.append({
                "code":       code,
                "name":       r.get("candidate_name", r.get("party", code)),
                "pct":        round(float(r.get("vote_pct", r.get("pct", 0)) or 0), 2),
                "votes":      round(float(r.get("vote_total", r.get("votes", 0)) or 0), 0),
                "eliminated": eliminated,
                "winner":     winner,
            })
        irv_rounds.append({"round": rnum, "candidates": candidates})

    condorcet_matchups = []
    condorcet_winner   = None
    cond_rows = read_csv(irv_dir / "condorcet_matchups_2028.csv")
    for r in cond_rows:
        a       = r.get("candidate_a", r.get("a", ""))
        b       = r.get("candidate_b", r.get("b", ""))
        votes_a = float(r.get("votes_a_beats_b", r.get("votes_a", 0)) or 0)
        votes_b = float(r.get("votes_b_beats_a", r.get("votes_b", 0)) or 0)
        total   = votes_a + votes_b
        margin_pct = float(r.get("margin_pct", r.get("margin", 0)) or 0)
        if total > 0 and "margin_pct" not in r:
            margin_pct = (votes_a - votes_b) / total * 100
        condorcet_matchups.append({
            "candidateA": a,
            "candidateB": b,
            "aWinsPct":   round(votes_a / total * 100, 3) if total > 0 else 50.0,
            "margin":     round(margin_pct, 3),
            "winner":     a if votes_a >= votes_b else b,
        })
        if not condorcet_winner and r.get("condorcet_winner"):
            condorcet_winner = r["condorcet_winner"]

    state_rows  = read_csv(irv_dir / "irv_presidential_states_2028.csv")
    pod_rows    = read_csv(PURE_MULTI_DIR / "state_pod_assignments.csv")
    pod_by_fips = {r["state_fips"].zfill(2): r["pod"] for r in pod_rows}

    irv_state_winners = {}
    for r in state_rows:
        fips    = str(r["state_fips"]).zfill(2)
        fc_cols = [k for k in r.keys() if k.startswith("r1_pct_") or k.startswith("fc_pct_")]
        shares  = {}
        for col in fc_cols:
            code = col.replace("r1_pct_", "").replace("fc_pct_", "")
            val  = float(r.get(col) or 0)
            if val > 0:
                shares[code] = val
        total = sum(shares.values())
        winner = r.get("winner_code", r.get("irv_winner", ""))
        n_resp = int(float(r.get("n_respondents", 0) or r.get("total_weight", 0) or 0))
        irv_state_winners[fips] = {
            "stateAbbr":    r["state_abbr"],
            "winner":       winner,
            "pod":          pod_by_fips.get(fips, "D"),
            "nRespondents": n_resp,
            "shares":       {k: round(v / total, 4) for k, v in shares.items()} if total > 0 else {},
        }

    write_json({
        "irvRounds":         irv_rounds,
        "irvWinner":         irv_winner,
        "condorcetMatchups": condorcet_matchups,
        "condorcetWinner":   condorcet_winner,
        "irvStateWinners":   irv_state_winners,
    }, "rawMultiPresidentialElection.json")


# ---------- fdProfiles.json ----------
def build_fd_profiles():
    """Position profiles for all 71 FD candidates. Key positions = items where
    |candidate_value - overall| >= 3pp (binary/likert rows only).
    """
    stats_path   = FD_DIR / "profiles" / "factor_deviation_stats.csv"
    centroid_rows = read_csv(FD_DIR / "candidate_factor_centroids.csv")
    centroids     = {r["candidate_code"]: r for r in centroid_rows}
    cand_codes    = [r["candidate_code"] for r in centroid_rows]

    try:
        stat_rows = read_csv(stats_path)
    except FileNotFoundError:
        print(f"    [WARN] {stats_path} not found")
        write_json({}, "fdProfiles.json")
        return

    profiles = {}
    for code in cand_codes:
        c = centroids.get(code, {})
        key_positions = []
        for row in stat_rows:
            if row.get("type") not in ("binary", "likert"):
                continue
            try:
                val     = float(row.get(code, 0) or 0)
                overall = float(row.get("overall", 0) or 0)
                diff    = val - overall
            except (ValueError, TypeError):
                continue
            if abs(diff) >= 3.0:
                key_positions.append({
                    "variable": row["variable"],
                    "question": row.get("question", ""),
                    "domain":   row.get("domain", ""),
                    "value":    round(val, 1),
                    "overall":  round(overall, 1),
                    "diff":     round(diff, 1),
                })
        key_positions.sort(key=lambda x: -abs(x["diff"]))

        # Build variables dict (top 40 by |diffPp|) for CompareTab.
        # Use _extract_policy_vars() so we correctly handle binary, binary_agree,
        # likert5 (SA+A), and trust (not_very_much + none_at_all) types.
        def _get_val(r, _code=code):
            try:
                return float(r.get(_code) or 0)
            except (ValueError, TypeError):
                return None
        variables = _extract_policy_vars(stat_rows, _get_val, max_vars=40)

        profiles[code] = {
            "code":      code,
            "party":     c.get("party", ""),
            "axis":      c.get("axis", "base"),
            "direction": c.get("direction", "base"),
            "F1": float(c.get("F1_security_order", 0)),
            "F2": float(c.get("F2_electoral_skepticism", 0)),
            "F3": float(c.get("F3_government_distrust", 0)),
            "F4": float(c.get("F4_religious_traditionalism", 0)),
            "F5": float(c.get("F5_populist_conservatism", 0)),
            "keyPositions": key_positions[:8],
            "variables": variables,
        }

    write_json(profiles, "fdProfiles.json")


# ---------- pureMultiPrimary.json ----------
def build_pure_multi_primary():
    """Stage-by-stage data for the 21-candidate pure/raw multi primary run."""
    rows      = read_csv(PURE_MULTI_DIR / "primary_results_2028.csv")
    diag_rows = read_csv(PURE_MULTI_DIR / "primary_diagnostics_2028.csv")
    traj_pcts = _build_trajectory_pcts(diag_rows)

    # Load party centroids keyed by candidate_name (= party code: CON, SD, etc.)
    centroids_rows = read_csv(OUTPUTS / "candidate_factor_centroids.csv")
    party_f = {
        r["candidate_name"]: {
            "F1": float(r.get("F1_security_order", 0) or 0),
            "F2": float(r.get("F2_electoral_skepticism", 0) or 0),
            "F3": float(r.get("F3_government_distrust", 0) or 0),
            "F4": float(r.get("F4_religious_traditionalism", 0) or 0),
            "F5": float(r.get("F5_populist_conservatism", 0) or 0),
        }
        for r in centroids_rows
    }

    # Auto-detect stages from the CSV
    all_stages = []
    for row in rows:
        s = row.get("winnowing_point", row.get("stage", ""))
        if s and s not in all_stages:
            all_stages.append(s)
    # Filter to non-initial stages
    stages_order = [s for s in all_stages if s != "Initial_Slate"]
    stage_labels = {s: s.replace("_", " ").replace("After ", "") for s in stages_order}

    by_candidate   = defaultdict(dict)
    quota_by_stage = {}
    party_of_code  = {}
    for row in rows:
        stage = row.get("winnowing_point", row.get("stage", ""))
        code  = row.get("candidate_code", row.get("candidate", ""))
        party_of_code[code] = row.get("party_code", row.get("party", code.rsplit("_", 1)[0]))
        vote_pct = float(row.get("vote_pct", row.get("vote_share", 0)) or 0)
        vote_total = float(row.get("vote_total", 0) or 0)
        quota = float(row.get("quota_threshold", 0) or 0)
        by_candidate[code][stage] = {
            "voteTotal":      vote_total,
            "votePct":        traj_pcts.get((code, stage), vote_pct),
            "status":         row.get("status", "surviving"),
            "quotaThreshold": quota,
        }
        if quota > 0:
            quota_by_stage[stage] = quota

    candidates = []
    for code, stages in by_candidate.items():
        party = party_of_code.get(code, code.rsplit("_", 1)[0])
        f = party_f.get(party, {"F1": 0.0, "F2": 0.0, "F3": 0.0, "F4": 0.0, "F5": 0.0})
        candidates.append({
            "code":      code,
            "name":      code,
            "party":     party,
            "axis":      "base",
            "direction": "base",
            "F1": f["F1"], "F2": f["F2"], "F3": f["F3"], "F4": f["F4"], "F5": f["F5"],
            "stages": {s: stages.get(s, {
                "voteTotal": 0, "votePct": 0,
                "status": "previously_eliminated",
                "quotaThreshold": quota_by_stage.get(s, 0),
            }) for s in stages_order},
        })

    write_json({
        "stagesOrder":  stages_order,
        "stageLabels":  stage_labels,
        "quotaByStage": quota_by_stage,
        "candidates":   candidates,
    }, "pureMultiPrimary.json")


# ---------- pureMultiPrimarySankey.json ----------
def build_pure_multi_primary_sankey():
    """Sankey/alluvial data from primary_results + primary_diagnostics CSVs."""
    results_rows = read_csv(PURE_MULTI_DIR / "primary_results_2028.csv")
    diag_rows    = read_csv(PURE_MULTI_DIR / "primary_diagnostics_2028.csv")

    # Discover stages from results
    all_stages = []
    for r in results_rows:
        s = r.get("winnowing_point", r.get("stage", ""))
        if s and s not in all_stages:
            all_stages.append(s)
    initial_stage = all_stages[0] if all_stages else "Initial_Slate"
    elim_stages   = [s for s in all_stages if s != initial_stage]
    n_stages      = len(elim_stages)

    # Build per-stage candidate data {stage_idx: {code: {pct, status}}}
    stage_to_idx = {s: i for i, s in enumerate([initial_stage] + elim_stages)}
    candidates_at = {i: {} for i in range(len(all_stages))}

    for r in results_rows:
        stage   = r.get("winnowing_point", r.get("stage", ""))
        code    = r.get("candidate_code", r.get("candidate", ""))
        pct     = float(r.get("vote_pct", r.get("vote_share", 0)) or 0)
        status  = r.get("status", "surviving")
        idx     = stage_to_idx.get(stage)
        if idx is not None:
            candidates_at[idx][code] = {"pct": pct, "status": status}

    # Build transfer flows per stage {stage_idx: {from_code: [(to_code, votes, type)]}}
    transfers_at = {i: defaultdict(list) for i in range(1, len(all_stages))}
    for r in diag_rows:
        stage  = r.get("winnowing_point", "")
        idx    = stage_to_idx.get(stage)
        if idx is None or idx == 0:
            continue
        e_code = r.get("eliminated_code", "")
        d_code = r.get("dest_code", "")
        votes  = float(r.get("transferred_votes", 0) or 0)
        xtype  = r.get("transfer_type", "elimination")
        if e_code and d_code:
            transfers_at[idx][e_code].append((d_code, votes, xtype))

    # Compute total votes for percentage normalization
    total_votes = sum(c["pct"] for c in candidates_at[0].values()) or 100.0

    # Build nodes
    nodes = []
    for code, info in sorted(candidates_at[0].items(), key=lambda x: -x[1]["pct"]):
        if info["pct"] > 0:
            nodes.append({"id": f"{code}__0", "label": code, "stageIdx": 0, "pct": round(info["pct"], 3)})

    for stage_idx in range(1, len(all_stages)):
        for code, info in candidates_at[stage_idx].items():
            if info["status"] in ("surviving", "elected", "active"):
                pct = max(info["pct"], 0.1)  # minimum visibility for zero-vote survivors
                nodes.append({"id": f"{code}__{stage_idx}", "label": code, "stageIdx": stage_idx, "pct": round(pct, 3)})

    # Add exhausted nodes where needed
    for stage_idx in range(1, len(all_stages)):
        prev_codes = set(candidates_at[stage_idx - 1].keys())
        curr_surv  = {c for c, info in candidates_at[stage_idx].items()
                      if info["status"] in ("surviving", "elected", "active")}
        eliminated = prev_codes - curr_surv
        if eliminated:
            # Check if there's unaccounted vote flow
            nodes.append({"id": f"exhausted__{stage_idx}", "label": "Exhausted", "stageIdx": stage_idx, "pct": 0})

    node_ids = {n["id"] for n in nodes}
    links    = []

    def add_link(src, tgt, val, xtype="continuation"):
        if src in node_ids and tgt in node_ids and val > 0.005:
            links.append({"source": src, "target": tgt, "value": round(val, 3), "type": xtype})

    # Build links between stages
    for stage_idx in range(1, len(all_stages)):
        prev = candidates_at[stage_idx - 1]
        curr_surv = {c for c, info in candidates_at[stage_idx].items()
                     if info["status"] in ("surviving", "elected", "active")}
        xfers = transfers_at[stage_idx]

        # Total transferred per eliminated candidate (for percentage computation)
        elim_totals = {}
        for e_code, flows in xfers.items():
            elim_totals[e_code] = sum(v for _, v, _ in flows) or 1.0

        for code, info in prev.items():
            if info["status"] not in ("surviving", "elected", "active"):
                continue
            src_id  = f"{code}__{stage_idx - 1}"
            src_pct = info["pct"]

            if code in curr_surv:
                # Survivor: continuation link + any surplus transfers out
                surplus_flows = [(d, v, t) for d, v, t in xfers.get(code, []) if t == "surplus"]
                surplus_total = sum(v for _, v, _ in surplus_flows)
                elim_total    = elim_totals.get(code, 1.0)
                surplus_pct   = (surplus_total / elim_total * src_pct) if surplus_flows else 0

                add_link(src_id, f"{code}__{stage_idx}", src_pct - surplus_pct, "continuation")
                for dest, vol, _ in surplus_flows:
                    frac = vol / elim_total * src_pct
                    add_link(src_id, f"{dest}__{stage_idx}", frac, "surplus")
            else:
                # Eliminated: distribute to destinations
                flows = xfers.get(code, [])
                elim_total = elim_totals.get(code, 1.0)
                accounted = 0
                for dest, vol, xtype in flows:
                    frac = vol / elim_total * src_pct
                    tgt = f"{dest}__{stage_idx}"
                    if tgt in node_ids:
                        add_link(src_id, tgt, frac, "elimination")
                        accounted += frac
                remaining = src_pct - accounted
                if remaining > 0.01:
                    add_link(src_id, f"exhausted__{stage_idx}", remaining, "exhausted")

    # Stage labels
    counts = [
        sum(1 for info in candidates_at[i].values()
            if info["status"] in ("surviving", "elected", "active"))
        for i in range(len(all_stages))
    ]
    stage_label_names = ["Initial Slate"] + [s.replace("_", " ").replace("After ", "") for s in elim_stages]
    stage_labels = [f"{name} ({counts[i]})" for i, name in enumerate(stage_label_names)]

    write_json({"stageLabels": stage_labels, "nodes": nodes, "links": links}, "pureMultiPrimarySankey.json")


# ---------- pureMultiSenate*.json ----------
def build_pure_multi_senate():
    """Pure multi senate compositions. senator_code is 'PARTY_N'; party from senator_party col."""
    def _extract(rows):
        out = []
        for r in rows:
            party = r.get("senator_party", r["senator_code"].rsplit("_", 1)[0])
            out.append({
                "stateFips":        r["state_fips"].zfill(2),
                "stateAbbr":        r["state_abbr"],
                "senatorCode":      r["senator_code"],
                "senatorParty":     party,
                "senatorAxis":      "base",
                "senatorDir":       "base",
                # SenateSeat-compatible fields for SenateMap / ParliamentChart
                "senatorLabel":     r["senator_code"],
                "senatorType":      "pure",
                "primaryCluster":   _FD_PARTY_CLUSTER.get(party, ""),
                "secondaryCluster": "",
            })
        return out

    cond_rows = read_csv(PURE_MULTI_DIR / "senate" / "senate_composition.csv")
    irv_rows  = read_csv(PURE_MULTI_DIR / "senate" / "senate_irv_composition.csv")
    write_json(_extract(cond_rows), "pureMultiSenateCondorcet.json")
    write_json(_extract(irv_rows),  "pureMultiSenateIRV.json")


def build_fptp_disproportionality():
    rows = read_csv(RESULTS / "post_recs" / "Current Congressional Inequality.csv")
    out = []
    for r in rows:
        if not r.get("State"):
            continue
        try:
            out.append({
                "state": r["State"],
                "totalSeats": int(r["Total Seats"]),
                "gopFptpSeats": int(r["GOP FPTP Seats"]),
                "demFptpSeats": int(r["DEM FPTP Seats"]),
                "gopPrSeats": int(r["GOP PR Seats"]),
                "demPrSeats": int(r["Dem PR Seast"]),
                "gopVotePct": float(r["GOP Vote %"].rstrip("%")),
                "demVotePct": float(r["DEM Vote %"].rstrip("%")),
                "fptpSeatDiff": float(r["FPTP Seat Diff (pos = GOP, neg = DEM)"].rstrip("%")),
            })
        except (ValueError, KeyError):
            pass
    write_json(out, "fptpDisproportionality.json")


def build_district_stv_results():
    """Group district-level STV results by state FIPS for county tier map."""
    path = OUTPUTS / "pure_multi" / "house" / "stv_results_by_district.csv"
    if not path.exists():
        print(f"  Skipping districtStvResults (not found: {path})")
        write_json({}, "districtStvResults.json")
        return
    rows = read_csv(path)
    by_state: dict = {}
    for r in rows:
        state_fips = str(r["state_fips"]).zfill(2)
        elected = [r[f"elected_{i}"] for i in range(9) if r.get(f"elected_{i}")]
        entry = {
            "districtId":  r["district_id"],
            "densityTier": r["density_tier"],
            "seatCount":   int(r["seat_count"]),
            "elected":     elected,
            "nRespondents": int(r["n_respondents"]),
        }
        by_state.setdefault(state_fips, []).append(entry)
    write_json(by_state, "districtStvResults.json")


def build_district_county_map():
    """Map each district_id to its list of county FIPS5 strings."""
    path = Path(__file__).parent.parent.parent / "data" / "processed" / "county_to_district.csv"
    if not path.exists():
        print(f"  Skipping districtCountyMap (not found: {path})")
        write_json({}, "districtCountyMap.json")
        return
    rows = read_csv(path)
    result: dict = {}
    for r in rows:
        did   = r["district_id"]
        fips5 = str(r["county_fips5"]).zfill(5)
        result.setdefault(did, []).append(fips5)
    write_json(result, "districtCountyMap.json")


def build_county_tiers():
    """Map county FIPS → density tier using CDC NCHS Urban-Rural Classification (2013).

    Source: https://www.cdc.gov/nchs/data/data_acces_files/NCHSURCodes2013.xlsx
    Save as data/raw/NCHSURCodes2013.xlsx

    NCHS codes:
      1 = Large Central Metro (≥1M CBSA, principal city county) → URBAN
      2 = Large Fringe Metro (≥1M CBSA, outlying)              → URBAN
      3 = Medium Metro (250k–999k CBSA)                        → SUBURBAN
      4 = Small Metro (<250k CBSA)                             → SUBURBAN
      5 = Micropolitan                                         → RURAL
      6 = Noncore Rural                                        → RURAL
    """
    import openpyxl
    raw_path = Path(__file__).parent.parent.parent / "data" / "raw" / "NCHSURCodes2013.xlsx"
    if not raw_path.exists():
        print(f"  Skipping countyTiers (not found: {raw_path})")
        write_json({}, "countyTiers.json")
        return

    NCHS_TIER = {1:'URBAN', 2:'URBAN', 3:'SUBURBAN', 4:'SUBURBAN', 5:'RURAL', 6:'RURAL'}

    wb = openpyxl.load_workbook(raw_path, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))

    tiers = {}
    for row in rows[1:]:  # skip header
        fips = row[0]
        if fips is None:
            continue
        fips5 = str(int(fips)).zfill(5)
        state = fips5[:2]
        code = row[6]
        if state in ('60', '66', '69', '72', '78'):
            tiers[fips5] = 'RURAL'  # US territories not in NCHS
        else:
            tiers[fips5] = NCHS_TIER.get(code, 'RURAL')
    write_json(tiers, "countyTiers.json")


def build_rcv_results():
    """Assemble processed RCV race JSONs into a single grouped file.

    If data/outputs/rcv/ contains processed race JSONs (from process_rcv.py),
    merges them into the output. Otherwise preserves the existing rcvResults.json
    (which contains hardcoded summary data) unchanged.
    """
    rcv_dir = Path(__file__).parent.parent.parent / "data" / "outputs" / "rcv"
    if not rcv_dir.exists() or not list(rcv_dir.glob("*.json")):
        return  # Preserve existing hardcoded summary data

    result: dict = {"AK": [], "ME": []}
    for fpath in sorted(rcv_dir.glob("*.json")):
        try:
            with open(fpath) as f:
                race = json.load(f)
            state = race.get("state", "")
            if state in result:
                result[state].append(race)
        except Exception:
            pass
    for state in result:
        result[state].sort(key=lambda r: (-r.get("year", 0), r.get("office", "")))
    write_json(result, "rcvResults.json")


if __name__ == "__main__":
    print("Preparing data...")
    build_senate_vote_model()
    build_house_seats()
    build_house_transfers()
    build_fd_variant_attraction()
    build_house_vote_model()
    build_house_state_map()
    build_coalition_profiles()
    build_transfer_matrix()
    build_cluster_profiles()
    build_quiz()
    build_state_pods()
    build_fd_senate()
    build_fd_house_seats()
    build_fd_primary()
    build_fd_primary_state_winners()
    build_fd_primary_sankey()
    build_pure_multi_primary_state_winners()
    build_fd_presidential_election()
    build_fd_profiles()
    build_pure_multi_primary()
    build_pure_multi_primary_sankey()
    build_pure_multi_senate()
    build_raw_multi_presidential_election()
    build_house_seats_gauss()
    build_fptp_disproportionality()
    build_district_stv_results()
    build_district_county_map()
    build_county_tiers()
    build_rcv_results()
    print("Done.")
