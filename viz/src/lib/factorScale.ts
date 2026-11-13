import popMean from '../data/factorPopulationMean.json';
import popSd from '../data/factorPopulationSd.json';

const MEAN: Record<string, number> = popMean;
const SD: Record<string, number> = popSd;

/** A raw factor score on the app's one position scale: SDs of the weighted electorate, 0 at the
 *  average voter. clusterProfiles z_F* and partyFactorEllipses.json are built on the same scale. */
export const rawToZ = (raw: number, factor: string) => (raw - (MEAN[factor] ?? 0)) / (SD[factor] || 1);

/** A raw spread (SD) in the same units. Spreads are not shifted by the mean. */
export const rawSpreadToZ = (sd: number, factor: string) => sd / (SD[factor] || 1);
