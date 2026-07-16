/** Canonical display labels for simulation toggles — single source of truth. */

export type Pipeline = 'rawMulti' | 'factorDev';
export type Method = 'condorcet' | 'irv';
export type WyomingRule = 'double' | 'triple';
export type WfpMode = 'off' | 'on';
export type VoteMode = 'free' | 'whipped';

export const VOTE_MODEL_LABELS: Record<VoteMode, string> = {
  free:    'Free vote',
  whipped: 'Whipped',
};

export const PIPELINE_LABELS: Record<Pipeline, string> = {
  rawMulti:  'Party-Line',
  factorDev: 'Crossover',
};

export const PIPELINE_LABELS_LONG: Record<Pipeline, string> = {
  rawMulti:  'Party-Line (27 candidates)',
  factorDev: 'Crossover (37 candidates)',
};

export const PIPELINE_DESC: Record<Pipeline, string> = {
  factorDev: '9 base parties + 28 crossover variants. Each variant shifts one ideological axis by ±25% — producing candidates like LBR_hi_so (a Labor candidate who runs tougher on security) or CON_lo_pc (a Conservative who softens on populism).',
  rawMulti:  'All 9 parties field 3 intra-party candidates each (40/35/25 first-choice split). Same-party candidates share an identical position; only prominence differs.',
};

export const METHOD_LABELS: Record<Method, string> = {
  condorcet: 'Condorcet',
  irv:       'IRV',
};

export const WYOMING_LABELS: Record<WyomingRule, string> = {
  double: 'Double (873)',
  triple: 'Triple (~1,726)',
};

export const WFP_LABELS: Record<WfpMode, string> = {
  off: '9 Parties',
  on:  '+ OAO (C7)',
};
