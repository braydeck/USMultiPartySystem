import { useState } from 'react';
import type { SRCandidate } from '../../lib/singleRace';
import { styleLabel } from '../../lib/singleRace';
import { PARTY_NAMES, getFDColor, CURRENT_PARTIES } from '../../constants/parties';

const CURRENT_SET = new Set<string>(CURRENT_PARTIES);

interface Props {
  candidates: SRCandidate[];
  partyOrder: string[];
  value: string;
  onChange: (code: string) => void;
}

/** A candidate is a party plus a style. Pick the (data-derived) party first, then an
 * optional (imposed) factor-deviation style — defaulting to "Core" (the base party). */
export function CandidatePicker({ candidates, partyOrder, value, onChange }: Props) {
  const byCode: Record<string, SRCandidate> = {};
  for (const c of candidates) byCode[c.code] = c;
  const cur = byCode[value] ?? candidates[0];
  const party = cur.party;

  // Style options for the current party: Core (base) first, then variants.
  const styles = candidates
    .filter(c => c.party === party)
    .sort((a, b) => (a.axis === 'base' ? 0 : 1) - (b.axis === 'base' ? 0 : 1) ||
      a.axis.localeCompare(b.axis) || a.direction.localeCompare(b.direction));

  return (
    <div className="flex-1 min-w-0 space-y-1">
      <PartyDropdown
        partyOrder={partyOrder}
        value={party}
        onChange={p => onChange(p)}  // base candidate code === party code
      />
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        disabled={styles.length <= 1}
        aria-label="Candidate style"
        className="w-full rounded-md border border-border bg-card px-2 py-1 text-xs text-muted-foreground disabled:opacity-60"
      >
        {styles.map(c => (
          <option key={c.code} value={c.code}>{c.axis === 'base' || c.axis === 'current' ? 'Core' : styleLabel(c)}</option>
        ))}
      </select>
    </div>
  );
}

function PartyDropdown({ partyOrder, value, onChange }: {
  partyOrder: string[];
  value: string;
  onChange: (party: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const color = getFDColor(value, 'base');
  return (
    <div className="relative w-full">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        aria-haspopup="listbox"
        className="w-full flex items-center gap-2 rounded-md border bg-card px-2.5 py-1.5 text-sm hover:bg-muted transition-colors"
        style={{ borderColor: color + '99' }}
      >
        <span className="px-1.5 py-0.5 rounded text-xs font-semibold shrink-0" style={{ background: color + '33', color }}>
          {value}
        </span>
        <span className="truncate text-left flex-1">{PARTY_NAMES[value]}</span>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6" /></svg>
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} aria-hidden="true" />
          <div role="listbox" className="absolute left-0 mt-1 z-40 w-64 max-h-96 overflow-auto rounded-md border border-border bg-card shadow-lg py-1">
            {partyOrder.map((p, i) => {
              const sel = p === value;
              const divider = CURRENT_SET.has(p) && !CURRENT_SET.has(partyOrder[i - 1]);
              return (
                <div key={p}>
                  {divider && (
                    <div className="px-3 pt-2 pb-1 mt-1 border-t border-border text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                      Today's parties
                    </div>
                  )}
                  <button
                    type="button"
                    role="option"
                    aria-selected={sel}
                    onClick={() => { onChange(p); setOpen(false); }}
                    className={`w-full text-left px-3 py-2 text-sm flex items-center gap-2.5 transition-colors ${sel ? 'bg-slate-900 text-white' : 'hover:bg-muted'}`}
                  >
                    <span className="w-3 h-3 rounded-full shrink-0 ring-1 ring-black/10" style={{ background: getFDColor(p, 'base') }} />
                    <span className="font-medium">{PARTY_NAMES[p]}</span>
                  </button>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
