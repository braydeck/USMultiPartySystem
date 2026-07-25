import { useState } from 'react';
import { useUrlState } from '../hooks/useUrlState';
import type { RCVData, RCVRace, HouseStateEntry } from '../types';
import { PARTY_COLORS, F5_ORDER, getContrastText } from '../constants/parties';
import { Card } from '@/components/ui/card';
import { ToggleGroup } from '../components/shared/ToggleGroup';
import { StickyControlBar } from '../components/shared/StickyControlBar';

// Real candidate → closest simulation-party mapping for coloring
const CANDIDATE_PARTY: Record<string, string> = {
  // Alaska House
  'Mary Peltola':     'LBR',
  'Nick Begich':      'CON',
  'Sarah Palin':      'NAT',
  'Chris Bye':        'LIB',
  'Eric Hafner':      'LIB',
  'Al Gross':         'LBR',
  // Alaska Senate
  'Lisa Murkowski':   'CUP',
  'Kelly Tshibaka':   'CON',
  'Patricia Chesbro': 'LBR',
  'Buzz Kelley':      'POP',
  // Alaska Governor
  'Mike Dunleavy':    'CON',
  'Bill Walker':      'CUP',
  'Les Gara':         'LBR',
  'Charlie Pierce':   'POP',
  // Maine CD1
  'Chellie Pingree':  'PRG',
  'Ed Thelander':     'CON',
  'Ron Russell':      'CON',
  // Maine CD2
  'Jared Golden':     'LBR',
  'Bruce Poliquin':   'CON',
  'Tiffany Bond':     'LIB',
  'William Hoar':     'PRG',
  'Austin Theriault': 'POP',
};

function candidateColor(name: string): string {
  return PARTY_COLORS[CANDIDATE_PARTY[name] ?? ''] ?? '#6b7280';
}

function officeLabel(office: string): string {
  if (office === 'US_HOUSE')   return 'US House';
  if (office === 'US_SENATE')  return 'US Senate';
  if (office === 'GOVERNOR')   return 'Governor';
  return office;
}

// ── IRV Rounds Chart ────────────────────────────────────────────────────────

function IrvRoundsChart({ race }: { race: RCVRace }) {
  const { irvRounds, irvWinner } = race;
  if (!irvRounds.length) return null;

  const allCandidates = race.candidates;
  const BAR_H = 28;
  const LABEL_W = 120;
  const BAR_W = 600 - LABEL_W - 8;
  const LEGEND_H = 20;
  const chartH = LEGEND_H + irvRounds.length * (BAR_H + 6) + 4;

  return (
    <div className="overflow-x-auto">
      <svg
        viewBox={`0 0 600 ${chartH}`}
        style={{ width: '100%', height: 'auto', minWidth: 420 }}
      >
        {/* Candidate legend at top */}
        {allCandidates.map((cand, ci) => {
          const cols = Math.min(allCandidates.length, 3);
          const lx = LABEL_W + (ci % cols) * Math.floor(BAR_W / cols);
          const ly = Math.floor(ci / cols) * 13;
          return (
            <g key={cand} transform={`translate(${lx}, ${ly + 2})`}>
              <rect x={0} y={0} width={10} height={10} fill={candidateColor(cand)} opacity={0.85} rx={2} />
              <text x={14} y={9} fontSize={9} fill={cand === irvWinner ? '#1e293b' : '#64748b'}
                fontWeight={cand === irvWinner ? 'bold' : 'normal'}>
                {cand}{cand === irvWinner ? ' ✓' : ''}
              </text>
            </g>
          );
        })}

        {/* Round rows */}
        {irvRounds.map((round, ri) => {
          const y = LEGEND_H + ri * (BAR_H + 6);
          const eliminated = round.eliminated;
          // Build stacked segments
          let cx = LABEL_W;
          const segments: { cand: string; x: number; w: number }[] = [];
          for (const cand of allCandidates) {
            const pct = round.pcts[cand] ?? 0;
            if (pct === 0) continue;
            const w = Math.max(1, (pct / 100) * BAR_W);
            segments.push({ cand, x: cx, w });
            cx += w;
          }
          return (
            <g key={ri}>
              <text x={0} y={y + BAR_H / 2 + 4} fontSize={9} fill="#94a3b8" textAnchor="start">
                Rd {round.round}{eliminated ? ` (−${eliminated.split(' ').pop()})` : ''}
              </text>
              {segments.map(({ cand, x, w }) => {
                const pct = round.pcts[cand] ?? 0;
                const isElim = round.eliminated === cand;
                return (
                  <rect
                    key={cand}
                    x={x}
                    y={y}
                    width={w}
                    height={BAR_H}
                    fill={candidateColor(cand)}
                    opacity={isElim ? 0.35 : 0.85}
                  >
                    <title>{cand}: {pct.toFixed(1)}%</title>
                  </rect>
                );
              })}
              {/* 50% majority line */}
              <line
                x1={LABEL_W + BAR_W / 2}
                y1={y}
                x2={LABEL_W + BAR_W / 2}
                y2={y + BAR_H}
                stroke="#64748b"
                strokeWidth={1}
                strokeDasharray="3 2"
              />
              <text x={LABEL_W + BAR_W / 2 + 2} y={y + 9} fontSize={8} fill="#94a3b8">50%</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ── Condorcet Matrix ────────────────────────────────────────────────────────

function CondorcetGrid({ race }: { race: RCVRace }) {
  const { condorcetMatrix, condorcetWinner, candidates } = race;
  if (!Object.keys(condorcetMatrix).length) return null;

  const CELL = 52;
  const LABEL_W = 96;
  const w = LABEL_W + candidates.length * CELL;
  const h = LABEL_W + candidates.length * CELL;

  return (
    <div className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${w} ${h}`}
        style={{ width: '100%', maxWidth: w, height: 'auto' }}
      >
        {/* Column headers */}
        {candidates.map((cand, ci) => (
          <text
            key={cand}
            x={LABEL_W + ci * CELL + CELL / 2}
            y={LABEL_W - 4}
            textAnchor="middle"
            fontSize={9}
            fill={cand === condorcetWinner ? '#1e293b' : '#64748b'}
            fontWeight={cand === condorcetWinner ? 'bold' : 'normal'}
          >
            {cand.split(' ').pop()}
          </text>
        ))}
        {/* Row headers + cells */}
        {candidates.map((rowCand, ri) => (
          <g key={rowCand}>
            <text
              x={LABEL_W - 4}
              y={LABEL_W + ri * CELL + CELL / 2 + 4}
              textAnchor="end"
              fontSize={9}
              fill={rowCand === condorcetWinner ? '#1e293b' : '#64748b'}
              fontWeight={rowCand === condorcetWinner ? 'bold' : 'normal'}
            >
              {rowCand.split(' ').pop()}
            </text>
            {candidates.map((colCand, ci) => {
              if (rowCand === colCand) {
                return (
                  <rect
                    key={colCand}
                    x={LABEL_W + ci * CELL}
                    y={LABEL_W + ri * CELL}
                    width={CELL}
                    height={CELL}
                    fill="#f1f5f9"
                  />
                );
              }
              const pct = condorcetMatrix[rowCand]?.[colCand] ?? 0;
              const wins = pct > 0.5;
              const intensity = Math.abs(pct - 0.5) * 2; // 0–1
              const fill = wins
                ? `rgba(16,185,129,${0.15 + intensity * 0.5})`
                : `rgba(239,68,68,${0.1 + intensity * 0.35})`;
              return (
                <g key={colCand}>
                  <rect
                    x={LABEL_W + ci * CELL}
                    y={LABEL_W + ri * CELL}
                    width={CELL}
                    height={CELL}
                    fill={fill}
                    stroke="#fff"
                    strokeWidth={1}
                  />
                  <text
                    x={LABEL_W + ci * CELL + CELL / 2}
                    y={LABEL_W + ri * CELL + CELL / 2 + 4}
                    textAnchor="middle"
                    fontSize={10}
                    fontWeight="bold"
                    fill={wins ? '#065f46' : '#991b1b'}
                  >
                    {(pct * 100).toFixed(0)}%
                  </text>
                </g>
              );
            })}
          </g>
        ))}
      </svg>
      <p className="text-xs text-muted-foreground mt-1">
        Each cell = % of ballots preferring row candidate over column candidate. Green = row wins head-to-head.
      </p>
    </div>
  );
}

// ── CES Simulation Panel (shown once per state, at top) ─────────────────────

function CesSimPanel({ stateAbbr, houseStateMap }: { stateAbbr: 'AK' | 'ME'; houseStateMap: Record<string, HouseStateEntry> }) {
  const fips = stateAbbr === 'AK' ? '02' : '23';
  const sim = houseStateMap[fips];
  if (!sim) return null;
  const stateLabel = stateAbbr === 'AK' ? 'Alaska' : 'Maine';
  const actualSeats = sim.totalSeats / 2;  // sim runs at doubled size
  return (
    <Card className="p-4 space-y-2">
      <div className="flex items-baseline gap-2">
        <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          CES Simulation — {stateLabel}
        </h4>
        <span className="text-xs text-muted-foreground">
          9-party STV at {sim.totalSeats} seats ({actualSeats} actual × 2)
        </span>
      </div>
      <div className="flex rounded overflow-hidden" style={{ height: 36 }}>
        {Object.entries(sim.seats as Record<string, number>)
          .sort((a, b) => F5_ORDER.indexOf(a[0] as typeof F5_ORDER[number]) - F5_ORDER.indexOf(b[0] as typeof F5_ORDER[number]))
          .map(([party, seats]) => {
            const pct = (seats / sim.totalSeats) * 100;
            return (
              <div
                key={party}
                title={`${party}: ${seats} seats (${pct.toFixed(0)}%)`}
                className="flex items-center justify-center overflow-hidden"
                style={{
                  width: `${pct}%`,
                  backgroundColor: PARTY_COLORS[party] ?? '#6b7280',
                  minWidth: 4,
                }}
              >
                {pct >= 12 && <span className="text-xs font-bold chip-text" style={{ color: getContrastText(PARTY_COLORS[party] ?? '#6b7280') }}>{party}</span>}
              </div>
            );
          })}
      </div>
      <p className="text-xs text-muted-foreground">
        Simulated result from CES 2024 survey data with a full 9-party slate: what a multi-party STV system could elect.
        Compare with the real-ballot results below, which are limited to 2–4 candidates per race.
      </p>
    </Card>
  );
}

// ── Race Card ────────────────────────────────────────────────────────────────

function RaceCard({ race, defaultOpen = true }: { race: RCVRace; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const stateLabel = race.state === 'AK' ? 'Alaska' : 'Maine';
  const match = race.irvMatchesCondorcet;

  // Detect when plurality leader (R1 first-place) differs from IRV winner
  const r1 = race.irvRounds[0];
  const pluralityLeader = r1 ? Object.entries(r1.totals).sort((a, b) => b[1] - a[1])[0]?.[0] : null;
  const pluralityDiffersFromIRV = pluralityLeader && pluralityLeader !== race.irvWinner;

  return (
    <Card className="overflow-hidden">
      <button
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-muted transition-colors"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
      >
        <div className="flex items-center gap-3 flex-wrap text-left">
          <span className="text-sm font-semibold text-foreground">
            {race.year} — {race.raceName ?? officeLabel(race.office)} ({stateLabel})
          </span>
          <span className={`text-xs font-bold px-2 py-0.5 rounded ${
            match ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
          }`}>
            {match ? '✓ IRV = Condorcet' : '✗ IRV ≠ Condorcet'}
          </span>
          {pluralityDiffersFromIRV && (
            <span className="text-xs font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-700">
              ⚑ Plurality ≠ IRV
            </span>
          )}
        </div>
        <span className="text-muted-foreground text-sm ml-2">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-6 border-t border-border/50">
          {/* Winner summary */}
          <div className={`grid gap-3 pt-4 ${pluralityDiffersFromIRV ? 'sm:grid-cols-3' : 'sm:grid-cols-2'}`}>
            {pluralityDiffersFromIRV && (
              <div className="bg-blue-50 rounded-lg px-3 py-2">
                <div className="text-xs text-blue-400 mb-0.5">Round 1 Leader (Plurality)</div>
                <div className="text-sm font-bold text-blue-800">{pluralityLeader}</div>
                <div className="text-xs text-blue-500 mt-0.5">
                  {r1.pcts[pluralityLeader!]?.toFixed(1)}%, led but didn&apos;t win
                </div>
              </div>
            )}
            <div className="bg-muted rounded-lg px-3 py-2">
              <div className="text-xs text-muted-foreground mb-0.5">IRV Winner</div>
              <div className="text-sm font-bold text-foreground">{race.irvWinner}</div>
            </div>
            <div className={`rounded-lg px-3 py-2 ${match ? 'bg-muted' : 'bg-amber-50'}`}>
              <div className="text-xs text-muted-foreground mb-0.5">Condorcet Winner</div>
              <div className={`text-sm font-bold ${match ? 'text-foreground' : 'text-amber-800'}`}>
                {race.condorcetWinner ?? 'No Condorcet winner'}
              </div>
              {!match && race.condorcetWinner && (
                <div className="text-xs text-amber-600 mt-0.5">
                  {race.condorcetWinner} beats all others head-to-head but lost IRV
                </div>
              )}
            </div>
          </div>

          <div className="text-xs text-muted-foreground">
            {race.totalBallots.toLocaleString()} ballots cast · {race.candidates.length} candidates
          </div>

          <div>
            <h5 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-2">IRV Rounds</h5>
            <IrvRoundsChart race={race} />
          </div>

          <div>
            <h5 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-2">Condorcet Pairwise Matrix</h5>
            <CondorcetGrid race={race} />
          </div>

          {race.stvSeats !== undefined && race.stvElected && race.stvElected.length > 0 && (
            <div>
              <h5 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-2">
                STV at {race.stvSeats} Seats (doubled district size)
              </h5>
              <div className="flex flex-wrap gap-2 mb-2">
                {race.stvElected.map((cand, i) => (
                  <span
                    key={i}
                    className="text-sm font-semibold px-3 py-1 rounded-full chip-text"
                    style={{ backgroundColor: candidateColor(cand), color: getContrastText(candidateColor(cand)) }}
                  >
                    {cand}
                  </span>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">
                Real-ballot STV limited to actual ballot candidates ({race.candidates.length} total).
                With {race.stvSeats} seats, all or nearly all candidates are elected.
              </p>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

// ── Combined Delegation (ME: both districts at doubled seats) ────────────────

function CombinedDelegation({ cd1, cd2, year }: { cd1: RCVRace; cd2: RCVRace; year: number }) {
  const combined = [...(cd1.stvElected ?? []), ...(cd2.stvElected ?? [])];
  if (combined.length === 0) return null;

  // Count D vs R using party mapping
  const DEM_PARTIES = new Set(['LBR', 'PRG', 'LIB', 'DSA']);
  const dems = combined.filter(c => DEM_PARTIES.has(CANDIDATE_PARTY[c] ?? ''));
  const reps = combined.filter(c => !DEM_PARTIES.has(CANDIDATE_PARTY[c] ?? ''));

  return (
    <Card className="p-4 space-y-3 bg-indigo-50 border-indigo-200">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-indigo-900">
          {year} Maine Delegation — STV at 4 seats (2 per district)
        </h4>
        <span className="text-xs text-indigo-600">
          vs. today: {cd1.irvWinner.split(' ').pop()} + {cd2.irvWinner.split(' ').pop()} (both D)
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {combined.map((cand, i) => (
          <span
            key={i}
            className="text-sm font-semibold px-3 py-1 rounded-full chip-text"
            style={{ backgroundColor: candidateColor(cand), color: getContrastText(candidateColor(cand)) }}
          >
            {cand}
          </span>
        ))}
      </div>
      <div className="flex rounded overflow-hidden h-8 text-xs font-bold">
        {dems.map((c, i) => (
          <div
            key={i}
            className="flex items-center justify-center chip-text"
            style={{ width: `${100 / combined.length}%`, backgroundColor: candidateColor(c), color: getContrastText(candidateColor(c)) }}
          >
            {c.split(' ').pop()}
          </div>
        ))}
        {reps.map((c, i) => (
          <div
            key={i}
            className="flex items-center justify-center chip-text"
            style={{ width: `${100 / combined.length}%`, backgroundColor: candidateColor(c), color: getContrastText(candidateColor(c)) }}
          >
            {c.split(' ').pop()}
          </div>
        ))}
      </div>
      <p className="text-xs text-indigo-700">
        {dems.length}D + {reps.length}R, a proportional split reflecting Maine&apos;s competitive statewide vote.
        Under single-winner IRV, both seats go to Democrats.
      </p>
    </Card>
  );
}

// ── Main Tab ─────────────────────────────────────────────────────────────────

interface Props {
  data: RCVData;
  houseStateMap: Record<string, HouseStateEntry>;
}

export function RCVTab({ data, houseStateMap }: Props) {
  const [stateTab, setStateTab] = useUrlState<'AK' | 'ME'>('rcvState', 'AK', { allowed: ['AK', 'ME'] });

  const races = data[stateTab];
  const stateLabel = stateTab === 'AK' ? 'Alaska' : 'Maine';
  const mismatchCount = races.filter(r => !r.irvMatchesCondorcet).length;

  // Maine: group US_HOUSE races by year, reverse-chronological
  const meHouseYears = stateTab === 'ME'
    ? [...new Set(races.filter(r => r.office === 'US_HOUSE').map(r => r.year))].sort((a, b) => b - a)
    : [];

  function renderMeYear(year: number) {
    const cd1 = races.find(r => r.year === year && r.district === 'CD1');
    const cd2 = races.find(r => r.year === year && r.district === 'CD2');
    const isFirst = year === meHouseYears[0];
    return (
      <div key={year} className="space-y-3">
        <h3 className="text-base font-semibold text-foreground border-b border-border/50 pb-1">
          {year}{year === 2018 ? ' — Historical Reference' : ''}
        </h3>
        {cd1 && cd2 ? (
          <>
            <div className="grid md:grid-cols-2 gap-4">
              <RaceCard race={cd1} defaultOpen={isFirst} />
              <RaceCard race={cd2} defaultOpen={isFirst} />
            </div>
            <CombinedDelegation cd1={cd1} cd2={cd2} year={year} />
          </>
        ) : (
          <>
            {cd1 && <RaceCard race={cd1} defaultOpen={isFirst} />}
            {cd2 && <RaceCard race={cd2} defaultOpen={isFirst} />}
          </>
        )}
      </div>
    );
  }

  // Alaska: sort races reverse-chronological (newest first), first card open
  const akRacesSorted = [...races].sort((a, b) =>
    b.year !== a.year ? b.year - a.year : (a.office === 'US_HOUSE' ? -1 : 1)
  );

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-1">RCV in Practice — Alaska & Maine</h2>
        <p className="text-muted-foreground text-sm max-w-3xl">
          Alaska and Maine are the only US states that use ranked-choice voting for federal elections.
          Comparing IRV results with the Condorcet winner, and showing what multi-seat STV proportional
          representation would look like at doubled district size.
        </p>
      </div>

      <StickyControlBar label="RCV settings">
        <ToggleGroup label="State" value={stateTab} onChange={setStateTab}
          options={['AK', 'ME'] as const}
          labels={{ AK: 'Alaska', ME: 'Maine' }} />
      </StickyControlBar>

      {/* State context blurb */}
      <Card className="p-4 bg-muted text-sm text-muted-foreground space-y-1">
        {stateTab === 'AK' ? (
          <>
            <p><strong>Alaska</strong> adopted RCV in 2020 (Ballot Measure 2), first used in 2022.</p>
            <p>Uses a nonpartisan top-4 primary → RCV general for all state and federal offices.</p>
          </>
        ) : (
          <>
            <p><strong>Maine</strong> adopted RCV in 2016, first used in 2018 for federal offices.</p>
            <p>Maine has 2 congressional districts. CD1 (Portland/coast) leans Democrat; CD2 (rural interior) is competitive.
            Under STV at doubled seats (2 per district), both districts together elect a balanced 2D+2R delegation —
            compared to today&apos;s 2D under single-winner RCV.</p>
          </>
        )}
      </Card>

      {races.length === 0 ? (
        <Card className="border-dashed border-slate-300 p-10 text-center">
          <div className="text-muted-foreground text-sm">No race data loaded for {stateLabel}.</div>
        </Card>
      ) : (
        <>
          {/* CES simulation — shown once at top */}
          <CesSimPanel stateAbbr={stateTab} houseStateMap={houseStateMap} />

          {mismatchCount > 0 && (
            <Card className="bg-amber-50 border-amber-200 px-4 py-3 text-sm text-amber-800">
              <strong>{mismatchCount} race{mismatchCount > 1 ? 's' : ''}</strong> where IRV and Condorcet elected different winners.
            </Card>
          )}

          {stateTab === 'ME' ? (
            <div className="space-y-8">
              {meHouseYears.map(year => renderMeYear(year))}
            </div>
          ) : (
            <div className="space-y-4">
              {akRacesSorted.map((race, i) => (
                <RaceCard
                  key={`${race.state}-${race.year}-${race.office}-${i}`}
                  race={race}
                  defaultOpen={i === 0}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
