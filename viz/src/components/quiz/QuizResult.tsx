import { useState } from 'react';
import type { ClusterProfile } from '../../types';
import { FactorBar } from '../shared/FactorBar';
import { PARTY_COLORS, PARTY_TAGLINES, PARTY_BLURBS, DISPLAY_FACTORS } from '../../constants/parties';
import { resetUrlParams } from '../../hooks/useUrlState';
import { track } from '../../utils/analytics';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export interface RankEntry { party: string; partyName: string; prob: number }

interface Props {
  cluster: ClusterProfile;
  seats: number;
  shared?: boolean;
  ranking?: RankEntry[];
  onRetake: () => void;
  submissionId?: string;
  onVibe?: (v: 'fit' | 'miss') => void;
}

const SUBSTACK = 'https://braydendecker.substack.com/';

export function QuizResult({ cluster, seats, shared, ranking, onRetake, submissionId, onVibe }: Props) {
  const color = PARTY_COLORS[cluster.party] ?? '#6b7280';
  const tagline = PARTY_TAGLINES[cluster.party] ?? '';
  const blurb = PARTY_BLURBS[cluster.party] ?? '';
  const isBlend = !!ranking && ranking.length > 1 && (ranking[0].prob - ranking[1].prob) < 0.08;
  const [copied, setCopied] = useState(false);
  const [voted, setVoted] = useState<'fit' | 'miss' | null>(null);

  const shareUrl = `https://usmultipartysystem.pages.dev/r/${cluster.party}`;
  const shareText = `I'm ${cluster.partyName} in a multi-party America. Which party are you?`;

  // Defining positions: the party's biggest deviations from the national average.
  const positions = (cluster.keyPositions ?? []).slice(0, 5);

  // "See details" deep-links into the party comparison: this party + the two closest matches.
  const compareCodes = (ranking && ranking.length ? ranking.map(r => r.party) : [cluster.party]).join(',');
  const goToCompare = () => resetUrlParams({ tab: 'parties', section: 'compare', cmp: compareCodes });

  async function handleShare() {
    track('result_shared', { party: cluster.party });
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
          {DISPLAY_FACTORS.map(f => {
            const rec = cluster as unknown as Record<string, number>;
            return <FactorBar key={f} factor={f} value={rec[`z_${f}`] ?? rec[f]} />;
          })}
        </div>
      </Card>

      {!shared && onVibe && submissionId && (
        <div className="mb-6 rounded-lg border border-border p-4">
          {voted ? (
            <div className="text-sm text-muted-foreground">Thanks, noted.</div>
          ) : (
            <>
              <div className="text-sm font-semibold text-foreground mb-2">Does this match how you see yourself?</div>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  className="flex-1"
                  onClick={() => { setVoted('fit'); onVibe('fit'); }}
                >
                  That sounds right
                </Button>
                <Button
                  variant="secondary"
                  className="flex-1"
                  onClick={() => { setVoted('miss'); onVibe('miss'); }}
                >
                  Not really me
                </Button>
              </div>
            </>
          )}
        </div>
      )}

      {!shared && ranking && ranking.length > 1 && (
        <div className="mb-6">
          <div className="text-sm font-semibold text-foreground mb-2">Estimated chance you're each party</div>
          <div className="space-y-1.5">
            {ranking.map(r => {
              const c = PARTY_COLORS[r.party] ?? '#6b7280';
              return (
                <div key={r.party} className="flex items-center gap-2">
                  <span className="w-36 shrink-0 text-sm text-foreground">{r.partyName}</span>
                  <div className="flex-1 h-2.5 bg-muted rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${Math.round(r.prob * 100)}%`, backgroundColor: c }} />
                  </div>
                  <span className="w-10 text-right text-xs text-muted-foreground tabular-nums">{Math.round(r.prob * 100)}%</span>
                </div>
              );
            })}
          </div>
          <div className="text-xs text-muted-foreground mt-2">
            Estimated by placing your answers in the model's 5-factor space and comparing to each party's distribution (a soft classification, like the model uses, from this {''}quiz subset).
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
        <Button onClick={goToCompare} variant="secondary" className="w-full py-3">
          {shared ? `See ${cluster.partyName} in detail →` : 'See the details: you vs your closest parties →'}
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
