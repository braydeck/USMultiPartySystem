import type { ClusterProfile, FDCandidateProfile } from '../types';
import { CompareTab } from './CompareTab';

interface Props {
  clusters: ClusterProfile[];
  clusterSpreads: { party: string; n: number; [key: string]: string | number }[];
  fdProfiles: Record<string, FDCandidateProfile>;
}

// A single, selection-driven view: pick one party for its platform, several to compare.
// (Compare Policies + Party Platforms consolidated — see CompareTab.)
export function PartiesTab({ clusters, clusterSpreads, fdProfiles }: Props) {
  return <CompareTab clusters={clusters} fdProfiles={fdProfiles} clusterSpreads={clusterSpreads} />;
}
