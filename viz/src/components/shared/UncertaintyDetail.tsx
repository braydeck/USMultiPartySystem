import { useMemo, useState } from 'react';
import { PARTY_COLORS, PARTY_NAMES, getContrastText } from '../../constants/parties';
import type { SeatInterval, StateUncertainty } from '../../lib/uncertainty';

const party = (code: string) => code.split('_')[0];

function Pill({ code }: { code: string }) {
  const p = party(code);
  const color = PARTY_COLORS[p] ?? '#6b7280';
  return (
    <span className="inline-flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded leading-none shrink-0 chip-text"
      style={{ backgroundColor: color, color: getContrastText(color) }} title={PARTY_NAMES[p] ?? p}>{p}</span>
  );
}

export function UncertaintyDetail({ seats, states, nDraws, stateLabel }: {
  seats: Record<string, SeatInterval>;
  states?: Record<string, StateUncertainty>;
  nDraws: number;
  stateLabel?: (fips: string) => string;
}) {
  const [open, setOpen] = useState(false);

  const rows = useMemo(
    () => Object.entries(seats).filter(([, v]) => v.modal > 0 || v.observed > 0 || v.hi > 0)
      .sort((a, b) => b[1].modal - a[1].modal),
    [seats],
  );
  const close = useMemo(
    () => Object.entries(states ?? {}).filter(([, s]) => s.pModal < 0.70)
      .sort((a, b) => a[1].pModal - b[1].pModal),
    [states],
  );

  return (
    <div className="pt-3 border-t border-border/50">
      <button onClick={() => setOpen(o => !o)}
        className="text-[11px] font-semibold text-muted-foreground hover:text-foreground"
        aria-expanded={open}>
        {open ? '▾' : '▸'} Range across {nDraws.toLocaleString()} resamples
      </button>

      {open && (
        <div className="mt-3 space-y-4">
          <div>
            <div className="grid grid-cols-[auto_1fr_1fr_1fr] gap-x-3 gap-y-1 text-[10px] items-center">
              <span className="text-muted-foreground uppercase tracking-wider">Party</span>
              <span className="text-muted-foreground uppercase tracking-wider">Most likely</span>
              <span className="text-muted-foreground uppercase tracking-wider">Expected</span>
              <span className="text-muted-foreground uppercase tracking-wider">95% range</span>
              {rows.map(([p, v]) => (
                <div key={p} className="contents">
                  <Pill code={p} />
                  <span className="tabular-nums text-foreground font-semibold">{v.modal}</span>
                  <span className="tabular-nums text-muted-foreground">{v.expected.toFixed(1)}</span>
                  <span className="tabular-nums text-muted-foreground">{v.lo}–{v.hi}</span>
                </div>
              ))}
            </div>
          </div>

          {close.length > 0 && (
            <div>
              <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">
                Closest races
              </div>
              <div className="space-y-1.5">
                {close.map(([fips, s]) => (
                  <div key={fips} className="flex items-start gap-2 text-[10px]">
                    <span className="w-8 shrink-0 font-semibold text-foreground">
                      {stateLabel ? stateLabel(fips) : fips}
                    </span>
                    <Pill code={s.modal} />
                    <span className="tabular-nums text-foreground font-semibold w-10">
                      {Math.round(s.pModal * 100)}%
                    </span>
                    <span className="text-muted-foreground">
                      {Object.entries(s.dist).slice(1, 4)
                        .map(([p, v]) => `${p} ${Math.round(v * 100)}%`).join(' · ')}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
