import { Card } from '@/components/ui/card';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER_WFP as F5_ORDER, getContrastText } from '../../constants/parties';
import partyPopData from '../../data/partyPopulation.json';

type Row = { party: string; popShare: number; voteShare: number; turnoutPresidential: number; turnoutMidterm: number };
const DATA = partyPopData as unknown as Row[];

const oidx = (p: string) => F5_ORDER.indexOf(p as typeof F5_ORDER[number]);
const ORDER = [...DATA].sort((a, b) => oidx(a.party) - oidx(b.party));

function Bar({ title, sub, valueKey }: { title: string; sub: string; valueKey: 'popShare' | 'voteShare' }) {
  return (
    <div className="flex items-center gap-3">
      <div className="shrink-0 text-right" style={{ width: 80 }}>
        <div className="text-xs font-semibold text-foreground">{title}</div>
        <div className="text-xs text-muted-foreground">{sub}</div>
      </div>
      <div className="flex-1 flex rounded-lg overflow-hidden" style={{ height: 52 }}>
        {ORDER.map(r => {
          const pct = r[valueKey];
          const color = PARTY_COLORS[r.party] ?? '#6b7280';
          return (
            <div key={r.party}
              title={`${PARTY_NAMES[r.party] ?? r.party}: ${pct}%`}
              className="flex items-center justify-center overflow-hidden"
              style={{ width: `${pct}%`, backgroundColor: color, minWidth: pct < 3 ? 2 : 0 }}>
              {pct >= 4 && (
                <span className="text-xs font-bold leading-tight text-center px-0.5 chip-text"
                  style={{ color: getContrastText(color) }}>
                  {r.party}<br />{pct.toFixed(0)}%
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function PopulationBreakdown() {
  return (
    <Card className="p-5">
      <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3">
        Population Breakdown
      </div>

      <div className="space-y-1">
        <Bar title="Population" sub="all adults" valueKey="popShare" />
        <Bar title="Voters" sub="as cast · 2024" valueKey="voteShare" />
      </div>

      {/* Legend — party names only; the population→vote shift is shown by the two bars */}
      <div className="flex flex-wrap gap-x-3 gap-y-1.5 mt-3 pt-2 border-t border-border/50">
        {ORDER.map(r => (
          <div key={r.party} className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: PARTY_COLORS[r.party] ?? '#6b7280' }} />
            <span className="text-xs text-foreground font-medium">{PARTY_NAMES[r.party] ?? r.party}</span>
          </div>
        ))}
      </div>

      <p className="text-xs text-muted-foreground mt-2">
        Share of adults (top) vs share of people who actually voted in 2024 (bottom).
      </p>
    </Card>
  );
}
