import { useState } from 'react';
import type { ClusterProfile, VoteModelRow } from '../../types';
import { FactorBar } from '../shared/FactorBar';
import { PARTY_COLORS, PARTY_TAGLINES } from '../../constants/parties';
import { resetUrlParams } from '../../hooks/useUrlState';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface Props {
  cluster: ClusterProfile;
  seats: number;
  topScore?: number;
  secondScore?: number;
  shared?: boolean;
  houseVotes: VoteModelRow[];
  onRetake: () => void;
}

const SUBSTACK = 'https://braydendecker.substack.com/';

export function QuizResult({ cluster, seats, topScore, secondScore, shared, houseVotes, onRetake }: Props) {
  const color = PARTY_COLORS[cluster.party] ?? '#6b7280';
  const tagline = PARTY_TAGLINES[cluster.party] ?? '';
  const isBlend = topScore != null && secondScore != null && Math.abs(topScore - secondScore) < 0.03;
  const [copied, setCopied] = useState(false);

  const shareUrl = `https://usmultipartysystem.pages.dev/r/${cluster.party}`;
  const shareText = `I'm ${cluster.partyName} in a 9-party America. Which party are you?`;

  async function handleShare() {
    if (navigator.share) {
      try {
        await navigator.share({ title: 'Which party are you?', text: shareText, url: shareUrl });
        return;
      } catch { /* user cancelled or unsupported — fall through to copy */ }
    }
    try {
      await navigator.clipboard.writeText(`${shareText} ${shareUrl}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* clipboard blocked — ignore */ }
  }

  const strongSupport = houseVotes
    .filter(r => { const cv = cluster.variables[r.variable]; return cv && cv.pct > 75; })
    .slice(0, 3);
  const strongOppose = houseVotes
    .filter(r => { const cv = cluster.variables[r.variable]; return cv && cv.pct < 25; })
    .slice(0, 3);

  return (
    <div className="max-w-xl mx-auto" aria-live="polite">
      <Card className="border-2 overflow-hidden mb-6" style={{ borderColor: color }}>
        <div className="px-6 py-5" style={{ backgroundColor: color + '22' }}>
          <div className="text-xs uppercase tracking-widest mb-1" style={{ color }}>
            {shared ? 'The Party' : 'Your Match'}
          </div>
          <div className="text-2xl font-bold" style={{ color }}>{cluster.partyName}</div>
          {tagline && <div className="text-sm text-foreground/80 mt-1">{tagline}</div>}
          <div className="text-sm text-muted-foreground mt-2">{seats} of 873 House seats</div>
          {isBlend && (
            <div className="text-xs text-muted-foreground mt-2">
              Close call. You also align closely with a neighboring party.
            </div>
          )}
        </div>
        <div className="px-6 py-4 space-y-1">
          {(['F1','F2','F3','F4','F5'] as const).map(f => (
            <FactorBar key={f} factor={f} value={(cluster as unknown as Record<string, number>)[f]} />
          ))}
        </div>
      </Card>

      {strongSupport.length > 0 && (
        <div className="mb-4">
          <div className="text-sm font-semibold text-green-600 mb-2">Strongly supports:</div>
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
          <div className="text-sm font-semibold text-red-600 mb-2">Strongly opposes:</div>
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

      <div className="space-y-2">
        <Button onClick={handleShare} className="w-full py-3 text-white" style={{ backgroundColor: color }}>
          {copied ? '✓ Link copied' : 'Share your result'}
        </Button>
        <Button onClick={() => resetUrlParams({ tab: 'house' })} variant="secondary" className="w-full py-3">
          Explore the full simulation →
        </Button>
        <div className="flex items-center justify-between pt-1 text-sm">
          <button onClick={onRetake} className="text-muted-foreground hover:text-foreground underline">
            {shared ? 'Take the quiz yourself' : 'Retake quiz'}
          </button>
          <a href={SUBSTACK} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline font-medium">
            Read the argument →
          </a>
        </div>
      </div>
    </div>
  );
}
