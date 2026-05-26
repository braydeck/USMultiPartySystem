import { FACTOR_LABELS, FACTOR_POLES } from '../../constants/parties';

interface Props {
  factor: string;
  value: number; // -2 to +2 range
}

function barColor(v: number): string {
  if (v > 0.8) return '#ef4444';
  if (v > 0.3) return '#f97316';
  if (v > -0.3) return '#6b7280';
  if (v > -0.8) return '#3b82f6';
  return '#1d4ed8';
}

export function FactorBar({ factor, value }: Props) {
  const label = FACTOR_LABELS[factor] ?? factor;
  const pct = Math.round(((value + 2) / 4) * 100);
  const color = barColor(value);
  const poles = FACTOR_POLES[factor];

  return (
    <div className="mb-2">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-600">{label}</span>
        <span style={{ color }} className="font-mono font-semibold">
          {value >= 0 ? '+' : ''}{value.toFixed(2)}
        </span>
      </div>
      <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      {poles && (
        <div className="flex justify-between text-slate-400 mt-0.5" style={{ fontSize: 9 }}>
          <span>{poles.low}</span>
          <span>{poles.high}</span>
        </div>
      )}
    </div>
  );
}
