# Design backlog

Ideas the user has asked to keep for later implementation. Each entry says what it is, why it
came up, and what already exists to build on. Move an entry out when it ships.

## Named coalitions, and fusing them (raised 2026-10-28)

Label the most likely governing coalitions, and let a user fuse two or more parties into one to
see how the results change.

- **Why:** under proportional rules no party reaches a majority (the House needs three or more
  parties in every nine-party bootstrap draw), so the balance of power is the coalition math.
  Neighboring parties can be close enough to merge: Labor and Democratic Alliance (formerly
  Liberal) differ by 6 points on average across 71 policy items, with 41 items within 5 points.
- **Naming:** a fused LBR + DAL could itself be called "Democratic Alliance", the name chosen
  for the former Liberal party, which reads naturally as a coalition name.
- **Two modes:**
  - *Labeling*: name the likely coalitions on the chamber views, for example the smallest set of
    parties that reaches a majority in most draws.
  - *Fusing*: rerun the count with the fused parties' ballots merged into one party. That needs a
    pipeline run (or a cheap approximation) and changes STV transfers, so it is not just adding
    seats.
- **Build on:** `viz/src/components/senate/SenateCoalitionCard.tsx` already shows coalition math
  for the Senate; the bootstrap payloads (`viz/src/data/uncertainty*.json`) give per-draw seat
  counts to compute how often a coalition reaches a majority.

## Faster bootstrap draws (raised 2026-10-28)

Spec: [specs/bootstrap_speedup.md](specs/bootstrap_speedup.md). Measured: ballot generation's
per-voter Python loops and temp-file round-trips take about 6 s of a 12.5 s draw; vote counting
about 4 s. Vectorize ballots first, then in-memory draw inputs, then Numba only if needed.
