#!/usr/bin/env python3
"""
report_blend_profiles.py
------------------------
Report item-level policy profiles for any blended candidate type.
Shows how a blend differs from the pure primary cluster, with items
normalized to 0–1 across the full cluster range for comparability.
Abortion (CC24_325) is reported as raw week limits + percentage change.
ideo5 is excluded from the ranked policy table and shown separately
as a demographic reference only.

Usage:
  python3 report_blend_profiles.py --blend CON/SD
  python3 report_blend_profiles.py --blend STY/REF
  python3 report_blend_profiles.py --primary 0 --secondary 1 --weight 0.55
  python3 report_blend_profiles.py --all-senate-winners
  python3 report_blend_profiles.py --all-senate-winners --output blend_profiles.txt
"""

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent.parent
ITEM_MEANS_PATH = BASE_DIR / "analysis" / "clustering_old" / "cluster_item_means.csv"
SENATE_COMP     = BASE_DIR / "data" / "outputs" / "senate" / "senate_composition.csv"
SENATE_CANDS    = BASE_DIR / "data" / "outputs" / "senate" / "state_senate_candidates.csv"
OUTPUT_DIR      = BASE_DIR / "data" / "outputs" / "senate"

# ── Cluster mappings ─────────────────────────────────────────────────────────
PARTY_ABBR = {0: "CON", 1: "SD", 2: "STY", 3: "NAT",
              4: "LIB", 5: "REF", 6: "CTR", 8: "DSA", 9: "PRG"}
PARTY_IDX  = {v: k for k, v in PARTY_ABBR.items()}
ACTIVE_CLUSTERS = [0, 1, 2, 3, 4, 5, 6, 8, 9]

# ── Policy items (same 24+1 base as generate_candidate_profiles.py) ──────────
# CC24_340a excluded (data quality); ideo5 excluded from policy table
ITEMS_25 = [
    "pew_churatd", "CC24_302",   "CC24_303",   "CC24_341a",  "CC24_341c",
    "CC24_341d",   "CC24_323a",  "CC24_323b",  "CC24_323d",  "CC24_321b",
    "CC24_321d",   "CC24_321e",  "CC24_325",   "CC24_324b",  "CC24_340a",
    "CC24_340b",   "CC24_340c",  "CC24_340e",  "CC24_340f",  "CC24_440b",
    "CC24_440c",   "CC24_421_1", "CC24_421_2", "CC24_423",   "CC24_424",
]
ITEMS_24      = [it for it in ITEMS_25 if it != "CC24_340a"]
POLICY_ITEMS  = ITEMS_24 + ["pew_religimp"]   # 25 items — ideo5 excluded
ABORTION_VAR  = "CC24_325"
IDEO_VAR      = "ideo5"


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def load_item_means() -> pd.DataFrame:
    df = pd.read_csv(ITEM_MEANS_PATH)
    df = df.set_index("variable")
    cluster_cols = [f"c{k}" for k in ACTIVE_CLUSTERS]
    # Compute per-item min/max/range across active clusters
    df["_min"]   = df[cluster_cols].min(axis=1)
    df["_max"]   = df[cluster_cols].max(axis=1)
    df["_range"] = df["_max"] - df["_min"]
    return df


def get_senate_winner_blends(item_means: pd.DataFrame) -> list[dict]:
    """Return unique winner types from senate simulation, with avg w_primary."""
    comp  = pd.read_csv(SENATE_COMP)
    cands = pd.read_csv(SENATE_CANDS)

    merged = comp.merge(
        cands[["state_abbr", "cand_code", "w_primary"]].drop_duplicates(
            ["state_abbr", "cand_code"]),
        left_on=["state_abbr", "senator_label"],
        right_on=["state_abbr", "cand_code"],
        how="left",
    )
    summary = (merged
               .groupby("senator_label")
               .agg(
                   primary   = ("primary_cluster", "first"),
                   secondary = ("secondary_cluster",
                                lambda x: int(x.dropna().iloc[0])
                                if x.notna().any() else None),
                   w_primary = ("w_primary", "mean"),
                   seats     = ("state_abbr", "count"),
               )
               .reset_index()
               .sort_values("seats", ascending=False))

    blends = []
    for _, r in summary.iterrows():
        pri = int(r["primary"])
        sec = int(r["secondary"]) if pd.notna(r["secondary"]) else None
        wp  = float(r["w_primary"]) if pd.notna(r["w_primary"]) else 1.0
        blends.append({
            "label":     r["senator_label"],
            "primary":   pri,
            "secondary": sec,
            "w_primary": round(wp, 4),
            "seats":     int(r["seats"]),
        })
    return blends


# ─────────────────────────────────────────────────────────────────────────────
# Profile computation
# ─────────────────────────────────────────────────────────────────────────────

def _norm(value: float, item_row: pd.Series) -> float:
    """Normalize value to [0,1] using item's cluster range."""
    r = item_row["_range"]
    if r == 0 or math.isnan(r):
        return 0.5
    return float(np.clip((value - item_row["_min"]) / r, 0.0, 1.0))


def _abortion_weeks(stored: float) -> float:
    """Convert stored abortion value (40-raw; high=restrictive) to week limit."""
    return 40.0 - stored


def compute_profile(item_means: pd.DataFrame,
                    primary: int,
                    secondary: int | None,
                    w_primary: float) -> pd.DataFrame:
    """
    Compute per-item normalized profile for a candidate blend.
    Returns DataFrame with columns:
      variable, label, domain, scale,
      pri_val, blend_val, sec_val,
      pri_norm, blend_norm, sec_norm,
      shift_pct, abs_shift
    """
    w_sec = 1.0 - w_primary
    records = []
    all_vars = POLICY_ITEMS + ([IDEO_VAR] if IDEO_VAR in item_means.index else [])

    for var in all_vars:
        if var not in item_means.index:
            continue
        row = item_means.loc[var]
        pri_val   = float(row[f"c{primary}"])
        sec_val   = float(row[f"c{secondary}"]) if secondary is not None else float("nan")
        blend_val = (w_primary * pri_val + w_sec * sec_val
                     if secondary is not None and not math.isnan(sec_val)
                     else pri_val)

        pri_norm   = _norm(pri_val, row)
        blend_norm = _norm(blend_val, row)
        sec_norm   = _norm(sec_val, row) if secondary is not None else float("nan")
        shift_pct  = (blend_norm - pri_norm) * 100.0

        records.append({
            "variable":  var,
            "label":     row.get("label", var),
            "domain":    row.get("domain", ""),
            "scale":     row.get("scale", ""),
            "pri_val":   pri_val,
            "blend_val": blend_val,
            "sec_val":   sec_val,
            "pri_norm":  pri_norm,
            "blend_norm": blend_norm,
            "sec_norm":  sec_norm,
            "shift_pct": shift_pct,
            "abs_shift": abs(shift_pct),
        })
    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fn(val: float, width: int = 5) -> str:
    """Format normalized 0-1 value, or '—' for NaN."""
    if math.isnan(val):
        return "  —  ".rjust(width)
    return f"{val:.2f}".rjust(width)


def _fs(val: float) -> str:
    """Format shift percentage."""
    if math.isnan(val):
        return "   —  "
    return f"{val:+.1f}%".rjust(7)


# ─────────────────────────────────────────────────────────────────────────────
# Report printing
# ─────────────────────────────────────────────────────────────────────────────

def print_blend_report(primary: int,
                       secondary: int | None,
                       w_primary: float,
                       item_means: pd.DataFrame,
                       label: str | None = None,
                       outfile=None) -> None:

    def p(*args, **kwargs):
        print(*args, **kwargs)
        if outfile:
            print(*args, file=outfile, **kwargs)

    pri_name   = PARTY_ABBR.get(primary, str(primary))
    sec_name   = PARTY_ABBR.get(secondary, str(secondary)) if secondary is not None else None
    blend_name = label or (f"{pri_name}/{sec_name}" if sec_name else pri_name)
    w_sec      = round(1.0 - w_primary, 4)

    p()
    p("═" * 105)
    if secondary is not None:
        p(f"  BLEND PROFILE: {blend_name}  "
          f"(w = {w_primary:.2f} {pri_name}  /  {w_sec:.2f} {sec_name})")
        p(f"  Normalized shift = how far the blend moves from pure {pri_name}  "
          f"as % of the item's full cluster range")
        p(f"  0.00 = most liberal/permissive end of cluster range  "
          f"|  1.00 = most conservative end")
    else:
        p(f"  PURE CANDIDATE: {blend_name}  —  no secondary cluster")
    p("═" * 105)

    df = compute_profile(item_means, primary, secondary, w_primary)

    # ── Policy items table ────────────────────────────────────────────────────
    policy_df = df[df["variable"].isin(POLICY_ITEMS)].sort_values(
        "abs_shift", ascending=False)

    sec_hdr = f"Pure {sec_name:3s}" if sec_name else "  —   "
    p()
    p(f"  {'Domain':<22} {'Item':<50} {'Pure':>5} {'Blend':>6} {sec_hdr:>7}  "
      f"{'Shift':>7}")
    p(f"  {'':22} {'':50} {pri_name:>5} {'':>6} {'':>7}  {'':>7}")
    p("  " + "─" * 101)

    for _, r in policy_df.iterrows():
        var = r["variable"]
        lbl = str(r["label"])
        if len(lbl) > 50:
            lbl = lbl[:48] + ".."

        if var == ABORTION_VAR:
            # ── Abortion: special dual-line treatment ─────────────────────────
            pri_wk  = _abortion_weeks(r["pri_val"])
            bld_wk  = _abortion_weeks(r["blend_val"])
            sec_wk  = _abortion_weeks(r["sec_val"]) if not math.isnan(r["sec_val"]) else None
            d_wk    = bld_wk - pri_wk
            pct_chg = (d_wk / pri_wk * 100.0) if pri_wk > 0 else 0.0

            sec_wk_str = f"{sec_wk:5.1f}wk" if sec_wk is not None else "   —  "
            p(f"  {'Abortion':<22} {'Abortion week limit':<50} "
              f"{pri_wk:4.1f}wk {bld_wk:5.1f}wk {sec_wk_str:>7}  "
              f"{d_wk:>+5.1f}wk ({pct_chg:>+4.0f}%)")
            p(f"  {'':22} {'  └─ (normalized 0–1 scale)':<50} "
              f"{_fn(r['pri_norm']):>7} {_fn(r['blend_norm']):>6} "
              f"{_fn(r['sec_norm']):>7}  {_fs(r['shift_pct'])}")
        else:
            p(f"  {r['domain']:<22} {lbl:<50} "
              f"{_fn(r['pri_norm']):>7} {_fn(r['blend_norm']):>6} "
              f"{_fn(r['sec_norm']):>7}  {_fs(r['shift_pct'])}")

    # ── Summary ───────────────────────────────────────────────────────────────
    p()
    if secondary is not None:
        p(f"  ── Top 5 differentiators  ({pri_name} → {blend_name}) ──")
        for i, (_, r) in enumerate(policy_df.head(5).iterrows(), 1):
            lbl = str(r["label"])[:58]
            if r["variable"] == ABORTION_VAR:
                pri_wk = _abortion_weeks(r["pri_val"])
                bld_wk = _abortion_weeks(r["blend_val"])
                d_wk   = bld_wk - pri_wk
                pct    = (d_wk / pri_wk * 100.0) if pri_wk > 0 else 0.0
                p(f"    {i}. {lbl:<58}  {r['shift_pct']:>+7.1f}% of range  "
                  f"  ({pri_wk:.1f}wk → {bld_wk:.1f}wk, {pct:>+.0f}%)")
            else:
                p(f"    {i}. {lbl:<58}  {r['shift_pct']:>+7.1f}% of range")

        flat = policy_df[policy_df["abs_shift"] < 2.0]
        if not flat.empty:
            flat_labels = "; ".join(
                f"{r['domain']} ({r['variable']})"
                for _, r in flat.head(4).iterrows()
            )
            p(f"  Essentially unchanged (<2% shift): {flat_labels}")

    # ── Demographic reference ─────────────────────────────────────────────────
    ideo = df[df["variable"] == IDEO_VAR]
    if not ideo.empty:
        r = ideo.iloc[0]
        p()
        p(f"  ── Demographic reference (not a policy item; excluded from table) ──")
        p(f"  Ideology self-placement  (1 = very liberal … 7 = very conservative)")
        sec_str = (f" |  Pure {sec_name}: {r['sec_val']:.2f}"
                   if sec_name and not math.isnan(r["sec_val"]) else "")
        p(f"  Pure {pri_name}: {r['pri_val']:.2f}  |  Blend: {r['blend_val']:.2f}{sec_str}")
    p()


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_blend_label(label: str) -> tuple[int, int | None]:
    parts = label.strip().split("/")
    pri = PARTY_IDX.get(parts[0].upper())
    if pri is None:
        raise ValueError(f"Unknown party: '{parts[0]}'. Valid: {list(PARTY_IDX)}")
    if len(parts) == 1:
        return pri, None
    sec = PARTY_IDX.get(parts[1].upper())
    if sec is None:
        raise ValueError(f"Unknown party: '{parts[1]}'. Valid: {list(PARTY_IDX)}")
    return pri, sec


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--blend", metavar="PARTY[/PARTY]",
                     help="e.g. CON/SD  or  STY/REF  or  SD  (pure)")
    grp.add_argument("--all-senate-winners", action="store_true",
                     help="Report all unique winner types from senate simulation")
    grp.add_argument("--primary", type=int, metavar="IDX",
                     help="Primary cluster index (0–9)")
    ap.add_argument("--secondary", type=int, default=None,
                    help="Secondary cluster index (use with --primary)")
    ap.add_argument("--weight", type=float, default=0.55,
                    help="w_primary weight (default 0.55; use with --primary)")
    ap.add_argument("--output", metavar="FILENAME",
                    help="Also write to Claude/outputs/senate/<FILENAME>")
    args = ap.parse_args()

    item_means = load_item_means()

    outfile = None
    if args.output:
        out_path = OUTPUT_DIR / args.output
        out_path.parent.mkdir(parents=True, exist_ok=True)
        outfile = open(out_path, "w")
        print(f"Writing output to {out_path}")

    try:
        if args.all_senate_winners:
            blends = get_senate_winner_blends(item_means)
            print(f"\nReporting {len(blends)} unique senate winner types:\n")
            for b in blends:
                sec_str = f"/{PARTY_ABBR[b['secondary']]}" if b["secondary"] is not None else ""
                seats   = b["seats"]
                print(f"  {b['label']:14s}  {seats:2d} seat{'s' if seats != 1 else ' '}"
                      f"  w={b['w_primary']:.2f}/{1-b['w_primary']:.2f}")
            for b in blends:
                print_blend_report(
                    primary=b["primary"], secondary=b["secondary"],
                    w_primary=b["w_primary"], item_means=item_means,
                    label=b["label"], outfile=outfile,
                )

        elif args.blend:
            primary, secondary = parse_blend_label(args.blend)
            # Auto-look up average weight from senate results if available
            w = args.weight
            try:
                blends = get_senate_winner_blends(item_means)
                match = next((b for b in blends if b["label"] == args.blend), None)
                if match:
                    w = match["w_primary"]
                    print(f"Using senate average w_primary={w:.4f} for {args.blend}")
            except Exception:
                pass
            print_blend_report(primary, secondary, w, item_means,
                                label=args.blend, outfile=outfile)

        else:
            print_blend_report(args.primary, args.secondary, args.weight,
                                item_means, outfile=outfile)

    finally:
        if outfile:
            outfile.close()


if __name__ == "__main__":
    main()
