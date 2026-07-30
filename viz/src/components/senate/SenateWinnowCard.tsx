import { useMemo, useState } from 'react';
import { PARTY_COLORS, PARTY_NAMES, getContrastText, buildDisplayLabels } from '../../constants/parties';
import { Button } from '@/components/ui/button';
import type { SenateWinnowData, SenateWinnowFinalist } from '../../types';

interface Props {
  data: SenateWinnowData;
}

interface TooltipInfo { x: number; y: number; lines: string[] }

// Winnow tallies sit on a Droop-quota scale, not a majority scale, so bars are drawn
// against a fixed ceiling above the quota rather than against 100%.
const AXIS_MAX = 50;
const MIN_LABEL_PCT = 4;

function PartyPill({ party, label }: { party: string; label?: string }) {
  const color = PARTY_COLORS[party] ?? '#6b7280';
  return (
    <span
      className="inline-flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded leading-none shrink-0 chip-text"
      style={{ backgroundColor: color, color: getContrastText(color) }}
    >
      {label ?? party}
    </span>
  );
}

/** A finalist's winnow tally: own first-choice votes plus transfers received while the
 *  field was cut to five, drawn against a shared axis with the quota marked. */
function WinnowBar({ party, label, sublabel, firstChoice, sources, total, quotaPct, onTip, tipTitle }: {
  party: string;
  label?: string;
  sublabel?: string;
  firstChoice: number;
  sources: { party: string; pct: number }[];
  total: number;
  quotaPct: number;
  onTip: (t: TooltipInfo | null) => void;
  tipTitle: string;
}) {
  const segments = [
    { key: '__own', party, pct: firstChoice, own: true },
    ...sources.map(s => ({ key: s.party, party: s.party, pct: s.pct, own: false })),
  ].filter(s => s.pct > 0);

  const tipLines = [
    tipTitle,
    `First-choice: ${firstChoice.toFixed(1)}%`,
    ...sources.map(s => `Transfers from ${s.party}: ${s.pct.toFixed(1)}%`),
    `Total at winnow: ${total.toFixed(1)}% (quota ${quotaPct.toFixed(1)}%)`,
  ];

  return (
    <div className="flex items-center gap-2">
      <div className="w-24 shrink-0 flex items-center justify-end gap-1.5">
        <PartyPill party={party} label={label} />
        {sublabel && <span className="text-[10px] text-muted-foreground tabular-nums">{sublabel}</span>}
      </div>
      <div className="flex-1 min-w-0">
        <div
          className="relative h-6 cursor-pointer"
          onMouseMove={e => onTip({ x: e.clientX, y: e.clientY, lines: tipLines })}
          onMouseLeave={() => onTip(null)}
        >
          <div className="flex h-full">
            {segments.map(seg => {
              const segColor = PARTY_COLORS[seg.party] ?? '#6b7280';
              const w = (seg.pct / AXIS_MAX) * 100;
              return (
                <div key={seg.key}
                  className="h-full flex items-center justify-center overflow-hidden first:rounded-l-sm"
                  style={{
                    width: `${w}%`,
                    backgroundColor: segColor,
                    opacity: seg.own ? 1 : 0.55,
                    borderLeft: seg.own ? undefined : '1px solid rgba(255,255,255,0.6)',
                  }}>
                  {seg.pct >= MIN_LABEL_PCT && (
                    <span className="text-[9px] font-bold truncate px-1 chip-text"
                      style={{ color: getContrastText(segColor) }}>
                      {seg.own ? 'Own' : seg.party} {seg.pct.toFixed(1)}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
          <div className="absolute inset-y-0 border-l-2 border-dashed border-foreground/45 pointer-events-none"
            style={{ left: `${(quotaPct / AXIS_MAX) * 100}%` }} />
          {/* Total sits at the bar's tip, matching the coalition card. */}
          <div className="absolute inset-y-0 flex items-center pointer-events-none whitespace-nowrap pl-2 text-[10px] font-semibold text-foreground tabular-nums"
            style={{ left: `${(total / AXIS_MAX) * 100}%` }}>
            {total.toFixed(1)}%
          </div>
        </div>
      </div>
    </div>
  );
}

export function SenateWinnowCard({ data }: Props) {
  const [selectedFips, setSelectedFips] = useState<string | null>(null);
  const [tip, setTip] = useState<TooltipInfo | null>(null);

  const stateList = useMemo(
    () => Object.values(data.states).sort((a, b) => a.abbr.localeCompare(b.abbr)),
    [data],
  );
  const selected = selectedFips ? data.states[selectedFips] : null;
  const quota = data.quotaPct;

  // The winnow always fills five slots, so some finalists advance without ever
  // clearing the quota — splitting them says which is which.
  const split = useMemo(() => {
    const empty: SenateWinnowFinalist[] = [];
    if (!selected) return { above: empty, below: empty };
    const sorted = [...selected.finalists].sort((a, b) => b.total - a.total);
    return {
      above: sorted.filter(f => f.total >= quota),
      below: sorted.filter(f => f.total < quota),
    };
  }, [selected, quota]);

  // Two candidates from one party can both be finalists, so pills carry the display
  // code (CON_1 / CON_2) when a party fields more than one, and the plain party
  // otherwise — the same rule the vote-flow chart uses.
  const finalistLabels = useMemo(
    () => selected ? buildDisplayLabels(selected.finalists.map(f => f.code)) : {},
    [selected],
  );

  const axisTicks = [0, quota, AXIS_MAX];

  // Transfer slivers are often too narrow to carry their own label, so the source
  // parties are named in a legend rather than left to the tooltip.
  const legendParties = useMemo(() => {
    const set = new Set<string>();
    const rows = selected
      ? selected.finalists.map(f => ({ own: f.firstChoice, srcs: f.sources }))
      : data.averages.map(a => ({ own: a.avgFirstChoice, srcs: a.avgSources }));
    for (const r of rows) {
      for (const s of r.srcs) if (s.pct < MIN_LABEL_PCT) set.add(s.party);
    }
    return [...set];
  }, [data, selected]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        <Button onClick={() => setSelectedFips(null)}
          variant={!selectedFips ? 'default' : 'secondary'} size="sm">
          National Average
        </Button>
        <select
          value={selectedFips ?? ''}
          onChange={e => setSelectedFips(e.target.value || null)}
          className="text-xs border border-border rounded px-2 py-1 text-muted-foreground"
          aria-label="Select a state"
        >
          <option value="">Select a state…</option>
          {stateList.map(st => (
            <option key={st.fips} value={st.fips}>{st.abbr}</option>
          ))}
        </select>
      </div>

      {/* National: finalist slots per party, with the average tally of those slots */}
      {!selectedFips && (
        <div className="space-y-3">
          <div className="text-[10px] text-muted-foreground">
            Finalist slots held out of {data.totalSlots} ({stateList.length} states &times; 5 finalists),
            with the average tally of those slots.
          </div>
          <div className="flex items-center gap-2">
            <div className="w-24 shrink-0 text-right text-[9px] text-muted-foreground uppercase tracking-wider">
              Slots
            </div>
            <div className="flex-1 min-w-0 relative h-3">
              <div className="absolute text-[9px] font-semibold text-muted-foreground -translate-x-1/2 whitespace-nowrap"
                style={{ left: `${(quota / AXIS_MAX) * 100}%` }}>
                quota
              </div>
            </div>
          </div>
          <div className="space-y-1.5">
            {data.averages.map(a => (
              <WinnowBar key={a.party}
                party={a.party}
                sublabel={String(a.finalistSlots)}
                firstChoice={a.avgFirstChoice}
                sources={a.avgSources}
                total={a.avgTotal}
                quotaPct={quota}
                onTip={setTip}
                tipTitle={`${PARTY_NAMES[a.party] ?? a.party} — ${a.finalistSlots} finalist slots`}
              />
            ))}
          </div>
          <div className="flex items-center gap-2">
            <div className="w-24 shrink-0" />
            <div className="flex-1 min-w-0 relative text-[9px] text-muted-foreground h-4">
              {axisTicks.map(t => {
                const frac = (t / AXIS_MAX) * 100;
                return (
                  <span key={t} className="absolute whitespace-nowrap"
                    style={{
                      left: `${frac}%`,
                      transform: frac === 0 ? 'none' : frac === 100 ? 'translateX(-100%)' : 'translateX(-50%)',
                    }}>
                    {t === quota ? `${t.toFixed(1)}% quota` : `${t}%`}
                  </span>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Per-state: the five finalists that advanced */}
      {selected && (
        <div className="space-y-4">
          <div>
            <div className="text-[10px] font-semibold text-emerald-600 uppercase tracking-widest mb-1">
              Reached quota — {selected.abbr}
            </div>
            {split.above.length > 0 ? (
              <div className="space-y-1">
                {split.above.map(f => (
                  <WinnowBar key={f.code}
                    party={f.party}
                    label={finalistLabels[f.code]}
                    firstChoice={f.firstChoice}
                    sources={f.sources}
                    total={f.total}
                    quotaPct={quota}
                    onTip={setTip}
                    tipTitle={`${PARTY_NAMES[f.party] ?? f.party} — reached quota`}
                  />
                ))}
              </div>
            ) : (
              <div className="text-[10px] text-muted-foreground">
                No candidate cleared the quota outright in this state.
              </div>
            )}
          </div>

          {split.below.length > 0 && (
            <div>
              <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest mb-1">
                Advanced below quota
              </div>
              <div className="text-[10px] text-muted-foreground mb-2">
                The winnow fills all five slots, so these advance on remaining strength
                once the field runs out rather than by clearing the quota.
              </div>
              <div className="space-y-1">
                {split.below.map(f => (
                  <WinnowBar key={f.code}
                    party={f.party}
                    label={finalistLabels[f.code]}
                    firstChoice={f.firstChoice}
                    sources={f.sources}
                    total={f.total}
                    quotaPct={quota}
                    onTip={setTip}
                    tipTitle={`${PARTY_NAMES[f.party] ?? f.party} — advanced below quota`}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {legendParties.length > 0 && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 pt-2 border-t border-border/50">
          <span className="text-[9px] text-muted-foreground uppercase tracking-wider">Transfers from</span>
          {legendParties.map(p => (
            <span key={p} className="flex items-center gap-1.5" title={PARTY_NAMES[p] ?? p}>
              <span className="w-3 h-3 rounded-sm"
                style={{ backgroundColor: PARTY_COLORS[p] ?? '#6b7280', opacity: 0.55 }} />
              <span className="text-[10px] text-muted-foreground">{PARTY_NAMES[p] ?? p}</span>
            </span>
          ))}
        </div>
      )}

      {tip && (
        <div className="fixed z-50 bg-slate-800 text-white text-xs rounded px-3 py-2 shadow-lg pointer-events-none"
          style={{ left: tip.x + 12, top: tip.y - 10, maxWidth: 280 }}>
          {tip.lines.map((l, i) => (
            <div key={i} className={i === 0 ? 'font-semibold mb-0.5' : 'text-slate-300'}>{l}</div>
          ))}
        </div>
      )}
    </div>
  );
}
