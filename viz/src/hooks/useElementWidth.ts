import { useCallback, useRef, useState } from 'react';

// Tracks an element's rendered content-box width, so JS logic (e.g. deciding which
// seat-share segments are too narrow for an inline label) can match what CSS container
// queries do visually, without hand-computing layout from percentages alone.
//
// A callback ref rather than useRef plus a mount-time effect: the measured element is not
// always present when the calling component mounts. The cartogram's sidebar bar is rendered by
// a child that appears only once its hex tiling has loaded, so an effect with [] deps found
// ref.current still null, bailed, and never observed anything — leaving width at 0, which reads
// as "every segment is too narrow to label". Attaching on the ref callback measures whenever the
// node actually arrives.
export function useElementWidth<T extends HTMLElement = HTMLDivElement>() {
  const [width, setWidth] = useState(0);
  const observer = useRef<ResizeObserver | null>(null);

  const ref = useCallback((el: T | null) => {
    observer.current?.disconnect();
    observer.current = null;
    if (!el) return;
    setWidth(el.getBoundingClientRect().width);
    const ro = new ResizeObserver(entries => {
      const w = entries[0]?.contentRect.width;
      if (w != null) setWidth(w);
    });
    ro.observe(el);
    observer.current = ro;
  }, []);

  return [ref, width] as const;
}
