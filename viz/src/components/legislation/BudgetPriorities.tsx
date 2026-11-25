import { useMemo, useState } from 'react';
import type { CandidateVoteRow } from '../../types';
import { F5_ORDER, PARTY_NAMES, getPartyColor } from '../../constants/parties';
import type { VoteMode } from '../../constants/labels';
import { bamForFrac } from '../../lib/bam';
import { cividisForFrac, cividisText } from '../../lib/cividis';
import { ToggleGroup } from '../shared/ToggleGroup';
import { blocOutcome, passProbability, type SeatMap } from './voteBloc';
import { CoalitionMap } from './CoalitionMap';
import { getBayesianLabel, VerdictBadge, WhippedBadge } from './UnifiedBillTable';
import { FOOTNOTE, MINOR_HEADING, TABLE_HEADER } from '../../constants/typography';

// The CES state-spending battery (CC24_443_1..5; pipeline/build_budget_priorities.py). Each row's
// observedPct is the share wanting more spending in that category. Split into two readings:
//   level  each party's mean share across the five categories, against the national mean
//   mix    each category's share as it stands, or minus the party's own mean, so a party that
//          wants less of everything still shows which category it ranks highest
// then the five items through the same chamber views as the bills.

export type BudgetRow = CandidateVoteRow & { category: string; overallPct: number };

const MIX_CLAMP = 40;
type MixView = 'share' | 'relative';
const MIX_LABELS: Record<MixView, string> = { share: 'Share wanting more', relative: 'Relative to party average' };

export function BudgetPriorities({ rows, houseSeats, senateSeats, voteModel }: {
  rows: BudgetRow[];
  houseSeats: SeatMap;
  senateSeats: SeatMap;
  voteModel: VoteMode;
}) {
  const { level, national: natAvg, order } = useMemo(() => {
    const level: Record<string, number> = {};
    for (const p of F5_ORDER) level[p] = rows.reduce((s, r) => s + (r.parties[p]?.observedPct ?? 0), 0) / rows.length;
    const national = rows.reduce((s, r) => s + r.overallPct, 0) / rows.length;
    const order = [...F5_ORDER].sort((a, b) => level[b] - level[a]);
    return { level, national, order };
  }, [rows]);

  const [mix, setMix] = useState<MixView>('share');
  const whipped = voteModel === 'whipped';
  const COLS = `40px repeat(${rows.length}, minmax(0, 1fr))`;

  return (
    <div className="space-y-6">
      <div>
        <h5 className={`${MINOR_HEADING} mb-1`}>Level: how much more spending</h5>
        <p className={`${FOOTNOTE} mb-2`}>Each party's average share wanting more spending across the five categories. National average {Math.round(natAvg)}%.</p>
        <div className="space-y-1">
          {order.map((p) => (
            <div key={p} className="grid grid-cols-[44px_1fr_36px] items-center gap-2">
              <span className="text-3xs font-bold text-right" style={{ color: getPartyColor(p) }} title={PARTY_NAMES[p] ?? p}>{p}</span>
              <div className="relative h-4 rounded bg-muted/40">
                <div className="absolute inset-y-0 left-0 rounded" style={{ width: `${level[p]}%`, backgroundColor: getPartyColor(p), opacity: 0.85 }} />
                <div className="absolute -inset-y-0.5 w-0.5 bg-foreground/80" style={{ left: `${natAvg}%` }} title={`National average ${Math.round(natAvg)}%`} />
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
        <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
          <h5 className={MINOR_HEADING}>Priorities by category</h5>
          <ToggleGroup value={mix} onChange={setMix} options={['share', 'relative'] as const} labels={MIX_LABELS} />
        </div>
        <p className={`${FOOTNOTE} mb-2`}>
          {mix === 'share'
            ? '% of each party wanting more spending in each category.'
            : 'Each category\u2019s share minus that party\u2019s own average, in points, so a party that wants less overall still shows what it ranks highest. Teal: above its average. Magenta: below it.'}
        </p>
        <div className="overflow-x-auto">
          <div>
            <div className={`grid gap-px items-end mb-px ${TABLE_HEADER}`} style={{ gridTemplateColumns: COLS }}>
              <span />
              {rows.map((r) => <span key={r.variable} className="text-center normal-case tracking-normal leading-tight px-0.5 text-4xs sm:text-3xs hyphens-auto">{r.category}</span>)}
            </div>
            {[...order, 'National'].map((p) => {
              const national = p === 'National';
              const avg = national ? natAvg : level[p];
              return (
                <div key={p} className={`grid gap-px items-center mb-px ${national ? 'mt-1' : ''}`} style={{ gridTemplateColumns: COLS }}>
                  <span className="text-3xs font-bold text-right pr-1.5" style={{ color: national ? undefined : getPartyColor(p) }}
                    title={national ? 'All respondents' : PARTY_NAMES[p] ?? p}>{national ? 'All' : p}</span>
                  {rows.map((r) => {
                    const v = national ? r.overallPct : r.parties[p]?.observedPct ?? 0;
                    const d = v - avg;
                    let bg: string, fg: string, text: string;
                    if (mix === 'share') {
                      bg = cividisForFrac(v / 100); fg = cividisText(bg); text = `${Math.round(v)}`;
                    } else {
                      bg = bamForFrac(0.5 + Math.max(-MIX_CLAMP, Math.min(MIX_CLAMP, d)) / (2 * MIX_CLAMP));
                      fg = Math.abs(d) > MIX_CLAMP * 0.55 ? '#fff' : '#0f172a';
                      text = `${d > 0 ? '+' : d < 0 ? '\u2212' : ''}${Math.abs(Math.round(d))}`;
                    }
                    return (
                      <span key={r.variable} className="h-8 rounded-[2px] flex items-center justify-center text-3xs font-semibold tabular-nums"
                        style={{ backgroundColor: bg, color: fg }}
                        title={`${national ? 'All respondents' : PARTY_NAMES[p] ?? p}, ${r.category}: ${Math.round(v)}% want more (average across categories ${Math.round(avg)}%)`}>
                        {text}
                      </span>
                    );
                  })}
                </div>
              );
            })}
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
