import { type ReactNode } from 'react';
import { useUrlState } from '../../hooks/useUrlState';

/**
 * A section the reader opens on demand.
 *
 * Collapsed by default: these hold supporting detail on a page whose spine is the
 * headline comparison, the seat-share chart and the map. Content is unmounted while
 * closed, not hidden, so the charts inside cost nothing until they are asked for.
 *
 * Open/closed lives in the URL under `id`, which does two things: the STV and
 * party-list views mount separate instances of the same section, so without it the page
 * would slam shut every time the reader switched system; and a link carries what the
 * sender had open. Closed is the default, so a shut section adds nothing to the URL.
 */
interface Props {
  /** URL key, shared by every view that renders this same section. */
  id: string;
  /** Shown on the closed button, e.g. "See party profiles". */
  title: string;
  /** Optional one-line hint beside the title. */
  hint?: string;
  children: ReactNode;
}

export function CollapsibleSection({ id, title, hint, children }: Props) {
  const [raw, setRaw] = useUrlState<string>(id, '', { allowed: ['', '1'] });
  const open = raw === '1';
  const setOpen = (fn: (o: boolean) => boolean) => setRaw(fn(open) ? '1' : '');
  return (
    <div className="rounded-lg border border-border bg-card">
      <button
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        className="w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-slate-50 rounded-lg"
      >
        <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"
          style={{ transform: open ? 'rotate(90deg)' : 'none', transition: 'transform 0.15s' }}>
          <path d="M2 0 L8 5 L2 10 Z" fill="currentColor" className="text-muted-foreground" />
        </svg>
        <span className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">
          {title}
        </span>
        {hint && <span className="text-xs text-muted-foreground normal-case tracking-normal">{hint}</span>}
      </button>
      {open && <div className="px-4 pb-4 pt-1 space-y-6">{children}</div>}
    </div>
  );
}
