import { useMemo } from 'react';
import type { CondorcetMatchup } from '../../types';
import { getBlendColor, buildDisplayLabels } from '../../constants/parties';

interface Props {
  matchups: CondorcetMatchup[];
  condorcetWinner: string;
  scale?: number;
}

export function CondorcetMatrix({ matchups, condorcetWinner, scale = 1 }: Props) {
  // Collect all candidates
  const candidateSet = new Set<string>();
  for (const m of matchups) {
    candidateSet.add(m.candidateA);
    candidateSet.add(m.candidateB);
  }
  const candidates = Array.from(candidateSet);
  const labels = useMemo(() => buildDisplayLabels(candidateSet), [matchups]); // eslint-disable-line react-hooks/exhaustive-deps
  const label = (code: string) => labels[code] ?? code;

  // Build win/loss lookup: winsMap[row][col] = { aWinsPct, margin, winner }
  const winsMap: Record<string, Record<string, { aWinsPct: number; margin: number; winner: string }>> = {};
  for (const m of matchups) {
    if (!winsMap[m.candidateA]) winsMap[m.candidateA] = {};
    if (!winsMap[m.candidateB]) winsMap[m.candidateB] = {};
    winsMap[m.candidateA][m.candidateB] = { aWinsPct: m.aWinsPct, margin: m.margin, winner: m.winner };
    winsMap[m.candidateB][m.candidateA] = { aWinsPct: 1 - m.aWinsPct, margin: -m.margin, winner: m.winner };
  }

  // Sort: Condorcet winner first, then by number of wins
  const winCount = (code: string) =>
    candidates.filter(other => other !== code && winsMap[code]?.[other]?.winner === code).length;

  const sorted = [...candidates].sort((a, b) => {
    if (a === condorcetWinner) return -1;
    if (b === condorcetWinner) return 1;
    return winCount(b) - winCount(a);
  });

  const baseCellSize = Math.min(52, Math.floor(480 / (sorted.length + 1)));
  const cellSize = Math.round(baseCellSize * scale);
  const labelW = Math.round(56 * scale);
  const labelFontSize = Math.round(10 * scale);
  const cellFontSize = Math.round(8 * scale);
  const totalW = labelW + sorted.length * cellSize;

  return (
    <div style={{ overflowX: 'auto' }} aria-label="Condorcet pairwise matchup matrix" role="img">
      <div style={{ minWidth: totalW, position: 'relative' }}>
        {/* Column headers */}
        <div className="flex" style={{ paddingLeft: labelW }}>
          {sorted.map(col => {
            const color = getBlendColor(col);
            return (
              <div
                key={col}
                style={{ width: cellSize, flexShrink: 0 }}
                className="flex items-end justify-center pb-1"
              >
                <span
                  className="font-bold font-mono"
                  style={{ color, writingMode: 'vertical-rl', textOrientation: 'mixed', fontSize: labelFontSize }}
                >
                  {label(col)}
                </span>
              </div>
            );
          })}
        </div>

        {/* Rows */}
        {sorted.map(row => {
          const isWinner = row === condorcetWinner;
          const rowColor = getBlendColor(row);
          const wins = winCount(row);
          return (
            <div key={row} className="flex items-center" style={{ height: cellSize }}>
              {/* Row label */}
              <div
                style={{ width: labelW, flexShrink: 0 }}
                className="flex items-center justify-end pr-1.5 gap-1"
              >
                {isWinner && (
                  <span className="text-amber-500 text-xs">★</span>
                )}
                <span
                  className="font-bold font-mono"
                  style={{ color: rowColor, fontSize: labelFontSize }}
                >
                  {label(row)}
                </span>
                <span className="text-muted-foreground" style={{ fontSize: labelFontSize }}>{wins}W</span>
              </div>

              {/* Cells */}
              {sorted.map(col => {
                if (row === col) {
                  return (
                    <div
                      key={col}
                      style={{ width: cellSize, height: cellSize - 2, flexShrink: 0, margin: 1 }}
                      className="bg-muted rounded-sm"
                    />
                  );
                }

                const matchup = winsMap[row]?.[col];
                if (!matchup) return (
                  <div key={col} style={{ width: cellSize, height: cellSize - 2, flexShrink: 0, margin: 1 }} />
                );

                const rowWins = matchup.winner === row;
                const margin = Math.abs(matchup.margin);
                const intensity = Math.min(1, margin / 30); // saturate at 30pp

                const bg = rowWins
                  ? `rgba(34,197,94,${0.15 + intensity * 0.55})`
                  : `rgba(239,68,68,${0.15 + intensity * 0.55})`;

                return (
                  <div
                    key={col}
                    title={`${label(row)} vs ${label(col)}: ${label(rowWins ? row : col)} wins by ${margin.toFixed(1)}pp`}
                    style={{
                      width: cellSize,
                      height: cellSize - 2,
                      flexShrink: 0,
                      margin: 1,
                      backgroundColor: bg,
                      borderRadius: 3,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <span style={{ fontSize: cellFontSize, fontWeight: 600, color: rowWins ? '#15803d' : '#b91c1c' }}>
                      {rowWins ? '+' : '−'}{margin.toFixed(0)}
                    </span>
                  </div>
                );
              })}
            </div>
          );
        })}

        {/* Caption */}
        <div className="text-xs text-muted-foreground mt-2 flex gap-4">
          <span>
            <span className="inline-block w-3 h-3 rounded-sm bg-green-400 opacity-60 mr-1 align-middle" />
            Row beats column
          </span>
          <span>
            <span className="inline-block w-3 h-3 rounded-sm bg-red-400 opacity-60 mr-1 align-middle" />
            Row loses to column
          </span>
          <span className="text-amber-500">★ = Condorcet winner (all-green row)</span>
        </div>
      </div>
    </div>
  );
}
