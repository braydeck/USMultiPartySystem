import factorItems from '../data/factorItems.json';

export const PARTY_COLORS: Record<string, string> = {
  // Cool left (green→blue), distinct center (violet, brown), warm right (orange→red)
  PRG: '#15803d',  // lively green, deep (leftmost)
  DSA: '#22c55e',  // lively green, bright
  OAO: '#0284c7',  // rich azure (DAL's color, a placeholder; OAO's color is the researcher's call)
  LBR: '#38bdf8',  // vivid sky blue (Labor — formerly SD)
  STY: '#8a70b8',  // violet (center)
  CUP: '#825a27',  // brown (center)
  CON: '#e68c2c',  // orange
  POP: '#d34812',  // red-orange
  NAT: '#a01d2a',  // deep red (rightmost)
  // Current (real) parties — muted D/R/I, rendered dashed to read as "status quo".
  DEM: '#5b7fa6',
  IND: '#8a8f98',
  REP: '#a66b6b',
};

// Left→right order for the nine parties: weighted Economic Conservatism (F5) centroid, low to high
// (ruled 2026-11-04). Mirrors LEFT_RIGHT in pipeline/party_codes.py; the hex cartograms read this copy.
// Cluster ID 4 (DAL) holds no voters in the nine-party typology.
export const F5_ORDER = ['OAO','PRG','DSA','LBR','STY','CUP','CON','NAT','POP'] as const;

// Back-compat alias (previously toggled the 10th party); now identical to F5_ORDER.
export const F5_ORDER_WFP = F5_ORDER;

/** Party ordering (all nine parties). Arg retained for call-site compatibility. */
export function partyOrder(): readonly string[] {
  return F5_ORDER;
}

// Today's real parties (pid3), shown after the US baseline in the Parties tab.
export const CURRENT_PARTIES = ['DEM', 'IND', 'REP'] as const;
const CURRENT_SET = new Set<string>(CURRENT_PARTIES);
/** True for the real-party codes (Democratic/Independent/Republican), which render dashed. */
export function isCurrentParty(code: string): boolean {
  return CURRENT_SET.has(code);
}

export const PARTY_NAMES: Record<string, string> = {
  OAO: 'Order and Opportunity',
  PRG: 'Progressive',
  DSA: 'Democratic Socialists',
  LBR: 'Labor',
  STY: 'Solidarity',
  CUP: 'Civic Union',
  CON: 'Conservative',
  NAT: 'Nationalist',
  POP: 'Populist',
  DEM: 'Democratic',
  IND: 'Independent',
  REP: 'Republican',
};

// Copied from analysis/efa/rebuild_nine_parties/party_descriptions.md (the researcher's file); edit there, then copy.
export const PARTY_TAGLINES: Record<string, string> = {
  OAO: 'Left on economics, moderate on culture, pro-police, and trusts government',
  PRG: 'Progressive across the board; backs arming Ukraine and trusts elections',
  DSA: 'Socialist left: shift police funding, secular, and distrusts government',
  LBR: 'Progressive on culture, climate and civil liberties; shift police funding',
  STY: 'Backs student-debt relief and Medicaid, along with tax cuts and school vouchers',
  CUP: 'Socially liberal, centrist on economics, pro-police, and trusts institutions',
  CON: 'Pro-order and pro-border, low-tax, and backs Medicaid expansion',
  NAT: 'Anti-immigration, culturally traditional, low-tax, and distrusts government',
  POP: 'Distrusts elections and government; opposes more public spending',
};

// Paragraph descriptions, copied from analysis/efa/rebuild_nine_parties/party_descriptions.md.
export const PARTY_BLURBS: Record<string, string> = {
  OAO: 'The working-class left of order. Backs Medicaid expansion, student-debt relief, higher taxes on top earners and more police funding; supports school vouchers and parental consent on pronouns. The most trusting of the federal government. Older, urban, lower-income, and about a third Black.',
  PRG: 'The college-educated progressive left. Backs abortion rights, a path to legal status, climate rules and an assault-weapons ban, and a majority would move police funding to other services. The strongest support for sending arms to Ukraine. Trusts elections. The most college-educated party.',
  DSA: 'The socialist left. Near-unanimous for moving police funding to other services, abortion rights and a path to legal status. Distrusts the federal government. The youngest party, with the highest shares of LGBT and atheist or agnostic members.',
  LBR: 'The civil-libertarian left. Backs abortion rights, a path to legal status, climate rules and higher taxes on top earners, and a majority would move police funding to other services. College-educated, secular and suburban.',
  STY: 'The cross-pressured working class, and the largest party. Backs student-debt relief, Medicaid expansion and a path to legal status, along with extending the 2017 tax cuts, school vouchers and parental consent on pronouns. Younger, racially diverse and lower-income; members come from both major parties.',
  CUP: 'The suburban moderate. Backs abortion rights, an assault-weapons ban and Medicaid expansion; splits on the 2017 tax cuts and mostly opposes student-debt relief. Supports more police funding and trusts elections and the federal government. Older homeowners, with the highest share of self-described moderates.',
  CON: 'The mainstream right. Backs the border wall, more police funding, more fossil-fuel production and extending the 2017 tax cuts. Supports Medicaid expansion and splits on repealing the Affordable Care Act. Older, mostly white homeowners.',
  NAT: 'The hard right. Backs the border wall, more fossil-fuel production, repealing the Affordable Care Act and parental consent before schools use a new name or pronoun. Opposes higher taxes on top earners. The most culturally conservative party, and distrusts the federal government. Older, white, married and Protestant.',
  POP: 'The anti-government party. The most distrustful of elections and the federal government, and the most opposed to new spending on schools, health care, roads and police. Splits on the border wall and abortion. Younger, mostly independent, and often religiously unaffiliated.',
};

export const CLUSTER_TO_PARTY: Record<string, string> = {
  '0': 'CON',
  '1': 'LBR',
  '2': 'STY',
  '3': 'NAT',
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

// The four factors of the nine-party typology (pipeline/factor_keys.py). F3 retired with it.
export const FACTOR_LABELS: Record<string, string> = {
  F1: 'Security & Order',
  F2: 'Government Distrust',
  F4: 'Cultural Conservatism',
  F5: 'Economic Conservatism',
};

/**
 * Accent colour per voting system. Shared by the Overview's ConceptStrip and the per-chamber
 * MechanismStrip primers, so a system reads the same colour wherever it is named.
 */
export const SYSTEM_COLORS: Record<string, string> = {
  FPTP: '#64748b',
  Condorcet: '#a16207',
  IRV: '#16a34a',
  STV: '#1d4ed8',
  'Party List': '#0369a1',
};

/**
 * What each factor is actually made of, in policy terms. A factor name alone ("Populist
 * Conservatism") says how the axis was scored, not which questions loaded onto it, so the
 * reader has no way to check the label against anything they hold an opinion about.
 */
export const FACTOR_DOMAINS: Record<string, string> = {
  F1: 'Policing, Border Security, and Law-Enforcement Spending',
  F2: 'Trust in Government and Elections',
  F4: 'Abortion, Gender, Religion, and School Choice',
  F5: 'State Social Spending, Medicaid, and Taxes',
};

export const FACTOR_SHORT: Record<string, string> = {
  F1: 'SO',
  F2: 'GD',
  F4: 'CC',
  F5: 'EC',
};

// Factors shown in party-facing displays, in strength order: how much each factor separates
// the parties (eta-squared by party, viz/src/data/factorLoadings.json: F4 0.75, F1 0.69,
// F5 0.69, F2 0.23). Everything that lists factors reads this, so the reader meets them in the
// same order and the strongest one first.
export const DISPLAY_FACTORS = ['F4', 'F1', 'F5', 'F2'] as const;

/** Single-hue purple ramp for discriminatory strength (η², ~0–0.8): light = weak, dark = strong. */
export function etaPurple(eta: number): string {
  const t = Math.max(0, Math.min(1, eta / 0.8));
  const lightness = 86 - t * 50;  // 86% (weak) → 36% (strong)
  return `hsl(271, 64%, ${lightness}%)`;
}

export const FACTOR_POLES: Record<string, { low: string; high: string }> = {
  F1: { low: 'Civil Libertarian', high: 'Law & Order' },
  F2: { low: 'Trusts Government', high: 'Distrusts Government' },
  F4: { low: 'Culturally Progressive', high: 'Culturally Conservative' },
  F5: { low: 'Economic Left', high: 'Economic Right' },
};

// Variable → primary factor, and every item loading |λ| > 0.20 per factor, signed so a positive
// loading means the item's keyed answer (support, agree, increase, low trust) goes with a high
// score. Generated by viz/scripts/make_factor_reference.py from the four-factor loadings.
export const VAR_FACTOR: Record<string, string> = factorItems.primary;
export const FACTOR_ITEMS: Record<string, { key: string; loading: number }[]> = factorItems.items;

// Reverse mapping: variable key → all factors it loads on
export const VAR_ALL_FACTORS: Record<string, { factor: string; loading: number }[]> = {};
for (const [factor, items] of Object.entries(FACTOR_ITEMS)) {
  for (const item of items) {
    if (!VAR_ALL_FACTORS[item.key]) VAR_ALL_FACTORS[item.key] = [];
    VAR_ALL_FACTORS[item.key].push({ factor, loading: item.loading });
  }
}
