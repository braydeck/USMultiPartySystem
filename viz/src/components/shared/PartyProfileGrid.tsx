import { useState } from 'react';
import type { ClusterProfile } from '../../types';
import { PartyProfileCard } from './PartyProfileCard';
import { Button } from '@/components/ui/button';

interface Props {
  clusters: ClusterProfile[];
}

export function PartyProfileGrid({ clusters }: Props) {
  const [mode, setMode] = useState<'strength' | 'percentile'>('strength');

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">Party Profiles</h3>
          <p className="text-xs text-muted-foreground">
            {mode === 'strength'
              ? 'Intensity of each ideological position (σ from zero = factor model center).'
              : 'How each party compares to all American voters surveyed (percentile rank).'}
          </p>
        </div>
        <div className="flex gap-1 shrink-0 ml-4">
          <Button onClick={() => setMode('strength')}
            variant={mode === 'strength' ? 'default' : 'secondary'}
            size="sm">
            Strength
          </Button>
          <Button onClick={() => setMode('percentile')}
            variant={mode === 'percentile' ? 'default' : 'secondary'}
            size="sm">
            Percentile
          </Button>
        </div>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {clusters.map(cluster => (
          <PartyProfileCard key={cluster.party} cluster={cluster} mode={mode} />
        ))}
      </div>
    </div>
  );
}
