#!/usr/bin/env python3
"""Regenerate the Legislation vote-model families (house + senate, all 7 turnout stops) from the
rank-7 trees. Legislation bakes in the app defaults: rank-7 chambers + depth-7 president.

Only the LegislationTab consumes houseVoteModelTurnout*/senateVoteModelTurnout*, so overwriting the
standard names is safe. The WFP builders recompute the Raw-Multi house/senate + president columns
from the tree's rank-7 seat summaries and depth-7 finalists."""
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "viz" / "scripts"))
from prepare_data import build_house_vote_model_wfp, build_senate_vote_model_wfp, OUTPUTS  # noqa: E402

STOPS = [(0, "", "Turnout"), (5, "_l5", "TurnoutL5"), (10, "_l10", "TurnoutL10"),
         (15, "_l15", "TurnoutL15"), (20, "_l20", "TurnoutL20"), (25, "_l25", "TurnoutL25"),
         (30, "_l30", "TurnoutL30")]

for lam, suf, name in STOPS:
    tree = OUTPUTS / f"pure_multi_turnout{suf}_top7"
    triple = OUTPUTS / f"pure_multi_triple_turnout{suf}_top7"
    build_house_vote_model_wfp(tree, out_name=f"houseVoteModel{name}.json", triple_src=triple)
    build_senate_vote_model_wfp(tree, out_name=f"senateVoteModel{name}.json")
    print(f"  λ{lam}: house + senate vote models from {tree.name} (+ triple {triple.name})")
print("done — Legislation vote models now reflect the rank-7 chambers + depth-7 president")
