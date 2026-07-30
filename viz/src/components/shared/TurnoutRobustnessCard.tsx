import { useMemo, useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { PARTY_COLORS, PARTY_NAMES } from '../../constants/parties';
import { uncertaintyAt } from '../../lib/uncertainty';

type Pres = { condorcetWinner: string; irvWinner: string };
// President + House use the rank-7 model (the app default), read from the lazy depth bundles;
// full-ranking would misstate the presidency, which flips at the observed-turnout floor.
type HplTop7 = Record<string, Record<string, Record<string, { national: { stvSeats: Record<string, number> } }>>>;
type Gd = Record<string, Record<string, Pres>>;

const party = (code: string) => String(code).split('_')[0];

// % of the inter-force turnout gap closed. 0 = observed; ≤15 plausible; 20–30 stress.
const STOPS = [0, 5, 10, 15, 20, 25, 30];
const STOP_KEYS = ['0', '5', '10', '15', '20', '25', '30'];

/** Largest party in the MODAL Condorcet senate, on the 51-seat basis (uncertainty seats are on
 *  102). This has to be the modal chamber: the Senate composition card on this same tab reports
 *  the modal headline, and a plurality tallied from the observed per-state JSONs contradicts it.
 *  Ties break on party code so the answer never depends on key insertion order. */
function modalSenatePlurality(gi: number): [string, number] {
  const seats = uncertaintyAt(gi)?.senate.cond.seats ?? {};
  const ranked = Object.entries(seats)
    .map(([p, v]) => [p, v.modal / 2] as [string, number])
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  return ranked[0] ?? ['—', 0];
}

/** One party's modal Condorcet senate seats, 51-seat basis. */
function modalSenateSeats(gi: number, p: string): number {
  return (uncertaintyAt(gi)?.senate.cond.seats[p]?.modal ?? 0) / 2;
}

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
  const [i, setI] = useState(1); // slider index into STOPS; default = 5% gap closed
  const [hpl, setHpl] = useState<HplTop7 | null>(null);
  const [gd, setGd] = useState<Gd | null>(null);
  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/housePartyList.json`).then(r => r.json()).then(setHpl).catch(() => {});
    fetch(`${import.meta.env.BASE_URL}data/generalDepth.json`).then(r => r.json()).then(setGd).catch(() => {});
  }, []);

  const series = useMemo(() => {
    if (!hpl || !gd) return null;
    return {
      presCond: STOP_KEYS.map(s => party(gd.top7[s].condorcetWinner)),
      presIrv: STOP_KEYS.map(s => party(gd.top7[s].irvWinner)),
      presCondRaw: STOP_KEYS.map(s => gd.top7[s].condorcetWinner),
      presIrvRaw: STOP_KEYS.map(s => gd.top7[s].irvWinner),
      senPlur: STOPS.map((_, gi) => modalSenatePlurality(gi)),
      senLBR: STOPS.map((_, gi) => modalSenateSeats(gi, 'LBR')),
      senSTY: STOPS.map((_, gi) => modalSenateSeats(gi, 'STY')),
      houseSTY: STOP_KEYS.map(s => hpl.top7.double[s].national.stvSeats.STY ?? 0),
    };
  }, [hpl, gd]);

  if (!series) {
    return (
      <Card className="p-5">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">Turnout Robustness</h3>
        <p className="text-[13px] text-muted-foreground">Loading…</p>
      </Card>
    );
  }

  const winnerRows = [
    { office: 'President · Condorcet', winners: series.presCond, cur: series.presCondRaw[i],
      note: 'single national head-to-head' },
    { office: 'President · IRV', winners: series.presIrv, cur: series.presIrvRaw[i],
      note: 'strongest first-choice base' },
    { office: 'Senate · Condorcet', winners: series.senPlur.map(p => p[0]), cur: series.senPlur[i][0],
      note: `most likely plurality of 51 · ${series.senPlur[i][0]} ${series.senPlur[i][1]} seats` },
  ].map(r => ({ ...r, flip: flipGap(r.winners) }));

  // House is a proportional chamber — plurality is uninformative. Track Solidarity's
  // delegation, the quantity that actually moves.
  const styLo = Math.min(...series.houseSTY), styHi = Math.max(...series.houseSTY);
  const houseSwing = styHi - styLo;
  // Senate endpoints for the paragraph below, read from the same modal series the table uses.
  const senLbrLo = series.senLBR[0], senLbrHi = series.senLBR[series.senLBR.length - 1];
  const senStyLo = series.senSTY[0], senStyHi = series.senSTY[series.senSTY.length - 1];

  return (
    <Card className="p-5">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
        Turnout Robustness
      </h3>
      <p className="text-[13px] text-muted-foreground mb-4 leading-relaxed">
        <span className="font-semibold text-foreground">Most outcomes hold across the plausible turnout band.</span> The
        slider closes the turnout gap between forces (the suppressed voting more, PR&apos;s documented contraction
        effect) and marks where each office&apos;s winner flips. The app opens at 5% gap closed; 0% is pure observed
        2024 turnout, ≤15% is plausible in one cycle, 20–30% is a stress test.
      </p>

      {/* Slider */}
      <div className="mb-5 max-w-xl">
        <input type="range" min={0} max={STOPS.length - 1} step={1} value={i}
          onChange={e => setI(Number(e.target.value))}
          className="w-full accent-indigo-600" />
        {/* stops at 0/.17/.33/.5/.67/.83/1 — green ≤15% (plausible), amber 20–30% (stress); boundary between the 15 and 20 stops */}
        <div className="relative h-1.5 rounded bg-amber-200/70 mt-1">
          <div className="absolute inset-y-0 left-0 rounded bg-emerald-400/70" style={{ width: '58.33%' }} />
        </div>
        <div className="flex justify-between text-[11px] text-muted-foreground mt-1">
          <span>Observed (2024)</span>
          <span className="font-semibold text-foreground">{STOPS[i]}% gap closed{STOPS[i] >= 20 ? ' · stress' : STOPS[i] > 0 ? ' · plausible' : ' · observed'}</span>
          <span>Stress (30%)</span>
        </div>
        <p className="text-[10px] text-muted-foreground mt-1">
          <span className="text-emerald-700">▉ plausible (≤15%)</span> · <span className="text-amber-700">▉ stress (20–30%)</span>. The quasi-experimental PR turnout effect is small (1–4pts aggregate); &gt;30% is beyond one-cycle evidence.
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

      <div className="mt-4 space-y-2.5 text-[13px] leading-relaxed">
        <p>
          <span className="font-semibold text-amber-700">President: the Condorcet winner turns on turnout.</span>{' '}
          <span className="text-foreground/90">At the 5% default it is Solidarity; at pure observed 2024 turnout (0%) it flips to Labor, which already wins IRV at every level. A Solidarity presidency needs even a small mobilization of suppressed voters; the Labor (IRV) result is robust.</span>
        </p>
        <p>
          <span className="font-semibold text-emerald-700">House: the ranking holds; only margins move.</span>{' '}
          <span className="text-foreground/90">No party has a majority. Conservative stays the largest delegation and Solidarity a smaller minority, below both Conservative and Labor, though its seats grow {styLo}→{styHi} as the gap closes.</span>
        </p>
        <p>
          <span className="font-semibold text-emerald-700">Senate: Labor holds the plurality at every level of turnout.</span>{' '}
          <span className="text-foreground/90">Labor leads at observed turnout and at every stop through the 30% stress ceiling, {senLbrLo} seats falling to {senLbrHi} as the gap closes. Solidarity takes most of what Labor and Conservative give up, {senStyLo}&rarr;{senStyHi} seats, and closes to within {senLbrHi - senStyHi} seat{senLbrHi - senStyHi === 1 ? '' : 's'} at the stress ceiling without ever taking the plurality. Turnout changes how large Labor&apos;s Senate plurality is, not who holds it, and no party is close to 26 at any stop.</span>
        </p>
      </div>
      <p className="mt-3 text-[11px] text-muted-foreground">
        Chambers use the rank-7 ballot model (the app default). Contraction is modeled as upward mobilization of the
        suppressed forces, holding high-turnout forces fixed: conservative for containment, since it never deflates the poles.
      </p>
    </Card>
  );
}
