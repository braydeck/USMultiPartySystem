import { useState } from 'react';
import { PARTY_NAMES, getBlendColor } from '../../constants/parties';
import { FIELD_LABEL } from '../../constants/typography';
import { DISSOLVABLE } from '../../lib/dissolve';
import { useDissolved, type ScenarioStatus } from '../../hooks/useDissolve';

/** Settings-bar dropdown: pick parties to take out of the field. Their voters count for their
 *  next choice, and every count on the page reruns. */
export function DissolveMenu({ status }: { status: ScenarioStatus }) {
  const [dissolved, setDissolved] = useDissolved();
  const [open, setOpen] = useState(false);
  const toggle = (p: string) =>
    setDissolved(dissolved.includes(p) ? dissolved.filter(x => x !== p) : [...dissolved, p]);
  const lastStanding = DISSOLVABLE.length - dissolved.length === 1;
  const label = dissolved.length ? `Dissolved: ${dissolved.join(', ')}` : 'None';

  return (
    <div className="relative flex items-center gap-2">
      <span className={FIELD_LABEL}>Dissolve</span>
      <button type="button" onClick={() => setOpen(o => !o)} aria-expanded={open}
        className={`text-xs font-medium rounded-md px-2.5 py-1 border ${dissolved.length
          ? 'border-amber-400 bg-amber-50 text-amber-900' : 'border-border bg-secondary text-foreground'}`}>
        {label} ▾
      </button>
      {status === 'loading' && <span className="text-2xs text-muted-foreground">loading…</span>}
      {status === 'missing' && <span className="text-2xs text-amber-700" title="This combination has not been built yet">not built</span>}
      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} aria-hidden="true" />
          <div className="absolute left-0 top-full mt-1 z-40 w-[min(90vw,340px)] rounded-md border border-border bg-card shadow-lg p-2">
            <div className="flex flex-wrap gap-1">
              {DISSOLVABLE.map(p => {
                const gone = dissolved.includes(p);
                const c = getBlendColor(p);
                return (
                  <button key={p} type="button" onClick={() => toggle(p)} disabled={!gone && lastStanding}
                    aria-pressed={gone} title={PARTY_NAMES[p] ?? p}
                    className={`text-xs font-semibold px-2.5 py-1 rounded-full border disabled:opacity-40 ${gone ? 'line-through bg-slate-100 text-slate-400 border-dashed' : ''}`}
                    style={gone ? { borderColor: c } : { borderColor: c, color: c }}>
                    {p}
                  </button>
                );
              })}
            </div>
            {dissolved.length > 0 && (
              <button type="button" onClick={() => setDissolved([])}
                className="mt-2 text-xs font-medium text-indigo-600 hover:underline">Restore all</button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
