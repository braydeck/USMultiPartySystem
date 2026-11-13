import { describe, it, expect } from 'vitest';
import clusterProfiles from '../data/clusterProfiles.json';
import currentProfiles from '../data/currentPartyProfiles.json';
import clusterSpreads from '../data/clusterSpreads.json';
import currentSpreads from '../data/currentPartySpreads.json';
import { PARTY_ELLIPSES, ELLIPSE_FACTORS } from './partyOverlap';
import { rawToZ } from './factorScale';

// The 2D bubbles (z_F*), the 2D penumbras (clusterSpreads via rawToZ) and the 3D view
// (partyFactorEllipses) must place each party at the same point. z_F* is rounded to 2 dp.
const TOL = 0.006;
type Row = Record<string, number | string>;

describe('one position scale', () => {
  it('formulated parties agree across all three sources', () => {
    for (const [party, e] of Object.entries(PARTY_ELLIPSES)) {
      const cp = (clusterProfiles as unknown as Row[]).find(r => r.party === party)!;
      const cs = (clusterSpreads as Row[]).find(r => r.party === party)!;
      ELLIPSE_FACTORS.forEach((f, i) => {
        expect(Math.abs(Number(cp[`z_${f}`]) - e.mean[i]), `${party} ${f} z_F`).toBeLessThan(TOL);
        expect(Math.abs(rawToZ(Number(cs[`mean_${f}`]), f) - e.mean[i]), `${party} ${f} spread`).toBeLessThan(TOL);
      });
    }
  });

  it('current parties agree between profiles and spreads', () => {
    for (const cs of currentSpreads as Row[]) {
      const cp = (currentProfiles as unknown as Row[]).find(r => r.party === cs.party)!;
      for (const f of ELLIPSE_FACTORS) {
        expect(Math.abs(Number(cp[`z_${f}`]) - rawToZ(Number(cs[`mean_${f}`]), f)), `${cs.party} ${f}`).toBeLessThan(TOL);
      }
    }
  });
});
