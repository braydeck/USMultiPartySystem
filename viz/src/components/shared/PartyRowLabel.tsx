import { getBlendColor } from '../../constants/parties';

// Left label for every comparison-chart row: left-aligned code in the party color, with a
// leading party-colored dot ONLY when this party's value on this item is a signature match
// (same condition as the faded-bar rule). The dot slot is always reserved so codes stay
// aligned whether or not the dot shows. National ("U.S.") never gets a dot.
export function PartyRowLabel({ code, signature = false, className = 'w-11' }:
  { code: string; signature?: boolean; className?: string }) {
  const isNat = code === '__NAT__';
  const color = isNat ? '#64748b' : getBlendColor(code);
  const showDot = signature && !isNat;
  return (
    <span className={`shrink-0 flex items-center gap-1 font-bold tabular-nums ${className}`} style={{ color }}>
      <span className="w-1.5 h-1.5 rounded-full shrink-0"
        style={{ backgroundColor: showDot ? color : 'transparent' }} />
      <span className="truncate">{isNat ? 'U.S.' : code}</span>
    </span>
  );
}
