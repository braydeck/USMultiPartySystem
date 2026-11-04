"""Pin party IDs for the nine (ruled 2026-11-04) into data/processed/party_id_reference.csv.

dpgmm_clustering.py gives each fitted cluster the ID of the reference party it retains most of, so this file decides
which slot each of the nine takes. Slots follow pipeline/party_codes.ALL_PARTIES, keeping every continuing code in its
old slot: CON 0, LBR 1 (Labor, cluster E), STY 2, NAT 3, POP 5, CUP 6, OAO 7, DSA 8, PRG 9; slot 4 (DAL) is empty.
Source: the cap-9 modal seed solution of listwise_check/outputs/stage_c_v2/labels.npz, letters and codes from
listwise_check/outputs/compare_typologies_k9/letters.csv (label "CON (A)" etc.).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
LW = ROOT / "analysis/efa/exploration/listwise_check"
sys.path.insert(0, str(LW))
import loading_draws as ld  # noqa: E402

SLOT = {"CON": 0, "LBR": 1, "STY": 2, "NAT": 3, "POP": 5, "CUP": 6, "OAO": 7, "DSA": 8, "PRG": 9}

S = pd.read_csv(LW / "outputs/stage_c_v2/scores.csv", usecols=["caseid"])
z = np.load(LW / "outputs/stage_c_v2/labels.npz")
lab = ld.modal_solution(list(zip(range(42, 62), z["9_seed"], z["9_seed_bounds"])))[0]
let = pd.read_csv(LW / "outputs/compare_typologies_k9/letters.csv")
code = {int(c): l.split(" (")[0] for c, l in zip(let.cluster, let.label)}
out = pd.DataFrame({"caseid": S.caseid.values, "party_id": [SLOT[code[int(k)]] for k in lab]})
out.to_csv(ROOT / "data/processed/party_id_reference.csv", index=False)
print(out.party_id.value_counts().sort_index().to_dict())
