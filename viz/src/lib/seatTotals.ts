import type { DistrictResult } from '../types';

/** Seats won per party, plus the chamber size, counted off the district results. */
export interface SeatTotals { per: Record<string, number>; all: number }

export function seatTotals(districtResults: Record<string, DistrictResult[]>): SeatTotals {
  const per: Record<string, number> = {};
  let all = 0;
  for (const rows of Object.values(districtResults)) {
    for (const d of rows) for (const p of d.elected) { per[p] = (per[p] ?? 0) + 1; all++; }
  }
  return { per, all };
}
