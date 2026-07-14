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

  const winnerRows = [
    { office: 'President — Condorcet', winners: series.presCond, cur: presData[i].condorcetWinner,
      note: 'single national head-to-head' },
    { office: 'President — IRV', winners: series.presIrv, cur: presData[i].irvWinner,
      note: 'strongest first-choice base' },
    { office: 'Senate — Condorcet', winners: series.senPlur.map(p => p[0]), cur: series.senPlur[i][0],
      note: `plurality of 51 · ${series.senPlur[i][0]} ${series.senPlur[i][1]} seats` },
  ].map(r => ({ ...r, flip: flipGap(r.winners) }));

  // House is a proportional chamber — plurality is uninformative. Track Solidarity's
  // delegation, the quantity that actually moves.
  const styLo = Math.min(...series.houseSTY), styHi = Math.max(...series.houseSTY);
  const houseSwing = styHi - styLo;

  return (
    <Card className="p-5">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
        Turnout Robustness — Gap-Compression Sweep
      </h3>
      <p className="text-xs text-muted-foreground mb-4">
        How far must the turnout gap between forces close for each office&apos;s winner to change? Drag from
        observed 2024 turnout toward parity. A sensitivity check, not a forecast.
      </p>

      {/* Slider */}
      <div className="mb-5 max-w-xl">
        <input type="range" min={0} max={STOPS.length - 1} step={1} value={i}
          onChange={e => setI(Number(e.target.value))}
          className="w-full accent-indigo-600" />
        {/* plausible post-reform band (~0–30% of the gap); gap% maps 1:1 to track fraction */}
        <div className="relative h-1.5 rounded bg-slate-200 mt-1">
          <div className="absolute inset-y-0 left-0 rounded bg-emerald-400/70" style={{ width: '30%' }} />
        </div>
        <div className="flex justify-between text-[11px] text-muted-foreground mt-1">
          <span>As cast · 2024 (0%)</span>
          <span className="font-semibold text-foreground">Gap closed: {STOPS[i]}%</span>
          <span>Latent preference · parity (100%)</span>
        </div>
        <p className="text-[10px] text-emerald-700 mt-1">
          ▉ Plausible post-reform range (~0–30%): PR closes the representation gap, not the income/education one.
        </p>
      </div>

      <div className="grid grid-cols-[1.5fr_1fr_auto] gap-x-3 text-xs">
        <div className="text-muted-foreground uppercase tracking-widest pb-1">Office</div>
        <div className="text-muted-foreground uppercase tracking-widest pb-1">Winner @ {STOPS[i]}%</div>
        <div className="text-muted-foreground uppercase tracking-widest pb-1 text-right">Verdict</div>
        {winnerRows.map(r => (
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
        {/* House — proportional, so report Solidarity's delegation, not the plurality. */}
        <div className="contents">
          <div className="py-2 border-t border-border/50">
            <div className="text-foreground font-medium leading-tight">House — Solidarity delegation</div>
            <div className="text-[11px] text-muted-foreground">of 873 seats · plurality (CON) stable, composition is the story</div>
          </div>
          <div className="py-2 border-t border-border/50">
            <span className="font-semibold" style={{ color: PARTY_COLORS.STY }}>{series.houseSTY[i]} seats</span>
          </div>
          <div className="py-2 border-t border-border/50 text-right">
            <span className="font-semibold text-amber-600">{styLo}→{styHi} ({houseSwing})</span>
          </div>
        </div>
      </div>

      <p className="mt-4 text-[11px] text-muted-foreground">
        President robust everywhere. House scales smoothly (quote it as a range). The Senate is the one contingent
        result — its flip sits <em>inside</em> the plausible band, so call it a coin-flip, not a win.
      </p>
    </Card>
  );
}
