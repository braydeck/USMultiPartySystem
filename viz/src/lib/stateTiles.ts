/**
 * Dealing a state's hexagon tiles out to parties.
 *
 * Tiles arrive sorted west→east (the cartogram builder does that once, at build time), so
 * dealing them in ideological order gives every state a left-to-right gradient — the same
 * reading the House map gives a district. Every state uses the same order, so a colour
 * boundary means the same thing in Wyoming as in California.
 */

import { PARTY_COLORS, F5_ORDER } from '../constants/parties';

/** Tile with no party: a state whose data is missing, or a rounding leftover. */
export const C_TILE_EMPTY = '#e2e8f0';

export const partyOf = (code: string) => code.split('_')[0];

export const tileColor = (code: string) => PARTY_COLORS[partyOf(code)] ?? '#94a3b8';

/** Ideological order, tolerant of the `CON_1` candidate codes the presidency uses. */
export function f5FillOrder(codes: string[]): string[] {
  return [...codes].sort((a, b) => {
    const ra = F5_ORDER.indexOf(partyOf(a) as typeof F5_ORDER[number]);
    const rb = F5_ORDER.indexOf(partyOf(b) as typeof F5_ORDER[number]);
    return (ra === -1 ? 99 : ra) - (rb === -1 ? 99 : rb) || a.localeCompare(b);
  });
}

/**
 * Merge a state's tiles into one path per party.
 *
 * Merging matters: a state can hold 520 tiles, and re-rendering ten paths when the reader
 * moves a control is a different proposition from re-rendering 520.
 */
export function dealTiles(
  counts: Record<string, number>,
  seatPaths: string[],
  emptyColor = C_TILE_EMPTY,
): { party: string; d: string; color: string }[] {
  const byParty = new Map<string, string[]>();
  let i = 0;
  for (const code of f5FillOrder(Object.keys(counts))) {
    for (let k = 0; k < (counts[code] ?? 0) && i < seatPaths.length; k++) {
      const at = byParty.get(code);
      if (at) at.push(seatPaths[i]); else byParty.set(code, [seatPaths[i]]);
      i++;
    }
  }
  // Leftovers stay empty rather than borrowing a neighbouring party's colour.
  for (; i < seatPaths.length; i++) {
    const at = byParty.get('');
    if (at) at.push(seatPaths[i]); else byParty.set('', [seatPaths[i]]);
  }
  return [...byParty].map(([party, ds]) => ({
    party,
    d: ds.join(''),
    color: party ? tileColor(party) : emptyColor,
  }));
}
