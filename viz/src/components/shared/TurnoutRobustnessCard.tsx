import { useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { PARTY_COLORS, PARTY_NAMES } from '../../constants/parties';
import presFull from '../../data/rawMultiPresidentialElection.json';
import presCurr from '../../data/rawMultiPresidentialElectionTurnout.json';
import senFull from '../../data/pureMultiSenateCondorcet.json';
import senCurr from '../../data/pureMultiSenateCondorcetTurnout.json';
import houseFull from '../../data/houseSeats.json';
import houseCurr from '../../data/houseSeatsTurnout.json';

type Pres = { condorcetWinner: string; irvWinner: string };
type SenSeat = { senatorParty: string };
// House seats key party by cluster index (0-9), not code.
type HouseSeat = { party: number; partyName: string; national: number };

const party = (code: string) => code.split('_')[0];
const CLUSTER_CODE = ['CON', 'LBR', 'STY', 'NAT', 'LIB', 'POP', 'CUP', 'OAO', 'DSA', 'PRG'];

function pill(code: string) {
  const p = party(code);
  const color = PARTY_COLORS[p] ?? '#6b7280';
  return (
    <span className="inline-flex items-center gap-1.5 font-semibold" style={{ color }}>
      <span className="w-2 h-2 rounded-full" style={{ background: color }} />
      {PARTY_NAMES[p] ?? p}
    </span>
  );
}

/** Plurality party of a seat list, with its seat count. */
function plurality(seats: { party: string }[]): [string, number] {
  const counts: Record<string, number> = {};
  for (const s of seats) counts[s.party] = (counts[s.party] ?? 0) + 1;
  const [top] = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  return top as [string, number];
}

export function TurnoutRobustnessCard() {
  const rows = useMemo(() => {
    const pf = presFull as unknown as Pres, pc = presCurr as unknown as Pres;
    const sf = senFull as unknown as SenSeat[], sc = senCurr as unknown as SenSeat[];
    const hf = houseFull as unknown as HouseSeat[], hc = houseCurr as unknown as HouseSeat[];

    const senF = plurality(sf.map(s => ({ party: party(s.senatorParty) })));
    const senC = plurality(sc.map(s => ({ party: party(s.senatorParty) })));
    const hfTop = CLUSTER_CODE[[...hf].sort((a, b) => b.national - a.national)[0].party];
    const hcTop = CLUSTER_CODE[[...hc].sort((a, b) => b.national - a.national)[0].party];
    const styF = hf.find(h => h.party === 2)?.national ?? 0;
    const styC = hc.find(h => h.party === 2)?.national ?? 0;

    return [
      { office: 'President — Condorcet', full: pf.condorcetWinner, curr: pc.condorcetWinner,
        detail: 'single national head-to-head' },
      { office: 'President — IRV', full: pf.irvWinner, curr: pc.irvWinner,
        detail: 'strongest first-choice base' },
      { office: 'Senate — Condorcet', full: senF[0], curr: senC[0],
        detail: `plurality of 51: ${senF[0]} ${senF[1]} → ${senC[0]} ${senC[1]}` },
      { office: 'House — seats', full: hfTop, curr: hcTop,
        detail: `Solidarity ${styF}→${styC} seats` },
    ].map(r => ({ ...r, robust: party(r.full) === party(r.curr) }));
  }, []);

  return (
    <Card className="p-5">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
        Turnout Robustness
      </h3>
      <p className="text-xs text-muted-foreground mb-4 max-w-2xl">
        Does each office&apos;s winner survive the conservative floor? <strong>Full participation</strong> counts
        every latent preference once; <strong>current participation</strong> re-weights each force by its validated
        2024 turnout (Solidarity 37%, vs 77&ndash;83% for the high-education blocs). The gap between them is the
        mobilization the reform is designed to produce.
      </p>

      <div className="grid grid-cols-[1.4fr_1fr_1fr_auto] gap-x-3 gap-y-0 text-xs">
        <div className="text-muted-foreground uppercase tracking-widest pb-1">Office</div>
        <div className="text-muted-foreground uppercase tracking-widest pb-1">Full</div>
        <div className="text-muted-foreground uppercase tracking-widest pb-1">Current turnout</div>
        <div className="text-muted-foreground uppercase tracking-widest pb-1 text-right">Verdict</div>
        {rows.map(r => (
          <div key={r.office} className="contents">
            <div className="py-2 border-t border-border/50">
              <div className="text-foreground font-medium leading-tight">{r.office}</div>
              <div className="text-[11px] text-muted-foreground">{r.detail}</div>
            </div>
            <div className="py-2 border-t border-border/50">{pill(r.full)}</div>
            <div className="py-2 border-t border-border/50">{pill(r.curr)}</div>
            <div className="py-2 border-t border-border/50 text-right">
              <span className={`font-semibold ${r.robust ? 'text-emerald-600' : 'text-amber-600'}`}>
                {r.robust ? 'Robust' : 'Sensitive'}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 space-y-1.5 text-[11px] text-muted-foreground max-w-2xl">
        <p>
          <strong>Read it as a direction of travel, not a range.</strong> The current-turnout column is the
          suppressed-electorate floor; the reform moves outcomes up toward the full-participation ceiling as the
          previously-unrepresented mobilize. The floor also doubles as a calibration check &mdash; it roughly
          reproduces today&apos;s electorate.
        </p>
        <p>
          The single national Presidency is robust; the aggregated multi-race offices (Senate, House) are
          turnout-sensitive, because dispersed low-turnout forces like Solidarity need the mobilization the reform
          provides to clear district and state thresholds. The separate <em>No Solidarity</em> toggle answers a
          different question (coordination failure), so it is not a test of Solidarity&apos;s viability.
        </p>
      </div>
    </Card>
  );
}
