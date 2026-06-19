export const PARTY_COLORS: Record<string, string> = {
  PRG: '#1e3a8a',  // deep navy (cool, leftmost)
  LIB: '#1d4ed8',  // royal blue
  DSA: '#60a5fa',  // steel blue
  SD:  '#06b6d4',  // bright cyan/teal
  STY: '#16a34a',  // green (centrist left anchor)
  CUP: '#a16207',  // dark yellow (centrist right anchor)
  CON: '#ea580c',  // orange-red
  POP: '#dc2626',  // crimson
  NAT: '#7f1d1d',  // deep maroon (warm, rightmost)
};

export const F5_ORDER = ['PRG','LIB','DSA','SD','STY','CUP','CON','POP','NAT'] as const;

export const PARTY_NAMES: Record<string, string> = {
  CON: 'Conservative',
  SD:  'Social Democrat',
  STY: 'Solidarity',
  POP: 'Populist',
  CUP: 'Civic Union Party',
  LIB: 'Liberal',
  NAT: 'Nationalist',
  DSA: 'Democratic Socialists',
  PRG: 'Progressive',
};

export const PARTY_TAGLINES: Record<string, string> = {
  PRG: 'Climate action, social justice, universal programs',
  LIB: 'Civil liberties, regulated markets, global engagement',
  DSA: 'Worker power, economic equality, public ownership',
  SD:  'Strong safety net, institutional reform, center-left',
  STY: 'Cross-cutting populism, skeptical of both establishments',
  CUP: 'Moderate on economics and culture, institutionalist',
  CON: 'Free markets, traditional values, national sovereignty',
  POP: 'Anti-establishment right, immigration restriction',
  NAT: 'Cultural conservatism, economic nationalism, strong borders',
};

// One-to-two sentence descriptions: who the cluster is and what it supports.
// Keep these factual (positions, demographics) — no editorial commentary.
export const PARTY_BLURBS: Record<string, string> = {
  PRG: 'The urban, college-educated left. Strongly progressive on taxes, climate, immigration, and civil liberties. Trusts elections and institutions.',
  DSA: 'The young, urban democratic-socialist left. Strongly progressive on economics and culture, secular, and skeptical of elections and institutions.',
  LIB: 'The older, professional-class left. Progressive on economics, climate, and civil liberties. Supports border enforcement.',
  SD:  'The working-class, racially diverse center-left. Backs the safety net, clean energy, and a Dreamer pathway, along with border enforcement.',
  STY: 'Young, majority non-white, lowest-income, and religiously traditional. Economically progressive on Medicaid and infrastructure, and skeptical of elections and institutions.',
  CUP: 'The religious, mostly-white moderate. Centrist on economics and culture, law-and-order, and trusting of elections.',
  CON: 'The pre-Trump, Reaganite right. Low-tax and law-and-order; trusts elections and backs universal background checks.',
  POP: 'The populist right. Immigration-restrictionist, skeptical of elections, and religiously traditional. Some support raising corporate taxes.',
  NAT: 'The far right. Strongly anti-immigration, religiously traditional, low-tax, and skeptical of elections.',
};

export const CLUSTER_TO_PARTY: Record<string, string> = {
  '0': 'CON',
  '1': 'SD',
  '2': 'STY',
  '3': 'NAT',
  '4': 'LIB',
  '5': 'POP',
  '6': 'CUP',
  '8': 'DSA',
  '9': 'PRG',
};

export const PARTY_TO_CLUSTER: Record<string, string> = Object.fromEntries(
  Object.entries(CLUSTER_TO_PARTY).map(([k, v]) => [v, k])
);

function hexToRgb(hex: string): [number, number, number] {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? [parseInt(result[1], 16), parseInt(result[2], 16), parseInt(result[3], 16)]
    : [128, 128, 128];
}

// 65/35 weighted blend — first component dominant
function blendHex(hex1: string, hex2: string, w1 = 0.65): string {
  const [r1, g1, b1] = hexToRgb(hex1);
  const [r2, g2, b2] = hexToRgb(hex2);
  const r = Math.round(r1 * w1 + r2 * (1 - w1));
  const g = Math.round(g1 * w1 + g2 * (1 - w1));
  const b = Math.round(b1 * w1 + b2 * (1 - w1));
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

/** Returns color for a party code.
 * Active formats:
 *   "CON"        — pure party, exact party color
 *   "STY_lo_ae"  — FD variant, returns base party color
 *   "STY_1"      — pure multi variant, returns base party color
 */
export function getBlendColor(code: string): string {
  if (!code) return '#6b7280';
  if (code.includes('/')) {
    const parts = code.split('/');
    const c1 = PARTY_COLORS[parts[0]] ?? '#6b7280';
    const c2 = PARTY_COLORS[parts[1]] ?? '#6b7280';
    return blendHex(c1, c2);
  }
  // FD/multi variant: underscore with lowercase suffix (e.g. STY_lo_ae, STY_1)
  if (code.includes('_')) {
    const [base, lean] = code.split('_', 2);
    if (lean === lean.toLowerCase() && PARTY_COLORS[base]) {
      const c1 = PARTY_COLORS[base];
      const c2 = PARTY_COLORS[lean.toUpperCase()] ?? c1;
      return blendHex(c1, c2, 0.85);
    }
  }
  return PARTY_COLORS[code] ?? '#6b7280';
}

/** Lighten a hex color by mixing toward white at the given amount (0–1) */
export function lightenHex(hex: string, amount = 0.35): string {
  const [r, g, b] = hexToRgb(hex);
  const r2 = Math.round(r + (255 - r) * amount);
  const g2 = Math.round(g + (255 - g) * amount);
  const b2 = Math.round(b + (255 - b) * amount);
  return `#${r2.toString(16).padStart(2, '0')}${g2.toString(16).padStart(2, '0')}${b2.toString(16).padStart(2, '0')}`;
}

/** Darken a hex color by mixing toward black at the given amount (0–1) */
export function darkenHex(hex: string, amount = 0.20): string {
  const [r, g, b] = hexToRgb(hex);
  const r2 = Math.round(r * (1 - amount));
  const g2 = Math.round(g * (1 - amount));
  const b2 = Math.round(b * (1 - amount));
  return `#${r2.toString(16).padStart(2, '0')}${g2.toString(16).padStart(2, '0')}${b2.toString(16).padStart(2, '0')}`;
}

/** Color for an FD candidate: base = full party color, hi = lightened, lo = darkened */
export function getFDColor(party: string, direction: 'base' | 'hi' | 'lo'): string {
  const base = PARTY_COLORS[party] ?? '#6b7280';
  if (direction === 'hi') return lightenHex(base, 0.35);
  if (direction === 'lo') return darkenHex(base, 0.20);
  return base;
}

/** Given a senator_code like "CON" or "STY_lo_ae", return the primary party code */
export function getPrimaryParty(code: string): string {
  if (!code) return '';
  return code.split('/')[0];
}

/** Use blend color for composite codes, pure party color for singles */
export function getPartyColor(code: string): string {
  return getBlendColor(code);
}

/**
 * Build a display-label map for a set of candidate codes.
 * Numbered variants like CON_1 are simplified to CON when no CON_2/CON_3 exist.
 * Non-numeric suffixes (e.g. STY_hi_so) are always kept.
 */
export function buildDisplayLabels(codes: Iterable<string>): Record<string, string> {
  const all = [...codes];
  // Count how many numbered variants each base party has
  const numberedByBase: Record<string, string[]> = {};
  for (const code of all) {
    const m = code.match(/^([A-Z]+)_(\d+)$/);
    if (m) {
      const base = m[1];
      if (!numberedByBase[base]) numberedByBase[base] = [];
      numberedByBase[base].push(code);
    }
  }
  const labels: Record<string, string> = {};
  for (const code of all) {
    const m = code.match(/^([A-Z]+)_(\d+)$/);
    if (m && (numberedByBase[m[1]]?.length ?? 0) <= 1) {
      labels[code] = m[1]; // strip _1 when sole candidate
    } else {
      labels[code] = code;
    }
  }
  return labels;
}

export const FACTOR_LABELS: Record<string, string> = {
  F1: 'Security & Order',
  F2: 'Electoral Skepticism',
  F3: 'Government Distrust',
  F4: 'Religious Traditionalism',
  F5: 'Populist Conservatism',
};

export const FACTOR_SHORT: Record<string, string> = {
  F1: 'SO',
  F2: 'ES',
  F3: 'GD',
  F4: 'RT',
  F5: 'PC',
};

export const FACTOR_POLES: Record<string, { low: string; high: string }> = {
  F1: { low: 'Civil Libertarian', high: 'Law & Order' },
  F2: { low: 'Election Supporting', high: 'Election Skeptic' },
  F3: { low: 'Pro-Establishment',   high: 'Anti-Establishment' },
  F4: { low: 'Secular',           high: 'Faith-Guided' },
  F5: { low: 'Progressive',       high: 'Conservative' },
};

// Variable → primary EFA factor (highest absolute loading > 0.3, from efa_loadings_k5_final.csv)
// Items marked * are content-based assignments (not in the 24-item EFA set)
// Note: F3 primary items (CC24_423, CC24_424 — trust questions) are not in the policy dataset
export const VAR_FACTOR: Record<string, string> = {
  // F1 – Security & Order
  CC24_321d:         'F1',  // loading +0.734
  CC24_323b:         'F1',  // loading +0.705
  CC24_340f:         'F1',  // loading +0.664
  CC24_321e:         'F1',  // loading +0.653
  CC24_340e:         'F1',  // loading +0.493
  // F2 – Electoral Skepticism (likert5 stored as _agree variants)
  CC24_421_1_agree:  'F2',  // loading +0.726
  CC24_421_2_agree:  'F2',  // loading +0.901
  // F3 – Government Distrust
  CC24_423:          'F3',  // loading +0.663 (low trust in federal government)
  CC24_424:          'F3',  // loading +0.476 (low trust in state government)
  // F4 – Religious Traditionalism
  pew_churatd:       'F4',  // loading +0.688 (church attendance)
  CC24_325_median:   'F4',  // loading +0.688 (abortion weeks — continuous)
  CC24_340c:         'F4',  // loading +0.651 (same-sex marriage)
  CC24_340b:         'F4',  // loading +0.489 (abortion access)
  CC24_324b:         'F4',  // loading +0.297 F4 vs +0.268 F1
  CC24_444a:         'F4',  // * gender transition surgery
  CC24_444b:         'F4',  // * parental consent name/pronoun
  CC24_444c:         'F4',  // * abortion-inducing drugs by mail
  CC24_444d:         'F4',  // * travel for abortion
  // F5 – Populist Conservatism (negative loadings mean high F5 → conservative response)
  CC24_440b_agree:   'F5',  // loading −0.616 (racial problems are rare)
  CC24_321b:         'F5',  // loading −0.557 (concealed carry)
  CC24_323d:         'F5',  // loading −0.540 (Dreamers pathway)
  CC24_341c:         'F5',  // loading −0.534 (allow $400k+ tax rates to rise)
  CC24_323a:         'F5',  // loading −0.520 (legal status for undocumented)
  CC24_440c_agree:   'F5',  // loading −0.437 (women seek power over men)
  CC24_341d:         'F5',  // loading −0.365 (infrastructure spending)
};

// All EFA factor loadings (|loading| > 0.20), sorted by |loading| desc per factor.
// Items intentionally repeat across factors when they cross-load.
export const FACTOR_ITEMS: Record<string, { key: string; loading: number }[]> = {
  F1: [
    { key: 'CC24_321d', loading: +0.734 },
    { key: 'CC24_323b', loading: +0.705 },
    { key: 'CC24_340f', loading: +0.664 },
    { key: 'CC24_321e', loading: +0.653 },
    { key: 'CC24_340e', loading: +0.493 },
    { key: 'CC24_323a', loading: +0.319 },
    { key: 'CC24_323d', loading: +0.313 },
    { key: 'CC24_324b', loading: +0.268 },
    { key: 'CC24_341a', loading: +0.260 },
  ],
  F2: [
    { key: 'CC24_421_2_agree', loading: +0.901 },
    { key: 'CC24_421_1_agree', loading: +0.726 },
    { key: 'CC24_424', loading: +0.380 },
    { key: 'CC24_423', loading: +0.240 },
    { key: 'CC24_440c_agree', loading: +0.209 },
    { key: 'CC24_341a', loading: +0.202 },
  ],
  F3: [
    { key: 'CC24_423', loading: +0.663 },
    { key: 'CC24_424', loading: +0.476 },
    { key: 'CC24_340e', loading: -0.319 },
    { key: 'CC24_323a', loading: +0.270 },
    { key: 'CC24_323d', loading: +0.225 },
    { key: 'CC24_440c_agree', loading: -0.219 },
    { key: 'CC24_440b_agree', loading: -0.208 },
    { key: 'CC24_303', loading: +0.203 },
  ],
  F4: [
    { key: 'pew_churatd', loading: +0.688 },
    { key: 'CC24_325_median', loading: +0.688 },
    { key: 'CC24_340c', loading: +0.651 },
    { key: 'CC24_340b', loading: +0.489 },
    { key: 'CC24_341d', loading: +0.300 },
    { key: 'CC24_324b', loading: +0.297 },
    { key: 'CC24_341c', loading: +0.285 },
    { key: 'CC24_341a', loading: +0.240 },
    { key: 'CC24_303', loading: +0.219 },
  ],
  F5: [
    { key: 'CC24_440b_agree', loading: -0.616 },
    { key: 'CC24_321b', loading: -0.557 },
    { key: 'CC24_323d', loading: -0.540 },
    { key: 'CC24_341c', loading: -0.534 },
    { key: 'CC24_323a', loading: -0.520 },
    { key: 'CC24_440c_agree', loading: -0.437 },
    { key: 'CC24_341d', loading: -0.365 },
    { key: 'CC24_340e', loading: +0.341 },
    { key: 'CC24_340f', loading: -0.271 },
    { key: 'CC24_341a', loading: -0.238 },
  ],
};

// Reverse mapping: variable key → all factors it loads on
export const VAR_ALL_FACTORS: Record<string, { factor: string; loading: number }[]> = {};
for (const [factor, items] of Object.entries(FACTOR_ITEMS)) {
  for (const item of items) {
    if (!VAR_ALL_FACTORS[item.key]) VAR_ALL_FACTORS[item.key] = [];
    VAR_ALL_FACTORS[item.key].push({ factor, loading: item.loading });
  }
}
