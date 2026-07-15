import { Card } from '@/components/ui/card';
import { PARTY_COLORS, PARTY_NAMES } from '../../constants/parties';
import ageData from '../../data/ageDistribution.json';

type Party = { party: string; p10: number; q25: number; median: number; q75: number; p90: number };
type AgeData = { national: Party; parties: Party[] };
const DATA = ageData as AgeData;

const AXIS_MIN = 18, AXIS_MAX = 80;
const TICKS = [20, 30, 40, 50, 60, 70, 80];
const pos = (x: number) => ((x - AXIS_MIN) / (AXIS_MAX - AXIS_MIN)) * 100;

// Youngest force at the top.
const ORDER = [...DATA.parties].sort((a, b) => a.median - b.median);
const NAT_MED = pos(DATA.national.median);

function Track({ r }: { r: Party }) {
  const color = PARTY_COLORS[r.party] ?? '#6b7280';
  const L = pos(r.p10), R = pos(r.p90), b1 = pos(r.q25), b2 = pos(r.q75), m = pos(r.median);
  return (
    <div className="relative" style={{ height: 24 }}
      title={`${PARTY_NAMES[r.party] ?? r.party}: median ${r.median} · middle 50% ${r.q25}–${r.q75} · 10–90% ${r.p10}–${r.p90}`}>
      {/* national median reference */}
      <div className="absolute inset-y-0" style={{ left: `${NAT_MED}%`, width: 1, backgroundColor: '#cbd5e1' }} />
      {/* whisker: 10th–90th percentile */}
      <div className="absolute top-1/2 -translate-y-1/2" style={{ left: `${L}%`, width: `${R - L}%`, height: 1.5, backgroundColor: color, opacity: 0.5 }} />
      {[L, R].map((x, i) => (
        <div key={i} className="absolute top-1/2 -translate-y-1/2" style={{ left: `${x}%`, width: 1.5, height: 9, backgroundColor: color, opacity: 0.6 }} />
      ))}
      {/* box: middle 50% (Q25–Q75) */}
      <div className="absolute top-1/2 -translate-y-1/2 rounded-sm" style={{ left: `${b1}%`, width: `${b2 - b1}%`, height: 15, backgroundColor: color, opacity: 0.85 }} />
      {/* median tick, haloed so it reads on any fill */}
      <div className="absolute top-1/2 -translate-y-1/2" style={{ left: `${m}%`, width: 2.5, height: 19, backgroundColor: '#0f172a', boxShadow: '0 0 0 1px rgba(255,255,255,0.9)' }} />
    </div>
  );
}

export function AgeDistributionCard() {
  return (
    <Card className="p-5">
      <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1">
        Age by Force
      </div>
      <p className="text-xs text-muted-foreground mb-4">
        Each force&apos;s 2024 age distribution. The bar is the middle 50% of members, the tick is the median, and the
        thin whiskers reach the 10th and 90th percentiles. Sorted youngest to oldest.
      </p>

      <div className="grid items-center gap-x-3 gap-y-1.5" style={{ gridTemplateColumns: '104px 1fr 30px' }}>
        {/* axis header */}
        <div />
        <div className="relative h-4 text-[10px] text-muted-foreground">
          {TICKS.map(t => (
            <span key={t} className="absolute -translate-x-1/2 tabular-nums" style={{ left: `${pos(t)}%` }}>{t}</span>
          ))}
        </div>
        <div className="text-[10px] text-muted-foreground text-right leading-tight">med</div>

        {ORDER.map(r => (
          <div key={r.party} className="contents">
            <div className="text-xs font-semibold text-foreground text-right truncate">{PARTY_NAMES[r.party] ?? r.party}</div>
            <Track r={r} />
            <div className="text-xs font-semibold tabular-nums text-right" style={{ color: PARTY_COLORS[r.party] ?? '#6b7280' }}>{r.median}</div>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-3 pt-2 border-t border-border/50 text-[11px] text-muted-foreground">
        <span className="inline-flex items-center gap-1.5"><span className="inline-block rounded-sm bg-foreground/70" style={{ width: 16, height: 9 }} /> middle 50%</span>
        <span className="inline-flex items-center gap-1.5"><span className="inline-block bg-foreground" style={{ width: 2.5, height: 12 }} /> median</span>
        <span className="inline-flex items-center gap-1.5"><span className="inline-block bg-foreground/50" style={{ width: 16, height: 1.5 }} /> 10th–90th pct</span>
        <span className="ml-auto">National median {DATA.national.median}</span>
      </div>

      <p className="text-xs text-muted-foreground mt-2">
        Democratic Socialists (median {ORDER[0].median}) and Solidarity ({DATA.parties.find(p => p.party === 'STY')?.median})
        are the youngest forces; Order &amp; Opportunity ({DATA.parties.find(p => p.party === 'OAO')?.median}) and the
        Nationalist right ({DATA.parties.find(p => p.party === 'NAT')?.median}) skew oldest.
      </p>
    </Card>
  );
}
