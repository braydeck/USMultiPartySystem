import { useState, useMemo } from 'react';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER_WFP as F5_ORDER } from '../../constants/parties';
import { CondorcetMatrix } from '../presidential/CondorcetMatrix';
import type { CondorcetMatchup } from '../../types';
import { Button } from '@/components/ui/button';

interface CellData { winRate: number; avgMargin: number; n: number }
interface StateMatchup { candidateA: string; candidateB: string; aWinsPct: number; margin: number; winner: string }
interface StateData { abbr: string; winner: string; matchups: StateMatchup[] }
interface SenateCondorcetData {
  parties: string[];
  matrix: Record<string, Record<string, CellData>>;
  overallWinner: string;
  states: Record<string, StateData>;
}

interface Props {
  data: SenateCondorcetData;
}

export default function SenateCondorcetView({ data }: Props) {
  const [selectedState, setSelectedState] = useState<string | null>(null);
  const [tip, setTip] = useState<{ x: number; y: number; lines: string[] } | null>(null);

  // Only show parties that appear in the matrix
  const parties = useMemo(
    () => F5_ORDER.filter(p => data.matrix[p] && Object.keys(data.matrix[p]).length > 0),
    [data],
  );

  const stateList = useMemo(
    () => Object.entries(data.states)
      .map(([fips, st]) => ({ fips, ...st }))
      .sort((a, b) => a.abbr.localeCompare(b.abbr)),
    [data],
  );

  const selectedData = selectedState ? data.states[selectedState] : null;

  // Convert state matchups to CondorcetMatchup[] for the reusable component
  const stateMatchups: CondorcetMatchup[] = useMemo(() => {
    if (!selectedData) return [];
    return selectedData.matchups.map(m => ({
      candidateA: m.candidateA,
      candidateB: m.candidateB,
      aWinsPct: m.aWinsPct,
      margin: m.margin,
      winner: m.winner,
    }));
  }, [selectedData]);

  const cellSize = 58;
  const labelW = 48;

  return (
    <div className="space-y-4">
      {/* Selector */}
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

      {/* National average matrix */}
      {!selectedState && (
        <div>
          <div className="text-[10px] text-muted-foreground mb-3">
            Win rate across all states where both parties appear as finalists. Green = row party wins more often.
            Overall Condorcet champion: <strong className="text-muted-foreground">{data.overallWinner}</strong>
          </div>
          <div className="flex justify-center" style={{ overflowX: 'auto' }}>
            <div style={{ minWidth: labelW + parties.length * cellSize }}>
              {/* Column headers */}
              <div className="flex" style={{ paddingLeft: labelW }}>
                {parties.map(col => (
                  <div key={col} style={{ width: cellSize, flexShrink: 0 }}
                    className="flex items-end justify-center pb-1">
                    <span className="font-bold font-mono"
                      style={{ color: PARTY_COLORS[col], writingMode: 'vertical-rl', fontSize: 11 }}>
                      {col}
                    </span>
                  </div>
                ))}
              </div>

              {/* Rows */}
              {parties.map(row => {
                const isWinner = row === data.overallWinner;
                const color = PARTY_COLORS[row] ?? '#6b7280';
                return (
                  <div key={row} className="flex items-center" style={{ height: cellSize }}>
                    <div style={{ width: labelW, flexShrink: 0 }}
                      className="flex items-center justify-end pr-1.5 gap-1">
                      {isWinner && <span className="text-amber-500 text-sm">★</span>}
                      <span className="font-bold font-mono" style={{ color, fontSize: 11 }}>{row}</span>
                    </div>
                    {parties.map(col => {
                      if (row === col) {
                        return <div key={col} style={{ width: cellSize, height: cellSize - 2, flexShrink: 0, margin: 1 }}
                          className="bg-muted rounded-sm" />;
                      }
                      const cell = data.matrix[row]?.[col];
                      if (!cell || cell.n === 0) {
                        return <div key={col} style={{ width: cellSize, height: cellSize - 2, flexShrink: 0, margin: 1 }}
                          className="bg-slate-50 rounded-sm flex items-center justify-center">
                          <span className="text-[8px] text-slate-300">—</span>
                        </div>;
                      }
                      const wins = cell.winRate > 0.5;
                      const intensity = Math.min(1, Math.abs(cell.winRate - 0.5) * 2.5);
                      const bg = wins
                        ? `rgba(34,197,94,${0.12 + intensity * 0.55})`
                        : `rgba(239,68,68,${0.12 + intensity * 0.55})`;

                      return (
                        <div
                          key={col}
                          style={{
                            width: cellSize, height: cellSize - 2, flexShrink: 0, margin: 1,
                            backgroundColor: bg, borderRadius: 4,
                            display: 'flex', flexDirection: 'column',
                            alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
                          }}
                          onMouseMove={e => setTip({
                            x: e.clientX, y: e.clientY,
                            lines: [
                              `${PARTY_NAMES[row] ?? row} vs ${PARTY_NAMES[col] ?? col}`,
                              `${row} wins ${Math.round(cell.winRate * 100)}% of ${cell.n} matchups`,
                              `Avg margin: ${cell.avgMargin > 0 ? '+' : ''}${cell.avgMargin.toFixed(1)}pp`,
                            ],
                          })}
                          onMouseLeave={() => setTip(null)}
                        >
                          <span style={{ fontSize: 13, fontWeight: 700, color: wins ? '#15803d' : '#b91c1c' }}>
                            {Math.round(cell.winRate * 100)}%
                          </span>
                          <span style={{ fontSize: 8, color: '#94a3b8' }}>
                            n={cell.n}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                );
              })}

              {/* Legend */}
              <div className="text-xs text-muted-foreground mt-3 flex flex-wrap gap-x-4 gap-y-1">
                <span>
                  <span className="inline-block w-3 h-3 rounded-sm bg-green-400 opacity-60 mr-1 align-middle" />
                  Row wins &gt;50%
                </span>
                <span>
                  <span className="inline-block w-3 h-3 rounded-sm bg-red-400 opacity-60 mr-1 align-middle" />
                  Row wins &lt;50%
                </span>
                <span className="text-amber-500">★ Overall Condorcet champion</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Per-state drill-down */}
      {selectedData && (
        <div>
          <div className="text-[10px] text-muted-foreground mb-3">
            {selectedData.abbr} · Condorcet winner: <strong className="text-muted-foreground">{selectedData.winner}</strong>
          </div>
          <div className="flex justify-center">
            <CondorcetMatrix
              matchups={stateMatchups}
              condorcetWinner={selectedData.winner}
              scale={1.3}
            />
          </div>
        </div>
      )}

      {/* Tooltip */}
      {tip && (
        <div className="fixed z-50 bg-slate-800 text-white text-xs rounded px-3 py-2 shadow-lg pointer-events-none"
          style={{ left: tip.x + 12, top: tip.y - 10, maxWidth: 240 }}>
          {tip.lines.map((l, i) => (
            <div key={i} className={i === 0 ? 'font-semibold mb-0.5' : 'text-slate-300'}>{l}</div>
          ))}
        </div>
      )}
    </div>
  );
}
