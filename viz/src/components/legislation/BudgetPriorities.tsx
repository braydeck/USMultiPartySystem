import { useMemo } from 'react';
import type { CandidateVoteRow } from '../../types';
import { F5_ORDER, PARTY_NAMES, getPartyColor } from '../../constants/parties';
import type { VoteMode } from '../../constants/labels';
import { bamForFrac } from '../../lib/bam';
import { blocOutcome, passProbability, type SeatMap } from './voteBloc';
import { CoalitionMap } from './CoalitionMap';
import { getBayesianLabel, VerdictBadge, WhippedBadge } from './UnifiedBillTable';
import { FOOTNOTE, MINOR_HEADING, TABLE_HEADER } from '../../constants/typography';

// The CES state-spending battery (CC24_443_1..5; pipeline/build_budget_priorities.py). Each row's
// observedPct is the share wanting more spending in that category. Split into two readings:
//   level  each party's mean share across the five categories, against the national mean
//   mix    each category minus the party's own mean, so a party that wants less of everything
//          still shows which category it ranks highest
// then the five items through the same chamber views as the bills.

export type BudgetRow = CandidateVoteRow & { category: string; overallPct: number };

const MIX_CLAMP = 40;

export function BudgetPriorities({ rows, houseSeats, senateSeats, voteModel }: {
  rows: BudgetRow[];
  houseSeats: SeatMap;
  senateSeats: SeatMap;
  voteModel: VoteMode;
}) {
  const { level, national, order } = useMemo(() => {
    const level: Record<string, number> = {};
    for (const p of F5_ORDER) level[p] = rows.reduce((s, r) => s + (r.parties[p]?.observedPct ?? 0), 0) / rows.length;
    const national = rows.reduce((s, r) => s + r.overallPct, 0) / rows.length;
    const order = [...F5_ORDER].sort((a, b) => level[b] - level[a]);
    return { level, national, order };
  }, [rows]);

  const whipped = voteModel === 'whipped';
  const COLS = `40px repeat(${rows.length}, minmax(0, 1fr))`;

  return (
    <div className="space-y-6">
      <div>
        <h5 className={`${MINOR_HEADING} mb-1`}>Level: how much more spending</h5>
        <p className={`${FOOTNOTE} mb-2`}>Each party's average share wanting more spending across the five categories. National average {Math.round(national)}%.</p>
        <div className="space-y-1">
          {order.map((p) => (
            <div key={p} className="grid grid-cols-[44px_1fr_36px] items-center gap-2">
              <span className="text-3xs font-bold text-right" style={{ color: getPartyColor(p) }} title={PARTY_NAMES[p] ?? p}>{p}</span>
              <div className="relative h-4 rounded bg-muted/40">
                <div className="absolute inset-y-0 left-0 rounded" style={{ width: `${level[p]}%`, backgroundColor: getPartyColor(p), opacity: 0.85 }} />
                <div className="absolute -inset-y-0.5 w-0.5 bg-foreground/80" style={{ left: `${national}%` }} title={`National average ${Math.round(national)}%`} />
              </div>
              <span className="text-2xs tabular-nums">{Math.round(level[p])}%</span>
            </div>
          ))}
        </div>
        <p className={`${FOOTNOTE} mt-1.5 flex items-center gap-1.5`}>
          <span className="inline-block w-0.5 h-3 bg-foreground/80" /> national average
        </p>
      </div>

      <div>
        <h5 className={`${MINOR_HEADING} mb-1`}>Mix: which categories each party ranks highest</h5>
        <p className={`${FOOTNOTE} mb-2`}>Each category's share minus that party's own average, in points. Teal: above the party's average. Magenta: below it.</p>
        <div className="overflow-x-auto">
          <div>
            <div className={`grid gap-px items-end mb-px ${TABLE_HEADER}`} style={{ gridTemplateColumns: COLS }}>
              <span />
              {rows.map((r) => <span key={r.variable} className="text-center normal-case tracking-normal leading-tight px-0.5 text-4xs sm:text-3xs hyphens-auto">{r.category}</span>)}
            </div>
            {order.map((p) => (
              <div key={p} className="grid gap-px items-center mb-px" style={{ gridTemplateColumns: COLS }}>
                <span className="text-3xs font-bold text-right pr-1.5" style={{ color: getPartyColor(p) }} title={PARTY_NAMES[p] ?? p}>{p}</span>
                {rows.map((r) => {
                  const v = r.parties[p]?.observedPct ?? 0;
                  const d = v - level[p];
                  const bg = bamForFrac(0.5 + Math.max(-MIX_CLAMP, Math.min(MIX_CLAMP, d)) / (2 * MIX_CLAMP));
                  const dark = Math.abs(d) > MIX_CLAMP * 0.55;
                  return (
                    <span key={r.variable} className="h-8 rounded-[2px] flex items-center justify-center text-3xs font-semibold tabular-nums"
                      style={{ backgroundColor: bg, color: dark ? '#fff' : '#0f172a' }}
                      title={`${PARTY_NAMES[p] ?? p}, ${r.category}: ${Math.round(v)}% want more (party average ${Math.round(level[p])}%)`}>
                      {d > 0 ? '+' : d < 0 ? '−' : ''}{Math.abs(Math.round(d))}
                    </span>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div>
        <h5 className={`${MINOR_HEADING} mb-1`}>Chamber outcome by category</h5>
        <p className={`${FOOTNOTE} mb-2`}>
          {whipped
            ? 'Whipped: each party casts every seat for the side its majority favors.'
            : 'Free vote: the chance more than half the chamber backs more spending, each member voting at their party’s observed support.'}
        </p>
        <div className="overflow-x-auto mb-4">
          <table className="w-full text-xs">
            <thead>
              <tr className={TABLE_HEADER}>
                <th className="text-left font-normal py-1">Category</th>
                <th className="text-right font-normal py-1 pl-2">Nationally</th>
                <th className="text-right font-normal py-1 pl-2">House</th>
                <th className="text-right font-normal py-1 pl-2">Senate</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const cell = (seats: SeatMap) => {
                  if (whipped) return <WhippedBadge pass={blocOutcome(r, seats).pass} kind="pass" />;
                  const p = passProbability(r, seats);
                  return (
                    <span className="inline-flex items-center gap-1.5 justify-end">
                      <span className="tabular-nums">{p == null ? '–' : `${Math.round(p * 100)}%`}</span>
                      <span className="hidden sm:inline"><VerdictBadge label={getBayesianLabel([p])} /></span>
                    </span>
                  );
                };
                return (
                  <tr key={r.variable} className="border-t border-border/40">
                    <td className="py-1.5">{r.category}</td>
                    <td className="py-1.5 text-right tabular-nums">{Math.round(r.overallPct)}%</td>
                    <td className="py-1.5 text-right">{cell(houseSeats)}</td>
                    <td className="py-1.5 text-right">{cell(senateSeats)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <CoalitionMap candidateVotes={rows} houseSeats={houseSeats} senateSeats={senateSeats} voteModel={voteModel} />
      </div>
    </div>
  );
}
