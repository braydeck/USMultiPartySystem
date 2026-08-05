import { useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { PARTY_NAMES } from '../../constants/parties';
import { partyOf } from '../../lib/stateTiles';
import { CartogramPanel, type CartogramView } from './CartogramPanel';
import type { PresidentialStateWinner, TopTwoCell, TopTwoRoute } from '../../types';
import { FIELD_LABEL } from '../../constants/typography';

/**
 * The top-two reduction, mapped.
 *
 * Two rows rather than one flat list, because the views are a 2x2 and a baseline, not five
 * peers: the allocation rule and the counting method vary independently, and first-choice share
 * is the unallocated vote both allocations are read against. Share sits in the allocation row
 * but behind a divider and in the outline variant, since it is not a third allocation — it
 * removes the allocation, and picking it greys both the pair beside it and the method row.
 *
 * Share draws on the population basis and everything else on the electoral basis, so switching
 * to it redraws the country — which is the point. The gap between the two silhouettes is the
 * college's thumb on the scale.
 */

export type TopTwoAlloc = 'prop' | 'wta';
export type TopTwoMethod = 'condorcet' | 'irv';

const ALLOC_LABELS: Record<TopTwoAlloc, string> = {
  prop: 'Top 2 Proportional',
  wta: 'Top 2 WTA',
};
const METHOD_LABELS: Record<TopTwoMethod, string> = {
  condorcet: 'Condorcet',
  irv: 'IRV',
};

const nameOf = (code: string) => PARTY_NAMES[partyOf(code)] ?? partyOf(code);
const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

interface Props {
  cell: TopTwoCell;
  /** per-state first-choice shares, for the share view */
  stateWinners: Record<string, PresidentialStateWinner>;
  /** national first-choice shares, for the share view's legend */
  nationalShares: { code: string; pct: number }[];
  share: boolean;
  alloc: TopTwoAlloc;
  method: TopTwoMethod;
  onShare: (v: boolean) => void;
  onAlloc: (v: TopTwoAlloc) => void;
  onMethod: (v: TopTwoMethod) => void;
  /** Maps a candidate code to the label the rest of the page uses. */
  label: (code: string) => string;
}

/** FIPS -> abbreviation, taken from the payload so it always covers the modelled states. */
function abbrByFips(stateWinners: Record<string, PresidentialStateWinner>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [fips, sw] of Object.entries(stateWinners)) out[fips] = sw.stateAbbr;
  return out;
}

function allocView(route: TopTwoRoute, alloc: TopTwoAlloc, fipsToAbbr: Record<string, string>,
                   label: (c: string) => string): CartogramView {
  const countsByAbbr: Record<string, Record<string, number>> = {};
  const evByAbbr: Record<string, number> = {};
  for (const [fips, st] of Object.entries(route.states)) {
    const abbr = fipsToAbbr[fips];
    if (!abbr) continue;
    countsByAbbr[abbr] = alloc === 'prop'
      ? { [route.a]: st.propA, [route.b]: st.propB }
      : { [st.wtaTo]: st.ev };
    evByAbbr[abbr] = st.ev;
  }
  const tally = alloc === 'prop' ? route.prop : route.wta;
  const winner = alloc === 'prop' ? route.propWinner : route.wtaWinner;
  return {
    basis: 'ec',
    countsByAbbr,
    apportion: false,
    evByAbbr,
    totals: [route.a, route.b].map(c => ({ code: c, value: tally[c] ?? 0 })),
    majority: route.majority,
    format: String,
    perStateSuffix: abbr => ` · ${evByAbbr[abbr] ?? 0} electors`,
    nationalLabel: `${route.totalEv} electors`,
    summary: `${route.majority} of ${route.totalEv} electors wins. `
      + (winner ? `${nameOf(winner)} clears it.` : 'Nobody clears it, so the House decides.'),
    blurb: alloc === 'prop'
      ? `Each state splits its electors in proportion to ballots counted for ${label(route.a)} or ${label(route.b)}.`
      : `Each state gives every elector to whichever of ${label(route.a)} and ${label(route.b)} it prefers.`,
    footnote: 'One hexagon = one elector. States are sized by electoral votes.',
    ariaLabel: 'Top-two electoral college cartogram',
    subject: 'elector map',
  };
}

function shareView(stateWinners: Record<string, PresidentialStateWinner>,
                   nationalShares: { code: string; pct: number }[]): CartogramView {
  const countsByAbbr: Record<string, Record<string, number>> = {};
  for (const sw of Object.values(stateWinners)) countsByAbbr[sw.stateAbbr] = sw.shares;
  const lead = nationalShares[0];
  return {
    basis: 'pop',
    countsByAbbr,
    apportion: true,
    evByAbbr: null,
    totals: nationalShares.map(s => ({ code: s.code, value: s.pct })),
    format: pct,
    perStateSuffix: () => ' · first choice',
    nationalLabel: 'National first choice',
    summary: `${nameOf(lead?.code ?? '')} leads on first preferences with ${pct(lead?.pct ?? 0)}, `
      + 'a plurality and not a majority. This is the field the top two are drawn from.',
    blurb: 'States sized by population. Hexes apportioned by first vote share, before any reduction to two.',
    footnote: 'States sized by population. Hexes apportioned by first vote share.',
    ariaLabel: 'First-choice vote share cartogram',
    subject: 'vote share map',
  };
}

export function TopTwoCartogram({
  cell, stateWinners, nationalShares, share, alloc, method,
  onShare, onAlloc, onMethod, label,
}: Props) {
  const fipsToAbbr = useMemo(() => abbrByFips(stateWinners), [stateWinners]);
  const route = cell[method];

  const view = useMemo(
    () => share ? shareView(stateWinners, nationalShares)
                : allocView(route, alloc, fipsToAbbr, label),
    [share, stateWinners, nationalShares, route, alloc, fipsToAbbr, label],
  );

  return (
    <CartogramPanel view={view}>
      <div className="space-y-1.5">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`${FIELD_LABEL} w-20 shrink-0`}>Allocation</span>
          <div className="flex flex-wrap items-center gap-1">
            {(['prop', 'wta'] as TopTwoAlloc[]).map(v => (
              <Button key={v} onClick={() => { onShare(false); onAlloc(v); }} size="sm"
                variant={!share && alloc === v ? 'default' : 'secondary'}
                className={share ? 'opacity-50' : ''}>
                {ALLOC_LABELS[v]}
              </Button>
            ))}
            {/* Shares the row but is not a third allocation — it removes the allocation, and with
                it the method below. Hence the divider, the "or", and the outline variant rather
                than joining the filled pair. */}
            <span className="mx-1 h-5 w-px bg-border shrink-0" aria-hidden="true" />
            <span className="text-3xs uppercase tracking-widest text-muted-foreground mr-1" aria-hidden="true">or</span>
            <Button onClick={() => onShare(true)} size="sm"
              variant={share ? 'default' : 'outline'}>
              First-choice share
            </Button>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className={`${FIELD_LABEL} w-20 shrink-0`}>Method</span>
          <div className="flex flex-wrap gap-1">
            {(['condorcet', 'irv'] as TopTwoMethod[]).map(v => (
              <Button key={v} onClick={() => { onShare(false); onMethod(v); }} size="sm"
                variant={!share && method === v ? 'default' : 'secondary'}
                className={share ? 'opacity-50' : ''}>
                {METHOD_LABELS[v]} — {label(cell[v].a)} v {label(cell[v].b)}
              </Button>
            ))}
          </div>
        </div>
      </div>
    </CartogramPanel>
  );
}
