import { useMemo, useCallback } from 'react';
import { useUrlState } from './useUrlState';
import { F5_ORDER } from '../constants/parties';

/**
 * The set of parties currently highlighted on the House map and grid.
 *
 * Backed by the URL rather than component state because four different components
 * render against it — the map and the grid, under STV and under party list — and they
 * mount and unmount as the reader switches. Local state would drop the coalition every
 * time. It also makes a coalition shareable. Stored in F5_ORDER so the parameter is
 * stable whatever order the reader clicked in.
 */
export function usePartyHighlight(): [ReadonlySet<string>, (next: ReadonlySet<string>) => void] {
  const [raw, setRaw] = useUrlState<string>('hl', '');
  const value = useMemo(() => new Set(raw ? raw.split(',') : []), [raw]);
  const set = useCallback(
    (next: ReadonlySet<string>) => setRaw(F5_ORDER.filter(p => next.has(p)).join(',')),
    [setRaw],
  );
  return [value, set];
}
