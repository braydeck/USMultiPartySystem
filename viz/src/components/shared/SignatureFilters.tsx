import type { SignatureFilterState } from '../../hooks/useSignatureFilter';

/**
 * The Consensus × Mainstream/Deviant control, shared by Compare Policies and Party
 * Platforms so the two views present the identical filter. `accent` tints the inputs.
 */
export function SignatureFilters({ s, accent }: { s: SignatureFilterState; accent: string }) {
  return (
    <div className="grid sm:grid-cols-2 gap-5 items-end">
      <div style={{ opacity: s.useConsensus ? 1 : 0.45 }}>
        <label className="flex items-center gap-2 text-xs mb-1 cursor-pointer">
          <input type="checkbox" checked={s.useConsensus} onChange={e => s.setUseConsensus(e.target.checked)}
            style={{ accentColor: accent }} />
          <span className="font-semibold text-foreground">Consensus</span>
          <span className="text-muted-foreground">— held by</span>
          <span className="font-mono font-semibold ml-auto" style={{ color: accent }}>≥{s.consPct}% or ≤{100 - s.consPct}%</span>
        </label>
        <input type="range" min={50} max={100} step={5} value={s.consPct} disabled={!s.useConsensus}
          onChange={e => s.setConsPct(Number(e.target.value))} className="w-full" style={{ accentColor: accent }} />
      </div>
      <div style={{ opacity: s.useAlign ? 1 : 0.45 }}>
        <label className="flex items-center gap-2 text-xs mb-1 cursor-pointer">
          <input type="checkbox" checked={s.useAlign} onChange={e => s.setUseAlign(e.target.checked)}
            style={{ accentColor: accent }} />
          <span className="font-semibold text-foreground">{s.alignMode === 'deviant' ? 'Deviant' : 'Mainstream'}</span>
          <span className="text-muted-foreground">— {s.alignMode === 'deviant' ? 'far from' : 'close to'} the U.S. average</span>
          <span className="font-mono font-semibold ml-auto" style={{ color: accent }}>
            {s.alignMode === 'deviant' ? '≥' : '≤'}{s.alignPp} pts
          </span>
        </label>
        <div className="flex items-center gap-2">
          <div className="flex gap-1 shrink-0">
            {(['mainstream', 'deviant'] as const).map(m => (
              <button key={m} onClick={() => s.setAlignMode(m)} disabled={!s.useAlign}
                className={`text-[10px] px-1.5 py-0.5 rounded border ${s.alignMode === m ? 'bg-secondary text-foreground font-semibold' : 'text-muted-foreground'}`}>
                {m === 'mainstream' ? '≤ mainstream' : '≥ deviant'}
              </button>
            ))}
          </div>
          <input type="range" min={0} max={50} step={5} value={s.alignPp} disabled={!s.useAlign}
            onChange={e => s.setAlignPp(Number(e.target.value))} className="flex-1" style={{ accentColor: accent }} />
        </div>
      </div>
    </div>
  );
}
