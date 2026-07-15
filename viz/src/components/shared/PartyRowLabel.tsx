import { getBlendColor } from '../../constants/parties';

// Left label for every comparison-chart row: a solid party-colored dot + the code, left-aligned.
// The dot makes the party identifiable even on charts whose bars/cells are NOT party-colored
// (composition, heatmap, frequency ramps), where colored code text alone is hard to read.
export function PartyRowLabel({ code, className = 'w-11' }: { code: string; className?: string }) {
  const isNat = code === '__NAT__';
  const color = isNat ? '#64748b' : getBlendColor(code);
  return (
    <span className={`shrink-0 flex items-center gap-1 font-bold tabular-nums ${className}`} style={{ color }}>
      <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
      <span className="truncate">{isNat ? 'U.S.' : code}</span>
    </span>
  );
}
