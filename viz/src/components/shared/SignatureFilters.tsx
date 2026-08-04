import type { SignatureFilterState } from '../../hooks/useSignatureFilter';

/**
 * The three signature axes. Each mark (C cohesive, D deviant, M mainstream) always shows,
 * driven by its slider; the per-axis "filter" checkbox trims the list to rows matching that
 * axis (checking several narrows to rows matching all). Slim inline strip for the sticky header.
 */
export function SignatureFilters({ s, accent }: { s: SignatureFilterState; accent: string }) {
  const axis = (label: string, cmp: string, val: number, min: number, max: number,
    set: (n: number) => void, filterOn: boolean, setFilter: (b: boolean) => void) => (
    <div className="flex items-center gap-1.5 shrink-0">
      <span className="font-semibold text-foreground whitespace-nowrap">{label}</span>
      <input type="range" min={min} max={max} step={5} value={val}
        onChange={e => set(Number(e.target.value))} className="w-16" style={{ accentColor: accent }} />
      <span className="font-mono font-semibold tabular-nums w-9" style={{ color: accent }}>{cmp}{val}{max === 100 ? '%' : ''}</span>
      <label className="flex items-center gap-0.5 cursor-pointer text-muted-foreground" title={`Filter to ${label} rows`}>
        <input type="checkbox" checked={filterOn} onChange={e => setFilter(e.target.checked)} style={{ accentColor: accent }} />
        filter
      </label>
    </div>
  );
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-2xs">
      {axis('C Cohesion', '≥', s.consPct, 50, 100, s.setConsPct, s.filterCohesion, s.setFilterCohesion)}
      {axis('D Deviance', '≥', s.deviantPp, 0, 50, s.setDeviantPp, s.filterDeviant, s.setFilterDeviant)}
      {axis('M Mainstream', '≤', s.mainstreamPp, 0, 50, s.setMainstreamPp, s.filterMainstream, s.setFilterMainstream)}
    </div>
  );
}
