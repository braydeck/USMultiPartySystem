import { useEffect, useRef, useState } from 'react';

/**
 * Drives a sticky control bar's compact/expanded state from the bar's own position on the page.
 *
 * Two things this has to get right, both of which have bitten before:
 *
 * 1. Trigger off the BAR's position, not a page-wide `window.scrollY > N`. A fixed count only
 *    lines up on tabs where the bar sits just under the header; on a tab that stacks charts above
 *    it (Parties) the same count fires thousands of pixels early, so the bar is already collapsed
 *    before you ever scroll to it. A sentinel rendered immediately above the bar gives a position
 *    that's correct on every tab.
 *
 * 2. Collapse and re-expand at DIFFERENT thresholds (hysteresis). Collapsing hides controls, so
 *    the document gets shorter (~200px on the House bar), and the browser's scroll anchoring
 *    compensates by pulling scrollY back up by that same amount to keep visible content stable.
 *    With one shared threshold that pullback lands back on the expanded side, which re-grows the
 *    document, which pushes scroll down across the line again — an oscillation that reads as the
 *    page fighting you or snapping backward on a slow scroll (a fast scroll just crosses the
 *    unstable band before it can settle). Requiring more upward scroll to re-expand than downward
 *    to collapse breaks the loop, because the shrink can no longer move you far enough to flip the
 *    state back.
 *
 * The re-expand buffer is derived from the bar's own expanded height rather than hard-coded: the
 * document can never shrink by more than the bar's full height, so that's a guaranteed-sufficient
 * band and it self-tunes per bar instead of assuming one tab's measurements fit all of them.
 *
 * `collapseAfter` is the knob for how eagerly it collapses: px scrolled past the bar's sticky
 * point before it condenses. Raise it for a later, gentler collapse; lower it for a snappier one.
 */
export function useStickyCollapse(collapseAfter = 60) {
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const barRef = useRef<HTMLDivElement | null>(null);
  const [scrolled, setScrolled] = useState(false);
  const [expanded, setExpanded] = useState(false);
  // Mirrors `scrolled` for reads inside the scroll handler, which must not re-subscribe per change.
  const scrolledRef = useRef(false);
  const expandedHeightRef = useRef(0);

  useEffect(() => {
    let ticking = false;

    const check = () => {
      ticking = false;
      const sentinel = sentinelRef.current;
      if (!sentinel) return;

      // Record the bar's height while it's showing full controls — the ceiling on how far the
      // document can shrink when it collapses, and so the hysteresis band.
      const bar = barRef.current;
      if (bar && !scrolledRef.current) {
        expandedHeightRef.current = Math.max(expandedHeightRef.current, bar.offsetHeight);
      }

      // How far the bar has scrolled above the top of the viewport.
      const above = -sentinel.getBoundingClientRect().top;
      const buffer = Math.max(expandedHeightRef.current, 120);
      const next = scrolledRef.current
        ? above > collapseAfter - buffer   // already compact: takes a real scroll back up to undo
        : above > collapseAfter;           // expanded: condense once the bar is stuck

      if (next === scrolledRef.current) return;
      scrolledRef.current = next;
      setScrolled(next);
      if (!next) setExpanded(false); // back above the bar → full controls, drop any manual expand
    };

    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(check);
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    check();
    return () => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
    };
  }, [collapseAfter]);

  const compact = scrolled && !expanded;
  return { sentinelRef, barRef, compact, scrolled, expanded, setExpanded };
}
