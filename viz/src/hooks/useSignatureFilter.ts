import { useUrlState, useUrlNumber } from './useUrlState';
import type { SignatureFilter } from '../lib/signature';

export interface SignatureFilterState {
  filter: SignatureFilter;   // thresholds only; annotations always show
  consPct: number;
  setConsPct: (n: number) => void;
  deviantPp: number;
  setDeviantPp: (n: number) => void;
  mainstreamPp: number;
  setMainstreamPp: (n: number) => void;
  // Per-axis filter checkboxes: when checked, trim the list to rows matching that axis.
  filterCohesion: boolean;
  setFilterCohesion: (b: boolean) => void;
  filterDeviant: boolean;
  setFilterDeviant: (b: boolean) => void;
  filterMainstream: boolean;
  setFilterMainstream: (b: boolean) => void;
}

/**
 * Signature annotation thresholds + per-axis filter toggles, in shared URL params so Compare
 * Policies and Party Platforms stay in lockstep and the choice is deep-linkable. Marks always
 * show (Consensus ≥70%, Deviant ≥25pts, Mainstream ≤10pts); the filter toggles default off.
 */
export function useSignatureFilter(): SignatureFilterState {
  const [consPct, setConsPct] = useUrlNumber('consPct', 70);
  const [deviantPp, setDeviantPp] = useUrlNumber('devPp', 25);
  const [mainstreamPp, setMainstreamPp] = useUrlNumber('mainPp', 10);
  const [fCoh, setFCoh] = useUrlState<'on' | 'off'>('fCoh', 'off', { allowed: ['on', 'off'] });
  const [fDev, setFDev] = useUrlState<'on' | 'off'>('fDev', 'off', { allowed: ['on', 'off'] });
  const [fMain, setFMain] = useUrlState<'on' | 'off'>('fMain', 'off', { allowed: ['on', 'off'] });
  return {
    filter: { consPct, deviantPp, mainstreamPp },
    consPct, setConsPct,
    deviantPp, setDeviantPp,
    mainstreamPp, setMainstreamPp,
    filterCohesion: fCoh === 'on',
    setFilterCohesion: b => setFCoh(b ? 'on' : 'off'),
    filterDeviant: fDev === 'on',
    setFilterDeviant: b => setFDev(b ? 'on' : 'off'),
    filterMainstream: fMain === 'on',
    setFilterMainstream: b => setFMain(b ? 'on' : 'off'),
  };
}
