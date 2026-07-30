# Senate Coalition / Head-to-Head — Method-Exclusive Redesign

## Intent

On the **Senate tab** (`viz/src/tabs/SenateTab.tsx`), the "How Senators Build
Their Coalition" card is showing the wrong election, off the wrong scenario, under
the wrong method label. Replace it with a card that actually shows how the winning
senator accumulated votes, make it appear only under IRV, and give the Condorcet
toggle the head-to-head matrix instead. Re-point every senate card at the active
participation stop so the whole tab reports one consistent chamber.

## Diagnosis (what is actually broken)

Four independent defects, established from the code and data:

1. **Wrong election.** `senate_stv_buckets.csv` records the *winnow* stage — a
   5-seat Gregory STV run (`STV_SURVIVORS = 5`,
   `pipeline/pure_only/run_pure_multi_senate.py:526`) that narrows a state's ~20
   candidates to 5 finalists. Its Droop quota is `total/(5+1)` ≈ 16.7%, which is
   why every finalist's bar lands near 20% and nothing crosses 50%. This stage has
   no relationship to how the single IRV or Condorcet winner accumulated votes.
   AL is the clean illustration: the card shows winner `STY_1` at 18.66% with zero
   transfers while `CON_1` sits at 35.89%.

2. **Stale scenario.** `build_senate_buckets` and `build_senate_condorcet`
   (`viz/scripts/prepare_data.py:2581`, `:2673`) read `PURE_MULTI_DIR`
   (`data/outputs/pure_multi`) — the unweighted baseline. The tab's seat data comes
   from `pure_multi_turnout_l5` at the `part=5` default. Hence "STY 30s". Actual
   defaults: IRV `CON 24 · LBR 21 · LIB 4 · STY 1 · POP 1`; Condorcet
   `LBR 22 · STY 13 · CON 11 · POP 4 · CUP 1`. Neither card responds to the
   participation slider.

3. **Method mislabeling.** `prepare_data.py:2632` always averages off
   `st["condWinner"]`, but `SenateBuckets.tsx` flips its caption to "IRV" when the
   toggle is IRV. The IRV view has never shown IRV.

4. **Fan chart presentation.** Its data is correct (`activeSeats` resolves to the
   active pipeline × method × turnout stop), but the card has no title, no method
   name, and plots 51 while `SenateCompositionCard` directly above plots 102 —
   51 states (50 + DC) × 2, per `SenateCompositionCard.tsx:78`. It reads as a
   different chamber.

## Decisions (locked)

- **Either/or by method.** One card slot. `method === 'irv'` → coalition card;
  `method === 'condorcet'` → head-to-head matrix. Never both.
- **The winnow stage is kept, relabeled.** It is a real stage and the only thing
  the current data describes. It becomes its own card, "How the Field Narrows to
  Five Finalists," with the ≈16.7% quota named in copy and drawn as a marker line.
  Shown under both methods, since the winnow runs before either.
- **Coalition bars use an absolute 0–100% axis** with a 50% majority line, not
  normalization to 100% of the final tally. Under IRV the winner's final-round
  total genuinely crosses 50%; showing it against the real threshold is the point.
- **Fan chart doubles** to match `SenateCompositionCard` (102 = 51 × 2), and gets
  a title naming the active method. The total is derived from the seat array
  length, never hardcoded.
- **Crossover (`pipeline === 'factorDev'`) keeps today's behavior** — no coalition
  or matrix card. Extending it requires changing
  `pipeline/run_fd_senate_simulation.py` as well, which is outside this change.
- **No ballot-depth dimension.** Senate finalists are ranked in full
  (`state_ballots_full`, `run_pure_multi_senate.py:564`), so the senate JSONs come
  from `pure_multi_turnout_l{N}` and not the `_top{N}` trees. Unchanged.

## Pipeline change

`pipeline/pure_only/run_pure_multi_senate.py`

Replace `irv_winner()` (line 401) with:

```python
def irv_rounds(ballots_arr, weights, candidates) -> tuple[str, list]:
    """Plain IRV among a candidate list → (winner_code, rounds).

    rounds[i] = [{"code", "party", "votes", "pct", "eliminated"}], one entry per
    candidate active in that round. Exactly one entry per round has
    eliminated=True, except the final round.
    """
```

Preserve the existing semantics exactly so winners do not move:

- majority test `totals[c] / total > 0.5`,
- elimination `min(active, key=lambda c: (totals[c], c))`,
- the `total == 0` break and the `next(iter(active))` fallback.

Both call sites (`irv_win`, line 564; `prob_irv_win`, line 596) take
`winner, rounds = irv_rounds(...)` and keep passing `winner` to `make_comp_row`.

New output, primary (Gauss-free) path only:

`data/outputs/<tree>/senate/senate_irv_rounds.json`

```json
{
  "01": {
    "abbr": "AL",
    "winner": "STY_1",
    "totalWeight": 726.21,
    "rounds": [
      { "round": 1, "candidates": [
        { "code": "CON_1", "party": "CON", "votes": 292.5, "pct": 40.28, "eliminated": false },
        { "code": "STY_1", "party": "STY", "votes": 193.5, "pct": 26.65, "eliminated": false }
      ]}
    ]
  }
}
```

**Verification gate:** the six existing CSVs must be byte-identical after the
refactor. The script is deterministic (`default_rng(42)`); a rerun of
`pure_multi` on the pre-change code produced an empty `git diff`, so any diff in
those CSVs means the refactor changed behavior.

## Reruns

Seven trees, the ones the participation slider maps to via
`_build_turnout_variant` (`prepare_data.py:3276`):

| Stop | Env | Tree |
| --- | --- | --- |
| `part=0` | `TURNOUT_WEIGHT=1 TURNOUT_LAMBDA=0` | `pure_multi_turnout` |
| `part=5…30` | `TURNOUT_WEIGHT=1 TURNOUT_LAMBDA=0.05…0.30` | `pure_multi_turnout_l5…_l30` |

Plus `pure_multi` (no env) to keep the baseline tree consistent. ~4.4s each.

Only `senate_irv_rounds.json` needs these reruns. `senate_stv_buckets.csv` and
`senate_condorcet_results.csv` are already present in all seven trees (verified),
so the buckets and Condorcet builders just need parameterizing.

## prepare_data.py changes

All three builders take `(src_dir, out_name)` and join `_build_turnout_variant`,
so each emits a `{suffix}` variant for `Turnout` and `TurnoutL5…L30`.

`build_turnout_scenario` reorders so the live `pure_multi_turnout` work runs before
the dormant `pure_multi_nosty_turnout` variant, and guards that dormant call with a
`FileNotFoundError` catch. The NoSty tree is not regenerated by the senate reruns
and so lacks `senate_irv_rounds.json`; unguarded, its failure would abort the three
primary-path primary builders that follow it.

### `build_senate_irv_rounds(src_dir, out_name)` → `senateIrvRounds{suffix}.json`

```json
{
  "states": { "01": { "abbr": "AL", "winner": "…", "rounds": [ … ] } },
  "averages": [
    { "party": "CON", "seats": 24, "avgFirstChoice": 31.2,
      "avgSources": [ { "party": "NAT", "pct": 14.1 } ], "avgFinal": 55.4 }
  ]
}
```

`states` passes `rounds` through in `IRVRound[]` shape so `IRVSankey` consumes it
unchanged.

`averages` is computed **off the IRV winner** (this is defect 3), over the states
that party wins at this stop:

- `avgFirstChoice` — mean of the winner's round-1 `pct`.
- `avgSources[p]` — mean transfer inflow attributed to party `p`. Attribution
  walks the rounds: the winner's `pct` gain between round `i` and `i+1` is
  attributed to the party of the candidate eliminated in round `i`. Gains are
  summed per source party, then divided by `seats`.
- `avgFinal` — mean of the winner's final-round `pct`.

This attribution is **exact, not inferred**. `generate_ballots`
(`run_pure_multi_senate.py:165`) returns a full ranking of every candidate, and
the final IRV runs on `state_ballots_full`, so all 5 finalists appear on every
ballot and no ballot can exhaust. Round-over-round gain therefore equals transfer
volume identically.

Sort `averages` by `seats` descending. Drop sources below 0.1pp, matching the
existing threshold.

### `build_senate_condorcet(src_dir, out_name)` → `senateCondorcet{suffix}.json`

Body unchanged; only parameterized. Its input
(`senate/senate_condorcet_results.csv`) already exists at every stop, so this
needs no rerun.

### `build_senate_buckets(src_dir, out_name)` → `senateBuckets{suffix}.json`

Per-state `finalists` unchanged — that data is correct for what it describes.
Replace the `averages` block, which currently misattributes the winnow to the
Condorcet winner's coalition, with finalist-slot counts:

```json
"averages": [
  { "party": "CON", "finalistSlots": 71,
    "avgFirstChoice": 14.2,
    "avgSources": [ { "party": "NAT", "pct": 3.1 } ],
    "avgTotal": 19.8 }
]
```

`finalistSlots` counts how many of the 255 finalist slots (51 states × 5) that
party holds; the averages are over those slots. Add `"quotaPct"` to the top level,
computed as `100 / (STV_SURVIVORS + 1)`, so the component draws the marker line
from data rather than a hardcoded constant.

## Component changes

### `SenateTab.tsx`

Import the three new JSON families as stop arrays indexed by `gi`, following the
file's existing pattern (it already imports 28 seat-stop JSONs directly). Drop the
`senateBuckets` / `senateCondorcet` props and their `App.tsx` imports rather than
threading 21 props through.

Card slot, replacing the two `pipeline === 'rawMulti'` blocks at lines 243–269:

```tsx
{rawMultiOn && (method === 'irv'
  ? <SenateCoalitionCard data={irvRoundsStops[gi]} />
  : <SenateCondorcetCard data={senCondorcetStops[gi]} />)}
{rawMultiOn && <SenateWinnowCard data={bucketStops[gi]} />}
```

Fan chart card (line 211): add a title — `Senate Chamber — {method label} ·
{total} seats`, where `total = activeSeats.length * 2` — and double
`parliamentSegments[].seats`, with the ×2 rationale in copy matching
`SenateCompositionCard`'s existing note (one winner per state, doubled to fill both
of the state's seats).

### New `components/senate/SenateCoalitionCard.tsx`

- **National view** (default): one horizontal bar per seat-holding party on a
  shared absolute 0–100% axis, with a 50% majority rule line drawn across all
  bars. Darkest segment = own first-choice; lighter segments = transfers, colored
  by *source* party. Segment labels sit above the bar (the convention set in
  29f9df2), with the party pill and seat count in the left gutter. Legend appears
  only for slivers too narrow for their inline label — same rule as
  `SenateCompositionCard`.
- **Per-state view**: `IRVSankey` reused, above a final-round list giving each
  survivor's share, the winner's margin in pp, and a runner-up marker.
- Each bar's tally label is positioned at the bar's own tip rather than in a
  right-hand column, so the number stays adjacent to what it measures.

`IRVSankey`'s `rounds` prop widens from `IRVRound[]` to a new `IRVFlowRound` — the
three fields the chart actually reads (`code`, `pct`, `eliminated`). Presidential
rounds remain assignable, and the senate rounds (which carry a `party` field the
presidential ones lack) become usable without padding the payload with unused
`name` / `votes` / `winner` fields.
- State selection: same "National Average" button + `<select>` control as the
  current `SenateBuckets`, so the interaction is unchanged.
- Candidate codes never surface as bare initials in labels — party labels only,
  per project convention. `buildDisplayLabels` already collapses `CON_1` → `CON`
  where a party has a single variant; the Sankey inherits that behavior.

### `components/senate/SenateWinnowCard.tsx`

Today's `SenateBuckets.tsx`, renamed and retitled. Changes:

- Title: "How the Field Narrows to Five Finalists".
- Copy states the mechanism: a 5-seat STV winnow with a Droop quota of ~16.7%
  cuts the state's full candidate field to five, and IRV or Condorcet then picks
  the senator from those five.
- Bars run against a fixed 0–50% axis with a quota marker at `data.quotaPct`. A
  0–100% axis would leave these ~20% tallies unreadable, and the quota — not a
  majority — is the threshold that matters here.
- National view renders `finalistSlots` instead of `seats`, and the
  method-dependent caption is removed — the winnow is method-independent.
- The old "Eliminated / Eliminated during IRV" sub-block was never accurate for
  this stage. The per-state view instead splits the five finalists into "Reached
  quota" and "Advanced below quota", since the winnow fills all five slots
  regardless of whether a candidate ever cleared the quota.
- Finalist pills carry `buildDisplayLabels` output, so a state where one party
  fields two finalists reads `CON_1` / `CON_2` rather than two identical `CON`
  pills, while sole candidates stay as the plain party code.
- A "Transfers from" legend names source parties whose slivers are too narrow to
  label inline, so the chart is readable without hovering.

### `components/senate/SenateCondorcetView.tsx`

Structurally unchanged, fed per-stop data, with two legibility fixes surfaced by
finally reading it against real numbers:

- The `n=` counts were slate-400 on saturated red cells and effectively invisible;
  they now inherit the cell's own green/red at 0.7 opacity.
- "Overall Condorcet champion: STY" reads as a contradiction next to a chamber
  where LBR wins 22 seats and STY 13. The label becomes "Broadest appeal, by
  average win rate across its pairings", and says plainly that being hardest to
  beat one-on-one is not the same as winning the most seats.

### `types/index.ts`

Add `SenateIrvRoundsData`, `SenateCoalitionAverage`, and `SenateWinnowData`.
Reuse the existing `IRVRound` / `PresidentialCandidate` shapes for the rounds
payload — the senate rounds carry `code`, `pct`, and `eliminated`, which is what
`IRVSankey` reads.

## Cost

21 new JSONs, ~1.1MB added to a 4.8MB `viz/src/data`. Statically imported in
`SenateTab.tsx`, consistent with the 28 seat-stop JSONs already there.

## Verification

Automated:

- Six existing senate CSVs byte-identical after the `irv_rounds` refactor.
- `pnpm typecheck` and `pnpm lint` clean.

Manual, in the browser, since none of this is unit-testable presentation:

- At `part=5`, IRV coalition bars sum to the party's real final-round tally and
  every bar crosses the 50% line; seat counts in the gutter match
  `CON 24 · LBR 21 · LIB 4 · STY 1 · POP 1`.
- Toggling Condorcet swaps the card to the matrix and the winnow card stays.
- Moving the participation slider changes the coalition bars, the matrix, and the
  winnow card together.
- A per-state Sankey's final column matches that state's IRV winner in
  `SenateMap`.
- Fan chart legend totals 102 and agrees per-party with `SenateCompositionCard`.
- Switching to Crossover hides both the coalition and matrix cards, as today.

## Out of scope

- Coalition / matrix cards for the Crossover (FD) pipeline.
- Any change to `SenateCompositionCard`, `SenateMap`, the vote model table, or the
  Crossover analysis section.
- The `_gauss` and `_prob` reference variants — `senate_irv_rounds.json` is
  emitted for the primary path only.
