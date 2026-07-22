#!/usr/bin/env python3
"""Rebuild the deployed senate JSONs (all 7 turnout stops) from the rank-7-winnow trees.

The senate has no ballot-depth toggle: its 5 finalists come from a rank-7 STV winnow of the
~20-candidate state field, and the final IRV/Condorcet among those 5 is full-ranked. This writes
the _top7 senate results over the standard deployed senate JSON names the SenateTab imports."""
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "viz" / "scripts"))
from prepare_data import build_pure_multi_senate, OUTPUTS  # noqa: E402

STOPS = [(0, "", "Turnout"), (5, "_l5", "TurnoutL5"), (10, "_l10", "TurnoutL10"),
         (15, "_l15", "TurnoutL15"), (20, "_l20", "TurnoutL20"), (25, "_l25", "TurnoutL25"),
         (30, "_l30", "TurnoutL30")]

for lam, suf, name in STOPS:
    tree = OUTPUTS / f"pure_multi_turnout{suf}_top7"
    build_pure_multi_senate(src_dir=tree,
                            cond_name=f"pureMultiSenateCondorcet{name}.json",
                            irv_name=f"pureMultiSenateIRV{name}.json")
    print(f"  λ{lam}: rebuilt from {tree.name}")
print("done — deployed senate JSONs now reflect the rank-7 winnow")
