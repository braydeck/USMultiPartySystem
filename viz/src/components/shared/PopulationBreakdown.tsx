import { Card } from '@/components/ui/card';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER, getContrastText } from '../../constants/parties';
import partyPopData from '../../data/partyPopulation.json';

type Row = { party: string; popShare: number; voteShare: number; turnout: number };
const DATA = partyPopData as Row[];

// Left→right ideological order so the stack reads as a spectrum.
const oidx = (p: string) => F5_ORDER.indexOf(p as typeof F5_ORDER[number]);
const ORDER = [...DATA].sort((a, b) => oidx(a.party) - oidx(b.party));

function StackedBar({ label, sub, valueKey }: { label: string; sub: string; valueKey: 'popShare' | 'voteShare' }) {
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1">
        <span className="text-xs font-semibold text-foreground">{label}</span>
        <span className="text-[11px] text-muted-foreground">{sub}</span>
      </div>
      <div className="flex h-9 w-full overflow-hidden rounded-md border border-border/50">
        {ORDER.map(r => {
          const pct = r[valueKey];
          const color = PARTY_COLORS[r.party] ?? '#9ca3af';
          return (
            <div key={r.party} className="flex items-center justify-center overflow-hidden"
              style={{ width: `${pct}%`, background: color }}
              title={`${PARTY_NAMES[r.party] ?? r.party}: ${pct}%`}>
              {pct >= 6 && (
                <span className="text-[10px] font-semibold leading-none px-0.5 truncate"
                  style={{ color: getContrastText(color) }}>
                  {r.party}{pct >= 9 ? ` ${Math.round(pct)}` : ''}
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
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
        Population Breakdown
      </h3>
      <p className="text-xs text-muted-foreground mb-4 max-w-2xl">
        How the nine forces map onto the electorate. The top bar is each force&apos;s share of the adult
        population; the bottom bar is its share of the people who actually voted in 2024. The gap between them
        is the turnout distortion — Solidarity is 12% of the population but 7% of voters, while high-turnout
        blocs (Progressive, Liberal, Nationalist) punch above their population weight.
      </p>

      <div className="space-y-3">
        <StackedBar label="Adult population" sub="latent preference · everyone counted once" valueKey="popShare" />
        <StackedBar label="2024 voters — as cast" sub="weighted by validated turnout" valueKey="voteShare" />
      </div>

      {/* Legend + turnout */}
      <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1.5">
        {ORDER.map(r => (
          <span key={r.party} className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <span className="w-2.5 h-2.5 rounded-sm" style={{ background: PARTY_COLORS[r.party] ?? '#9ca3af' }} />
            <span className="text-foreground font-medium">{PARTY_NAMES[r.party] ?? r.party}</span>
            <span>{r.popShare}%→{r.voteShare}% · {r.turnout}% turnout</span>
          </span>
        ))}
      </div>
    </Card>
  );
}
