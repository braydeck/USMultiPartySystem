# NEXT: Nine-party production   (written 2026-11-10 by the session that set the party order, palette and quiz hints)

## Where it stands
- Production runs on the nine parties, on `main` at 69ea807 (rebuild edd9249, descriptions 09afbd3, quiz 11a68fb,
  order/palette/signals cf77d20, quiz hints 69ea807). `bd-nine-parties` equals `main`.
- `python3 pipeline/check_stale.py`: all groups current (stamp `data/outputs/.verified.json`). `npm test` in `viz/`
  85 of 85, `tsc -b` clean.
- Party order = vote-agreement MDS: DSA PRG LBR CUP STY OAO CON POP NAT. `analysis/coalitions/vote_agreement.py`
  writes `data/processed/party_order.csv` (read by `pipeline/party_codes.LEFT_RIGHT`) and rewrites `F5_ORDER` in
  `viz/src/constants/parties.ts`. Local review page `analysis/coalitions/outputs/vote_agreement.html`.
- Per-draw House seats for coalition odds: `analysis/coalitions/house_draw_seats.py` ->
  `outputs/house_draw_seats_l5.csv` (1,000 draws from the cached re-clustering fits, default view).
- Quiz: 25 / 40 items, DPGMM components as classifier (`viz/src/data/quizShortform.json`, placement 85.6% short,
  95.3% long), hints under nine negatively worded items (`HINTS` in `viz/scripts/make_quiz_questions.py`).
- Unverified: no browser pass yet over the changed views (pass/fail colors on Legislation, Senate, Presidency; new
  palette on maps and pills; quiz hints).

## Waiting on the researcher
- Remaining red/green that are not pass/fail signals: Overview good/bad cards, What Is This? callouts, loading-sign
  colors, representation-gap deltas, GOP red, rural green. The F4 Cultural Conservatism factor color equals CON's
  #ef4444. Say which move to the bam poles or a new factor color; nothing changes until then.
- Overlap floor for `analysis/bootstrap/recluster.py` (proposed 2026-11-04, never ruled). Today every draw cluster
  gets a party by Hungarian match with no minimum overlap.

## Next steps
1. Browser QA: `cd viz && npm run dev`, check Legislation, Senate, Presidency, House maps, Quiz at desktop and phone.
2. Apply whatever the researcher rules on the red/green list above; rerun `npm test`.

## Running
- Nothing from this workstream. Restart the agreement and color-picker pages with
  `python3 -m http.server 8766 --bind 127.0.0.1` in `analysis/coalitions/outputs/`. Port 8765 now belongs to another
  session's uvicorn app; leave it alone.

## Don't redo
- Rulings live in `../exploration/listwise_check/DECISIONS.md` (2026-11-04 through 2026-11-07): nine parties, quiz
  versions, TikTok out, split cutoff 21, party order, colors, status signals, quiz hints. Don't rescan caps, reselect
  items, or put the Economic Conservatism order back; `F5_ORDER` keeps its old name on purpose.
- `house_draw_seats.py` anchors on `uncertaintyTurnoutL5.json` observed seats (default view), not
  `houseSeatsTurnoutL5.json` (full ranking).
- `data/bootstrap_cache/` holds the nine-party fits; delete it only after a new typology.
- `data/outputs/*.out`, `*.log` and `analysis/coalitions/outputs/house_draw_seats_run.log` stay uncommitted.
- `../rebuild_eight_parties/` is superseded. Don't write `analysis/validation/` (ANES is the researcher's).
- Quiz text stays verbatim CES; plain-language help goes in `HINTS`, not in the question.
