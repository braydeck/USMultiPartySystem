import { useStickyCollapse } from '../../hooks/useStickyCollapse';

interface Props {
  children: React.ReactNode;
  label?: string;
}

export function StickyControlBar({ children, label = 'Controls' }: Props) {
  const { sentinelRef, barRef, compact, scrolled, expanded, setExpanded } = useStickyCollapse();

  return (
    <>
      {/* Marks where the bar sits in normal flow, so the collapse triggers off the bar's own
          position rather than a page-wide scroll count. */}
      <div ref={sentinelRef} aria-hidden="true" />
      <div ref={barRef} className="sticky top-[40px] z-10 bg-white/95 backdrop-blur-sm border-b border-border/50 -mx-4 px-4 py-2">
        {compact && (
          <button
            type="button"
            onClick={() => setExpanded(true)}
            className="flex sm:hidden w-full items-center justify-between gap-2 text-xs py-0.5"
          >
            <span className="font-semibold text-foreground">{label}</span>
            <span className="shrink-0 font-medium text-indigo-600">Settings ▾</span>
          </button>
        )}
        <div className={`flex flex-wrap items-center gap-4 ${compact ? 'hidden sm:flex' : ''}`}>
          {scrolled && expanded && (
            <button type="button" onClick={() => setExpanded(false)}
              className="sm:hidden text-xs font-medium text-indigo-600 w-full text-right -mb-1">▴ collapse</button>
          )}
          {children}
        </div>
      </div>
    </>
  );
}
