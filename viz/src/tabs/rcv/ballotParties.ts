/**
 * Ballot-line parties for the real Alaska/Maine elections on the RCV tab.
 *
 * Deliberately separate from PARTY_COLORS: those are the ten simulated parties, and
 * an earlier version of this tab mapped real candidates onto them (Peltola → LBR,
 * Palin → NAT), which asserted a placement the data never established. These are the
 * parties that actually appeared on the ballot, in muted tones so the simulation's
 * saturated palette stays reserved for simulated results.
 */

export const BALLOT_PARTY_COLORS: Record<string, string> = {
  D:   '#4a72a8',
  R:   '#b05a54',
  I:   '#8a8f98',
  L:   '#c08a2e',
  G:   '#4a8c62',
  AIP: '#8a6a45',
};

export const BALLOT_PARTY_NAMES: Record<string, string> = {
  D:   'Democratic',
  R:   'Republican',
  I:   'Independent',
  L:   'Libertarian',
  G:   'Green',
  AIP: 'Alaskan Independence',
};

const WRITE_IN = '#c3c8d0';

export function partyColor(party: string | null | undefined): string {
  if (!party) return WRITE_IN;
  return BALLOT_PARTY_COLORS[party] ?? WRITE_IN;
}

/** Parties that caucus with, or run to the left of, the Democrats — used only to
 *  describe a delegation's partisan balance, never to score a candidate. */
export const LEFT_OF_CENTER = new Set(['D', 'G']);
