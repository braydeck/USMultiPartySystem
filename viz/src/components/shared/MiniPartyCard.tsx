import { getBlendColor } from '../../constants/parties';
import type { KeyPosition } from '../../types';

interface Props {
  code: string;
  seats?: number;
  votePct?: number;
  positions?: KeyPosition[];
  F5?: number;
  sortMetric?: string;
  sortValue?: number;
}

export function MiniPartyCard({ code, seats, votePct, positions }: Props) {
  const color = getBlendColor(code);
  const topPositions = positions?.slice(0, 2) ?? [];

  return (
    <div
      className="rounded-lg border bg-white overflow-hidden"
      style={{ borderColor: color + '55', borderLeftColor: color, borderLeftWidth: 3 }}
    >
      <div className="px-3 py-2">
        <div className="flex items-center justify-between mb-1">
          <span
            className="text-xs font-bold font-mono px-1.5 py-0.5 rounded"
            style={{ backgroundColor: color + '22', color }}
          >
            {code}
          </span>
          {seats !== undefined && (
            <span className="text-xs text-slate-500 font-mono">{seats}s</span>
          )}
          {votePct !== undefined && (
            <span className="text-xs font-mono" style={{ color }}>{votePct.toFixed(1)}%</span>
          )}
        </div>
        {topPositions.length > 0 && (
          <ul className="space-y-0.5">
            {topPositions.map((pos, i) => (
              <li key={i} className="text-xs text-slate-600 flex items-start gap-1 leading-tight">
                <span className="sr-only">{pos.direction === 'supports' ? 'Supports:' : 'Opposes:'}</span>
                <span
                  aria-hidden="true"
                  className="shrink-0 mt-0.5"
                  style={{ color: pos.direction === 'supports' ? '#22c55e' : '#ef4444', fontSize: 9 }}
                >
                  {pos.direction === 'supports' ? '▲' : '▼'}
                </span>
                <span className="line-clamp-2">{pos.question}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
