// Domains whose items are several distinct "Prefix: option" batteries that should
// render under sub-headers with the prefix stripped from each row.
export const SUBGROUPED_DOMAINS = new Set(['Foreign Policy & Defense', 'Voting History']);
export const MULTISELECT_DOMAINS = new Set(['Foreign Policy & Defense']); // bars can sum >100%
export const SUBGROUP_LABELS: Record<string, string> = {
  'Ukraine': 'U.S. response to Russia–Ukraine',
  'Israel/Gaza': 'U.S. response to Israel–Gaza',
  'Use US troops': 'When to use U.S. military force',
  '2016': '2016 presidential vote',
  '2020': '2020 presidential vote',
  '2024': '2024 election & approval',
};

export const stripPrefix = (q: string) => (q.includes(': ') ? q.split(': ').slice(1).join(': ') : q);

export interface SubGroup<T> {
  header: string | null;
  label: string;
  multi: boolean;
  items: T[];
}

/** Split a domain's items into "Prefix: …" batteries under sub-headers, else one group. */
export function buildSubgroups<T extends { question: string }>(domain: string, items: T[]): SubGroup<T>[] {
  if (!SUBGROUPED_DOMAINS.has(domain)) return [{ header: null, label: '', multi: false, items }];
  const groups: SubGroup<T>[] = [];
  const idx = new Map<string, number>();
  for (const v of items) {
    const pfx = v.question.includes(': ') ? v.question.split(': ')[0] : '';
    if (!idx.has(pfx)) {
      idx.set(pfx, groups.length);
      groups.push({ header: pfx, label: SUBGROUP_LABELS[pfx] ?? pfx, multi: MULTISELECT_DOMAINS.has(domain), items: [] });
    }
    groups[idx.get(pfx)!].items.push(v);
  }
  return groups;
}
