import { useMemo, useState } from 'react';
import { Card } from '@/components/ui/card';
import { PARTY_COLORS, PARTY_NAMES } from '../../constants/parties';
// Compression stops: 0 = observed 2024 turnout; 10/20/30 = % of the inter-force gap closed.
import presL0 from '../../data/rawMultiPresidentialElectionTurnout.json';
import presL10 from '../../data/rawMultiPresidentialElectionTurnoutL10.json';
import presL20 from '../../data/rawMultiPresidentialElectionTurnoutL20.json';
import presL30 from '../../data/rawMultiPresidentialElectionTurnoutL30.json';
import senL0 from '../../data/pureMultiSenateCondorcetTurnout.json';
import senL10 from '../../data/pureMultiSenateCondorcetTurnoutL10.json';
import senL20 from '../../data/pureMultiSenateCondorcetTurnoutL20.json';
import senL30 from '../../data/pureMultiSenateCondorcetTurnoutL30.json';
import houseL0 from '../../data/houseSeatsTurnout.json';
import houseL10 from '../../data/houseSeatsTurnoutL10.json';
import houseL20 from '../../data/houseSeatsTurnoutL20.json';
import houseL30 from '../../data/houseSeatsTurnoutL30.json';

type Pres = { condorcetWinner: string; irvWinner: string };
type SenSeat = { senatorParty: string };
type HouseSeat = { party: number; national: number };

const party = (code: string) => String(code).split('_')[0];
const CLUSTER_CODE = ['CON', 'LBR', 'STY', 'NAT', 'LIB', 'POP', 'CUP', 'OAO', 'DSA', 'PRG'];

// % of the inter-force turnout gap closed. 0 = observed; ≤10 plausible; 20–30 stress.
const STOPS = [0, 10, 20, 30];
const presData = [presL0, presL10, presL20, presL30] as unknown as Pres[];
const senData = [senL0, senL10, senL20, senL30] as unknown as SenSeat[][];
const houseData = [houseL0, houseL10, houseL20, houseL30] as unknown as HouseSeat[][];

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
  const [i, setI] = useState(0); // slider index into STOPS; default = 0 (observed data)

  const series = useMemo(() => ({
    presCond: presData.map(d => party(d.condorcetWinner)),
    presIrv: presData.map(d => party(d.irvWinner)),
    senPlur: senData.map(s => plurality(s)),
    houseTop: houseData.map(h => houseTop(h)),
    houseSTY: houseData.map(h => houseSTY(h)),
  }), []);

  const winnerRows = [
    { office: 'President · Condorcet', winners: series.presCond, cur: presData[i].condorcetWinner,
      note: 'single national head-to-head' },
    { office: 'President · IRV', winners: series.presIrv, cur: presData[i].irvWinner,
      note: 'strongest first-choice base' },
    { office: 'Senate · Condorcet', winners: series.senPlur.map(p => p[0]), cur: series.senPlur[i][0],
      note: `plurality of 51 · ${series.senPlur[i][0]} ${series.senPlur[i][1]} seats` },
  ].map(r => ({ ...r, flip: flipGap(r.winners) }));

  // House is a proportional chamber — plurality is uninformative. Track Solidarity's
  // delegation, the quantity that actually moves.
  const styLo = Math.min(...series.houseSTY), styHi = Math.max(...series.houseSTY);
  const houseSwing = styHi - styLo;

  return (
    <Card className="p-5">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
        Turnout Robustness
      </h3>
      <p className="text-xs text-muted-foreground mb-4">
        How much would the turnout gap between forces have to compress (the previously-ignored voting more,
        the documented <em>contraction effect</em> of PR) for each office&apos;s winner to change? Default is
        observed 2024 turnout (no assumed response); ≤10% closure is plausible for one cycle, 20–30% is a stress test.
      </p>

      {/* Slider */}
      <div className="mb-5 max-w-xl">
        <input type="range" min={0} max={STOPS.length - 1} step={1} value={i}
          onChange={e => setI(Number(e.target.value))}
          className="w-full accent-indigo-600" />
        {/* stops sit at track fractions 0/.33/.67/1 — green ≤10% (plausible), amber 20–30% (stress) */}
        <div className="relative h-1.5 rounded bg-amber-200/70 mt-1">
          <div className="absolute inset-y-0 left-0 rounded bg-emerald-400/70" style={{ width: '50%' }} />
        </div>
        <div className="flex justify-between text-[11px] text-muted-foreground mt-1">
          <span>Observed (2024)</span>
          <span className="font-semibold text-foreground">{STOPS[i]}% gap closed{STOPS[i] >= 20 ? ' · stress' : STOPS[i] === 10 ? ' · plausible' : ''}</span>
          <span>Stress (30%)</span>
        </div>
        <p className="text-[10px] text-muted-foreground mt-1">
          <span className="text-emerald-700">▉ plausible (≤10%)</span> · <span className="text-amber-700">▉ stress (20–30%)</span>. The quasi-experimental PR turnout effect is small (1–4pts aggregate); &gt;30% is beyond one-cycle evidence.
        </p>
      </div>

      <div className="grid grid-cols-[1.5fr_1fr_auto] gap-x-3 text-xs">
        <div className="text-muted-foreground uppercase tracking-widest pb-1">Office</div>
        <div className="text-muted-foreground uppercase tracking-widest pb-1">Winner @ {STOPS[i]}% closed</div>
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
            <div className="text-foreground font-medium leading-tight">House · Solidarity delegation</div>
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
        <strong>President:</strong> robust. Solidarity (Condorcet) and Labour (IRV) hold at observed turnout and at
        every compression level. <strong>House:</strong> Conservative stays the plurality throughout; Solidarity&apos;s
        delegation scales {styLo}→{styHi} seats and only strengthens with compression. <strong>Senate:</strong> the one
        result observed data does <em>not</em> support. Labour leads at observed turnout and at plausible compression
        (≤10%); Solidarity only reaches the plurality under stress-level compression (~20–30%), beyond what one cycle
        plausibly delivers. So at observed turnout the Senate is Labour&apos;s, and Solidarity&apos;s Senate is conditional on mobilization.
      </p>
      <p className="mt-2 text-[10px] text-muted-foreground">
        Contraction is modeled as upward mobilization of the suppressed forces, holding high-turnout forces fixed:
        conservative for containment, since it never deflates the poles.
      </p>
    </Card>
  );
}
