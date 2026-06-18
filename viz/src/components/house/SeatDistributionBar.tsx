import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, LabelList,
} from 'recharts';
import type { HouseSeat } from '../../types';
import { PARTY_COLORS, CLUSTER_TO_PARTY } from '../../constants/parties';

interface Props {
  seats: HouseSeat[];
}

export function SeatDistributionBar({ seats: rawSeats }: Props) {
  const seats = [...rawSeats].filter(s => s.national > 0).sort((a, b) => b.national - a.national);

  const partyCode = (s: HouseSeat) => CLUSTER_TO_PARTY[String(s.party)] ?? 'CUP';
  const color = (s: HouseSeat) => PARTY_COLORS[partyCode(s)] ?? '#6b7280';

  const data = seats.map(s => ({
    name: s.partyName,
    code: partyCode(s),
    URBAN: s.urban,
    SUBURBAN: s.suburban,
    RURAL: s.rural,
    total: s.national,
  }));

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="bg-white border border-border rounded px-3 py-2 text-sm text-foreground">
        <div className="font-semibold mb-1">{label}</div>
        {payload.map((p: any) => (
          <div key={p.name} className="flex justify-between gap-4">
            <span className="text-muted-foreground">{p.name}:</span>
            <span style={{ color: p.fill }}>{p.value} seats</span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <ResponsiveContainer width="100%" height={350}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 8, right: 60, bottom: 8, left: 110 }}
        barSize={18}
      >
        <XAxis
          type="number"
          tick={{ fill: '#94a3b8', fontSize: 11 }}
          axisLine={{ stroke: '#e2e8f0' }}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={108}
          tick={{ fill: '#cbd5e1', fontSize: 12 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        {(['URBAN', 'SUBURBAN', 'RURAL'] as const).map((district, i) => (
          <Bar key={district} dataKey={district} stackId="a" isAnimationActive={false}>
            {data.map((entry) => (
              <Cell
                key={entry.code + district}
                fill={color(rawSeats.find(s => CLUSTER_TO_PARTY[String(s.party)] === entry.code)!)}
                opacity={1 - i * 0.2}
              />
            ))}
            {district === 'RURAL' && (
              <LabelList
                dataKey="total"
                position="right"
                style={{ fill: '#94a3b8', fontSize: 11 }}
              />
            )}
          </Bar>
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
