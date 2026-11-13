import depthNational from '../data/houseDepthNational.json';

/** National STV seats at the House tab's opening settings (rank-7 ballots, double map, 5% turnout
 *  gap), so a chart off the House tab sizes parties by the chamber the House tab first shows. */
export const DEFAULT_HOUSE_SEATS = (depthNational as unknown as Record<string, Record<string, Record<string,
  { national: { stvSeats: Record<string, number> } }>>>).top7.double['5'].national.stvSeats;
