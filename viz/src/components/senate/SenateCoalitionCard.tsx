import { useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { PARTY_COLORS, PARTY_NAMES, getContrastText } from '../../constants/parties';
import { IRVSankey } from '../presidential/IRVSankey';
import type { SenateIrvRoundsData, SenateCoalitionAverage } from '../../types';
import type { StateUncertainty } from '../../lib/uncertainty';

interface Props {
  data: SenateIrvRoundsData;
  states?: Record<string, StateUncertainty>;
}

interface TooltipInfo { x: number; y: number; lines: string[] }

// Bars sit on an absolute 0–100% axis so the 50% majority line means what it says.
const MAJORITY = 50;
// Below this width a segment's inline label is unreadable, so it moves to the legend.
const MIN_LABEL_PCT = 7;

function PartyPill({ party }: { party: string }) {
  const color = PARTY_COLORS[party] ?? '#6b7280';
  return (
    <span
      className="inline-flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded leading-none shrink-0 chip-text"
      style={{ backgroundColor: color, color: getContrastText(color) }}
    >
      {party}
    </span>
  );
}

/** One party's average winning coalition: own first-choice block, then transfer blocks
 *  coloured by the party the votes came from. Widths are shares of the whole electorate,
 *  so the bar ends where that senator's final IRV tally ended. */
function CoalitionBar({ avg, onTip }: {
  avg: SenateCoalitionAverage;
  onTip: (t: TooltipInfo | null) => void;
}) {
  const transferTotal = avg.avgSources.reduce((s, x) => s + x.pct, 0);
  const segments = [
    { key: 'own', party: avg.party, pct: avg.avgFirstChoice, own: true },
    ...avg.avgSources.map(s => ({ key: s.party, party: s.party, pct: s.pct, own: false })),
  ].filter(s => s.pct > 0);

  const tipLines = [
    `${PARTY_NAMES[avg.party] ?? avg.party} — ${avg.seats} ${avg.seats === 1 ? 'seat' : 'seats'}`,
    `Own first-choice: ${avg.avgFirstChoice.toFixed(1)}%`,
    ...avg.avgSources.map(s => `Transfers from ${s.party}: ${s.pct.toFixed(1)}%`),
    `Final tally: ${avg.avgFinal.toFixed(1)}%`,
  ];

  return (
    <div className="flex items-center gap-2">
      <div className="w-24 shrink-0 flex items-center justify-end gap-1.5">
        <PartyPill party={avg.party} />
        <span className="text-[10px] text-muted-foreground tabular-nums">
          {avg.seats}
        </span>
      </div>
      <div className="flex-1 min-w-0">
        <div
          className="relative h-6 cursor-pointer"
          onMouseMove={e => onTip({ x: e.clientX, y: e.clientY, lines: tipLines })}
          onMouseLeave={() => onTip(null)}
        >
          <div className="flex h-full">
            {segments.map(seg => {
              const segColor = PARTY_COLORS[seg.party] ?? '#6b7280';
              return (
                <div
                  key={seg.key}
                  className="h-full flex items-center justify-center overflow-hidden first:rounded-l-sm"
                  style={{
                    width: `${seg.pct}%`,
                    backgroundColor: segColor,
                    opacity: seg.own ? 1 : 0.55,
                    borderLeft: seg.own ? undefined : '1px solid rgba(255,255,255,0.6)',
                  }}
                >
                  {seg.pct >= MIN_LABEL_PCT && (
                    <span className="text-[9px] font-bold truncate px-1 chip-text"
                      style={{ color: getContrastText(segColor) }}>
                      {seg.own ? 'Own' : seg.party} {seg.pct.toFixed(1)}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
          {/* Majority line, drawn over the bar so the crossing point is unambiguous */}
          <div className="absolute inset-y-0 border-l-2 border-dashed border-foreground/45 pointer-events-none"
            style={{ left: `${MAJORITY}%` }} />
          {/* Tally sits at the bar's tip rather than in a far-right column, so the
              number stays next to the thing it measures. */}
          <div className="absolute inset-y-0 flex items-center pointer-events-none whitespace-nowrap pl-2 text-[10px] tabular-nums"
            style={{ left: `${avg.avgFinal}%` }}>
            <span className="font-semibold text-foreground">{avg.avgFinal.toFixed(1)}%</span>
            {transferTotal > 0 && (
              <span className="text-muted-foreground">
                &nbsp;· {transferTotal.toFixed(1)} transferred
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function SenateCoalitionCard({ data, states }: Props) {
  const [selectedFips, setSelectedFips] = useState<string | null>(null);
  const [tip, setTip] = useState<TooltipInfo | null>(null);

  const stateList = useMemo(
    () => Object.entries(data.states)
      .map(([fips, st]) => ({ fips, ...st }))
      .sort((a, b) => a.abbr.localeCompare(b.abbr)),
    [data],
  );
  const selected = selectedFips ? data.states[selectedFips] : null;
  const su = selectedFips ? states?.[selectedFips] : undefined;
  // In a state where the observed run names a different winner than the likely one, show a
  // representative run that produces the likely winner instead — a real coherent count,
  // labelled as an example rather than as measurement.
  const shownRounds = su?.repRounds ?? selected?.rounds;
  const shownWinner = su?.repRounds ? su.modal : selected?.winner;

  // Segments too narrow to carry their own inline label surface in a legend instead.
  const legendParties = useMemo(() => {
    const set = new Set<string>();
    for (const a of data.averages) {
      if (a.avgFirstChoice > 0 && a.avgFirstChoice < MIN_LABEL_PCT) set.add(a.party);
      for (const s of a.avgSources) if (s.pct < MIN_LABEL_PCT) set.add(s.party);
    }
    return [...set];
  }, [data]);

  // Final-round head-to-head for the selected state.
  const finalRound = shownRounds?.[shownRounds.length - 1];
  const finalStandings = useMemo(() => {
    if (!finalRound) return [];
    return [...finalRound.candidates].sort((a, b) => b.pct - a.pct);
  }, [finalRound]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        <Button onClick={() => setSelectedFips(null)}
          variant={!selectedFips ? 'default' : 'secondary'} size="sm">
          National Average
        </Button>
        <select
          value={selectedFips ?? ''}
          onChange={e => setSelectedFips(e.target.value || null)}
          className="text-xs border border-border rounded px-2 py-1 text-muted-foreground"
          aria-label="Select a state"
        >
          <option value="">Select a state…</option>
          {stateList.map(st => (
            <option key={st.fips} value={st.fips}>{st.abbr}</option>
          ))}
        </select>
      </div>

      {/* National: average winning coalition per party */}
      {!selectedFips && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <div className="w-24 shrink-0 text-right text-[9px] text-muted-foreground uppercase tracking-wider">
              Seats
            </div>
            <div className="flex-1 min-w-0 relative h-3">
              <div className="absolute text-[9px] font-semibold text-muted-foreground -translate-x-1/2 whitespace-nowrap"
                style={{ left: `${MAJORITY}%` }}>
                50% majority
              </div>
            </div>
          </div>

          <div className="space-y-1.5">
            {data.averages.map(a => (
              <CoalitionBar key={a.party} avg={a} onTip={setTip} />
            ))}
          </div>

          {/* Ticks are absolutely positioned so they land on the axis fractions they
              name — a justify-between row would drift with each label's own width. */}
          <div className="flex items-center gap-2">
            <div className="w-24 shrink-0" />
            <div className="flex-1 min-w-0 relative h-4 text-[9px] text-muted-foreground">
              {[0, 25, 50, 75, 100].map(t => (
                <span key={t}
                  className="absolute whitespace-nowrap"
                  style={{
                    left: `${t}%`,
                    transform: t === 0 ? 'none' : t === 100 ? 'translateX(-100%)' : 'translateX(-50%)',
                  }}>
                  {t}%
                </span>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-24 shrink-0" />
            <div className="flex-1 min-w-0 text-[9px] text-muted-foreground">
              Share of the state electorate
            </div>
          </div>

          {legendParties.length > 0 && (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 pt-2 border-t border-border/50">
              {legendParties.map(p => (
                <span key={p} className="flex items-center gap-1.5" title={PARTY_NAMES[p] ?? p}>
                  <span className="w-3 h-3 rounded-sm"
                    style={{ backgroundColor: PARTY_COLORS[p] ?? '#6b7280', opacity: 0.55 }} />
                  <span className="text-[10px] text-muted-foreground">{PARTY_NAMES[p] ?? p}</span>
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Per-state: the actual round-by-round flow, then the final two */}
      {selected && (
        <div className="space-y-3">
          {su?.repRounds && (
            <div className="text-[10px] text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1.5 mb-2">
              Example count producing the likely winner ({su.modal.split('_')[0]},{' '}
              {Math.round(su.pModal * 100)}% of resamples). The observed sample gives{' '}
              {su.observed.split('_')[0]} at {Math.round(su.pObserved * 100)}%. Individual
              percentages here illustrate one path rather than measuring this state.
            </div>
          )}
          <IRVSankey rounds={shownRounds!} irvWinner={shownWinner!} />

          <div className="pt-3 border-t border-border/50">
            <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest mb-2">
              Final round — {selected.abbr}
            </div>
            <div className="space-y-1">
              {finalStandings.map((c, i) => (
                <div key={c.code} className="flex items-center gap-2">
                  <PartyPill party={c.party ?? c.code.split('_')[0]} />
                  <span className="text-[11px] text-foreground tabular-nums font-semibold w-14">
                    {c.pct.toFixed(1)}%
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    {i === 0
                      ? `wins — ${(c.pct - (finalStandings[1]?.pct ?? 0)).toFixed(1)}pp ahead`
                      : i === 1 ? 'runner-up' : 'still standing'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {su?.decomp && (
            <div className="pt-3 border-t border-border/50">
              <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest mb-2">
                Across {Object.keys(su.dist).length > 0 ? 'resamples' : ''} — why this race is close
              </div>
              <div className="grid grid-cols-[auto_1fr_1fr_1fr_1fr] gap-x-3 gap-y-1 text-[10px] items-center">
                <span className="text-muted-foreground">Party</span>
                <span className="text-muted-foreground">Makes final 5</span>
                <span className="text-muted-foreground">Reaches last round</span>
                <span className="text-muted-foreground">Wins</span>
                <span className="text-muted-foreground">Wins if it gets there</span>
                {Object.entries(su.decomp)
                  .sort((a, b) => b[1].win - a[1].win)
                  .filter(([, d]) => d.slate > 0.02)
                  .map(([p, d]) => (
                    <div key={p} className="contents">
                      <PartyPill party={p} />
                      <span className="tabular-nums text-muted-foreground">{Math.round(d.slate * 100)}%</span>
                      <span className="tabular-nums text-muted-foreground">{Math.round(d.final * 100)}%</span>
                      <span className="tabular-nums text-foreground font-semibold">{Math.round(d.win * 100)}%</span>
                      <span className="tabular-nums text-muted-foreground">
                        {d.winIfFinal == null ? '—' : `${Math.round(d.winIfFinal * 100)}%`}
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      )}

      {tip && (
        <div className="fixed z-50 bg-slate-800 text-white text-xs rounded px-3 py-2 shadow-lg pointer-events-none"
          style={{ left: tip.x + 12, top: tip.y - 10, maxWidth: 280 }}>
          {tip.lines.map((l, i) => (
            <div key={i} className={i === 0 ? 'font-semibold mb-0.5' : 'text-slate-300'}>{l}</div>
          ))}
        </div>
      )}
    </div>
  );
}
