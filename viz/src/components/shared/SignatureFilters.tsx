import type { SignatureFilterState } from '../../hooks/useSignatureFilter';

/**
 * Three annotation axes shared by Compare Policies and Party Platforms: Consensus (a left
 * cohesion dot), Deviant (a right "D"), and Mainstream (a right "M"). These annotate rows
 * rather than hiding them. `accent` tints the inputs.
 */
export function SignatureFilters({ s, accent }: { s: SignatureFilterState; accent: string }) {
  return (
    <div className="grid sm:grid-cols-3 gap-5 items-end">
      <div style={{ opacity: s.useConsensus ? 1 : 0.45 }}>
        <label className="flex items-center gap-2 text-xs mb-1 cursor-pointer">
          <input type="checkbox" checked={s.useConsensus} onChange={e => s.setUseConsensus(e.target.checked)}
            style={{ accentColor: accent }} />
          <span className="font-semibold text-foreground">● Consensus</span>
          <span className="text-muted-foreground">— tightly held</span>
          <span className="font-mono font-semibold ml-auto" style={{ color: accent }}>≥{s.consPct}%</span>
        </label>
        <input type="range" min={50} max={100} step={5} value={s.consPct} disabled={!s.useConsensus}
          onChange={e => s.setConsPct(Number(e.target.value))} className="w-full" style={{ accentColor: accent }} />
      </div>
      <div style={{ opacity: s.useDeviant ? 1 : 0.45 }}>
        <label className="flex items-center gap-2 text-xs mb-1 cursor-pointer">
          <input type="checkbox" checked={s.useDeviant} onChange={e => s.setUseDeviant(e.target.checked)}
            style={{ accentColor: accent }} />
          <span className="font-semibold text-foreground">D Deviant</span>
          <span className="text-muted-foreground">— far from U.S.</span>
          <span className="font-mono font-semibold ml-auto" style={{ color: accent }}>≥{s.deviantPp} pts</span>
        </label>
        <input type="range" min={0} max={50} step={5} value={s.deviantPp} disabled={!s.useDeviant}
          onChange={e => s.setDeviantPp(Number(e.target.value))} className="w-full" style={{ accentColor: accent }} />
      </div>
      <div style={{ opacity: s.useMainstream ? 1 : 0.45 }}>
        <label className="flex items-center gap-2 text-xs mb-1 cursor-pointer">
          <input type="checkbox" checked={s.useMainstream} onChange={e => s.setUseMainstream(e.target.checked)}
            style={{ accentColor: accent }} />
          <span className="font-semibold text-foreground">M Mainstream</span>
          <span className="text-muted-foreground">— close to U.S.</span>
          <span className="font-mono font-semibold ml-auto" style={{ color: accent }}>≤{s.mainstreamPp} pts</span>
        </label>
        <input type="range" min={0} max={50} step={5} value={s.mainstreamPp} disabled={!s.useMainstream}
          onChange={e => s.setMainstreamPp(Number(e.target.value))} className="w-full" style={{ accentColor: accent }} />
      </div>
    </div>
  );
}
