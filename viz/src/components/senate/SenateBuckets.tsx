import { useState } from 'react';
import { PARTY_COLORS, PARTY_NAMES, getContrastText } from '../../constants/parties';
import { Button } from '@/components/ui/button';

interface Source { party: string; pct: number }
interface Finalist { code: string; party: string; firstChoice: number; sources: Source[]; total: number }
interface StateData { fips: string; abbr: string; condWinner: string; irvWinner: string; finalists: Finalist[] }
interface Average { party: string; seats: number; avgFirstChoice: number; avgSources: Source[]; avgTotal: number }
interface BucketData { states: Record<string, StateData>; averages: Average[] }

interface Props {
  data: BucketData;
  method: 'condorcet' | 'irv';
}

interface TooltipInfo { x: number; y: number; lines: string[] }

function CandidatePill({ code, party, dimmed }: { code: string; party: string; dimmed?: boolean }) {
  const color = PARTY_COLORS[party] ?? '#6b7280';
  return (
    <span
      className="inline-flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded leading-none shrink-0 chip-text"
      style={{ backgroundColor: color, color: getContrastText(color), opacity: dimmed ? 0.4 : 1 }}
    >
      {code}
    </span>
  );
}

export default function SenateBuckets({ data, method }: Props) {
  const [selectedState, setSelectedState] = useState<string | null>(null);
  const [tip, setTip] = useState<TooltipInfo | null>(null);

  const stateList = Object.values(data.states).sort((a, b) => a.abbr.localeCompare(b.abbr));
  const selectedData = selectedState ? data.states[selectedState] : null;

  return (
    <div className="space-y-4">
      {/* State selector */}
      <div className="flex items-center gap-2 flex-wrap">
        <Button
          onClick={() => setSelectedState(null)}
          variant={!selectedState ? 'default' : 'secondary'}
          size="sm"
        >
          National Average
        </Button>
        <select
          value={selectedState ?? ''}
          onChange={e => setSelectedState(e.target.value || null)}
          className="text-xs border border-border rounded px-2 py-1 text-muted-foreground"
        >
          <option value="">Select a state…</option>
          {stateList.map(st => (
            <option key={st.fips} value={st.fips}>{st.abbr}</option>
          ))}
        </select>
      </div>

      {/* National averages — 100% stacked */}
      {!selectedState && (
        <div className="space-y-1.5">
          <div className="text-[10px] text-muted-foreground mb-2">
            Average vote composition for each winning party&apos;s senators ({method === 'condorcet' ? 'Condorcet' : 'IRV'})
          </div>
          {data.averages.map(a => {
            const color = PARTY_COLORS[a.party] ?? '#6b7280';
            const totalInput = a.avgFirstChoice + a.avgSources.reduce((s, src) => s + src.pct, 0);

            return (
              <div key={a.party} className="flex items-center gap-2">
                <div className="w-20 shrink-0 text-right flex items-center justify-end gap-1">
                  <CandidatePill code={a.party} party={a.party} />
                  <span className="text-[9px] text-muted-foreground">{a.seats}s</span>
                </div>
                <div
                  className="flex-1 h-6 cursor-pointer"
                  onMouseMove={e => setTip({
                    x: e.clientX, y: e.clientY,
                    lines: [
                      `${PARTY_NAMES[a.party] ?? a.party} — ${a.seats} seats (avg)`,
                      `First-choice: ${a.avgFirstChoice.toFixed(1)}%`,
                      ...a.avgSources.map(s => `← ${s.party}: ${s.pct.toFixed(1)}%`),
                    ],
                  })}
                  onMouseLeave={() => setTip(null)}
                >
                  <div className="flex h-full rounded-sm overflow-hidden">
                    {a.avgFirstChoice > 0 && (() => {
                      const w = (a.avgFirstChoice / totalInput) * 100;
                      return (
                        <div className="h-full flex items-center justify-center overflow-hidden" style={{
                          width: `${w}%`, backgroundColor: color, opacity: 0.85,
                        }}>
                          {w > 12 && (
                            <span className="text-[8px] font-bold truncate px-0.5 chip-text"
                              style={{ color: getContrastText(color), textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}>
                              First-choice {a.avgFirstChoice.toFixed(1)}%
                            </span>
                          )}
                        </div>
                      );
                    })()}
                    {a.avgSources.map((s, i) => {
                      const w = (s.pct / totalInput) * 100;
                      return (
                        <div key={i} className="h-full flex items-center justify-center overflow-hidden" style={{
                          width: `${w}%`,
                          backgroundColor: PARTY_COLORS[s.party] ?? '#6b7280',
                          opacity: 0.65,
                          borderLeft: '0.5px solid rgba(255,255,255,0.5)',
                        }}>
                          {w > 8 && (
                            <span className="text-[8px] font-bold truncate px-0.5 chip-text"
                              style={{ color: getContrastText(PARTY_COLORS[s.party] ?? '#6b7280'), textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}>
                              ← {s.party} {s.pct.toFixed(1)}%
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* State drill-down — winner + eliminated */}
      {selectedData && (() => {
        const winnerCode = method === 'condorcet' ? selectedData.condWinner : selectedData.irvWinner;
        const winner = selectedData.finalists.find(f => f.code === winnerCode);
        const eliminated = selectedData.finalists
          .filter(f => f.code !== winnerCode)
          .sort((a, b) => a.firstChoice - b.firstChoice); // weakest first (elimination order)

        if (!winner) return null;

        const winnerColor = PARTY_COLORS[winner.party] ?? '#6b7280';
        const totalInput = winner.firstChoice + winner.sources.reduce((s, src) => s + src.pct, 0);

        return (
          <div className="space-y-4">
            {/* Winner */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <CandidatePill code={winner.code} party={winner.party} />
                <span className="text-xs font-semibold text-emerald-600">
                  {method === 'condorcet' ? 'Condorcet' : 'IRV'} winner — {selectedData.abbr}
                </span>
              </div>
              <div className="text-[10px] text-muted-foreground mb-1">
                {winner.firstChoice.toFixed(1)}% first-choice
                {winner.sources.length > 0 && ` + ${(totalInput - winner.firstChoice).toFixed(1)}% from transfers`}
              </div>
              <div
                className="h-7 cursor-pointer"
                onMouseMove={e => setTip({
                  x: e.clientX, y: e.clientY,
                  lines: [
                    `${winner.code} — ${PARTY_NAMES[winner.party] ?? winner.party} ★ WINNER`,
                    `First-choice: ${winner.firstChoice.toFixed(1)}%`,
                    ...winner.sources.map(s => `← ${s.party}: ${s.pct.toFixed(1)}%`),
                  ],
                })}
                onMouseLeave={() => setTip(null)}
              >
                <div className="flex h-full rounded-sm overflow-hidden">
                  {winner.firstChoice > 0 && (() => {
                    const w = (winner.firstChoice / totalInput) * 100;
                    return (
                      <div className="h-full flex items-center justify-center overflow-hidden" style={{
                        width: `${w}%`, backgroundColor: winnerColor, opacity: 0.85,
                      }}>
                        {w > 12 && (
                          <span className="text-[8px] font-bold truncate px-0.5 chip-text"
                            style={{ color: getContrastText(winnerColor), textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}>
                            First-choice {winner.firstChoice.toFixed(1)}%
                          </span>
                        )}
                      </div>
                    );
                  })()}
                  {winner.sources.map((s, i) => {
                    const w = (s.pct / totalInput) * 100;
                    return (
                      <div key={i} className="h-full flex items-center justify-center overflow-hidden" style={{
                        width: `${w}%`,
                        backgroundColor: PARTY_COLORS[s.party] ?? '#6b7280',
                        opacity: 0.65,
                        borderLeft: '0.5px solid rgba(255,255,255,0.5)',
                      }}>
                        {w > 8 && (
                          <span className="text-[8px] font-bold truncate px-0.5 chip-text"
                            style={{ color: getContrastText(PARTY_COLORS[s.party] ?? '#6b7280'), textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}>
                            ← {s.party} {s.pct.toFixed(1)}%
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Eliminated */}
            <div>
              <div className="text-[10px] font-bold text-red-400 uppercase tracking-widest mb-1">
                Eliminated
              </div>
              <div className="text-[10px] text-muted-foreground mb-2">
                Eliminated during IRV in approximate order (lowest first-choice share first)
              </div>
              <div className="space-y-1">
                {eliminated.map(f => (
                  <div key={f.code} className="flex items-center gap-2">
                    <CandidatePill code={f.code} party={f.party} dimmed />
                    <span className="text-[10px] text-muted-foreground">
                      {f.firstChoice.toFixed(1)}% first-choice
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        );
      })()}

      {/* Tooltip */}
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
