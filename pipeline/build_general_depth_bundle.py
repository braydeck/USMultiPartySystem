#!/usr/bin/env python3
"""Bundle the presidency general-election JSONs (depths 3/5/7/10 × 7 turnout stops) into a single
lazy-loaded asset: viz/public/data/generalDepth.json = {depthKey: {partKey: PresidentialElection}}.

Ballot depth changes only WHICH 5 finalists advance (via the matching top-N primary); the general
itself full-ranks those 5. 'full' ranking uses the existing static rawMultiPresidentialElection*.json."""
import json
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "viz" / "scripts"))
import prepare_data as pd_mod  # noqa: E402
from prepare_data import build_raw_multi_presidential_election, OUTPUTS  # noqa: E402

_captured = {}
pd_mod.write_json = lambda data, name: _captured.__setitem__("last", data)

STOPS = [(0, ""), (5, "_l5"), (10, "_l10"), (15, "_l15"), (20, "_l20"), (25, "_l25"), (30, "_l30")]
DEPTHS = [3, 5, 7, 10]

bundle = {}
for depth in DEPTHS:
    by_part = {}
    for lam, suf in STOPS:
        tree = OUTPUTS / f"pure_multi_turnout{suf}_top{depth}"
        build_raw_multi_presidential_election(tree, "x")
        by_part[str(lam)] = _captured["last"]
    bundle[f"top{depth}"] = by_part
    print(f"  top{depth}: 7 stops")

out = BASE / "viz" / "public" / "data" / "generalDepth.json"
out.write_text(json.dumps(bundle, separators=(",", ":")))
print(f"Wrote {out} ({out.stat().st_size / 1e6:.2f} MB)")
