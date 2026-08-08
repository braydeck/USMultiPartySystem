/** Surname suffixes that must not be mistaken for the surname itself — naive
 *  last-token extraction turns "Nick Begich III" into "III". */
const SUFFIXES = new Set(['jr', 'jr.', 'sr', 'sr.', 'ii', 'iii', 'iv', 'v']);

/** Shortest label that still identifies a candidate in a chart axis or a bar. */
export function shortName(full: string): string {
  const parts = full.trim().split(/\s+/);
  if (parts.length === 1) return parts[0];
  let i = parts.length - 1;
  while (i > 0 && SUFFIXES.has(parts[i].toLowerCase())) i--;
  return parts[i];
}
