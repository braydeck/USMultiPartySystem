import { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, ReferenceLine, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { getBlendColor } from '../../constants/parties';
import type { IRVRound } from '../../types';

interface Props {
  rounds: IRVRound[];
  irvWinner: string;
}

export function IRVRoundsChart({ rounds, irvWinner }: Props) {
  const [selectedRound, setSelectedRound] = useState(rounds.length - 1);
  const safeSelected = Math.min(selectedRound, rounds.length - 1);
  const round = rounds[safeSelected];

  const data = [...round.candidates].sort((a, b) => b.pct - a.pct);

  return (
    <div>
      <div className="flex flex-wrap gap-2 mb-4">
        {rounds.map((r, i) => (
          <button
            key={r.round}
            onClick={() => setSelectedRound(i)}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              selectedRound === i
                ? 'bg-amber-600 text-white'
                : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
            }`}
          >
            Round {r.round}
            {i === rounds.length - 1 && (
              <span className="ml-1 text-amber-300">★</span>
            )}
          </button>
        ))}
      </div>

      <div className="mb-2 text-xs text-slate-500">
        {selectedRound < rounds.length - 1
          ? `${round.candidates.filter(c => c.eliminated).map(c => c.code).join(', ')} eliminated this round`
          : `Final: ${irvWinner} wins with ${data.find(c => c.winner)?.pct.toFixed(1)}%`}
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 40, top: 4, bottom: 4 }}>
          <XAxis type="number" domain={[0, 55]} tickFormatter={v => `${v}%`} tick={{ fontSize: 10, fill: '#94a3b8' }} />
          <YAxis type="category" dataKey="code" width={72} tick={{ fontSize: 10, fill: '#94a3b8' }} />
          <ReferenceLine x={50} stroke="#f59e0b" strokeDasharray="4 2" strokeWidth={1.5} label={{ value: '50%', position: 'right', fill: '#f59e0b', fontSize: 10 }} />
          <Tooltip
            formatter={(value) => [`${Number(value).toFixed(2)}%`, 'Vote share']}
            contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 6, fontSize: 12 }}
            labelStyle={{ color: '#0f172a' }}
          />
          <Bar dataKey="pct" radius={[0, 3, 3, 0]}>
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={entry.eliminated ? '#475569' : getBlendColor(entry.code)}
                fillOpacity={entry.eliminated ? 0.5 : 0.9}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <p className="text-xs text-slate-500 mt-2 text-center">
        Yellow line = 50% threshold. Gray bars = eliminated candidates.
      </p>
    </div>
  );
}
