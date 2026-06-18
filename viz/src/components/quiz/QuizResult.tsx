import { useState } from 'react';
import type { ClusterProfile } from '../../types';
import { FactorBar } from '../shared/FactorBar';
import { PARTY_COLORS, PARTY_TAGLINES, PARTY_BLURBS } from '../../constants/parties';
import { resetUrlParams } from '../../hooks/useUrlState';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export interface RankEntry { party: string; partyName: string; score: number }

interface Props {
  cluster: ClusterProfile;
  seats: number;
  shared?: boolean;
  ranking?: RankEntry[];
  onRetake: () => void;
}

const SUBSTACK = 'https://braydendecker.substack.com/';

export function QuizResult({ cluster, seats, shared, ranking, onRetake }: Props) {
  const color = PARTY_COLORS[cluster.party] ?? '#6b7280';
  const tagline = PARTY_TAGLINES[cluster.party] ?? '';
  const blurb = PARTY_BLURBS[cluster.party] ?? '';
  const isBlend = !!ranking && ranking.length > 1 && Math.abs(ranking[0].score - ranking[1].score) < 0.03;
  const [copied, setCopied] = useState(false);

  const shareUrl = `https://usmultipartysystem.pages.dev/r/${cluster.party}`;
  const shareText = `I'm ${cluster.partyName} in a 9-party America. Which party are you?`;

  // Defining positions: the party's biggest deviations from the national average.
  const positions = (cluster.keyPositions ?? []).slice(0, 5);

  async function handleShare() {
    if (navigator.share) {
      try {
        await navigator.share({ title: 'Which party are you?', text: shareText, url: shareUrl });
        return;
      } catch { /* cancelled / unsupported — fall through to copy */ }
    }
    try {
      await navigator.clipboard.writeText(`${shareText} ${shareUrl}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* clipboard blocked — ignore */ }
  }

  return (
    <div className="max-w-xl mx-auto" aria-live="polite">
      <Card className="border-2 overflow-hidden mb-6" style={{ borderColor: color }}>
        <div className="px-6 py-5" style={{ backgroundColor: color + '22' }}>
          <div className="text-xs uppercase tracking-widest mb-1" style={{ color }}>
            {shared ? 'The Party' : 'Your Match'}
          </div>
          <div className="text-2xl font-bold" style={{ color }}>{cluster.partyName}</div>
          {tagline && <div className="text-sm font-medium text-foreground/80 mt-1">{tagline}</div>}
          {blurb && <p className="text-sm text-muted-foreground mt-2 leading-relaxed">{blurb}</p>}
          <div className="text-xs text-muted-foreground mt-3">{seats} of 873 House seats under proportional rules</div>
          {isBlend && (
            <div className="text-xs text-muted-foreground mt-1">
              Close call. You align almost as well with {ranking![1].partyName}.
            </div>
          )}
        </div>
        <div className="px-6 py-4 space-y-1">
          {(['F1','F2','F3','F4','F5'] as const).map(f => (
            <FactorBar key={f} factor={f} value={(cluster as unknown as Record<string, number>)[f]} />
          ))}
        </div>
      </Card>

      {!shared && ranking && ranking.length > 1 && (
        <div className="mb-6">
          <div className="text-sm font-semibold text-foreground mb-2">Your closest matches</div>
          <div className="space-y-1.5">
            {ranking.map(r => {
              const c = PARTY_COLORS[r.party] ?? '#6b7280';
              return (
                <div key={r.party} className="flex items-center gap-2">
                  <span className="w-36 shrink-0 text-sm text-foreground">{r.partyName}</span>
                  <div className="flex-1 h-2.5 bg-muted rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${Math.round(r.score * 100)}%`, backgroundColor: c }} />
                  </div>
                  <span className="w-10 text-right text-xs text-muted-foreground tabular-nums">{Math.round(r.score * 100)}%</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {positions.length > 0 && (
        <div className="mb-6">
          <div className="text-sm font-semibold text-foreground mb-2">
            What sets {cluster.partyName} apart
          </div>
          <ul className="space-y-1.5">
            {positions.map((p, i) => {
              const supports = p.direction === 'supports';
              return (
                <li key={i} className="text-sm text-foreground flex items-start gap-2">
                  <span className="mt-0.5 shrink-0" style={{ color: supports ? '#16a34a' : '#dc2626' }} aria-hidden="true">
                    {supports ? '↑' : '↓'}
                  </span>
                  <span>
                    <span className="sr-only">{supports ? 'More supportive: ' : 'More opposed: '}</span>
                    {p.question}
                  </span>
                </li>
              );
            })}
          </ul>
          <div className="text-xs text-muted-foreground mt-2">
            Positions where this party diverges most from the national average.
          </div>
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
