import { useUrlState, useUrlNumber } from './useUrlState';
import type { SignatureFilter, AlignMode } from '../lib/signature';

export interface SignatureFilterState {
  filter: SignatureFilter;
  useConsensus: boolean;
  setUseConsensus: (b: boolean) => void;
  useAlign: boolean;
  setUseAlign: (b: boolean) => void;
  alignMode: AlignMode;
  setAlignMode: (m: AlignMode) => void;
  consPct: number;
  setConsPct: (n: number) => void;
  alignPp: number;
  setAlignPp: (n: number) => void;
}

/**
 * Consensus × Mainstream/Deviant filter, stored in shared URL params so Compare
 * Policies and Party Platforms stay in lockstep (no per-tab dissonance) and the
 * choice is deep-linkable. Defaults: Consensus on at 70%, Alignment off.
 */
export function useSignatureFilter(): SignatureFilterState {
  const [cons, setCons] = useUrlState<'on' | 'off'>('cons', 'on', { allowed: ['on', 'off'] });
  const [align, setAlign] = useUrlState<'on' | 'off'>('align', 'off', { allowed: ['on', 'off'] });
  const [alignMode, setAlignMode] = useUrlState<AlignMode>('alignDir', 'deviant', { allowed: ['deviant', 'mainstream'] });
  const [consPct, setConsPct] = useUrlNumber('consPct', 70);
  const [alignPp, setAlignPp] = useUrlNumber('alignPp', 25);
  return {
    filter: { useConsensus: cons === 'on', consPct, useAlign: align === 'on', alignMode, alignPp },
    useConsensus: cons === 'on',
    setUseConsensus: b => setCons(b ? 'on' : 'off'),
    useAlign: align === 'on',
    setUseAlign: b => setAlign(b ? 'on' : 'off'),
    alignMode,
    setAlignMode,
    consPct,
    setConsPct,
    alignPp,
    setAlignPp,
  };
}
