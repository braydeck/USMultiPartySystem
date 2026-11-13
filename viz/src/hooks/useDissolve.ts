import { useCallback, useEffect, useMemo, useState } from 'react';
import { useUrlState } from './useUrlState';
import { dissolveKey, loadScenario, parseDissolve } from '../lib/dissolve';

/** Tabs that read the dissolve scenarios; tab navigation carries the `dissolve` param between them. */
export const DISSOLVE_TABS = new Set(['presidency', 'senate', 'house', 'legislation']);

/** The dissolved parties, from the `dissolve` URL param (`?dissolve=NAT-LP`). */
export function useDissolved(): [string[], (next: string[]) => void] {
  const [raw, setRaw] = useUrlState<string>('dissolve', '');
  const list = useMemo(() => parseDissolve(raw), [raw]);
  const set = useCallback((next: string[]) => setRaw(dissolveKey(parseDissolve(next.join(',')))), [setRaw]);
  return [list, set];
}

export type ScenarioStatus = 'off' | 'loading' | 'ready' | 'missing';

/**
 * Scenario files for the current dissolve selection. With nothing dissolved, or for a
 * combination not built yet, `on` is false and every file is undefined, so the tab reads its
 * full-field data. While the files load they are undefined too and `status` is 'loading'.
 * A file is only ever returned for the selection it belongs to.
 */
export function useScenarioFiles<T extends Record<string, unknown>>(files: readonly string[]): {
  dissolved: string[]; key: string; on: boolean; status: ScenarioStatus; data: Partial<T>;
} {
  const [dissolved] = useDissolved();
  const key = dissolveKey(dissolved);
  const want = files.join('|');
  const [got, setGot] = useState<{ id: string; data: Partial<T>; failed: boolean } | null>(null);
  const id = `${key}::${want}`;
  useEffect(() => {
    if (!key) return;
    let live = true;
    const names = want.split('|');
    Promise.all(names.map(f => loadScenario(key, f)))
      .then(vals => { if (live) setGot({ id, data: Object.fromEntries(names.map((f, i) => [f, vals[i]])) as Partial<T>, failed: false }); })
      .catch(() => { if (live) setGot({ id, data: {}, failed: true }); });
    return () => { live = false; };
  }, [key, want, id]);
  if (!key) return { dissolved, key, on: false, status: 'off', data: {} };
  if (got?.id !== id) return { dissolved, key, on: false, status: 'loading', data: {} };
  if (got.failed) return { dissolved, key, on: false, status: 'missing', data: {} };
  return { dissolved, key, on: true, status: 'ready', data: got.data };
}

const lazyCache = new Map<string, Promise<unknown>>();

/** A lazily loaded payload, identified by `id` (null = not wanted yet). Loaded once per id per
 *  session; the value is only ever the one for the current id. */
export function useLazyData<T>(id: string | null, load: () => Promise<T>): T | null {
  const [got, setGot] = useState<{ id: string; v: T } | null>(null);
  useEffect(() => {
    if (!id) return;
    let live = true;
    let p = lazyCache.get(id);
    if (!p) {
      p = load();
      p.catch(() => lazyCache.delete(id));
      lazyCache.set(id, p);
    }
    p.then(v => { if (live) setGot({ id, v: v as T }); }).catch(() => {});
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);
  return got && got.id === id ? got.v : null;
}

export const fetchJson = <T,>(path: string): Promise<T> =>
  fetch(`${import.meta.env.BASE_URL}${path}`).then(r => { if (!r.ok) throw new Error(path); return r.json() as Promise<T>; });
