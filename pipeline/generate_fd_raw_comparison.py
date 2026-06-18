"""generate_fd_raw_comparison.py

Produce a clean policy comparison CSV showing all interpretable policy
variables (binary, binary_agree, likert5 SA+A, trust low-trust %) for all
71 FD candidates.

Output: data/outputs/factor_deviation/profiles/fd_policy_comparison.csv

Columns:
  variable, domain, question, metric, overall,
  CON, SD, STY, NAT, LIB, POP, CUP, DSA, PRG,   ← 9 base parties
  CON_hi_so, CON_lo_so, ...,                       ← 62 axis variants
  [all 71 cand cols in CSV order]

Metric labels:
  binary       → "% Supporting"
  binary_agree → "% Agreeing"
  likert5      → "% SA+A" (Strongly Agree + Agree)
  trust        → "% Low Trust" (Not very much + None at all)
"""

import csv
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
FD_DIR = ROOT / "data" / "outputs" / "factor_deviation"
STATS_CSV = FD_DIR / "profiles" / "factor_deviation_stats.csv"
OUT_CSV = FD_DIR / "profiles" / "fd_policy_comparison.csv"

META_COLS = {"variable", "domain", "type", "stat_label", "question", "overall"}
SKIP_PREFIXES = ("factor_sensitive",)

TRUST_QUESTIONS = {
    "CC24_423": "Low trust in federal government (not very much or none at all)",
    "CC24_424": "Low trust in state government (not very much or none at all)",
}


def load_stats():
    rows = []
    with open(STATS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            rows.append(row)
    cand_cols = [
        c for c in fieldnames
        if c not in META_COLS and not any(c.startswith(p) for p in SKIP_PREFIXES)
    ]
    return rows, cand_cols


def safe_float(val):
    try:
        return float(val or 0)
    except (ValueError, TypeError):
        return 0.0


def build_comparison(rows, cand_cols):
    """Return list of output dicts, one per interpretable policy variable."""
    out = []

    # ── Phase 1: binary & binary_agree ──────────────────────────────────────
    for r in rows:
        typ = r.get("type", "")
        lbl = r.get("stat_label", "")
        if not (
            (typ == "binary" and lbl == "% Supporting") or
            (typ == "binary_agree" and lbl == "% Agreeing")
        ):
            continue
        metric = "% Supporting" if typ == "binary" else "% Agreeing"
        entry = {
            "variable": r["variable"],
            "domain":   r.get("domain", ""),
            "question": r.get("question", r["variable"]),
            "metric":   metric,
            "overall":  round(safe_float(r.get("overall")), 1),
        }
        for c in cand_cols:
            entry[c] = round(safe_float(r.get(c)), 1)
        out.append(entry)

    # ── Phase 2: likert5 → % SA + % Agree ───────────────────────────────────
    likert_meta: dict = {}
    likert_sa: dict = {}
    likert_ag: dict = {}
    for r in rows:
        var = r["variable"]
        typ = r.get("type", "")
        lbl = r.get("stat_label", "")
        if typ == "likert5":
            likert_meta[var] = {
                "question": r.get("question", var),
                "domain": r.get("domain", ""),
            }
        elif typ == "likert5_dist":
            if lbl == "% Strongly Agree":
                likert_sa[var] = r
            elif lbl == "% Agree":
                likert_ag[var] = r

    for var, meta in sorted(likert_meta.items()):
        sa_row = likert_sa.get(var, {})
        ag_row = likert_ag.get(var, {})
        sa_overall = safe_float(sa_row.get("overall")) if sa_row else 0.0
        ag_overall = safe_float(ag_row.get("overall")) if ag_row else 0.0
        entry = {
            "variable": var + "_agree",
            "domain":   meta["domain"],
            "question": meta["question"],
            "metric":   "% SA+A",
            "overall":  round(sa_overall + ag_overall, 1),
        }
        for c in cand_cols:
            sa_val = safe_float(sa_row.get(c)) if sa_row else 0.0
            ag_val = safe_float(ag_row.get(c)) if ag_row else 0.0
            entry[c] = round(sa_val + ag_val, 1)
        out.append(entry)

    # ── Phase 3: trust → % low trust ────────────────────────────────────────
    trust_meta: dict = {}
    trust_nm: dict = {}   # "Not very much"
    trust_na: dict = {}   # "None at all"
    for r in rows:
        var = r["variable"]
        typ = r.get("type", "")
        lbl = r.get("stat_label", "")
        if typ == "trust":
            trust_meta[var] = {
                "question": r.get("question", var),
                "domain": r.get("domain", ""),
            }
        elif typ == "trust_dist":
            if "Not very much" in lbl:
                trust_nm[var] = r
            elif "None at all" in lbl:
                trust_na[var] = r

    for var, meta in sorted(trust_meta.items()):
        nm_row = trust_nm.get(var, {})
        na_row = trust_na.get(var, {})
        nm_overall = safe_float(nm_row.get("overall")) if nm_row else 0.0
        na_overall = safe_float(na_row.get("overall")) if na_row else 0.0
        entry = {
            "variable": var,
            "domain":   meta["domain"],
            "question": TRUST_QUESTIONS.get(var, meta["question"]),
            "metric":   "% Low Trust",
            "overall":  round(nm_overall + na_overall, 1),
        }
        for c in cand_cols:
            nm_val = safe_float(nm_row.get(c)) if nm_row else 0.0
            na_val = safe_float(na_row.get(c)) if na_row else 0.0
            entry[c] = round(nm_val + na_val, 1)
        out.append(entry)

    return out


def write_csv(rows_out, cand_cols):
    fieldnames = ["variable", "domain", "question", "metric", "overall"] + cand_cols
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows_out)
    print(f"Wrote {len(rows_out)} policy variables × {len(cand_cols)} candidates → {OUT_CSV}")


def main():
    if not STATS_CSV.exists():
        print(f"ERROR: stats file not found: {STATS_CSV}", file=sys.stderr)
        sys.exit(1)

    rows, cand_cols = load_stats()
    print(f"Loaded {len(rows)} stat rows, {len(cand_cols)} candidates")

    out = build_comparison(rows, cand_cols)

    # Sort by domain then variable for readability
    out.sort(key=lambda r: (r["domain"], r["variable"]))

    write_csv(out, cand_cols)


if __name__ == "__main__":
    main()
