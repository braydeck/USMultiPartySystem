export const PARTY_COLORS: Record<string, string> = {
  PRG: '#1e3a8a',  // deep navy (cool, leftmost)
  LIB: '#1d4ed8',  // royal blue
  DSA: '#60a5fa',  // steel blue
  SD:  '#06b6d4',  // bright cyan/teal
  STY: '#16a34a',  // green (centrist left anchor)
  CTR: '#a16207',  // dark yellow (centrist right anchor)
  CON: '#ea580c',  // orange-red
  REF: '#dc2626',  // crimson
  NAT: '#7f1d1d',  // deep maroon (warm, rightmost)
};

// Hardcoded overrides for composite codes that would otherwise blend to grey
const BLEND_OVERRIDES: Record<string, string> = {
  'CON/SD': '#b45309',  // warm amber-bronze (CON-dominant)
  'SD/CON': '#0c4a6e',  // deep dark navy (SD-dominant, clearly distinct)
};

export const F5_ORDER = ['PRG','LIB','DSA','SD','STY','CTR','CON','REF','NAT'] as const;

export const PARTY_NAMES: Record<string, string> = {
  CON: 'Conservative',
  SD:  'Social Democrat',
  STY: 'Solidarity',
  REF: 'Reform',
  CTR: 'Center',
  LIB: 'Liberal',
  NAT: 'Nationalist',
  DSA: 'Democratic Socialists',
  PRG: 'Progressive',
};

export const CLUSTER_TO_PARTY: Record<string, string> = {
  '0': 'CON',
  '1': 'SD',
  '2': 'STY',
  '3': 'NAT',
  '4': 'LIB',
  '5': 'REF',
  '6': 'CTR',
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

/** Returns color for a party code, blending if composite.
 * Handles three formats:
 *   "CON/STY"  — blended (~50/50), 65/35 visual blend
 *   "STY_ctr"  — light fusion (80/20), 85/15 visual blend toward primary
 *   "CON"      — pure party, exact party color
 */
export function getBlendColor(code: string): string {
  if (!code) return '#6b7280';
  if (BLEND_OVERRIDES[code]) return BLEND_OVERRIDES[code];
  if (code.includes('/')) {
    const parts = code.split('/');
    const c1 = PARTY_COLORS[parts[0]] ?? '#6b7280';
    const c2 = PARTY_COLORS[parts[1]] ?? '#6b7280';
    return blendHex(c1, c2);
  }
  // Light fusion: underscore with lowercase suffix (e.g. STY_ctr, CON_ref)
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

/** Given a senator_code like "CON/STY" or "CON", return the primary party code */
export function getPrimaryParty(code: string): string {
  if (!code) return '';
  return code.split('/')[0];
}

/** Use blend color for composite codes, pure party color for singles */
export function getPartyColor(code: string): string {
  return getBlendColor(code);
}

export const FACTOR_LABELS: Record<string, string> = {
  F1: 'Security & Order',
  F2: 'Electoral Skepticism',
  F3: 'Government Distrust',
  F4: 'Religious Traditionalism',
  F5: 'Populist Conservatism',
};
