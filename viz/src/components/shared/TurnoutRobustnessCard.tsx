import { useMemo, useState } from 'react';
import { Card } from '@/components/ui/card';
import { PARTY_COLORS, PARTY_NAMES } from '../../constants/parties';
// λ=1 (full participation) = base; λ=0 (observed) = Turnout; L25/L50/L75 = the middle stops.
import presL100 from '../../data/rawMultiPresidentialElection.json';
import presL0 from '../../data/rawMultiPresidentialElectionTurnout.json';
import presL25 from '../../data/rawMultiPresidentialElectionTurnoutL25.json';
import presL50 from '../../data/rawMultiPresidentialElectionTurnoutL50.json';
import presL75 from '../../data/rawMultiPresidentialElectionTurnoutL75.json';
import senL100 from '../../data/pureMultiSenateCondorcet.json';
import senL0 from '../../data/pureMultiSenateCondorcetTurnout.json';
import senL25 from '../../data/pureMultiSenateCondorcetTurnoutL25.json';
import senL50 from '../../data/pureMultiSenateCondorcetTurnoutL50.json';
import senL75 from '../../data/pureMultiSenateCondorcetTurnoutL75.json';
import houseL100 from '../../data/houseSeats.json';
import houseL0 from '../../data/houseSeatsTurnout.json';
import houseL25 from '../../data/houseSeatsTurnoutL25.json';
import houseL50 from '../../data/houseSeatsTurnoutL50.json';
import houseL75 from '../../data/houseSeatsTurnoutL75.json';

type Pres = { condorcetWinner: string; irvWinner: string };
type SenSeat = { senatorParty: string };
type HouseSeat = { party: number; national: number };

const party = (code: string) => String(code).split('_')[0];
const CLUSTER_CODE = ['CON', 'LBR', 'STY', 'NAT', 'LIB', 'POP', 'CUP', 'OAO', 'DSA', 'PRG'];

// Ordered floor → ceiling: % of the inter-force turnout gap that has closed.
const STOPS = [0, 25, 50, 75, 100];
const presData = [presL0, presL25, presL50, presL75, presL100] as unknown as Pres[];
const senData = [senL0, senL25, senL50, senL75, senL100] as unknown as SenSeat[][];
const houseData = [houseL0, houseL25, houseL50, houseL75, houseL100] as unknown as HouseSeat[][];

function plurality(seats: SenSeat[]): [string, number] {
  const counts: Record<string, number> = {};
  for (const s of seats) { const p = party(s.senatorParty); counts[p] = (counts[p] ?? 0) + 1; }
  return Object.entries(counts).sort((a, b) => b[1] - a[1])[0] as [string, number];
}
const houseTop = (seats: HouseSeat[]) => CLUSTER_CODE[[...seats].sort((a, b) => b.national - a.national)[0].party];
const houseSTY = (seats: HouseSeat[]) => seats.find(h => h.party === 2)?.national ?? 0;

function pill(code: string) {
  const p = party(code);
  const color = PARTY_COLORS[p] ?? '#6b7280';
  return (
    <span className="inline-flex items-center gap-1.5 font-semibold whitespace-nowrap" style={{ color }}>
      <span className="w-2 h-2 rounded-full" style={{ background: color }} />
      {PARTY_NAMES[p] ?? p}
    </span>
  );
}

/** First stop (as gap %) whose winner differs from the observed floor, or null if constant. */
function flipGap(winners: string[]): number | null {
  for (let i = 1; i < winners.length; i++) if (winners[i] !== winners[0]) return STOPS[i];
  return null;
}

export function TurnoutRobustnessCard() {
  const [i, setI] = useState(0); // slider index into STOPS

  const series = useMemo(() => ({
    presCond: presData.map(d => party(d.condorcetWinner)),
    presIrv: presData.map(d => party(d.irvWinner)),
    senPlur: senData.map(s => plurality(s)),
    houseTop: houseData.map(h => houseTop(h)),
    houseSTY: houseData.map(h => houseSTY(h)),
  }), []);

  const rows = [
    { office: 'President — Condorcet', winners: series.presCond, cur: presData[i].condorcetWinner,
      note: 'single national head-to-head' },
    { office: 'President — IRV', winners: series.presIrv, cur: presData[i].irvWinner,
      note: 'strongest first-choice base' },
    { office: 'Senate — Condorcet', winners: series.senPlur.map(p => p[0]), cur: series.senPlur[i][0],
      note: `plurality of 51 · ${series.senPlur[i][0]} ${series.senPlur[i][1]}` },
    { office: 'House — plurality', winners: series.houseTop, cur: series.houseTop[i],
      note: `Solidarity ${series.houseSTY[i]} seats (${series.houseSTY[0]}→${series.houseSTY[series.houseSTY.length - 1]})` },
  ].map(r => ({ ...r, flip: flipGap(r.winners) }));

  return (
    <Card className="p-5">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
        Turnout Robustness — Gap-Compression Sweep
      </h3>
      <p className="text-xs text-muted-foreground mb-4 max-w-2xl">
        How far does the <strong>participation gap</strong> between forces have to close for each office&apos;s
        winner to change? Drag the slider from <em>observed 2024 turnout</em> (Solidarity 37%, PRG 83%) toward
        <em> full parity</em>. This sweeps <em>relative</em> weight, not the aggregate turnout level — it&apos;s a
        sensitivity check, not a forecast of where the real electorate lands.
      </p>

      {/* Slider */}
      <div className="mb-5 max-w-xl">
        <input type="range" min={0} max={STOPS.length - 1} step={1} value={i}
          onChange={e => setI(Number(e.target.value))}
          className="w-full accent-indigo-600" />
        <div className="flex justify-between text-[11px] text-muted-foreground mt-1">
          <span>Observed gaps (0%)</span>
          <span className="font-semibold text-foreground">Gap closed: {STOPS[i]}%</span>
          <span>Full parity (100%)</span>
        </div>
      </div>

      <div className="grid grid-cols-[1.5fr_1fr_auto] gap-x-3 text-xs">
        <div className="text-muted-foreground uppercase tracking-widest pb-1">Office</div>
        <div className="text-muted-foreground uppercase tracking-widest pb-1">Winner @ {STOPS[i]}%</div>
        <div className="text-muted-foreground uppercase tracking-widest pb-1 text-right">Verdict</div>
        {rows.map(r => (
          <div key={r.office} className="contents">
            <div className="py-2 border-t border-border/50">
              <div className="text-foreground font-medium leading-tight">{r.office}</div>
              <div className="text-[11px] text-muted-foreground">{r.note}</div>
            </div>
            <div className="py-2 border-t border-border/50">{pill(r.cur)}</div>
            <div className="py-2 border-t border-border/50 text-right">
              {r.flip === null
                ? <span className="font-semibold text-emerald-600">Robust</span>
                : <span className="font-semibold text-amber-600">Flips at {r.flip}%</span>}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 space-y-1.5 text-[11px] text-muted-foreground max-w-2xl">
        <p>
          <strong>The Presidency is robust at every level.</strong> The Senate plurality flips to Solidarity once
          the gap closes just a quarter of the way. The House plurality (Conservative) holds throughout, but
          Solidarity&apos;s delegation ranges from 82 to 129 seats across the sweep. Robust results don&apos;t
          depend on where the real electorate lands; the flip-points say how much mobilization a contingent result needs.
        </p>
        <p>
          Observed gaps (0%) is the conservative floor — it bakes in the suppression proportional representation
          removes. The separate <em>No Solidarity</em> toggle answers a different question (coordination failure),
          so it is not a test of Solidarity&apos;s viability.
        </p>
      </div>
    </Card>
  );
}
