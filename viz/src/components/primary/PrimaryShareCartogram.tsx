import { useCallback, useMemo } from 'react';
import { PARTY_NAMES } from '../../constants/parties';
import { HexStateCartogram, type StateFill } from '../shared/HexStateCartogram';
import { dealTiles, f5FillOrder, partyOf, tileColor } from '../../lib/stateTiles';
import { largestRemainder } from '../../lib/ecAllocation';
import type { Cartogram } from '../../lib/hexCartogram';
import type { PrimaryStageShares, FDPrimaryData } from '../../types';

/**
 * The primary on the population cartogram, rolling forward a stage at a time.
 *
 * Two things happen as the reader advances a stage, and both are already in the payload:
 * a pod's states fill in for the first time, and states that voted earlier *recolour*,
 * because their ballots transfer as candidates are eliminated. Delaware's 14% OAO block
 * disappears after the retail stage and reappears as LIB and CUP. So the map is not a
 * running total being appended to — it is the whole field re-counted at every stage, which
 * is what STV actually does.
 *
 * States that have not voted yet stay as empty tiles, so the country fills in as the
 * calendar advances.
 */

const nameOf = (code: string) => PARTY_NAMES[partyOf(code)] ?? partyOf(code);
const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

/** Which pods have voted by each stage — the primary calendar. */
const STAGE_PODS: Record<string, Set<string>> = {
  After_Retail: new Set(['Retail']),
  After_Pod_A: new Set(['Retail', 'A']),
  After_Pod_C: new Set(['Retail', 'A', 'C']),
  After_Pod_BD: new Set(['Retail', 'A', 'B', 'C', 'D']),
};

/**
 * Exhausted ballots take tiles like a party, because at shallow ballot depths they are the
 * biggest bloc on the map: at a three-deep ranking they average 29% of the vote by the
 * final stage and reach 44% in one state. Dropping them would silently rescale every other
 * party up. They vanish entirely at seven-deep and beyond, where the ballots run out of
 * candidates before they run out of preferences.
 */
const EXHAUSTED = 'EXH';
// A clear mid grey, well away from C_NOT_VOTED: 'nobody ranked anyone else' and 'this
// state has not voted' are opposite facts, and two adjacent pale greys would read the same.
const C_EXHAUSTED = '#94a3b8';
const C_NOT_VOTED = '#f1f5f9';

interface Props {
  stageShares: Record<string, PrimaryStageShares>;
  stage: string;
  primaryData: FDPrimaryData;
}

export function PrimaryShareCartogram({ stageShares, stage, primaryData }: Props) {
  const activePods = STAGE_PODS[stage] ?? new Set<string>();

  /** Per-state shares at this stage, only for states whose pod has voted. */
  const byAbbr = useMemo(() => {
    const out: Record<string, { shares: Record<string, number>; pod: string; n: number }> = {};
    for (const ss of Object.values(stageShares)) {
      const sd = ss.stages[stage];
      if (!sd || !activePods.has(ss.pod)) {
        out[ss.stateAbbr] = { shares: {}, pod: ss.pod, n: ss.nRespondents };
        continue;
      }
      const shares: Record<string, number> = { ...sd.shares };
      if (sd.exhausted > 0) shares[EXHAUSTED] = sd.exhausted;
      out[ss.stateAbbr] = { shares, pod: ss.pod, n: ss.nRespondents };
    }
    return out;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stageShares, stage]);

  const voted = useMemo(
    () => Object.entries(byAbbr).filter(([, v]) => Object.keys(v.shares).length > 0).map(([a]) => a),
    [byAbbr],
  );

  /**
   * National share at this stage, weighted by respondents across the states that have
   * voted. Cumulative by construction: every voted state is counted at its current
   * transfer-inclusive share, not at the share it showed on the night.
   */
  const national = useMemo(() => {
    const totals: Record<string, number> = {};
    let n = 0;
    for (const abbr of voted) {
      const { shares, n: w } = byAbbr[abbr];
      n += w;
      for (const [code, s] of Object.entries(shares)) totals[code] = (totals[code] ?? 0) + s * w;
    }
    if (n === 0) return [];
    return Object.entries(totals)
      .map(([code, v]) => ({ code, pct: v / n }))
      .sort((a, b) => b.pct - a.pct || a.code.localeCompare(b.code));
  }, [voted, byAbbr]);

  const surviving = useMemo(() => primaryData.candidates
    .filter(c => {
      const sd = c.stages[stage];
      return sd && (sd.status === 'surviving' || sd.status === 'elected');
    })
    .map(c => c.code), [primaryData, stage]);

  const fills = useCallback((cg: Cartogram): StateFill[] => cg.states.map(st => {
    const shares = byAbbr[st.abbr]?.shares ?? {};
    const counts = Object.keys(shares).length ? largestRemainder(shares, st.seatCount) : {};
    return { abbr: st.abbr, groups: dealTiles(counts, st.seatPaths, C_NOT_VOTED) };
  }), [byAbbr]);

  const order = useMemo(() => {
    const codes = national.map(s => s.code).filter(c => c !== EXHAUSTED);
    return [...f5FillOrder(codes), ...(national.some(s => s.code === EXHAUSTED) ? [EXHAUSTED] : [])];
  }, [national]);

  const colorFor = (code: string) => (code === EXHAUSTED ? C_EXHAUSTED : tileColor(code));
  const labelFor = (code: string) => (code === EXHAUSTED ? 'Exhausted' : nameOf(code));

  const splitFor = (abbr: string): string[] => {
    const shares = byAbbr[abbr]?.shares;
    if (!shares) return [];
    const codes = Object.keys(shares).filter(c => c !== EXHAUSTED && (shares[c] ?? 0) > 0);
    return [...f5FillOrder(codes), ...(shares[EXHAUSTED] ? [EXHAUSTED] : [])];
  };

  const valueFor = (code: string, abbr: string | null): string => {
    const local = abbr ? byAbbr[abbr]?.shares : undefined;
    return pct(local ? local[code] ?? 0 : national.find(s => s.code === code)?.pct ?? 0);
  };

  const sidebar = (abbr: string | null) => {
    const state = abbr ? byAbbr[abbr] : undefined;
    const notYet = state && Object.keys(state.shares).length === 0;
    const codes = abbr ? splitFor(abbr) : order;
    return (
      <>
        <div className="text-xs font-semibold text-foreground mb-2">
          {abbr ? (
            <>
              {abbr}
              <span className="font-normal text-muted-foreground">
                {notYet ? ` · pod ${state?.pod}, votes later` : ' · this stage'}
              </span>
            </>
          ) : (
            <span className="text-muted-foreground">
              {voted.length} of {Object.keys(byAbbr).length} states voted · hover a state
            </span>
          )}
        </div>
        <div className="space-y-1">
          {codes.map(code => (
            <div key={code} className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-sm shrink-0" style={{ backgroundColor: colorFor(code) }} />
              <span className="text-xs text-foreground flex-1 min-w-0 truncate">{labelFor(code)}</span>
              <span className="text-xs tabular-nums font-medium text-foreground">{valueFor(code, abbr)}</span>
            </div>
          ))}
          {notYet && <div className="text-xs text-muted-foreground">No votes cast yet.</div>}
        </div>
        <div className="mt-3 pt-2 border-t border-border text-[10px] text-muted-foreground leading-snug">
          {surviving.length} candidate{surviving.length === 1 ? '' : 's'} still standing.
          {national[0] && ` ${labelFor(national[0].code)} leads the states that have voted with ${pct(national[0].pct)}.`}
        </div>
      </>
    );
  };

  const tooltip = (abbr: string) => {
    const state = byAbbr[abbr];
    const codes = splitFor(abbr);
    return (
      <>
        <span className="font-semibold">{abbr}</span>
        {codes.length === 0 && <span className="text-muted-foreground"> — pod {state?.pod}, votes later</span>}
        <div className="flex flex-wrap gap-1 mt-1">
          {codes.map(c => (
            <span key={c} className="px-1 rounded text-[10px] font-bold text-white"
              style={{ backgroundColor: colorFor(c) }} title={labelFor(c)}>
              {c === EXHAUSTED ? EXHAUSTED : partyOf(c)} {valueFor(c, abbr)}
            </span>
          ))}
        </div>
      </>
    );
  };

  return (
    <HexStateCartogram
      basis="pop"
      fills={fills}
      sidebar={sidebar}
      tooltip={tooltip}
      ariaLabel="Primary vote share cartogram"
      subject="primary vote map"
      footnote={'States sized by population. Hexes apportioned by first vote share.'}
    />
  );
}
