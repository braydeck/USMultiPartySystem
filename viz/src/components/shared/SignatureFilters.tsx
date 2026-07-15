import type { SignatureFilterState } from '../../hooks/useSignatureFilter';

/**
 * Three annotation axes shared by Compare Policies and Party Platforms: Consensus (a left
 * cohesion dot), Deviant (a right "D"), and Mainstream (a right "M"). These annotate rows
 * rather than hiding them. Rendered as a slim inline strip so it fits the floating header.
 */
export function SignatureFilters({ s, accent }: { s: SignatureFilterState; accent: string }) {
  const axis = (on: boolean, setOn: (b: boolean) => void, label: string, cmp: string,
    val: number, min: number, max: number, set: (n: number) => void) => (
    <div className="flex items-center gap-1.5 shrink-0" style={{ opacity: on ? 1 : 0.5 }}>
      <input type="checkbox" checked={on} onChange={e => setOn(e.target.checked)} style={{ accentColor: accent }} />
      <span className="font-semibold text-foreground whitespace-nowrap">{label}</span>
      <input type="range" min={min} max={max} step={5} value={val} disabled={!on}
        onChange={e => set(Number(e.target.value))} className="w-16" style={{ accentColor: accent }} />
      <span className="font-mono font-semibold tabular-nums w-12" style={{ color: accent }}>{cmp}{val}{max === 100 ? '%' : 'pt'}</span>
    </div>
  );
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[11px]">
      {axis(s.useConsensus, s.setUseConsensus, '● Consensus', '≥', s.consPct, 50, 100, s.setConsPct)}
      {axis(s.useDeviant, s.setUseDeviant, 'D Deviant', '≥', s.deviantPp, 0, 50, s.setDeviantPp)}
      {axis(s.useMainstream, s.setUseMainstream, 'M Mainstream', '≤', s.mainstreamPp, 0, 50, s.setMainstreamPp)}
      <label className="flex items-center gap-1.5 shrink-0 cursor-pointer border-l border-border/50 pl-4">
        <input type="checkbox" checked={s.filterMarked} onChange={e => s.setFilterMarked(e.target.checked)}
          style={{ accentColor: accent }} />
        <span className="font-semibold text-foreground whitespace-nowrap">Filter to marked</span>
      </label>
    </div>
  );
}
