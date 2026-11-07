#!/usr/bin/env python3
"""Local party-color picker (researcher, 2026-11-06). Never published.

Defaults to the production colors (viz/src/constants/parties.ts PARTY_COLORS; the researcher's palette applied
2026-11-06). Pill text is white for every party, as the app's CHIP_TEXT = 'white' sets it.
Data: party order from data/processed/party_order.csv, default-view House seats from
viz/src/data/uncertaintyTurnoutL5.json. Writes analysis/coalitions/outputs/party_colors.html.
"""
import json
import re
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
TOKENS = Path.home() / ".claude/skills/html-research-artifacts/assets/tokens.css"


def ts_map(ts, name):
    block = re.search(rf"export const {name}[^=]*=\s*\{{(.*?)\n\}};", ts, re.S).group(1)
    return dict(re.findall(r"^\s*(\w+):\s*'([^']*)'", block, re.M))


def main():
    ts = (BASE / "viz/src/constants/parties.ts").read_text()
    current, names = ts_map(ts, "PARTY_COLORS"), ts_map(ts, "PARTY_NAMES")
    po = pd.read_csv(BASE / "data/processed/party_order.csv")
    order = po.party.tolist()
    pos = dict(zip(po.party, (po.dim1 - po.dim1.min()) / (po.dim1.max() - po.dim1.min())))
    seats = {q: v["observed"] for q, v in json.loads((BASE / "viz/src/data/uncertaintyTurnoutL5.json").read_text())["house"]["seats"].items()}
    proposed = {q: current[q] for q in order}
    payload = {"order": order, "names": {q: names[q] for q in order}, "seats": seats, "pos": {q: round(float(v), 4) for q, v in pos.items()},
               "current": {q: current[q] for q in order}, "proposed": proposed,
               "statusQuo": {q: current[q] for q in ("DEM", "IND", "REP")}}
    tpl = (HERE / "party_colors_template.html").read_text()
    out = HERE / "outputs/party_colors.html"
    out.write_text(tpl.replace("/*TOKENS*/", TOKENS.read_text()).replace("/*DATA*/", json.dumps(payload)))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
