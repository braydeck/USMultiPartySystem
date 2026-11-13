import { createContext } from 'react';
import type { HouseSeat } from '../types';

/** With parties dissolved, the House tab provides the full field's national seats under the
 *  current settings, by system label, so every FPTPvsSTV card compares full field against
 *  dissolved in place of today's FPTP and two-party PR chambers. */
export interface DissolveCompare {
  dissolved: string[];
  full: Partial<Record<'STV' | 'Party List' | 'MMP', HouseSeat[]>>;
}
export const DissolveCompareContext = createContext<DissolveCompare | null>(null);
