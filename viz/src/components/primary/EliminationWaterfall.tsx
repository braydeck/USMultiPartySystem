import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ReferenceLine,
  ResponsiveContainer, Cell,
} from 'recharts';
import type { PrimaryCandidate } from '../../types';
import { getPartyColor } from '../../constants/parties';
import { CHART_TYPE, CHART_FILL } from '../../constants/typography';

interface Props {
  candidates: PrimaryCandidate[];
  stage: string;
  quota: number;
}

export function EliminationWaterfall({ candidates, stage, quota }: Props) {
  const data = candidates
    .map(c => {
      const s = c.stages[stage];
      return {
        name: c.name,
        code: c.code,
        votePct: s?.votePct ?? 0,
        status: s?.status ?? 'previously_eliminated',
        F5: c.F5,
      };
    })
    .sort((a, b) => a.F5 - b.F5);

  return (
    <ResponsiveContainer width="100%" height={420}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 8, right: 40, bottom: 8, left: 90 }}
      >
        <XAxis
          type="number"
          domain={[0, 'auto']}
          tickFormatter={v => `${v.toFixed(1)}%`}
          tick={{ fill: CHART_FILL.tick, fontSize: CHART_TYPE.seriesLabel }}
          axisLine={{ stroke: '#e2e8f0' }}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={88}
          tick={{ fill: CHART_FILL.faint, fontSize: CHART_TYPE.cellValue }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          formatter={(v) => [`${Number(v).toFixed(2)}%`, 'Vote Share']}
          contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 6 }}
          labelStyle={{ color: '#0f172a' }}
        />
        <ReferenceLine
          x={quota}
          stroke="#fbbf24"
          strokeDasharray="4 4"
          label={{ value: 'Quota', fill: '#fbbf24', fontSize: CHART_TYPE.seriesLabel, position: 'right' }}
        />
        <Bar dataKey="votePct" radius={[0, 3, 3, 0]} isAnimationActive animationDuration={400}>
          {data.map((entry) => {
            const elim = entry.status === 'previously_eliminated';
            const elimThisRound = entry.status === 'eliminated_this_round';
            const color = elim ? '#374151' : getPartyColor(entry.code);
            return (
              <Cell
                key={entry.code}
                fill={elim ? '#374151' : color}
                stroke={elimThisRound ? '#ef4444' : 'transparent'}
                strokeWidth={elimThisRound ? 2 : 0}
                opacity={elim ? 0.5 : 1}
              />
            );
          })}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
