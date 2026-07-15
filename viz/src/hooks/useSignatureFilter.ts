import { useUrlState, useUrlNumber } from './useUrlState';
import type { SignatureFilter } from '../lib/signature';

export interface SignatureFilterState {
  filter: SignatureFilter;
  useConsensus: boolean;
  setUseConsensus: (b: boolean) => void;
  consPct: number;
  setConsPct: (n: number) => void;
  useDeviant: boolean;
  setUseDeviant: (b: boolean) => void;
  deviantPp: number;
  setDeviantPp: (n: number) => void;
  useMainstream: boolean;
  setUseMainstream: (b: boolean) => void;
  mainstreamPp: number;
  setMainstreamPp: (n: number) => void;
}

/**
 * Consensus + Deviant + Mainstream annotation filter, stored in shared URL params so Compare
 * Policies and Party Platforms stay in lockstep and the choice is deep-linkable. All three
 * axes default on (Consensus ≥70%, Deviant ≥25pts, Mainstream ≤10pts) so the annotations show.
 */
export function useSignatureFilter(): SignatureFilterState {
  const [cons, setCons] = useUrlState<'on' | 'off'>('cons', 'on', { allowed: ['on', 'off'] });
  const [dev, setDev] = useUrlState<'on' | 'off'>('dev', 'on', { allowed: ['on', 'off'] });
  const [main, setMain] = useUrlState<'on' | 'off'>('main', 'on', { allowed: ['on', 'off'] });
  const [consPct, setConsPct] = useUrlNumber('consPct', 70);
  const [deviantPp, setDeviantPp] = useUrlNumber('devPp', 25);
  const [mainstreamPp, setMainstreamPp] = useUrlNumber('mainPp', 10);
  return {
    filter: {
      useConsensus: cons === 'on', consPct,
      useDeviant: dev === 'on', deviantPp,
      useMainstream: main === 'on', mainstreamPp,
    },
    useConsensus: cons === 'on',
    setUseConsensus: b => setCons(b ? 'on' : 'off'),
    consPct,
    setConsPct,
    useDeviant: dev === 'on',
    setUseDeviant: b => setDev(b ? 'on' : 'off'),
    deviantPp,
    setDeviantPp,
    useMainstream: main === 'on',
    setUseMainstream: b => setMain(b ? 'on' : 'off'),
    mainstreamPp,
    setMainstreamPp,
  };
}
