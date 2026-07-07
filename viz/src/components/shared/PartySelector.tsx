import { useState } from 'react';
import { PARTY_NAMES, getBlendColor, getContrastText } from '../../constants/parties';

interface Props {
  selected: string[];                       // full selection (may include crossover codes)
  onToggle: (code: string) => void;
  baseParties: string[];                    // base party codes shown as chips
  crossover?: { code: string; label: string }[]; // optional crossover candidates (in a popover)
}

/** Shared party picker: base parties as compact code chips (full name on hover), with an
 *  optional "crossover candidates" popover that floats over content — so it never grows the
 *  (sticky) bar it lives in. */
export function PartySelector({ selected, onToggle, baseParties, crossover }: Props) {
  const [open, setOpen] = useState(false);
  const chip = (code: string, title?: string) => {
    const on = selected.includes(code);
    const c = getBlendColor(code);
    return (
      <button key={code} onClick={() => onToggle(code)} title={title}
        className="text-xs font-semibold px-2.5 py-1 rounded-full border transition-all"
        style={{ borderColor: c, color: on ? getContrastText(c) : c, backgroundColor: on ? c : 'transparent' }}>
        {code}
      </button>
    );
  };
  const selectedCrossover = crossover?.filter(o => selected.includes(o.code)) ?? [];
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {baseParties.map(code => chip(code, PARTY_NAMES[code] ?? code))}
      {crossover && crossover.length > 0 && (
        <div className="relative">
          <button onClick={() => setOpen(o => !o)}
            className="text-[11px] font-medium text-muted-foreground hover:text-foreground border border-dashed border-border rounded-full px-2 py-1">
            {open ? '▾' : '＋'} Crossover{selectedCrossover.length ? ` · ${selectedCrossover.length}` : ` (${crossover.length})`}
          </button>
          {open && (
            <>
              <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} aria-hidden="true" />
              <div className="absolute left-0 mt-1 z-40 w-[min(90vw,540px)] max-h-72 overflow-y-auto flex flex-wrap gap-1 rounded-md border border-border bg-card shadow-lg p-2">
                {crossover.map(o => chip(o.code, o.label))}
              </div>
            </>
          )}
        </div>
      )}
      {/* selected crossover chips stay visible in the bar even when the popover is closed */}
      {!open && selectedCrossover.map(o => chip(o.code, o.label))}
    </div>
  );
}
