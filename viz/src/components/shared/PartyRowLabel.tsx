import { getBlendColor } from '../../constants/parties';

export type RowMark = { dot: boolean; mark: 'D' | 'M' | null };

// Shared signature tag: a small boxed letter used identically in the heatmap cells and the
// distribution-chart row labels, so C (cohesion) / M (mainstream) / D (deviance) read the same
// everywhere. White backing so it stands out on cividis cells and on white rows alike.
export type SigKind = 'C' | 'M' | 'D';
const SIG_STYLE: Record<SigKind, { fg: string; bd: string }> = {
  C: { fg: '#4f46e5', bd: '#c7d2fe' },  // cohesion — indigo
  M: { fg: '#475569', bd: '#cbd5e1' },  // mainstream — slate (neutral)
  D: { fg: '#b45309', bd: '#fde68a' },  // deviance — amber (stands out, matches ◆)
};
export function SigTag({ kind }: { kind: SigKind }) {
  const s = SIG_STYLE[kind];
  return (
    <span
      className="inline-flex items-center justify-center text-[8px] font-bold leading-none rounded-[3px] border px-[3px] py-[1.5px]"
      style={{ backgroundColor: 'rgba(255,255,255,0.92)', color: s.fg, borderColor: s.bd }}
    >
      {kind}
    </span>
  );
}

// Left label for every comparison-chart row. Two signature annotations sit with the code:
// a leading "C" when this party holds the item cohesively (its own members agree), and a
// trailing D / M when it is Deviant (far from U.S.) / Mainstream (close). Both slots are
// reserved so codes stay aligned. National ("U.S.") is never annotated. The "C" matches the
// heatmap tag so cohesion reads the same everywhere.
export function PartyRowLabel({ code, signature = false, mark = null, className = 'w-[76px]' }:
  { code: string; signature?: boolean; mark?: 'D' | 'M' | null; className?: string }) {
  const isNat = code === '__NAT__';
  const color = isNat ? '#64748b' : getBlendColor(code);
  const showC = signature && !isNat;
  const showMark = !isNat && mark != null;
  return (
    <span className={`shrink-0 flex items-center gap-1 font-bold tabular-nums ${className}`} style={{ color }}>
      <span className="w-4 shrink-0 flex justify-center">{showC && <SigTag kind="C" />}</span>
      <span className="whitespace-nowrap">{isNat ? 'U.S.' : code}</span>
      <span className="ml-auto shrink-0 flex justify-center w-4">{showMark && mark && <SigTag kind={mark} />}</span>
    </span>
  );
}
