# Hex seat cartogram — implementation handoff

Prototype is done and the design is settled. This is the spec for porting it into the
viz. Everything below was measured, not guessed; don't re-derive it.

Branch: `worktree-hexmap-seat-cartogram`. Reference render: `prototype/SHIP_x1_clipped.png`.

> **Shipped.** The port is done — `viz/src/lib/hexCartogram.ts` (geometry) and
> `viz/src/components/house/HexCartogram.tsx` (rendering), replacing the county-gradient
> map inside `HouseMap`. It serves STV and party list, double and triple Wyoming. See
> [What changed in the port](#what-changed-in-the-port) for where the shipped code
> departs from the spec below.

## What it is

A cartogram of the multi-member House where **one hexagon = one seat**. States keep a
recognizable outline but their area is proportional to population; districts are blobs of
seats; each seat is filled with its elected member's party colour.

The concept and the state outlines come from the **Congressional District Hexmap by Daniel
Donner for The Downballot** (<https://the-db.co/maps>), CC BY 4.0. Their unit is the
district (exactly 5 tiles each); ours is the seat, because our districts elect 2–10
members from 10 parties, so party colour has to live below the district level.

**Attribution is required** in anything published: credit the hexmap and link
`the-db.co/maps`. It is currently in the render footer and both script docstrings.

## The decision

**Clipped, 1 cell per seat, exploded 1.14, `cased` border style, rounded borders with
size-scaled weight.**

```
python pipeline/build_hex_seat_cartogram.py
python pipeline/render_hex_seat_cartogram.py --style cased --explode 1.14 --px-per-deg 82 \
    --out prototype/SHIP_x1_clipped.png
```

Rejected, with reasons:

- **Unclipped** (hexes overrun the border): keeps every seat exactly equal in area, but
  states stop being recognizable — Louisiana and Oklahoma become blobs. Kept as
  `--no-clip` because it's the honest comparison that justifies clipping.
- **2/3/5 cells per seat**: fits state outlines better (IoU 0.774 → 0.831 → 0.854 → 0.879)
  but the seat stops being a countable unit unless every cluster is compact, and even at
  90% compact the ragged 10% are ambiguous. Still buildable via `--cells-per-seat`.
- **`gap` border style** (white channel instead of a dark line): loses to `cased` now that
  clipping makes the state outline the dominant edge.

## Files

| path | role |
|---|---|
| `pipeline/hexmap_io.py` | shapefile + TopoJSON readers, no GDAL/shapely |
| `pipeline/build_hex_seat_cartogram.py` | all geometry → JSON. **This is the asset.** |
| `pipeline/render_hex_seat_cartogram.py` | matplotlib prototype renderer. Throwaway. |
| `data/raw/hexmap/HexStv30/` | state outlines (the container) |
| `data/raw/hexmap/HexDDv20/` | delegate districts, used only to place DC |
| `data/processed/hex_seat_cartogram.json` | build output, 1 cell/seat |
| `pipeline/county_split_overrides.csv` | cd119 county splits (Maricopa) |

Inputs the build reads: `viz/src/data/districtStvResults{,Triple}.json`,
`data/processed/county_to_district{,_triple}.csv`,
`viz/public/topojson/counties-10m.json`, `viz/src/constants/parties.ts` (colours, names,
and `F5_ORDER` — parsed, never duplicated).

## JSON schema

```jsonc
{
  "meta": { "R": 0.4216, "x0": ..., "y0": ..., "orientation": "pointy-top",
            "seats": 873, "cellsPerSeat": 1, "triple": false, "source": "..." },
  "states": {
    "CA": {
      "clip": true,                    // false only for DC
      "rings": [[[lon, lat], ...]],    // cartogram outline, already in render space
      "cells": [ { "col": 14, "row": 17, "core": "14,17",
                   "district": "06-01", "party": "LBR", "isCore": true } ]
    }
  }
}
```

- **Pointy-top, odd-r offset lattice.** Centre of `(col, row)` is
  `x0 + sqrt(3)*R*(col + 0.5*(row & 1))`, `y0 + 1.5*R*row`. Hexagon vertices at
  `centre + R*(sin(k*60°), cos(k*60°))`.
- **`core` is the seat id.** Cells sharing a `core` are one seat — draw no line between
  them. At 1 cell/seat every core cell is its own seat.
- **`isCore: false` cells are boundary fill.** They exist so the union of a state's cells
  covers its outline completely, leaving no sliver for the clip to expose. They inherit
  the district and party of the seat they were merged into. When rendering **unclipped,
  drop them** — drawing them as whole hexagons inflates every state past its real size
  and neighbours collide.

## Render spec

Draw per state, in this order, all clipped to that state's outline:

1. hexagon fills — party colour from `PARTY_COLORS`, no stroke
2. seat boundaries — white, `0.5pt`, only where `core` differs
3. district casing — white, `7.5pt`
4. district line — `#111827`, `4.7pt`
5. state outline — `#0b1220`, `3.4pt`, from `rings`, drawn over the clipped tiles

Weights are at a reference of 58 px/deg; scale linearly with px/deg.

**District weight scales with hex size.** The border staircases along hex edges, so a
stroke thinner than a step reads as notches. Factor
`min(1.8, max(1.0, (R / 0.1886) ** 0.55))` — 1.56× at 1 cell/seat, 1.0× at 5.

**Chain boundary edges into continuous paths before stroking.** In SVG this is free: emit
one `<path>` per border with `stroke-linejoin="round"`. Do not emit one segment per hex
edge — that was the prototype's bug and matplotlib couldn't join them.

**State outline weight tapers for small states**: `3.4 * min(1, max(0.4, (seats/10)**0.5))`.
A fixed heavy stroke is wider than Alaska's panhandle and erases it.

**Explode**: shift each state away from the map centre as a rigid body by
`(factor - 1) * (state_centroid - map_centroid)`, factor 1.14. Widens inter-state gaps
without disturbing the packing inside any state. Required for label placement to succeed.

**Labels**: outside the state, never on top of tiles or another label. Candidate positions
are a side plus a bias along it (below-toward-right, right-toward-top, …), preference
order leaning bottom-then-right, anchored to the state's silhouette in that direction.
Try **every side at the tightest offset before increasing the offset**, or you get
gratuitous leader lines. Reject any anchor nearer another state than its own. Draw a
leader line when the label sits more than 2R out. `PREFERRED` in the renderer holds 13
hand-set overrides. In the browser, measure real text extents instead of estimating from
point size.

## Measured findings

- **State area share tracks seat share to ±1.2 seats.** A lattice sized for 873 cells lands
  almost perfectly per state before any correction.
- **Clipping is not distortionary at the party level.** Worst single party 0.52pp
  (Conservative reads 22.6% of area against a 23.1% seat share); total absolute error
  2.13pp across 10 parties. Per-seat area varies a lot (p5–p95 0.75–1.21×) but is
  uncorrelated with party, so it cancels. Only 19 of 871 seats sit in states distorted more
  than 20%, and those states hold 3–5 seats each.
- **Net area loss from clipping is 0.00%** — R is chosen so total hexagon area equals total
  state area. It redistributes, it doesn't remove.
- **Donner's own numbers**, recovered from the shapefile: tile R = 0.26667° (= 4/15),
  exactly 5.0000 tiles per district, 2,175 tiles total. 430 of 435 districts single-part;
  the 5 exceptions are real islands. 72 interior districts sit at exactly 5 tiles, 363
  clipped ones range 3.66–6.33 — so they accept ±27% area error at the border to keep the
  silhouette. 97% of interior districts have 6–7 internal tile contacts of a possible 7.
- **Both border fixes matter, at different scales.** Weight is what makes districts legible
  zoomed out; rounding is what makes them look deliberate zoomed in. Rounding alone is
  nearly invisible at map scale — don't skip the weight. *(Half of this did not survive
  the port: rounding is dropped on screen. See the port notes.)*

## Known issues

- **Arizona `04-03`.** `county_to_district.csv` gives AZ only 2 districts (04-01 gets 1
  county, 04-02 the other 14) while the results JSON apportions 3.
  `pipeline/county_split_overrides.csv` fixes the *seeding* (04-03 now sits in the
  Maricopa area), but the underlying county file is still wrong and
  `districtCountyMap.json` has no polygon for 04-03. Only Arizona is affected.
- **3 of 150 district blobs hold one detached cell** at 1 cell/seat. Sizes are exact
  everywhere; contiguity loses the tie when the two conflict, because sizes are seat counts.
- Hawaii and Virginia have legitimately detached cells (islands, Eastern Shore).
- `docs/DATA_SOURCES.md` House table agreed with `houseSeats.json` after the last rebuild;
  worth rechecking the non-Conservative rows.

## What changed in the port

The spec above describes the print prototype. Five things had to differ in the browser.

- **The app fetches a geometry-only payload**, `viz/public/hexmap/hex_seat_cartogram{,_triple}.json`,
  written by the same build (`--viz-out` / `--no-viz`). It drops `party` — the map has to
  recolour for STV vs list, every ballot depth and every turnout stop, so baking one
  scenario's winners in would freeze it — pre-sorts each district's seats west→east so
  the app never redoes the centroid sort, and flattens cells to `[col, row, seatIdx,
  isCore]`. 255 KB → 132 KB, and 430 KB → 151 KB for triple.
- **Seat counts are exact in both files**: 873 across 150 districts, 1,726 across 243,
  checked against `districtStvResults{,Triple}.json`. Triple has 9 blobs with a detached
  cell against double's 3.
- **Weights are pixels, not points.** The app renders about five times smaller than the
  poster, so the prototype's map-unit widths land sub-pixel. They are converted to screen
  pixels with floors (seat 0.55, district 1.9, state 1.1) and drawn with
  `vector-effect: non-scaling-stroke`. Zooming multiplies them by `min(2.6, sqrt(k))`:
  the hexes grow, so the lines have to, but matching the zoom outright has a district
  line swallow the seats it separates.
- **Seat lines are grey and the district line runs 1.6× the print weight.** Districts
  were hard to pick out at app scale, and the cause was colour, not weight: seat
  boundaries and the district casing were both white, so a district border read as
  nothing more than a slightly fatter seat line. Splitting the colours — white means
  district, grey (`#c2ccd8`) means seat — does most of the work; the extra weight
  finishes it. Five variants rendered at map scale in `prototype/border_*.png`:
  baseline, heavier line, wider casing, grey seat lines, and both (shipped). Wider
  casing alone barely moves.
- **Labels are pinned to 11 screen px** and the frame is widened afterwards to whatever
  they need — Massachusetts places past Cape Cod and was being cut off. They sit inside
  the zoom group with `fontSize / k` so they hold their size. At app scale a label is
  ~2R rather than the poster's 0.7R, so the algorithm's "drop it rather than overlap"
  branch does real work; all 51 still place.
- **DC drops its boundary fill and is outlined by its own tiling.** It is the one
  unclipped state, so the fill has nothing to hide behind and inflated it into a blob,
  and its delegate-hexagon ring is bigger than its tiles so stroking that ring left a
  stray outline floating around them.
- **No corner fillet — district borders trace the hex edges exactly.** This reverses the
  prototype's rounding decision. The fillet cuts each corner back along its two edges,
  which at print scale was invisible but on screen visibly crossed jutting hexes: a
  district's own fill showed on the far side of its border, most obviously in Utah. The
  line is still chained into continuous paths and takes a round join and cap, which is
  what keeps a true-to-the-tiles staircase from reading as mitred sawteeth. At map scale
  the traced line is indistinguishable from the filleted one, which is the earlier
  finding — weight does the work zoomed out — arriving at the opposite conclusion about
  what to do zoomed in.

Behaviour differences a reader would notice: the map now opens on the whole country
rather than zoomed to Illinois, and clicking a selected state zooms back out. Selection
lives in `?mapstate=`. The Grid toggle, state dropdown, zoom buttons, district cards and
the statewide-pool note are all unchanged.

## Porting notes

The build script is renderer-agnostic and stays. The matplotlib renderer does not port —
rewrite it in SVG/d3, where several things I hand-rolled are native: `clipPath`, real path
joins, CSS-tunable weights, `paint-order` for label haloes. Reimplement `--explode` and
label placement in JS (~40 lines each).

Evaluate at shipping scale in the browser. Twice in this prototype a judgement made at
arbitrary matplotlib zoom reversed when checked at map scale. The numeric findings above
transferred fine; the visual ones needed redoing.
