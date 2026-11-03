"""Tag every ANES independent-pool item with its battery (docs/EFA_ITEM_SELECTION_ROBUSTNESS.md §3c step 1).

Data: ANES 2024 user guide and codebook PDF (2025-08-08 release), read with pdftotext. Codebook order is questionnaire
order. Pool: config/anes_independent_pool.csv (155 items).

A battery is a set of items sharing one response scale, asked consecutively with no other question between them.
Operationally:
  - Every codebook variable is a question at its codebook position. A summary variable (V...x) stands in for the
    questions its "Survey Question(s)" field names. Its components leave the sequence and the summary takes the first
    component's position, with the summary's own scale (the 7-point favor/oppose composite the respondent built
    across the branched question).
  - Scale = the set of value labels for codes >= 1 (refusals, don't knows and inapplicables are excluded).
  - A battery is a maximal run of consecutive questions with identical scales, counting every question in the
    codebook, not only pool items. Any question with a different scale ends the run.
  - A pool item that is a component of a summary variable takes the summary's position and scale.
  - A spliced pool item (anes_sources with "|", e.g. split-form versions) takes its first source's position and
    scale.
Writes questionnaire_position, scale and battery_id into config/anes_independent_pool.csv and prints every
multi-item battery for review against the questionnaire.
"""
import re
import subprocess

import pandas as pd

import matched_efa as me
import recode_matched as rm

POOL = me.HERE / "config" / "anes_independent_pool.csv"
CODEBOOK = rm.ANES_CSV.parent / "anes_timeseries_2024_userguidecodebook_20250808.pdf"
VAR = re.compile(r"^(V24\d{4}[a-z0-9]*)\b")
CODE = re.compile(r"(?<![\d-])(\d{1,3})\.\s+(\S.*)")


def parse():
    txt = subprocess.run(["pdftotext", "-layout", str(CODEBOOK), "-"], capture_output=True, text=True).stdout.split("\n")
    order, labels, sq = [], {}, {}
    cur, field = None, None
    for line in txt:
        m = VAR.match(line)
        if m:
            cur = m.group(1)
            if cur not in labels:
                order.append(cur)
                labels[cur], sq[cur] = {}, []
            field = None
            continue
        if cur is None:
            continue
        head = line[:21].strip()
        if head:
            field = head
        body = line[21:].strip()
        if field == "Value Labels" or (field is None and CODE.search(body)):
            c = CODE.search(body)
            if c and int(c.group(1)) >= 1 and int(c.group(1)) not in labels[cur]:
                labels[cur][int(c.group(1))] = c.group(2).strip().lower()
        if field == "Survey Question(s)" and body:
            sq[cur] += [s.strip() for s in body.split(",") if s.strip()]
        if field not in (None, "Value Labels", "Survey Question(s)") and head and head != "Value Labels":
            field = head
    return order, labels, sq


def main():
    order, labels, sq = parse()
    owner = {}
    for v in order:
        for q in sq[v]:
            owner.setdefault(q, []).append(v)
    # questions a summary variable stands in for: non-summary variables whose survey-question names it lists
    absorbed = {}
    for v in order:
        if v.endswith("x") and sq[v]:
            for q in sq[v]:
                for u in owner.get(q, []):
                    if u != v and not u.endswith("x"):
                        absorbed.setdefault(u, v)
    seq, pos_of = [], {}
    for v in order:
        if v in absorbed:
            s = absorbed[v]
            if s not in pos_of:
                pos_of[s] = len(seq)
                seq.append(s)
            continue
        if v.endswith("x") and v in pos_of:
            continue
        pos_of[v] = len(seq)
        seq.append(v)
    scale = {v: " / ".join(labels[v][k] for k in sorted(labels[v])) for v in seq}
    run, bid = {}, None
    for i, v in enumerate(seq):
        if i == 0 or scale[v] != scale[seq[i - 1]] or not scale[v]:
            bid = v
        run[v] = bid

    pool = pd.read_csv(POOL)
    # a pool item that is itself a component of a summary variable sits at that summary's question
    first = pool.anes_sources.str.split("|").str[0].map(lambda v: absorbed.get(v, v))
    missing = sorted(set(first) - set(pos_of))
    assert not missing, f"pool items not found in the codebook sequence: {missing}"
    pool["questionnaire_position"] = first.map(pos_of)
    pool["scale"] = first.map(scale)
    pool["battery_id"] = first.map(run)
    pool = pool.sort_values("questionnaire_position")
    span = pool.groupby("battery_id").item_id.agg(lambda s: s.iloc[0] if len(s) == 1 else f"{s.iloc[0]}..{s.iloc[-1]}")
    pool["battery_id"] = pool.battery_id.map(span)
    pool.to_csv(POOL, index=False)
    sizes = pool.battery_id.value_counts()
    print(f"{len(pool)} pool items in {pool.battery_id.nunique()} batteries; {int((sizes > 1).sum())} hold 2+ pool items")
    for b, g in pool.groupby("battery_id", sort=False):
        if len(g) > 1:
            print(f"\n[{b}] {g.scale.iloc[0][:90]}")
            for r in g.itertuples():
                print(f"   {r.item_id:10s} {r.label[:80]}")


if __name__ == "__main__":
    main()
