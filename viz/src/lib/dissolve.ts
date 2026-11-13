/**
 * Dissolved-party scenarios: every election rerun with one or more parties out of the field, each
 * of their voters counted for their next choice. pipeline/build_dissolve_scenarios.py writes one
 * folder per combination holding the same payload files the tabs read for the full field, in the
 * same shapes, so a tab swaps the file and every view works unchanged. Per-stop families
 * ({name}Turnout{,L5..L30}.json) are one file keyed by stop ('0'..'30'); housePartyList,
 * houseReserve and primaryDepth are split by ballot depth ({name}.{depth}.json).
 *
 * The files are served gzip-encoded from DISSOLVE_BASE: the dev server maps it onto
 * data/dissolve_store (vite.config.ts), production onto the bucket that holds the set.
 */
import { F5_ORDER, PARTY_NAMES } from '../constants/parties';

/** The parties that can be dissolved, in left-right order. */
export const DISSOLVABLE: readonly string[] = F5_ORDER;

export const DISSOLVE_BASE: string =
  (import.meta.env.VITE_DISSOLVE_BASE as string | undefined) ?? `${import.meta.env.BASE_URL}data/dissolve`;

/** URL token -> list. Unknown codes are dropped, order is normalized, and dissolving every party
 *  is refused (no election to run), so a hand-edited URL always names a built scenario. */
export function parseDissolve(raw: string): string[] {
  const want = new Set(raw.split(/[,-]/).map(s => s.trim().toUpperCase()).filter(Boolean));
  const out = DISSOLVABLE.filter(p => want.has(p));
  return out.length >= DISSOLVABLE.length ? [] : out;
}
export const dissolveKey = (parties: readonly string[]) => parties.join('-');

/** Names in a list with the serial comma: "Labor, Libertarian, and Nationalist". */
export function partyList(codes: readonly string[]): string {
  const n = codes.map(c => PARTY_NAMES[c] ?? c);
  if (n.length <= 2) return n.join(' and ');
  return `${n.slice(0, -1).join(', ')}, and ${n[n.length - 1]}`;
}

const cache = new Map<string, Promise<unknown>>();

/** One scenario file, fetched once per session. */
export function loadScenario<T>(key: string, file: string): Promise<T> {
  const id = `${key}/${file}`;
  let p = cache.get(id);
  if (!p) {
    p = fetch(`${DISSOLVE_BASE}/${id}.json`).then(r => {
      if (!r.ok) throw new Error(`dissolve ${id}: ${r.status}`);
      return r.json();
    });
    p.catch(() => cache.delete(id));
    cache.set(id, p);
  }
  return p as Promise<T>;
}

/** A per-stop family: one record per turnout stop, keyed '0'..'30'. */
export type ByStop<T> = Record<string, T>;
