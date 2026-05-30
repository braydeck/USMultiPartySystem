import type { ClusterProfile, VoteModelRow } from '../../types';
import { FactorBar } from '../shared/FactorBar';
import { PARTY_COLORS } from '../../constants/parties';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface Props {
  cluster: ClusterProfile;
  topScore: number;
  secondScore: number;
  houseVotes: VoteModelRow[];
  onRetake: () => void;
}

export function QuizResult({ cluster, topScore, secondScore, houseVotes, onRetake }: Props) {
  const color = PARTY_COLORS[cluster.party] ?? '#6b7280';
  const isBlend = Math.abs(topScore - secondScore) < 0.05;

  const strongSupport = houseVotes
    .filter(r => {
      const cv = cluster.variables[r.variable];
      return cv && cv.pct > 75;
    })
    .slice(0, 3);

  const strongOppose = houseVotes
    .filter(r => {
      const cv = cluster.variables[r.variable];
      return cv && cv.pct < 25;
    })
    .slice(0, 3);

  return (
    <div className="max-w-xl mx-auto" aria-live="polite">
      <Card className="border-2 overflow-hidden mb-6" style={{ borderColor: color }}>
        <div className="px-6 py-4" style={{ backgroundColor: color + '22' }}>
          <div className="text-xs uppercase tracking-widest mb-1" style={{ color }}>Your Match</div>
          <div className="text-2xl font-bold" style={{ color }}>{cluster.partyName}</div>
          <div className="text-sm text-muted-foreground mt-1">
            {cluster.seatsHouse} House seats
          </div>
          {isBlend && (
            <div className="text-xs text-yellow-400 mt-2">
              (Close match — you may also align with a neighboring party)
            </div>
          )}
        </div>
        <div className="px-6 py-4 space-y-1">
          {(['F1','F2','F3','F4','F5'] as const).map(f => (
            <FactorBar key={f} factor={f} value={(cluster as any)[f]} />
          ))}
        </div>
      </Card>

      {strongSupport.length > 0 && (
        <div className="mb-4">
          <div className="text-sm font-semibold text-green-400 mb-2">Strongly supports:</div>
          <ul className="space-y-1">
            {strongSupport.map(r => (
              <li key={r.variable} className="text-sm text-foreground flex items-start gap-2">
                <span className="text-green-500 mt-0.5" aria-hidden="true">✓</span>
                <span className="sr-only">Supports: </span>
                {r.question}
              </li>
            ))}
          </ul>
        </div>
      )}

      {strongOppose.length > 0 && (
        <div className="mb-6">
          <div className="text-sm font-semibold text-red-400 mb-2">Strongly opposes:</div>
          <ul className="space-y-1">
            {strongOppose.map(r => (
              <li key={r.variable} className="text-sm text-foreground flex items-start gap-2">
                <span className="text-red-500 mt-0.5" aria-hidden="true">✗</span>
                <span className="sr-only">Opposes: </span>
                {r.question}
              </li>
            ))}
          </ul>
        </div>
      )}

      <Button
        onClick={onRetake}
        variant="secondary"
        className="w-full py-3"
      >
        Retake Quiz
      </Button>
    </div>
  );
}
