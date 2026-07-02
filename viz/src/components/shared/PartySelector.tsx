import { useState } from 'react';
import { PARTY_NAMES, getBlendColor, getContrastText } from '../../constants/parties';

interface Props {
  selected: string[];                       // full selection (may include crossover codes)
  onToggle: (code: string) => void;
  baseParties: string[];                    // base party codes shown as chips
  crossover?: { code: string; label: string }[]; // optional expandable crossover candidates
}

/** Shared party picker: base parties as toggle chips, with an optional expandable
 *  "crossover candidates" section. Used by Compare Policies and Party Platforms. */
export function PartySelector({ selected, onToggle, baseParties, crossover }: Props) {
  const [open, setOpen] = useState(false);
  const chip = (code: string, label: string) => {
    const on = selected.includes(code);
    const c = getBlendColor(code);
    return (
      <button key={code} onClick={() => onToggle(code)}
        className="text-xs font-semibold px-2.5 py-1 rounded-full border transition-all"
        style={{ borderColor: c, color: on ? getContrastText(c) : c, backgroundColor: on ? c : 'transparent' }}>
        {label}
      </button>
    );
  };
  const openCrossover = crossover?.filter(o => selected.includes(o.code)) ?? [];
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">{baseParties.map(code => chip(code, PARTY_NAMES[code] ?? code))}</div>
      {crossover && crossover.length > 0 && (
        <div>
          <button onClick={() => setOpen(o => !o)}
            className="text-[11px] font-medium text-muted-foreground hover:text-foreground">
            {open ? '▾' : '▸'} Crossover candidates{openCrossover.length ? ` · ${openCrossover.length} selected` : ` (${crossover.length})`}
          </button>
          {open && (
            <div className="flex flex-wrap gap-1 mt-1.5">{crossover.map(o => chip(o.code, o.code))}</div>
          )}
          {!open && openCrossover.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">{openCrossover.map(o => chip(o.code, o.code))}</div>
          )}
        </div>
      )}
    </div>
  );
}
