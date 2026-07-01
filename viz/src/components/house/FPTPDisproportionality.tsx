import { useState, useMemo } from 'react';
import type { FPTPState, HouseStateEntry } from '../../types';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER_WFP as F5_ORDER, getContrastText } from '../../constants/parties';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';

interface Props {
  states: FPTPState[];
  stateMap?: Record<string, HouseStateEntry>;
}

const STATE_ABBR: Record<string, string> = {
  'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
  'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
  'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID',
  'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS',
  'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
  'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS',
  'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
  'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY',
  'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK',
  'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
  'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT',
  'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV',
  'Wisconsin': 'WI', 'Wyoming': 'WY',
};

const gerryScore = (s: FPTPState) => Math.abs(s.fptpSeatDiff);

function SpotlightBar({
  label, dem, gop, demTotal, gopTotal, total, lightColors,
}: {
  label: string;
  dem: number; gop: number; demTotal: number; gopTotal: number; total: number;
  lightColors?: boolean;
}) {
  const demPct = (dem / total) * 100;
  const gopPct = (gop / total) * 100;
  return (
    <div>
      <div className="text-xs text-muted-foreground font-medium mb-1">{label} ({total} seats)</div>
      <div className="flex rounded overflow-hidden" style={{ height: 26 }}>
        <div
          className="flex items-center justify-center"
          style={{
            width: `${demPct}%`,
            backgroundColor: lightColors ? '#93c5fd' : '#1d4ed8',
            minWidth: dem > 0 && demPct < 6 ? 3 : 0,
          }}
        >
          {demPct >= 22 && <span className="text-white text-xs font-bold">Dem {demTotal}</span>}
        </div>
        <div
          className="flex items-center justify-center"
          style={{
            width: `${gopPct}%`,
            backgroundColor: lightColors ? '#fca5a5' : '#dc2626',
            minWidth: gop > 0 && gopPct < 6 ? 3 : 0,
          }}
        >
          {gopPct >= 22 && <span className="text-white text-xs font-bold">Rep {gopTotal}</span>}
        </div>
      </div>
    </div>
  );
}

function StvBar({ entry }: { entry: HouseStateEntry }) {
  const { seats, totalSeats } = entry;
  const segments = F5_ORDER.filter(p => (seats[p] ?? 0) > 0).map(p => ({ party: p, n: seats[p] }));
  return (
    <div>
      <div className="text-xs text-muted-foreground font-medium mb-1">Multi-party STV ({totalSeats} seats)</div>
      <div className="flex rounded overflow-hidden" style={{ height: 26 }}>
        {segments.map(({ party, n }) => {
          const pct = (n / totalSeats) * 100;
          return (
            <div
              key={party}
              title={`${PARTY_NAMES[party] ?? party}: ${n} seats`}
              className="flex items-center justify-center overflow-hidden"
              style={{
                width: `${pct}%`,
                backgroundColor: PARTY_COLORS[party] ?? '#6b7280',
                minWidth: pct < 3 ? 2 : 0,
              }}
            >
              {pct >= 10 && <span className="text-xs font-bold leading-none chip-text" style={{ color: getContrastText(PARTY_COLORS[party] ?? '#6b7280') }}>{party}</span>}
            </div>
          );
        })}
      </div>
      <div className="flex flex-wrap gap-x-2.5 gap-y-0 mt-1">
        {segments.map(({ party, n }) => (
          <span key={party} className="text-xs text-muted-foreground">
            <span style={{ color: PARTY_COLORS[party] }} className="font-bold">{party}</span> {n}
          </span>
        ))}
      </div>
    </div>
  );
}

function SpotlightCard({
  stateName, allStates, onChangeState, stvEntry,
}: {
  stateName: string;
  allStates: FPTPState[];
  onChangeState: (s: string) => void;
  stvEntry?: HouseStateEntry;
}) {
  const data = allStates.find(s => s.state === stateName);
  if (!data) return null;

  const isGopOver  = data.fptpSeatDiff > 0;
  const overColor  = isGopOver ? '#dc2626' : '#1d4ed8';
  const overSeats  = isGopOver ? data.gopFptpSeats : data.demFptpSeats;
  const overSeatPct = Math.round((overSeats / data.totalSeats) * 100);
  const overVotePct = isGopOver ? data.gopVotePct : data.demVotePct;
  const score = gerryScore(data);

  const sortedOptions = [...allStates].sort((a, b) => gerryScore(b) - gerryScore(a));

  return (
    <Card className="p-3 flex flex-col gap-2.5">
      <div className="flex items-start justify-between gap-2">
        <select
          value={stateName}
          onChange={e => onChangeState(e.target.value)}
          className="flex-1 text-sm font-semibold text-foreground bg-transparent rounded border border-border py-0.5 px-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-400 cursor-pointer"
        >
          {sortedOptions.map(s => (
            <option key={s.state} value={s.state}>
              {s.state} ({gerryScore(s).toFixed(1)}pp)
            </option>
          ))}
        </select>
        <span
          className="shrink-0 text-xs font-bold px-2 py-0.5 rounded-full whitespace-nowrap"
          style={{ backgroundColor: overColor + '18', color: overColor }}
        >
          {isGopOver ? 'GOP' : 'Dem'} +{score.toFixed(1)}pp
        </span>
      </div>

      <SpotlightBar
        label="FPTP Today"
        dem={data.demFptpSeats} gop={data.gopFptpSeats}
        demTotal={data.demFptpSeats} gopTotal={data.gopFptpSeats}
        total={data.totalSeats}
      />
      <SpotlightBar
        label="Proportional (D+R)"
        dem={data.demPrSeats} gop={data.gopPrSeats}
        demTotal={data.demPrSeats} gopTotal={data.gopPrSeats}
        total={data.totalSeats}
        lightColors
      />
      {stvEntry && <StvBar entry={stvEntry} />}

      <p className="text-xs text-muted-foreground leading-snug">
        {isGopOver ? 'Republican' : 'Democrat'}s hold{' '}
        <span className="font-semibold" style={{ color: overColor }}>
          {overSeats}/{data.totalSeats} seats ({overSeatPct}%)
        </span>{' '}
        on {overVotePct.toFixed(1)}% of the vote.
      </p>
    </Card>
  );
}

export function FPTPDisproportionality({ states, stateMap }: Props) {
  const [spotlights, setSpotlights] = useState<[string, string, string]>([
    'Illinois', 'North Carolina', 'Florida',
  ]);
  const [sortBy, setSortBy] = useState<'diff' | 'seats' | 'az'>('diff');
  const [showDetail, setShowDetail] = useState(false);

  const setSpotlight = (i: 0 | 1 | 2) => (name: string) =>
    setSpotlights(prev => {
      const next = [...prev] as [string, string, string];
      next[i] = name;
      return next;
    });

  // Build stateAbbr → HouseStateEntry lookup from FIPS-keyed stateMap
  const abbrToEntry = useMemo(() => {
    if (!stateMap) return {} as Record<string, HouseStateEntry>;
    const lookup: Record<string, HouseStateEntry> = {};
    for (const entry of Object.values(stateMap)) {
      lookup[entry.stateAbbr] = entry;
    }
    return lookup;
  }, [stateMap]);

  const getStvEntry = (stateName: string) => {
    const abbr = STATE_ABBR[stateName];
    return abbr ? abbrToEntry[abbr] : undefined;
  };

  const validStates = states.filter(s => s.totalSeats > 0);

  const sorted = [...validStates].sort((a, b) => {
    if (sortBy === 'diff') return Math.abs(b.fptpSeatDiff) - Math.abs(a.fptpSeatDiff);
    if (sortBy === 'seats') return b.totalSeats - a.totalSeats;
    return a.state.localeCompare(b.state);
  });

  const W = 480, H = 300, PAD = 36;
  const PLOT_W = W - PAD * 2;
  const PLOT_H = H - PAD * 2;

  return (
    <div className="space-y-5">
      {/* Spotlight cards */}
      <div>
        <p className="text-xs text-muted-foreground mb-3">
          Use the dropdowns to compare any states — sorted by gerrymander score (seat share − vote share gap).
          {stateMap && <span> Third bar shows the 9-party STV simulation result.</span>}
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {([0, 1, 2] as const).map(i => (
            <SpotlightCard
              key={i}
              stateName={spotlights[i]}
              allStates={validStates}
              onChangeState={setSpotlight(i)}
              stvEntry={getStvEntry(spotlights[i])}
            />
          ))}
        </div>
      </div>

      {/* Collapsible bubble chart + table */}
      <Card className="overflow-hidden">
        <Button
          variant="ghost"
          className="flex items-center justify-between w-full px-4 py-3 text-left"
          onClick={() => setShowDetail(v => !v)}
          aria-expanded={showDetail}
        >
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
            Bubble chart &amp; full table
          </span>
          <span className="text-muted-foreground text-sm">{showDetail ? '▲' : '▼'}</span>
        </Button>

        {showDetail && (
          <div className="p-4 space-y-4">
            {/* Bubble chart */}
            <div>
              <div className="text-xs text-muted-foreground mb-2">
                Each bubble: X = GOP vote share, Y = GOP seat share. Diagonal = perfect proportionality.{' '}
                <span className="text-red-600 font-medium">Above = GOP over-represented</span>{' '}
                <span className="text-blue-600 font-medium">Below = Dem over-represented</span>
              </div>
              <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto' }}>
                <g transform={`translate(${PAD},${PAD})`}>
                  {[0, 25, 50, 75, 100].map(v => {
                    const x = (v / 100) * PLOT_W;
                    const y = PLOT_H - (v / 100) * PLOT_H;
                    return (
                      <g key={v}>
                        <line x1={x} y1={0} x2={x} y2={PLOT_H} stroke="#f1f5f9" strokeWidth={1} />
                        <line x1={0} y1={y} x2={PLOT_W} y2={y} stroke="#f1f5f9" strokeWidth={1} />
                        <text x={x} y={PLOT_H + 12} textAnchor="middle" fontSize={8} fill="#94a3b8">{v}%</text>
                        <text x={-8} y={y} textAnchor="end" dominantBaseline="middle" fontSize={8} fill="#94a3b8">{v}%</text>
                      </g>
                    );
                  })}
                  <line x1={0} y1={PLOT_H} x2={PLOT_W} y2={0} stroke="#94a3b8" strokeWidth={1.5} strokeDasharray="5 4" />
                  {sorted.map(s => {
                    const x = (s.gopVotePct / 100) * PLOT_W;
                    const gopSeatPct = (s.gopFptpSeats / s.totalSeats) * 100;
                    const y = PLOT_H - (gopSeatPct / 100) * PLOT_H;
                    const r = Math.max(3, Math.sqrt(s.totalSeats) * 2.2);
                    const color = gopSeatPct > s.gopVotePct ? '#dc2626' : '#1d4ed8';
                    return (
                      <g key={s.state}>
                        <circle cx={x} cy={y} r={r} fill={color} fillOpacity={0.55} stroke={color} strokeWidth={0.5}>
                          <title>{s.state}: Vote {s.gopVotePct.toFixed(1)}% GOP, Seat {gopSeatPct.toFixed(0)}% GOP ({s.gopFptpSeats}/{s.totalSeats})</title>
                        </circle>
                        {s.totalSeats >= 10 && (
                          <text x={x} y={y} textAnchor="middle" dominantBaseline="middle" fontSize={6} fill="white" fontWeight={700}>
                            {s.state.substring(0, 2)}
                          </text>
                        )}
                      </g>
                    );
                  })}
                  <text x={PLOT_W / 2} y={PLOT_H + 24} textAnchor="middle" fontSize={9} fill="#64748b">GOP Vote Share →</text>
                  <text
                    x={-24} y={PLOT_H / 2}
                    textAnchor="middle" fontSize={9} fill="#64748b"
                    transform={`rotate(-90,${-24},${PLOT_H / 2})`}
                  >GOP Seat Share →</text>
                </g>
              </svg>
            </div>

            {/* Sort + table */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs text-muted-foreground">Sort by:</span>
                {(['diff', 'seats', 'az'] as const).map(s => (
                  <Button
                    key={s}
                    onClick={() => setSortBy(s)}
                    variant={sortBy === s ? 'default' : 'secondary'}
                    size="sm"
                  >
                    {s === 'diff' ? 'Disproportionality' : s === 'seats' ? 'Seats' : 'A–Z'}
                  </Button>
                ))}
              </div>
              <div className="overflow-y-auto" style={{ maxHeight: 320 }}>
                <Table className="text-xs">
                  <TableHeader className="sticky top-0 bg-white">
                    <TableRow className="text-muted-foreground uppercase tracking-widest">
                      <TableHead className="text-left pb-1.5 pr-3">State</TableHead>
                      <TableHead className="text-right pb-1.5 px-2">Seats</TableHead>
                      <TableHead className="text-right pb-1.5 px-2">GOP Vote</TableHead>
                      <TableHead className="text-right pb-1.5 px-2">FPTP</TableHead>
                      <TableHead className="text-right pb-1.5 px-2">PR</TableHead>
                      <TableHead className="text-right pb-1.5 pl-2">Excess</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sorted.map(s => {
                      const excess = s.gopFptpSeats - s.gopPrSeats;
                      return (
                        <TableRow key={s.state}>
                          <TableCell className="py-1 pr-3 font-medium text-foreground">{s.state}</TableCell>
                          <TableCell className="text-right px-2 text-muted-foreground">{s.totalSeats}</TableCell>
                          <TableCell className="text-right px-2 text-muted-foreground">{s.gopVotePct.toFixed(0)}%</TableCell>
                          <TableCell className="text-right px-2 font-mono">
                            <span className="text-red-600">{s.gopFptpSeats}R</span>
                            <span className="text-slate-300 mx-0.5">/</span>
                            <span className="text-blue-600">{s.demFptpSeats}D</span>
                          </TableCell>
                          <TableCell className="text-right px-2 font-mono text-muted-foreground">
                            {s.gopPrSeats}R/{s.demPrSeats}D
                          </TableCell>
                          <TableCell
                            className="text-right pl-2 font-mono font-bold"
                            style={{ color: excess > 0 ? '#dc2626' : excess < 0 ? '#1d4ed8' : '#94a3b8' }}
                          >
                            {excess > 0 ? `+${excess}R` : excess < 0 ? `${Math.abs(excess)}D` : '—'}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
