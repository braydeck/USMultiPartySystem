import { useState, useEffect } from 'react';

interface Props {
  children: React.ReactNode;
  label?: string;
}

export function StickyControlBar({ children, label = 'Controls' }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => {
      const s = window.scrollY > 140;
      setScrolled(s);
      if (!s) setExpanded(false);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const compact = scrolled && !expanded;

  return (
    <div className="sticky top-[40px] z-10 bg-white/95 backdrop-blur-sm border-b border-border/50 -mx-4 px-4 py-2">
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
  );
}
