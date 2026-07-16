import { getBlendColor } from '../../constants/parties';

export type RowMark = { dot: boolean; mark: 'D' | 'M' | null };

// Left label for every comparison-chart row. Two signature annotations sit with the code:
// a leading "C" when this party holds the item cohesively (its own members agree), and a
// trailing D / M when it is Deviant (far from U.S.) / Mainstream (close). Both slots are
// reserved so codes stay aligned. National ("U.S.") is never annotated. The "C" matches the
// heatmap tag so cohesion reads the same everywhere.
export function PartyRowLabel({ code, signature = false, mark = null, className = 'w-11' }:
  { code: string; signature?: boolean; mark?: 'D' | 'M' | null; className?: string }) {
  const isNat = code === '__NAT__';
  const color = isNat ? '#64748b' : getBlendColor(code);
  const showC = signature && !isNat;
  const showMark = !isNat && mark != null;
  return (
    <span className={`shrink-0 flex items-center gap-0.5 font-bold tabular-nums ${className}`} style={{ color }}>
      <span className="w-2 text-[9px] leading-none shrink-0 text-center" style={{ color: showC ? color : 'transparent' }}>C</span>
      <span className="truncate min-w-0">{isNat ? 'U.S.' : code}</span>
      <span className="ml-auto pl-0.5 text-[9px] font-bold w-2 text-right"
        style={{ color: mark === 'D' ? '#1e293b' : '#94a3b8' }}>{showMark ? mark : ''}</span>
    </span>
  );
}
