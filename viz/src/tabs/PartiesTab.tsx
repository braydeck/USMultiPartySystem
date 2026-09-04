import type { ClusterProfile, FDCandidateProfile } from '../types';
import { CompareTab } from './CompareTab';
import { CrossPartyAcceptability } from '../components/parties/CrossPartyAcceptability';

interface Props {
  clusters: ClusterProfile[];
  clusterSpreads: { party: string; n: number; [key: string]: string | number }[];
  fdProfiles: Record<string, FDCandidateProfile>;
}

// A single, selection-driven view: pick one party for its platform, several to compare.
// (Compare Policies + Party Platforms consolidated — see CompareTab.)
//
// Cross-party acceptability sits outside CompareTab because it is a whole-electorate measure:
// received / leaked / net are fixed properties of the typology posterior, so the card does not
// respond to the party selection the rest of the tab is driven by.
export function PartiesTab({ clusters, clusterSpreads, fdProfiles }: Props) {
  return (
    <div className="space-y-6">
      <CompareTab clusters={clusters} fdProfiles={fdProfiles} clusterSpreads={clusterSpreads} />
      <CrossPartyAcceptability />
    </div>
  );
}
