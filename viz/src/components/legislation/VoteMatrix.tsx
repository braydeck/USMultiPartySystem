import { useMemo, useState } from 'react';
import type { CandidateVoteRow, VoteModelRow, PartyVote } from '../../types';
import { F5_ORDER, PARTY_NAMES, getPartyColor, getPrimaryParty } from '../../constants/parties';
import { cividisForFrac, cividisText } from '../../lib/cividis';
import { pLaw, verdict } from '../../lib/lawChain';
import type { Pipeline, Method, WyomingRule } from '../../constants/labels';
import houseSeats from '../../data/houseSeats.json';
import { BillFloor } from './BillFloor';
import { CandidateColumn } from './CandidateColumn';

interface Props {
  candidateVotes: CandidateVoteRow[];
  houseVotes: VoteModelRow[];
  senateVotes: VoteModelRow[];
  presWinner: string;
  pipeline: Pipeline;
  method: Method;
  wyoming: WyomingRule;
}

// Seat share per party (Raw-Multi house composition) — the whip/pivotal ordering.
// Roughly stable across scenarios; used only to find the pivotal party.
const CLUSTER_TO_PARTY: Record<number, string> = {
  0: 'CON', 1: 'LBR', 2: 'STY', 3: 'NAT', 4: 'LIB', 5: 'POP', 6: 'CUP', 7: 'OAO', 8: 'DSA', 9: 'PRG',
};
const SEAT_SHARE: Record<string, number> = Object.fromEntries(
  (houseSeats as { party: number; national: number }[]).map((r) => [CLUSTER_TO_PARTY[r.party], r.national]),
);

// Per-scenario field selectors (mirror UnifiedBillTable's combo pattern).
function houseFields(pipeline: Pipeline, wyoming: WyomingRule) {
  const triple = wyoming === 'triple';
  if (pipeline === 'factorDev')
    return triple
      ? { pass: 'houseFDTripleProbPass', ovr: 'houseFDTripleProbOverride' }
      : { pass: 'houseFDProbPass', ovr: 'houseFDProbOverride' };
  return triple
    ? { pass: 'houseRawMultiTripleProbPass', ovr: 'houseRawMultiTripleProbOverride' }
    : { pass: 'houseRawMultiProbPass', ovr: 'houseRawMultiProbOverride' };
}
function senateFields(pipeline: Pipeline, method: Method) {
  const p = pipeline === 'factorDev' ? 'FD' : 'RawMulti';
  const m = method === 'irv' ? 'irv' : 'cond';
  return { pass: `${m}${p}ProbPass` as keyof VoteModelRow, ovr: `${m}${p}ProbOverride` as keyof VoteModelRow };
}

const num = (v: unknown): number => (typeof v === 'number' ? v : 0);

/** A single party's vote cell: shade = P(yes), track = within-party spread band. */
function VoteCell({ v, pivotal, dim }: { v?: PartyVote; pivotal: boolean; dim: boolean }) {
  if (!v) return <div className="h-9 rounded bg-muted/30" />;
  const bg = cividisForFrac(v.pYes);
  const fg = cividisText(bg);
  return (
    <div
      className="relative h-9 rounded flex items-center justify-center text-[11px] font-semibold tabular-nums transition-opacity"
      style={{
        backgroundColor: bg,
        color: fg,
        opacity: dim ? 0.35 : 1,
        outline: pivotal ? '2px solid #f8fafc' : 'none',
        boxShadow: pivotal ? '0 0 0 3px rgba(15,23,42,0.9)' : 'none',
      }}
      title={`P(yes) ${(v.pYes * 100).toFixed(0)}% · band ${(v.bandLo * 100).toFixed(0)}–${(v.bandHi * 100).toFixed(0)}%${
        v.diverges ? ` · diverges ${v.delta! > 0 ? '+' : ''}${v.delta}pp from observed` : ''
      }`}
    >
      {Math.round(v.pYes * 100)}
      {/* within-party spread band */}
      <div className="absolute left-1 right-1 bottom-0.5 h-[3px] rounded-full" style={{ backgroundColor: fg, opacity: 0.25 }}>
        <div
          className="absolute h-[3px] rounded-full"
          style={{ left: `${v.bandLo * 100}%`, width: `${Math.max(2, (v.bandHi - v.bandLo) * 100)}%`, backgroundColor: fg, opacity: 0.9 }}
        />
      </div>
      {v.diverges && (
        <span className="absolute top-0 right-0.5 text-[9px] leading-none" style={{ color: fg }}>⚠</span>
      )}
    </div>
  );
}

export function VoteMatrix({ candidateVotes, houseVotes, senateVotes, presWinner, pipeline, method, wyoming }: Props) {
  const [openBill, setOpenBill] = useState<string | null>(null);
  const [selParty, setSelParty] = useState<string | null>(null);

  const presParty = getPrimaryParty(presWinner);
  const hf = houseFields(pipeline, wyoming);
  const sf = senateFields(pipeline, method);
  const houseByVar = useMemo(() => Object.fromEntries(houseVotes.map((r) => [r.variable, r])), [houseVotes]);
  const senateByVar = useMemo(() => Object.fromEntries(senateVotes.map((r) => [r.variable, r])), [senateVotes]);

  // Group bills by domain, preserving order.
  const groups = useMemo(() => {
    const g: { domain: string; rows: CandidateVoteRow[] }[] = [];
    for (const r of candidateVotes) {
      const last = g[g.length - 1];
      if (last && last.domain === r.domain) last.rows.push(r);
      else g.push({ domain: r.domain, rows: [r] });
    }
    return g;
  }, [candidateVotes]);

  const lawFor = (bill: CandidateVoteRow) => {
    const h = houseByVar[bill.variable];
    const s = senateByVar[bill.variable];
    const presV = bill.parties[presParty];
    const pSign = presV ? presV.pYes : 0;
    return pLaw({
      pHouse: num(h?.[hf.pass as keyof VoteModelRow]),
      pSenate: num(s?.[sf.pass]),
      pSign,
      pOverrideHouse: num(h?.[hf.ovr as keyof VoteModelRow]),
      pOverrideSenate: num(s?.[sf.ovr]),
    });
  };

  const pivotalFor = (bill: CandidateVoteRow) => {
    const pYesMap = Object.fromEntries(F5_ORDER.map((p) => [p, bill.parties[p]?.pYes ?? 0]));
    // inline to avoid importing when SEAT_SHARE keys differ
    const parties = F5_ORDER.filter((p) => (SEAT_SHARE[p] ?? 0) > 0);
    const total = parties.reduce((n, p) => n + (SEAT_SHARE[p] ?? 0), 0);
    const maj = total / 2;
    const ordered = [...parties].sort((a, b) => pYesMap[b] - pYesMap[a]);
    let cum = 0;
    for (const p of ordered) {
      cum += SEAT_SHARE[p] ?? 0;
      if (cum >= maj) return p;
    }
    return null;
  };

  const COLS = `grid-cols-[minmax(180px,1.6fr)_repeat(10,minmax(30px,1fr))_64px_72px]`;

  return (
    <div className="space-y-3">
      {/* Legend */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="inline-flex">
            {[0, 0.25, 0.5, 0.75, 1].map((t) => (
              <span key={t} className="w-4 h-3 first:rounded-l last:rounded-r" style={{ backgroundColor: cividisForFrac(t) }} />
            ))}
          </span>
          shade = P(candidate votes yes)
        </span>
        <span className="flex items-center gap-1.5"><span className="w-6 h-[3px] rounded-full bg-foreground/70" /> band = within-party spread</span>
        <span>⚠ = votes against what its ideology predicts</span>
        <span className="flex items-center gap-1.5"><span className="w-3.5 h-3.5 rounded" style={{ boxShadow: '0 0 0 2px #f8fafc, 0 0 0 4px rgba(15,23,42,0.9)' }} /> pivotal party</span>
      </div>

      <div className="overflow-x-auto">
        <div className="min-w-[900px]">
          {/* Header */}
          <div className={`grid ${COLS} gap-1 items-end pb-2 sticky top-0 z-10 bg-background`}>
            <div className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Bill</div>
            {F5_ORDER.map((p) => (
              <button
                key={p}
                onClick={() => setSelParty(selParty === p ? null : p)}
                className="flex flex-col items-center gap-0.5 group"
                title={`${PARTY_NAMES[p]} — click to inspect this party's votes`}
              >
                <span
                  className="w-full text-center text-[10px] font-bold rounded px-0.5 py-0.5"
                  style={{
                    backgroundColor: getPartyColor(p) + (selParty === p ? '' : '33'),
                    color: selParty === p ? '#fff' : getPartyColor(p),
                  }}
                >
                  {p}
                </span>
              </button>
            ))}
            <div className="text-[10px] font-semibold text-muted-foreground text-center">Pres<br />({presParty})</div>
            <div className="text-[10px] font-semibold text-muted-foreground text-center">Law</div>
          </div>

          {groups.map((g) => (
            <div key={g.domain}>
              <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/80 mt-3 mb-1 pl-1">{g.domain}</div>
              {g.rows.map((bill) => {
                const pivotal = pivotalFor(bill);
                const law = lawFor(bill);
                const presV = bill.parties[presParty];
                const pSign = presV?.pYes ?? 0;
                const lawV = verdict(law);
                const open = openBill === bill.variable;
                return (
                  <div key={bill.variable}>
                    <div
                      className={`grid ${COLS} gap-1 items-center py-0.5 cursor-pointer rounded hover:bg-muted/40 ${open ? 'bg-muted/50' : ''}`}
                      onClick={() => setOpenBill(open ? null : bill.variable)}
                    >
                      <div className="text-[11px] leading-tight pr-2 truncate" title={bill.question}>{bill.question}</div>
                      {F5_ORDER.map((p) => (
                        <VoteCell key={p} v={bill.parties[p]} pivotal={pivotal === p} dim={!!selParty && selParty !== p} />
                      ))}
                      {/* President sign/veto */}
                      <div
                        className="h-9 rounded flex items-center justify-center text-[10px] font-bold"
                        style={{ backgroundColor: pSign >= 0.5 ? '#16653420' : '#7f1d1d20', color: pSign >= 0.5 ? '#15803d' : '#b91c1c' }}
                        title={`${presParty} president, P(sign) ${(pSign * 100).toFixed(0)}%`}
                      >
                        {pSign >= 0.5 ? 'SIGN' : 'VETO'}
                      </div>
                      {/* Law verdict */}
                      <div className="h-9 rounded flex flex-col items-center justify-center bg-muted/40">
                        <span className="text-[11px] font-bold tabular-nums">{Math.round(law * 100)}%</span>
                        <span className="text-[8px] uppercase tracking-wide text-muted-foreground">{lawV}</span>
                      </div>
                    </div>
                    {open && (
                      <BillFloor
                        bill={bill}
                        houseRow={houseByVar[bill.variable]}
                        senateRow={senateByVar[bill.variable]}
                        presParty={presParty}
                        pivotal={pivotal}
                        houseField={hf}
                        senateField={sf}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {selParty && (
        <CandidateColumn party={selParty} candidateVotes={candidateVotes} onClose={() => setSelParty(null)} />
      )}
    </div>
  );
}
