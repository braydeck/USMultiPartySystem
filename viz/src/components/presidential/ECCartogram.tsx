import { useCallback, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { PARTY_NAMES } from '../../constants/parties';
import { HexStateCartogram, type StateFill } from '../shared/HexStateCartogram';
import { dealTiles, f5FillOrder, partyOf, tileColor } from '../../lib/stateTiles';
import type { Cartogram } from '../../lib/hexCartogram';
import {
  largestRemainder, MAP_VIEWS, MAP_VIEW_LABELS, MAP_VIEW_BLURB,
  type ECMethod, type ECTally, type MapView,
} from '../../lib/ecAllocation';
import type { PresidentialStateWinner } from '../../types';

/**
 * Five views of one election.
 *
 * What changes between them is the denominator, and each denominator gets its own tiling,
 * because making the denominator visible is a cartogram's whole job:
 *
 * - **First-choice share** uses the population basis: 4,365 tiles, states sized by their
 *   people, the smallest state still holding ten — enough to read a five-way split off a
 *   state the size of Wyoming. No electors and no thresholds; this is the vote itself.
 * - **The four elector rules** use the electoral basis: 975 tiles, one per elector, states
 *   scaled to electoral weight instead of population, so the two senatorial electors every
 *   state gets are part of the shape and Wyoming is drawn a third larger than its people
 *   alone would make it.
 *
 * Switching between the two redraws the country, and the difference between the two
 * silhouettes is the college's thumb on the scale.
 */

const nameOf = (code: string) => PARTY_NAMES[partyOf(code)] ?? partyOf(code);
const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

interface Props {
  tallies: Record<ECMethod, ECTally>;
  /** per-state first-choice shares, for the share view */
  stateWinners: Record<string, PresidentialStateWinner>;
  /** national first-choice shares, for the share view's legend */
  nationalShares: { code: string; pct: number }[];
  mapView: MapView;
  onMapView: (v: MapView) => void;
}

export function ECCartogram({ tallies, stateWinners, nationalShares, mapView, onMapView }: Props) {
  const share = mapView === 'share';
  const tally = share ? undefined : tallies[mapView];

  const sharesByAbbr = useMemo(() => {
    const out: Record<string, Record<string, number>> = {};
    for (const sw of Object.values(stateWinners)) out[sw.stateAbbr] = sw.shares;
    return out;
  }, [stateWinners]);

  const electorsByAbbr = useMemo(() => {
    const out: Record<string, Record<string, number>> = {};
    for (const s of tally?.states ?? []) out[s.abbr] = s.electors;
    return out;
  }, [tally]);

  const evByAbbr = useMemo(() => {
    const out: Record<string, number> = {};
    for (const s of tally?.states ?? []) out[s.abbr] = s.ev;
    return out;
  }, [tally]);

  /**
   * Under the elector rules a tile is an elector, so the counts go straight on — the three
   * winner-take-all rules hold a single entry and the state comes out solid. Under the
   * share view a tile is a slice of the state's population, so shares are apportioned
   * across them by largest remainder.
   */
  const fills = useCallback((cg: Cartogram): StateFill[] => cg.states.map(st => {
    const counts = share
      ? (sharesByAbbr[st.abbr] ? largestRemainder(sharesByAbbr[st.abbr], st.seatCount) : {})
      : electorsByAbbr[st.abbr] ?? {};
    return { abbr: st.abbr, groups: dealTiles(counts, st.seatPaths) };
  }), [share, sharesByAbbr, electorsByAbbr]);

  const order = useMemo(
    () => f5FillOrder(share ? nationalShares.map(s => s.code) : (tally?.byParty ?? []).map(p => p.code)),
    [share, nationalShares, tally],
  );

  const splitFor = (abbr: string): string[] => {
    const counts = share ? sharesByAbbr[abbr] : electorsByAbbr[abbr];
    if (!counts) return [];
    return f5FillOrder(Object.keys(counts)).filter(c => (counts[c] ?? 0) > 0);
  };

  /** Counts under the elector rules, percentages under the share view. */
  const valueFor = (code: string, abbr: string | null): string => {
    if (share) {
      const local = abbr ? sharesByAbbr[abbr] : undefined;
      return pct(local ? local[code] ?? 0 : nationalShares.find(s => s.code === code)?.pct ?? 0);
    }
    const local = abbr ? electorsByAbbr[abbr] : undefined;
    return String(local ? local[code] ?? 0 : tally?.byParty.find(p => p.code === code)?.ev ?? 0);
  };

  const sidebar = (abbr: string | null) => {
    const codes = abbr ? splitFor(abbr) : order;
    return (
      <>
        <div className="text-xs font-semibold text-foreground mb-2">
          {abbr ? (
            <>
              {abbr}
              <span className="font-normal text-muted-foreground">
                {share ? ' · first choice' : ` · ${evByAbbr[abbr] ?? 0} electors`}
              </span>
            </>
          ) : (
            <span className="text-muted-foreground">
              {share ? 'National first choice' : `${tally!.total} electors`} · hover a state
            </span>
          )}
        </div>
        <div className="space-y-1">
          {codes.map(code => (
            <div key={code} className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-sm shrink-0" style={{ backgroundColor: tileColor(code) }} />
              <span className="text-xs text-foreground flex-1 min-w-0 truncate">{nameOf(code)}</span>
              <span className="text-xs tabular-nums font-medium text-foreground">{valueFor(code, abbr)}</span>
            </div>
          ))}
        </div>
        <div className="mt-3 pt-2 border-t border-border text-[10px] text-muted-foreground leading-snug">
          {share
            ? `${nameOf(nationalShares[0]?.code ?? '')} leads on first preferences with `
              + `${pct(nationalShares[0]?.pct ?? 0)}, a plurality and not a majority.`
            : `${tally!.majority} of ${tally!.total} electors wins. `
              + (tally!.winner ? `${nameOf(tally!.winner)} clears it.` : 'Nobody clears it, so the House decides.')}
        </div>
      </>
    );
  };

  const tooltip = (abbr: string) => (
    <>
      <span className="font-semibold">{abbr}</span>
      {!share && ` — ${evByAbbr[abbr] ?? 0} elector${evByAbbr[abbr] === 1 ? '' : 's'}`}
      <div className="flex flex-wrap gap-1 mt-1">
        {splitFor(abbr).map(c => (
          <span key={c} className="px-1 rounded text-[10px] font-bold text-white"
            style={{ backgroundColor: tileColor(c) }} title={nameOf(c)}>
            {partyOf(c)} {valueFor(c, abbr)}
          </span>
        ))}
      </div>
    </>
  );

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted-foreground uppercase tracking-widest">View</span>
        <div className="flex flex-wrap gap-1">
          {MAP_VIEWS.map(v => (
            <Button key={v} onClick={() => onMapView(v)} size="sm"
              variant={mapView === v ? 'default' : 'secondary'}>
              {MAP_VIEW_LABELS[v]}
            </Button>
          ))}
        </div>
      </div>
      <p className="text-xs text-muted-foreground">{MAP_VIEW_BLURB[mapView]}</p>

      <HexStateCartogram
        basis={share ? 'pop' : 'ec'}
        fills={fills}
        sidebar={sidebar}
        tooltip={tooltip}
        ariaLabel={share ? 'First-choice vote share cartogram' : 'Electoral college cartogram'}
        subject={share ? 'vote share map' : 'elector map'}
        footnote={share
          ? 'States sized by population. Hexes apportioned by first vote share.'
          : 'One hexagon = one elector. States are sized by electoral votes.'}
      />
    </div>
  );
}
