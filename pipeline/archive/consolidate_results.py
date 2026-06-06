#!/usr/bin/env python3
"""
consolidate_results.py
----------------------
Consolidates simulation outputs into two human-readable CSVs in results/:

  state_results.csv         — one row per state, all senate/presidential winners
                              + per-cluster house seat counts
  national_composition.csv  — long-format national seat/winner table covering
                              senate, house, and presidency under every scenario

Reads from:
  data/outputs/senate/                   — mixed-candidate senate (Cond + IRV)
  data/outputs/pure_only/senate/         — pure-only senate (Cond + IRV)
  data/outputs/irv/                      — mixed-candidate presidential state IRV
  data/outputs/pure_only/irv/            — pure-only presidential state IRV
  data/outputs/No_C7_canonical/          — STV house district results
  data/outputs/primary_results_2028.csv  — mixed-candidate primary
  data/outputs/pure_only/primary_results_2028.csv — pure-only primary
"""

from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR    = Path(__file__).parent.parent
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

CLUSTER_NAMES = {0: "CON", 1: "SD", 2: "STY", 3: "NAT", 4: "LIB",
                 5: "REF", 6: "CTR", 7: "BD", 8: "DSA", 9: "PRG"}


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def state_house_seats(districts: pd.DataFrame) -> pd.DataFrame:
    """Aggregate cluster wins per state from STV district results."""
    elected_cols = [c for c in districts.columns if c.startswith("elected_party_")]
    rows = []
    for state_abbr, group in districts.groupby("state_abbr"):
        counts = {f"house_{name}": 0 for name in CLUSTER_NAMES.values()}
        for _, district in group.iterrows():
            for col in elected_cols:
                v = district[col]
                if pd.notna(v):
                    counts[f"house_{CLUSTER_NAMES[int(v)]}"] += 1
        counts["state_abbr"] = state_abbr
        counts["house_total_seats"] = sum(v for k, v in counts.items() if k.startswith("house_") and k != "house_total_seats")
        rows.append(counts)
    return pd.DataFrame(rows)


def build_state_results() -> pd.DataFrame:
    senate_cond_mixed = read_csv(BASE_DIR / "data/outputs/senate/senate_composition.csv")
    senate_irv_mixed  = read_csv(BASE_DIR / "data/outputs/senate/senate_irv_composition.csv")
    senate_cond_pure  = read_csv(BASE_DIR / "data/outputs/pure_only/senate/senate_composition.csv")
    senate_irv_pure   = read_csv(BASE_DIR / "data/outputs/pure_only/senate/senate_irv_composition.csv")
    pres_state_mixed  = read_csv(BASE_DIR / "data/outputs/irv/irv_presidential_states_2028.csv")
    pres_state_pure   = read_csv(BASE_DIR / "data/outputs/pure_only/irv/irv_presidential_states_2028.csv")
    house_districts   = read_csv(BASE_DIR / "data/outputs/No_C7_canonical/stv_results_by_district.csv")

    state_df = senate_cond_mixed[["state_abbr", "state_fips"]].copy()
    state_df["senate_cond_mixed"] = senate_cond_mixed["senator_code"]
    state_df = state_df.merge(
        senate_irv_mixed[["state_abbr", "winner_code"]].rename(columns={"winner_code": "senate_irv_mixed"}),
        on="state_abbr", how="left",
    )
    state_df = state_df.merge(
        senate_cond_pure[["state_abbr", "senator_code"]].rename(columns={"senator_code": "senate_cond_pure"}),
        on="state_abbr", how="left",
    )
    state_df = state_df.merge(
        senate_irv_pure[["state_abbr", "winner_code"]].rename(columns={"winner_code": "senate_irv_pure"}),
        on="state_abbr", how="left",
    )
    state_df = state_df.merge(
        pres_state_mixed[["state_abbr", "winner_label"]].rename(columns={"winner_label": "pres_irv_mixed"}),
        on="state_abbr", how="left",
    )
    state_df = state_df.merge(
        pres_state_pure[["state_abbr", "winner_label"]].rename(columns={"winner_label": "pres_irv_pure"}),
        on="state_abbr", how="left",
    )
    state_df = state_df.merge(state_house_seats(house_districts), on="state_abbr", how="left")

    return state_df.sort_values("state_abbr").reset_index(drop=True)


def senate_party_counts(df: pd.DataFrame, code_col: str) -> dict:
    return df[code_col].value_counts().to_dict()


def build_national_composition() -> pd.DataFrame:
    """Long-format: office, scenario, party, seats_or_role."""
    senate_cond_mixed = read_csv(BASE_DIR / "data/outputs/senate/senate_composition.csv")
    senate_irv_mixed  = read_csv(BASE_DIR / "data/outputs/senate/senate_irv_composition.csv")
    senate_cond_pure  = read_csv(BASE_DIR / "data/outputs/pure_only/senate/senate_composition.csv")
    senate_irv_pure   = read_csv(BASE_DIR / "data/outputs/pure_only/senate/senate_irv_composition.csv")

    rows = []

    # Senate (4 scenarios × seat counts per party)
    for scenario, code_col, df in [
        ("senate_cond_mixed", "senator_code", senate_cond_mixed),
        ("senate_irv_mixed",  "winner_code",  senate_irv_mixed),
        ("senate_cond_pure",  "senator_code", senate_cond_pure),
        ("senate_irv_pure",   "winner_code",  senate_irv_pure),
    ]:
        for party, count in senate_party_counts(df, code_col).items():
            rows.append({"office": "senate", "scenario": scenario, "party": party, "value": count, "metric": "seats"})

    # House (single scenario)
    house_summary = read_csv(BASE_DIR / "data/outputs/No_C7_canonical/stv_seat_summary.csv")
    for _, r in house_summary.iterrows():
        rows.append({
            "office": "house", "scenario": "stv_canonical",
            "party": CLUSTER_NAMES[int(r["party"])], "value": int(r["NATIONAL"]),
            "metric": "seats",
        })

    # Presidential general — final round results
    for scenario, path in [
        ("pres_irv_mixed", "data/outputs/irv/irv_presidential_national_2028.csv"),
        ("pres_irv_pure",  "data/outputs/pure_only/irv/irv_presidential_national_2028.csv"),
    ]:
        nat = read_csv(BASE_DIR / path)
        final = nat[nat["round"] == nat["round"].max()].sort_values("vote_pct", ascending=False)
        for i, (_, r) in enumerate(final.iterrows()):
            role = "winner" if r["winner"] else ("runner_up" if i == 1 else "finalist")
            rows.append({
                "office": "president", "scenario": scenario,
                "party": r["candidate_name"], "value": round(r["vote_pct"], 2),
                "metric": f"final_round_pct ({role})",
            })

    # Presidential primary — Ranked Pairs winners
    for scenario, path in [
        ("pres_primary_rp_mixed", "data/outputs/primary_results_2028.csv"),
        ("pres_primary_rp_pure",  "data/outputs/pure_only/primary_results_2028.csv"),
    ]:
        df = read_csv(BASE_DIR / path)
        last_stage = df[df["winnowing_point"] == df["winnowing_point"].unique()[-1]]
        survivors = last_stage[last_stage["status"] == "surviving"].sort_values("vote_pct", ascending=False)
        for _, r in survivors.iterrows():
            rows.append({
                "office": "president", "scenario": scenario,
                "party": r["candidate_name"], "value": round(r["vote_pct"], 4),
                "metric": "primary_finalist_pct",
            })

    return pd.DataFrame(rows)


def main():
    print("Building state_results.csv …")
    state_df = build_state_results()
    out_state = RESULTS_DIR / "state_results.csv"
    state_df.to_csv(out_state, index=False)
    print(f"  → {out_state}  ({len(state_df)} states, {len(state_df.columns)} columns)")

    print("\nBuilding national_composition.csv …")
    nat_df = build_national_composition()
    out_nat = RESULTS_DIR / "national_composition.csv"
    nat_df.to_csv(out_nat, index=False)
    print(f"  → {out_nat}  ({len(nat_df)} rows)")

    # Quick national senate summary readout
    print("\n=== National senate composition by scenario ===")
    senate_nat = nat_df[nat_df["office"] == "senate"]
    pivot = senate_nat.pivot_table(index="party", columns="scenario", values="value", fill_value=0).astype(int)
    pivot.loc["TOTAL"] = pivot.sum()
    print(pivot.to_string())

    print("\n=== Presidential general winners ===")
    prez = nat_df[(nat_df["office"] == "president") & nat_df["metric"].str.contains("winner")]
    print(prez[["scenario", "party", "value", "metric"]].to_string(index=False))


if __name__ == "__main__":
    main()
