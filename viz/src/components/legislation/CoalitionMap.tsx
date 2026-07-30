import { useMemo, useState } from 'react';
import type { CandidateVoteRow } from '../../types';
import { F5_ORDER, PARTY_NAMES, getPartyColor } from '../../constants/parties';
import type { VoteMode } from '../../constants/labels';
import { ToggleGroup } from '../shared/ToggleGroup';
import type { SeatMap } from './voteBloc';

// Who combines to pass each bill. Every bill is a row; parties are stacked left→right, each
// segment sized by its seats. The solid vertical rule at 50% is the majority. Parties left of it
// are the coalition that carries the bill; the one straddling it (white/dark ring) is pivotal.
//   • Whipped: a party casts all its seats for the side its majority favors — one segment per party.
//   • Free vote: each party's seats split by its yes-probability, so a split party shows on BOTH
//     sides (solid yes chunk left of the line, faded no chunk right of it).
// Seat weighting follows the scenario controls above.

type Chamber = 'house' | 'senate';
type Seg = { party: string; w: number; yes: boolean; key: string };

function segmentsFor(bill: CandidateVoteRow, seats: SeatMap, mode: VoteMode) {
  const parties = F5_ORDER.filter((p) => bill.parties[p] && (seats[p] ?? 0) > 0);
  const supp = (p: string) => bill.parties[p].observedPct ?? 0;
  const py = (p: string) => bill.parties[p].pYes ?? supp(p) / 100;
  let total = 0;
  for (const p of parties) total += seats[p] ?? 0;

  const yesSegs: Seg[] = [];
  const noSegs: Seg[] = [];
  if (mode === 'whipped') {
    for (const p of parties) {
      const s = seats[p] ?? 0;
      (supp(p) > 50 ? yesSegs : noSegs).push({ party: p, w: s, yes: supp(p) > 50, key: p });
    }
    yesSegs.sort((a, b) => supp(b.party) - supp(a.party));
    noSegs.sort((a, b) => supp(b.party) - supp(a.party));
  } else {
    for (const p of parties) {
      const s = seats[p] ?? 0;
      const yesW = s * py(p);
      const noW = s - yesW;
      if (yesW > 0.5) yesSegs.push({ party: p, w: yesW, yes: true, key: p + '-y' });
      if (noW > 0.5) noSegs.push({ party: p, w: noW, yes: false, key: p + '-n' });
    }
    yesSegs.sort((a, b) => py(b.party) - py(a.party));
    noSegs.sort((a, b) => py(b.party) - py(a.party));
  }

  const totalYes = yesSegs.reduce((s, x) => s + x.w, 0);
  const pass = totalYes > total / 2;
  // Pivotal only exists on a pass — the yes-segment whose seats carry the coalition over the line.
  let pivotalKey: string | null = null;
  if (pass) {
    let cum = 0;
    for (const seg of yesSegs) { cum += seg.w; if (cum >= total / 2) { pivotalKey = seg.key; break; } }
  }
  return { segs: [...yesSegs, ...noSegs], total, totalYes, pass, pivotalKey };
}

function CoalitionRow({ bill, seats, mode }: { bill: CandidateVoteRow; seats: SeatMap; mode: VoteMode }) {
  const { segs, total, pass, pivotalKey } = segmentsFor(bill, seats, mode);

  return (
    <div className="grid grid-cols-[minmax(140px,1.3fr)_2fr] gap-3 items-center py-1.5 border-t border-border/40">
      <div className="text-[11px] leading-tight flex items-start gap-1.5">
        <span className={`shrink-0 font-bold ${pass ? 'text-emerald-600' : 'text-rose-500'}`}
          title={pass ? 'Supporters hold a majority — passes' : 'Supporters fall short of a majority — fails'}>
          {pass ? '✓' : '✗'}
        </span>
        <span>{bill.question}</span>
      </div>
      <div className="relative h-7 rounded flex overflow-hidden bg-muted/30">
        {segs.map((seg) => {
          const w = (seg.w / total) * 100;
          const s = Math.round(seg.w);
          const isPivotal = seg.key === pivotalKey;
          const pct = Math.round(bill.parties[seg.party].observedPct ?? 0);
          const title = mode === 'whipped'
            ? `${PARTY_NAMES[seg.party] ?? seg.party}: ${pct}% support, ${s} seats${isPivotal ? ' · pivotal' : ''}${seg.yes ? '' : ' · opposes'}`
            : `${PARTY_NAMES[seg.party] ?? seg.party}: ~${s} seats voting ${seg.yes ? 'yes' : 'no'} (${pct}% support)${isPivotal ? ' · pivotal' : ''}`;
          return (
            <div key={seg.key}
              className="relative flex items-center justify-center overflow-hidden chip-text"
              style={{
                width: `${w}%`,
                backgroundColor: getPartyColor(seg.party),
                opacity: seg.yes ? 1 : 0.4,
                boxShadow: isPivotal ? 'inset 0 0 0 1.5px #fff, inset 0 0 0 3px rgba(15,23,42,0.85)' : 'none',
              }}
              title={title}>
              {w >= 9 && <span className="text-[9px] font-bold text-white leading-none">{seg.party}</span>}
            </div>
          );
        })}
        {/* majority line — white halo so it reads on any party color */}
        <div className="absolute inset-y-0 z-10" style={{ left: '50%', width: 2, backgroundColor: '#0f172a', boxShadow: '0 0 0 1.5px rgba(255,255,255,0.9)' }} />
      </div>
    </div>
  );
}

export function CoalitionMap({ candidateVotes, houseSeats, senateSeats, voteModel }: {
  candidateVotes: CandidateVoteRow[];
  houseSeats: SeatMap;
  senateSeats: SeatMap;
  voteModel: VoteMode;
}) {
  const [chamber, setChamber] = useState<Chamber>('house');
  const seats = chamber === 'house' ? houseSeats : senateSeats;

  // Group by domain, not by runs of adjacent rows. Bills arrive in CES variable order, which
  // interleaves domains — a student-loan item sits inside the immigration battery — so comparing
  // against the previous row alone printed "Immigration" three times and duplicated React keys.
  const groups = useMemo(() => {
    const byDomain = new Map<string, CandidateVoteRow[]>();
    for (const b of candidateVotes) {
      const rows = byDomain.get(b.domain);
      if (rows) rows.push(b);
      else byDomain.set(b.domain, [b]);
    }
    return [...byDomain].map(([domain, rows]) => ({ domain, rows }));
  }, [candidateVotes]);

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <ToggleGroup label="Chamber" value={chamber} onChange={setChamber}
          options={['house', 'senate'] as const} labels={{ house: 'House', senate: 'Senate' }} />
        {/* party color key */}
        <div className="flex flex-wrap gap-x-2.5 gap-y-1">
          {F5_ORDER.map((p) => (
            <span key={p} className="flex items-center gap-1 text-[10px] font-semibold" style={{ color: getPartyColor(p) }}>
              <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: getPartyColor(p) }} />{p}
            </span>
          ))}
        </div>
      </div>

      <div className="hidden md:grid grid-cols-[minmax(140px,1.3fr)_2fr] gap-3 px-0 pb-1 text-[10px] text-muted-foreground uppercase tracking-widest">
        <div>Bill</div>
        {/* Swatches rather than words: the two marks are a ring and a line, and naming them was
            how the header came to claim a diamond and a dashed rule that were never drawn. */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span>{voteModel === 'whipped' ? 'Parties by support' : 'Votes by party'} · seat-weighted</span>
          <span className="flex items-center gap-1.5 normal-case tracking-normal">
            <span className="w-4 h-3.5 rounded-sm bg-muted-foreground/30"
              style={{ boxShadow: 'inset 0 0 0 1.5px #fff, inset 0 0 0 3px rgba(15,23,42,0.85)' }} />
            pivotal
          </span>
          <span className="flex items-center gap-1.5 normal-case tracking-normal">
            <span className="relative w-4 h-3.5">
              <span className="absolute inset-y-0 left-1/2 -ml-px" style={{
                width: 2, backgroundColor: '#0f172a', boxShadow: '0 0 0 1.5px rgba(255,255,255,0.9)',
              }} />
            </span>
            majority
          </span>
        </div>
      </div>

      {groups.map((g) => (
        <div key={g.domain}>
          <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/80 mt-3 mb-0.5">{g.domain}</div>
          {g.rows.map((bill) => (
            <CoalitionRow key={bill.variable} bill={bill} seats={seats} mode={voteModel} />
          ))}
        </div>
      ))}

      <p className="text-[11px] text-muted-foreground mt-3">
        <span className="text-emerald-600 font-bold">✓</span>/<span className="text-rose-500 font-bold">✗</span> marks
        whether the bill's supporters hold a seat majority. On a pass, the pivotal party (white/dark ring) is the one
        whose seats tip the coalition over the line; a defeat has no pivotal party.{' '}
        {voteModel === 'whipped'
          ? 'Each party votes as a bloc — all its seats go to the side its majority favors (faded = opposes).'
          : 'Each party’s seats split by its yes-probability, so a divided party appears on both sides — solid = its yes votes, faded = its no votes.'}
      </p>
    </div>
  );
}
