import { useUrlState, urlForParams } from '../hooks/useUrlState';
import type { ClusterProfile, FDCandidateProfile } from '../types';
import { CompareTab } from './CompareTab';
import { PartyPlatform } from './PartyPlatform';
import { ToggleGroup } from '../components/shared/ToggleGroup';
import { StickyControlBar } from '../components/shared/StickyControlBar';

interface Props {
  clusters: ClusterProfile[];
  clusterSpreads: { party: string; n: number; [key: string]: string | number }[];
  fdProfiles: Record<string, FDCandidateProfile>;
}

type Section = 'compare' | 'platform';

export function PartiesTab({ clusters, clusterSpreads, fdProfiles }: Props) {
  const [section, setSection] = useUrlState<Section>('section', 'compare', { allowed: ['compare', 'platform'] });

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-1">Parties</h2>
        <p className="text-muted-foreground text-sm">
          A 10-party model of the American electorate, including the reintroduced Order and
          Opportunity Party (C7). Each party reflects a distinct ideological constellation
          derived from CES 2024 survey data.
        </p>
      </div>

      <StickyControlBar>
        <ToggleGroup label="View" value={section} onChange={setSection}
          options={['compare', 'platform'] as const}
          labels={{ compare: 'Compare Policies', platform: 'Party Platforms' }}
          hrefFor={v => urlForParams({ section: v === 'compare' ? null : v })} />
      </StickyControlBar>

      {section === 'compare' && (
        <CompareTab clusters={clusters} fdProfiles={fdProfiles} />
      )}

      {section === 'platform' && (
        <PartyPlatform clusters={clusters} clusterSpreads={clusterSpreads} />
      )}
    </div>
  );
}
