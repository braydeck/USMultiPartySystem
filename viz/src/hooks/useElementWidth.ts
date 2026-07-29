import { useEffect, useRef, useState } from 'react';

// Tracks an element's rendered content-box width, so JS logic (e.g. deciding which
// seat-share segments are too narrow for an inline label) can match what CSS container
// queries do visually, without hand-computing layout from percentages alone.
export function useElementWidth<T extends HTMLElement = HTMLDivElement>() {
  const ref = useRef<T | null>(null);
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(entries => {
      const w = entries[0]?.contentRect.width;
      if (w != null) setWidth(w);
    });
    ro.observe(el);
    setWidth(el.getBoundingClientRect().width);
    return () => ro.disconnect();
  }, []);

  return [ref, width] as const;
}
