#!/usr/bin/env python3
"""Markdown tables for the README from observed.csv and per_draw.csv (written by run_k9_bootstrap.py).

A party's seat distribution uses only the draws where that party matched (retained >= 50% of its
seed-61 voters); a draw where the ID went to a different group of voters says nothing about that party.
"""
import argparse
from pathlib import Path

import pandas as pd
from sklearn.metrics import adjusted_rand_score

HERE = Path(__file__).resolve().parent
PARTIES = ["CON", "LBR", "STY", "NAT", "LIB", "POP", "CUP", "OAO", "DSA", "PRG"]


def winner_table(d, col):
    n = len(d)
    vc = d[col].value_counts()
    return "\n".join([f"| Winner | Draws | P(winner) |", "|---|---|---|"]
                     + [f"| {p} | {c} | {c / n:.2f} |" for p, c in vc.items()])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work-dir", type=Path, help="run_k9_bootstrap.py work dir; adds ARI vs the observed K = 9 fit")
    a = ap.parse_args()
    obs = pd.read_csv(HERE / "observed.csv").iloc[0]
    d = pd.read_csv(HERE / "per_draw.csv")
    ok = d[d.status == "ok"]
    print(f"draws: {len(d)}, ok {len(ok)}, fit_failed {(d.status == 'fit_failed').sum()}\n")

    print("Observed:")
    print(f"  IRV {obs.pres_irv} over {obs.pres_irv_runner_up} by {obs.pres_irv_margin_pp} pp; RP {obs.pres_rp}; "
          f"finalists {obs.finalists}; empty {obs.empty_ids}; ARI vs 61 {obs.ari_vs_seed61}")
    for tag in ("share", "ret", "house", "list", "house3", "list3", "sen_irv", "sen_rp"):
        print(f"  {tag:8} " + "  ".join(f"{p} {obs[f'{tag}_{p}']}" for p in PARTIES))
    print(f"  EC IRV leader {obs.ec_irv_leader} {obs.ec_irv_leader_ev}\n")

    print("National IRV\n" + winner_table(ok, "pres_irv") + "\n")
    print("National Ranked Pairs\n" + winner_table(ok, "pres_rp") + "\n")
    print(f"IRV final-round margin, pp: median {ok.pres_irv_margin_pp.median():.1f}, "
          f"10th-90th {ok.pres_irv_margin_pp.quantile(.1):.1f}-{ok.pres_irv_margin_pp.quantile(.9):.1f}; "
          f"draws under 2 pp: {(ok.pres_irv_margin_pp < 2).sum()}")
    both = (ok.pres_irv == ok.pres_rp).sum()
    print(f"IRV and Ranked Pairs agree in {both} of {len(ok)} draws\n")

    rows = ["| Party | Matched draws | Empty ID | Finalist | House STV median (10th-90th) | Party list median (10th-90th) "
            "| Senate IRV median | Senate RP median |", "|---|---|---|---|---|---|---|---|"]
    for p in PARTIES:
        m = ok[ok[f"ret_{p}"] >= 50]
        empty = ok.empty_ids.fillna("").str.split().apply(lambda xs: p in xs).sum()
        fin = ok.finalists.str.split().apply(lambda xs: p in xs).sum()
        if len(m):
            h, l = m[f"house_{p}"], m[f"list_{p}"]
            cells = (f"{h.median():.0f} ({h.quantile(.1):.0f}-{h.quantile(.9):.0f})",
                     f"{l.median():.0f} ({l.quantile(.1):.0f}-{l.quantile(.9):.0f})",
                     f"{m[f'sen_irv_{p}'].median():.0f}", f"{m[f'sen_rp_{p}'].median():.0f}")
        else:
            cells = ("-", "-", "-", "-")
        rows.append(f"| {p} | {len(m)} of {len(ok)} | {empty} | {fin} | " + " | ".join(cells) + " |")
    print("\n".join(rows) + "\n")

    weak = ok.weak_matches.fillna("").str.split().apply(len)
    print(f"draws with every non-empty party matched >= 50%: "
          f"{sum(set(w.split()) <= set(e.split()) for w, e in zip(ok.weak_matches.fillna(''), ok.empty_ids.fillna('')))}"
          f"; weak-match count distribution {weak.value_counts().sort_index().to_dict()}")
    print(f"ARI vs seed 61: median {ok.ari_vs_seed61.median():.3f}, 10th-90th "
          f"{ok.ari_vs_seed61.quantile(.1):.3f}-{ok.ari_vs_seed61.quantile(.9):.3f}")
    if a.work_dir:
        ref = pd.read_csv(a.work_dir / "observed_typology.csv", usecols=["cluster"])["cluster"]
        ari = pd.Series([adjusted_rand_score(ref, pd.read_csv(a.work_dir / "typologies" / f"draw_{b:03d}.csv.gz",
                                                               usecols=["cluster"])["cluster"]) for b in ok.draw])
        print(f"ARI vs observed K = 9: median {ari.median():.3f}, 10th-90th {ari.quantile(.1):.3f}-{ari.quantile(.9):.3f}")
    print(f"EC IRV leader: {ok.ec_irv_leader.value_counts().to_dict()}; majority (>= 488) in "
          f"{(ok.ec_irv_leader_ev >= 488).sum()} draws")
    print(f"runtime: {d.sec.sum() / 3600:.1f} h over draws, median {d.sec.median():.0f}s per draw")


if __name__ == "__main__":
    main()
