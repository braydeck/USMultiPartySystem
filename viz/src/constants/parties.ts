export const PARTY_COLORS: Record<string, string> = {
  // Cool left (green→blue), distinct center (violet, brown), warm right (orange→red)
  PRG: '#15803d',  // lively green, deep (leftmost)
  DSA: '#22c55e',  // lively green, bright
  LIB: '#0284c7',  // rich azure
  LBR: '#38bdf8',  // vivid sky blue (Labor — formerly SD)
  STY: '#8a70b8',  // violet (center)
  CUP: '#825a27',  // brown (center)
  CON: '#e68c2c',  // orange
  POP: '#d34812',  // red-orange
  NAT: '#a01d2a',  // deep red (rightmost)
  OAO: '#0d9488',  // Order and Opportunity Party (C7) — teal (distinct from all others; avoids black-line conflicts)
};

// Left→right order for all 10 parties (OAO after Labor, before STY).
export const F5_ORDER = ['PRG','DSA','LIB','LBR','OAO','STY','CUP','CON','POP','NAT'] as const;

// Back-compat alias (previously toggled the 10th party); now identical to F5_ORDER.
export const F5_ORDER_WFP = F5_ORDER;

/** Party ordering (all 10 parties). Arg retained for call-site compatibility. */
export function partyOrder(_wfpOn?: boolean): readonly string[] {
  return F5_ORDER;
}

export const PARTY_NAMES: Record<string, string> = {
  CON: 'Conservative',
  LBR: 'Labor',                     // cluster 1 — working-class center-left (formerly SD)
  STY: 'Solidarity',
  POP: 'Populist',
  CUP: 'Civic Union Party',
  LIB: 'Liberal',                   // cluster 4 — professional establishment left
  NAT: 'Nationalist',
  DSA: 'Democratic Socialists',
  PRG: 'Progressive',
  OAO: 'Order and Opportunity Party', // cluster 7 (formerly WFP)
};

// Condensed from PARTY_BLURBS — keep factual (positions), no editorial/comparative phrasing.
export const PARTY_TAGLINES: Record<string, string> = {
  PRG: 'Progressive on taxes, climate, and civil liberties; trusts elections',
  LIB: 'Progressive on economics and climate; backs border enforcement and police',
  DSA: 'Progressive on economics and culture, secular, election-skeptic',
  LBR: 'Safety net, clean energy, and a Dreamer pathway with border enforcement',
  STY: 'Economically progressive and religiously traditional; election-skeptic',
  CUP: 'Centrist on economics and culture; law-and-order institutionalists',
  CON: 'Low-tax, law-and-order; trusts elections and backs background checks',
  POP: 'Immigration-restrictionist and election-skeptic; backs Medicaid expansion',
  NAT: 'Anti-immigration, religiously traditional, low-tax, and election-skeptic',
  OAO: 'Economically progressive and law-and-order; trusts elections',
};

// One-to-two sentence descriptions: who the cluster is and what it supports.
// Keep these factual (positions, demographics) — no editorial commentary.
export const PARTY_BLURBS: Record<string, string> = {
  PRG: 'The urban, college-educated left. Strongly progressive on taxes, climate, immigration, social justice, and civil liberties. Trusts elections and institutions.',
  DSA: 'The young, urban, anti-establishment left. Strongly progressive on economics and culture, and secular. Strongly skeptical of elections and institutions.',
  LIB: 'The older, professional-class left. Progressive on economics, climate, and civil liberties. Supports border enforcement and opposes cutting police.',
  LBR: 'The working-class, racially diverse center-left. Backs the safety net, clean energy, and a Dreamer pathway, along with border enforcement. More moderate on social issues than other Left parties.',
  STY: 'Young, majority non-white, lowest-income, and religiously traditional. Economically progressive on Medicaid and infrastructure, and skeptical of elections and institutions.',
  CUP: 'The religious, mostly-white moderate. Centrist on economics and culture, but place emphasis on law-and-order. The most institutionalist party.',
  CON: 'The pre-Trump, Reaganite right. Low-tax and law-and-order; trusts elections and backs universal background checks.',
  POP: 'The populist right. Immigration-restrictionist, skeptical of elections, and religiously traditional. Support Medicaid expansion.',
  NAT: 'The far right. Strongly anti-immigration, religiously traditional, low-tax, high racial and gender resentment, and skeptical of elections.',
  OAO: 'Among the most law-and-order parties of any — strong on policing, security, and order — while economically progressive on taxes, spending, and the safety net. Secular, and strongly trusts elections and institutions.',
};

export const CLUSTER_TO_PARTY: Record<string, string> = {
  '0': 'CON',
  '1': 'LBR',
  '2': 'STY',
  '3': 'NAT',
  '4': 'LIB',
  '5': 'POP',
  '6': 'CUP',
  '7': 'OAO',
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
 *   "STY_lo_id"  — FD variant, returns base party color
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
  // FD/multi variant: underscore with lowercase suffix (e.g. STY_lo_id, STY_1)
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

// Global chip/label text policy — single knob, flip and reload to compare:
//   'auto'  – per-chip: dark text on light fills, white otherwise (max readability, least uniform)
//   'white' – always white (uniform; unreadable on light fills like SD)
//   'dark'  – always near-black (uniform; unreadable on dark fills like PRG/NAT)
//   any hex – force one exact color everywhere, e.g. '#475569' (medium grey)
export const CHIP_TEXT: string = 'white';

const CHIP_TEXT_WHITE = '#ffffff';
const CHIP_TEXT_DARK = '#0f172a';

/** Readable text color for a party-colored chip/label background. Honors CHIP_TEXT;
 * in 'auto' mode picks dark vs white by WCAG luminance (light fills like SD get dark text). */
export function getContrastText(bg: string): string {
  if (CHIP_TEXT === 'white') return CHIP_TEXT_WHITE;
  if (CHIP_TEXT === 'dark') return CHIP_TEXT_DARK;
  if (CHIP_TEXT !== 'auto') return CHIP_TEXT; // explicit hex override
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(bg);
  if (!m) return CHIP_TEXT_WHITE;
  const lin = (v: number) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  };
  const L =
    0.2126 * lin(parseInt(m[1], 16)) +
    0.7152 * lin(parseInt(m[2], 16)) +
    0.0722 * lin(parseInt(m[3], 16));
  return L > 0.45 ? CHIP_TEXT_DARK : CHIP_TEXT_WHITE;
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

/** Given a code like "CON", "STY_lo_id", "CON_1", or "CON/POP", return the base party code */
export function getPrimaryParty(code: string): string {
  if (!code) return '';
  return code.split('/')[0].split('_')[0];
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
  F2: 'Institutional Distrust',
  F3: 'Government Distrust (residual)',
  F4: 'Religious Traditionalism',
  F5: 'Populist Conservatism',
};

export const FACTOR_SHORT: Record<string, string> = {
  F1: 'SO',
  F2: 'ID',
  F3: 'GD',
  F4: 'RT',
  F5: 'PC',
};

// Factors shown in party-facing displays. F3 (Government Distrust) is a non-interpretable
// residual whose party scores run OPPOSITE to real distrust (see docs/EFA_FACTORS.md); it is
// excluded here and surfaced only in the About factor reference, flagged as a residual.
export const DISPLAY_FACTORS = ['F1', 'F2', 'F4', 'F5'] as const;

/** Single-hue purple ramp for discriminatory strength (η², ~0–0.8): light = weak, dark = strong. */
export function etaPurple(eta: number): string {
  const t = Math.max(0, Math.min(1, eta / 0.8));
  const lightness = 86 - t * 50;  // 86% (weak) → 36% (strong)
  return `hsl(271, 64%, ${lightness}%)`;
}

export const FACTOR_POLES: Record<string, { low: string; high: string }> = {
  F1: { low: 'Civil Libertarian', high: 'Law & Order' },
  F2: { low: 'Trusts Institutions', high: 'Distrusts Institutions' },
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
  // F2 – Institutional Distrust (likert5 stored as _agree variants)
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
