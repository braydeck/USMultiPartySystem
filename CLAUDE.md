# START HERE

Repo: `/Users/bdecker/Local Projects/Personal/STV`. Direct push to `main`, no PR workflow.
This file auto-loads every session for this project only. Keep it short and current; when
something here goes stale, fix it here rather than adding a second note elsewhere.

`docs/AGENTS.md`, `docs/AGENT_CONTEXT.md`, and `docs/PROJECT_GUIDE.md` are stale (they describe
a two-worktree layout under `/Users/bdecker/Documents/STV/` that no longer exists). Read them
for EFA and vote-model background only, and verify any path or seat count first.

## What this is

A simulation of American elections under proportional representation, built from 2024 CES
survey data. A polychoric EFA reduces 24 policy items to 5 ideological factors; a Dirichlet
Process Gaussian Mixture Model clusters respondents into 10 voter types, and each cluster
becomes a party. Those parties then contest a House, a Senate, a presidency, and a legislative
agenda under several counting rules. The point is that the counting rule changes the answer.

The deliverable is a React + TypeScript + Vite + Tailwind + shadcn app in `viz/`, deployed to
Cloudflare.

## Invariants

| Fact | Value |
|---|---|
| Respondents after listwise deletion | **45,707** |
| Parties | **10**, all active. OAO (cluster 7) and STY (cluster 2) are never dissolved. |
| House chamber | **873 seats** (double magnitude), 1,726 (triple). **Not 435.** |
| House districts | 150 double, 243 triple. MMP and Single Race instead use the 436 real 119th-Congress districts. |
| Senate | 51 seats, one per state plus DC |
| Electoral college | 975 electors |
| Cluster to party | 0 CON, 1 LBR, 2 STY, 3 NAT, 4 LIB, 5 POP, 6 CUP, 7 OAO, 8 DSA, 9 PRG |
| App defaults | ballot depth `top7`, turnout gap `5%`, magnitude `double`, field `rawMulti` |

Before quoting any chamber-level count, sum it out of the JSON. Do not reach for 435.

## The five factors

F1 Security & Order. F2 Institutional Distrust (elections). F3 Government Distrust (residual).
F4 Religious Traditionalism. F5 Populist Conservatism (the primary left-right axis).

**F3 runs opposite to real distrust** (corr −0.38); F2 carries it (+0.84). F3 is a suppressor
kept only to isolate CUP. Never label F3 as "distrust" in reader-facing copy.

## How a voter becomes a ballot

The DPGMM gives each respondent a membership probability across all ten clusters. Candidate
scores come from that posterior, and `argsort` on the scores is the ranked ballot. Ranks 1
through 3 carry 98.6% of a voter's probability mass. Slate order within a party is fixed and
identical for every voter, so the model represents slate voting at the strong-discipline limit.

Two candidate fields exist. **`rawMulti` (pure_multi) is the only one displayed**: pure party
candidates, 1 to 3 per party by local strength. The **crossover** (`factor_deviation`) field
adds ideologically shifted variant candidates and is reachable only via `?lab=crossover`.

## The ten tabs

| Tab | What it simulates |
|---|---|
| **Overview** | Headline results, turnout robustness, the case for the whole thing |
| **Party Quiz** | Answer real CES items, get scored on the 5 factors, land in a party |
| **Parties** | Party platforms, factor positions, comparison against today's DEM/IND/REP |
| **Presidency** | *Primary:* 27 candidates (10 parties × 3) through a 4-stage rolling-electorate STV winnow (Retail 27→12, Pod A 12→9, Pod C 9→7, Pod B/D 7→5). *General:* national IRV, per-state IRV, and Ranked Pairs Condorcet over the 5 finalists, plus an electoral-college cartogram and a top-two reduction |
| **Senate** | Two stages per state: a rank-7 STV winnow of ~20 candidates to 5 finalists, then IRV or Condorcet over those 5 **fully ranked**. No depth toggle |
| **House** | Four systems on the same ballots: **STV** (multi-member, Droop quota, weighted inclusive Gregory), **Party List** (Sainte-Laguë), **MMP** (compensatory, real 119th districts + per-state top-off), and a **~20% per-state reserve** tier layered on STV or List. Toggles: system, magnitude, depth, turnout, reserve |
| **Single Race** | FPTP head-to-head in a real 119th district, with opinion and turnout sliders |
| **Legislation** | Bill-by-bill floor-vote probabilities for House and Senate, baked at rank-7 chambers and depth-7 president. Two models: **chamber vote model** (sum of independent binomials over observed per-party support) and **candidate vote model** (per-bill logistic regression on the 5 factors, predicting from party centroids). Their disagreement is the "divergence" finding |
| **IRV Case Studies** | Real Alaska and Maine cast vote records, not simulation |
| **What Is This?** | Methodology, the 10 parties, voting systems, turnout, caveats |

`polarization/` is a separate cross-national study (V-Dem / QoG) with its own README and
FINDINGS; it does not feed the app.

## Turnout and depth

**Turnout** weights each respondent by their cluster's validated 2024 turnout (CES `TS_g2024`,
Spec 1, roughly 59% weighted national). The `part` URL param picks a gap stop: 0, 5, 10, 15,
20, 25, 30. Default 5%. Every stop is a parallel `_turnout` / `_lNN` output tree.

**Ballot depth** is 3 / 5 / 7 / 10 / rank-all, default 7, exposed on House STV and the Primary.
Senate, presidential general, and Legislation are baked at rank-7.

## Where numbers come from

Displayed numbers live in `viz/src/data/*.json` (bundled) and `viz/public/data/*.json`
(fetched lazily). `viz/scripts/prepare_data.py` converts pipeline CSVs into most of them;
`pipeline/build_*.py` writes the rest.

**Trace a number to its JSON, then to the script that writes that JSON, before explaining it.**
Reading a script in `pipeline/` is not evidence the app uses it. Use
`grep -rln <module> pipeline/` to check for a live importer.

## The traps

1. **Ballot depth counts CANDIDATES, not parties.** Every party fields at least one candidate
   per district and strong parties field 2 to 4, so a depth-7 ballot reaches roughly **3
   parties**, never 7. Sizing is `n_candidates_for_district()` in
   `run_pure_multi_house_stv.py`; the Senate uses share thresholds (≥12% → 3, ≥5% → 2, ≥1% → 1).

2. **`pipeline/party_stv.py` is dead code.** Only `run_party_*.py` import it and nothing
   displayed reads its output. It counts parties rather than candidates, and its input
   `party_ballots.csv` is one column per party, the opposite of the live pipeline.

3. **Party List counts each voter's top party on purpose.** `run_pure_multi_house_stv.py`
   scores candidates with `prob_cluster_k`, so STV's rank-1 already *is* the argmax. Matching
   the vote definition makes a list-versus-STV gap purely about the counting rule. Settled.

4. **The typology CSV joins POSITIONALLY.** `typology_cluster_assignments.csv` has no `caseid`.
   Apply the identical `ITEMS_24 + commonpostweight` `notna()` mask to the DTA before
   concatenating, or the join is silently wrong.

5. **Below-quota seats track vote concentration, not district magnitude.** Short ballots
   exhaust and late seats fill under the Droop quota, but the figure stays high at full ranking
   in homogeneous districts, so it is structural rather than an exhaustion artifact.

6. **`id` is the correct FD axis label.** Do not re-run `rename_ae_to_es.py`.

7. **`prepare_data.py` alone is not the whole build.** It writes the pre-rank-7 Legislation and
   Senate files, so it must be followed by `build_legislation_rank7.py` and
   `build_senate_rank7.py` or those tabs silently revert. Full sequence:
   ```
   python3 viz/scripts/prepare_data.py
   python3 pipeline/build_legislation_rank7.py
   python3 pipeline/build_senate_rank7.py
   ```

8. **`NO_STY=1` / `pure_multi_nosty*` is a DEAD scenario** (Solidarity dissolved), as was
   `INCLUDE_C7` / `pure_multi_c7`. The consumers were removed 2026-09-07. Five `pure_only`
   runners still carry a labeled `NO_STY` branch; delete them rather than reasoning from them.

## Voice for app copy

Claim-first and mechanism-named. No editorial commentary ("surprisingly", "unlike X", "more
moderate than"). Party labels, never candidate codes (RH, MW, MRJ). Sparse em-dashes, never a
spaced one. Propose moving UI elements rather than removing them. See the user's global
`CLAUDE.md` and the `public-writing` skill.

## Deeper notes

Session memory is at
`~/.claude/projects/-Users-bdecker-Local-Projects-Personal-STV/memory/`, indexed by
`MEMORY.md`. **Open the linked file, not just the index line**, before reasoning about ballots,
depth, EFA factors, or which pipeline is live.
