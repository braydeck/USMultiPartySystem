import { useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER_WFP as F5_ORDER, getContrastText } from '../../constants/parties';
import { LABEL_MIN_WIDTH } from '../house/FPTPvsSTV';
import { useElementWidth } from '../../hooks/useElementWidth';
import partyPopData from '../../data/partyPopulation.json';
import { MINOR_HEADING, CARD_HINT } from '../../constants/typography';

type Row = { party: string; popShare: number; voteShare: number; turnoutPresidential: number; turnoutMidterm: number };
const DATA = partyPopData as unknown as Row[];

const oidx = (p: string) => F5_ORDER.indexOf(p as typeof F5_ORDER[number]);
const ORDER = [...DATA].sort((a, b) => oidx(a.party) - oidx(b.party));

const BAR_HEIGHT = 40; // matches the House/Senate seat-share cards

function Bar({ title, sub, valueKey }: { title: string; sub: string; valueKey: 'popShare' | 'voteShare' }) {
  return (
    <div>
      <div className="flex items-baseline gap-1.5 mb-1">
        <span className="text-xs font-semibold text-foreground">{title}</span>
        <span className="text-xs text-muted-foreground">· {sub}</span>
      </div>
      <div className="flex rounded-lg overflow-hidden" style={{ height: BAR_HEIGHT }}>
        {ORDER.map(r => {
          const pct = r[valueKey];
          const color = PARTY_COLORS[r.party] ?? '#6b7280';
          return (
            <div key={r.party}
              title={`${PARTY_NAMES[r.party] ?? r.party}: ${pct}%`}
              className="seat-segment flex min-w-0 items-center justify-center overflow-hidden"
              style={{ width: `${pct}%`, backgroundColor: color, minWidth: pct < 3 ? 2 : 0 }}>
              <span className="seat-segment-label text-xs font-bold leading-tight text-center px-0.5 chip-text"
                style={{ color: getContrastText(color) }}>
                {r.party}<br />{pct.toFixed(0)}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function PopulationBreakdown() {
  const [rootRef, rootWidth] = useElementWidth<HTMLDivElement>();

  // Parties whose sliver is too narrow for its inline label in either bar — for those, append
  // the percentage to the legend name; a plainly legible segment doesn't need restating.
  const smallParties = useMemo(() => {
    if (!rootWidth) return new Set<string>();
    const set = new Set<string>();
    for (const r of ORDER) {
      if ((r.popShare / 100) * rootWidth < LABEL_MIN_WIDTH) set.add(r.party);
      if ((r.voteShare / 100) * rootWidth < LABEL_MIN_WIDTH) set.add(r.party);
    }
    return set;
  }, [rootWidth]);

  return (
    <Card ref={rootRef} className="p-5">
      <div className={`${MINOR_HEADING} mb-3`}>
        Population Breakdown
      </div>

      <div className="space-y-3">
        <Bar title="Population" sub="all adults" valueKey="popShare" />
        <Bar title="Voters" sub="as cast · 2024" valueKey="voteShare" />
      </div>

      {/* Legend — every party's full name always shown; population/voter share is appended only
          for slivers too narrow to carry their own inline label in the bars above. */}
      <div className="mt-3 pt-2 border-t border-border/50">
        {smallParties.size > 0 && (
          <div className="text-xs font-semibold text-foreground mb-1.5">Population / Voters</div>
        )}
        <div className="flex flex-wrap gap-x-3 gap-y-1.5">
          {ORDER.map(r => (
            <div key={r.party} className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: PARTY_COLORS[r.party] ?? '#6b7280' }} />
              <span className="text-xs text-foreground font-medium">
                {PARTY_NAMES[r.party] ?? r.party}
                {smallParties.has(r.party) && (
                  <span className="text-muted-foreground font-normal"> {r.popShare.toFixed(0)}% / {r.voteShare.toFixed(0)}%</span>
                )}
              </span>
            </div>
          ))}
        </div>
      </div>

      <p className={`${CARD_HINT} mt-2`}>
        Share of adults (top) vs share of people who actually voted in 2024 (bottom).
      </p>
    </Card>
  );
}
