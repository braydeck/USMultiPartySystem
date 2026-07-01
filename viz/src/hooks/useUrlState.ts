import { useCallback, useMemo, useSyncExternalStore } from 'react';

/**
 * State synced to the URL query string, so tabs and filters are shareable and
 * bookmarkable. Drop-in replacements for useState: same [value, setValue] shape,
 * including functional updaters. Values equal to the default are omitted from the
 * URL to keep links clean.
 *
 * Backed by useSyncExternalStore so every consumer re-renders on any URL change
 * (including browser back/forward via popstate).
 */

const URL_STATE_EVENT = 'urlstatechange';

function subscribe(onChange: () => void) {
  window.addEventListener('popstate', onChange);
  window.addEventListener(URL_STATE_EVENT, onChange);
  return () => {
    window.removeEventListener('popstate', onChange);
    window.removeEventListener(URL_STATE_EVENT, onChange);
  };
}

const getSearch = () => window.location.search;

function writeParam(key: string, value: string | null, push: boolean) {
  const url = new URL(window.location.href);
  if (value === null || value === '') url.searchParams.delete(key);
  else url.searchParams.set(key, value);
  if (push) window.history.pushState(window.history.state, '', url);
  else window.history.replaceState(window.history.state, '', url);
  window.dispatchEvent(new Event(URL_STATE_EVENT));
}

/**
 * Replace the entire query string at once. Used for tab navigation so a tab's
 * filters don't linger in the URL after you leave it — each tab shows only its
 * own params while active. Falsy values are dropped.
 */
export function resetUrlParams(next: Record<string, string>, push = true) {
  const url = new URL(window.location.href);
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(next)) if (v) params.set(k, v);
  url.search = params.toString();
  if (push) window.history.pushState(window.history.state, '', url);
  else window.history.replaceState(window.history.state, '', url);
  window.dispatchEvent(new Event(URL_STATE_EVENT));
}

/**
 * Build (without navigating) the URL string that would result from applying these
 * param updates to the current location. Powers real <a href> links so tabs and
 * sections support "open in new tab" / middle-click. A null/empty value drops the
 * param; reset=true clears all existing params first (matches resetUrlParams, for
 * tab navigation that shouldn't carry a tab's filters forward).
 */
export function urlForParams(updates: Record<string, string | null>, reset = false): string {
  const url = new URL(window.location.href);
  const params = reset ? new URLSearchParams() : new URLSearchParams(url.search);
  for (const [k, v] of Object.entries(updates)) {
    if (!v) params.delete(k);
    else params.set(k, v);
  }
  const qs = params.toString();
  return `${url.pathname}${qs ? `?${qs}` : ''}${url.hash}`;
}

interface Options<T extends string> {
  /** If set, URL values outside this list fall back to the default (guards hand-edited URLs). */
  allowed?: readonly T[];
  /** Push a new history entry instead of replacing — use for navigation, not filter tweaks. */
  push?: boolean;
  /** Map internal value → URL token, so the URL can read in product language ({ factorDev: 'crossover' }). */
  map?: Partial<Record<T, string>>;
}

export function useUrlState<T extends string>(
  key: string,
  defaultValue: T,
  options: Options<T> = {},
): [T, (next: T | ((prev: T) => T)) => void] {
  const { allowed, push = false, map } = options;
  const search = useSyncExternalStore(subscribe, getSearch, getSearch);

  // token (as seen in the URL) → internal value
  const decode = useMemo(() => {
    const reverse: Record<string, T> = {};
    if (map) for (const internal in map) {
      const token = map[internal as T];
      if (token) reverse[token] = internal as T;
    }
    return reverse;
  }, [map]);

  const read = useCallback(
    (s: string): T => {
      const raw = new URLSearchParams(s).get(key);
      if (raw === null) return defaultValue;
      const internal = (decode[raw] ?? raw) as T;
      if (allowed && !(allowed as readonly string[]).includes(internal)) return defaultValue;
      return internal;
    },
    [key, defaultValue, allowed, decode],
  );

  const value = read(search);

  const set = useCallback(
    (next: T | ((prev: T) => T)) => {
      const resolved = typeof next === 'function' ? (next as (prev: T) => T)(read(window.location.search)) : next;
      const token = (map?.[resolved] ?? resolved) as string;
      writeParam(key, resolved === defaultValue ? null : token, push);
    },
    [key, defaultValue, push, map, read],
  );

  return [value, set];
}

export function useUrlNumber(
  key: string,
  defaultValue: number,
  options: { push?: boolean } = {},
): [number, (next: number | ((prev: number) => number)) => void] {
  const { push = false } = options;
  const search = useSyncExternalStore(subscribe, getSearch, getSearch);

  const parse = (raw: string | null) => {
    const n = raw !== null ? Number(raw) : NaN;
    return Number.isFinite(n) ? n : defaultValue;
  };
  const value = parse(new URLSearchParams(search).get(key));

  const set = useCallback(
    (next: number | ((prev: number) => number)) => {
      const resolved =
        typeof next === 'function' ? next(parse(new URLSearchParams(window.location.search).get(key))) : next;
      writeParam(key, resolved === defaultValue ? null : String(resolved), push);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [key, defaultValue, push],
  );

  return [value, set];
}
