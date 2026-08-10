/** The two House flow matrices across every configuration the tab exposes: apportionment ×
 *  ballot depth × turnout gap. Lazy-fetched from public/data like housePartyList, since 70
 *  configurations are 264 KB and only one is on screen at a time.
 *
 *  Built by analysis/quota_flows.py, which validates every configuration's elected seats against
 *  housePartyList's own stvElected lists before writing. */

export interface FlowConfig {
  parties: { party: string; seats: number; ownShare: number; byOrigin: Record<string, number> }[];
  transfersOut: {
    party: string; byDest: Record<string, number>;
    crossShare: number; internalShare: number; exhaustedShare: number;
  }[];
}

export interface QuotaFlows {
  meta: { depths: string[]; wyoming: string[]; gaps: number[]; default: string };
  configs: Record<string, FlowConfig>;
}

/** Key for one cell. Falls back to the default cell when a combination is missing, so a new
 *  control value cannot blank the charts. */
export function flowKey(depth: string, wyoming: string, gap: string | number): string {
  return `${depth}|${wyoming}|${gap}`;
}

export function configAt(data: QuotaFlows | null, key: string): FlowConfig | null {
  if (!data) return null;
  return data.configs[key] ?? data.configs[data.meta.default] ?? null;
}
