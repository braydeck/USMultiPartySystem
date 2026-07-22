import { Card } from '@/components/ui/card';
import { CandidatePicker } from './CandidatePicker';
import { PresidencyGrid } from './PresidencyGrid';
import { FaceoffBar, ToneLegend } from './FaceoffBar';
import { MicrotargetTable } from './MicrotargetTable';
import { aggregateFaceoff } from './faceoff';
import type { SRCandidate, H2HResult, ECResult, MicrotargetGroup } from '../../lib/singleRace';
import { styleLabel } from '../../lib/singleRace';
import { PARTY_NAMES, getContrastText } from '../../constants/parties';

type Office = 'house' | 'senate' | 'presidency';

interface Props {
  index: number;
  candidates: SRCandidate[];
  partyOrder: string[];
  aCode: string;
  bCode: string;
  aCand: SRCandidate;
  bCand: SRCandidate;
  aColor: string;
  bColor: string;
  office: Office;
  raceLabel: string;
  h2h?: H2HResult;
  ec?: ECResult;
  groups: MicrotargetGroup[];
  coalitionLabel: string;
  canRemove: boolean;
  onChangeA: (code: string) => void;
  onChangeB: (code: string) => void;
  onRemove: () => void;
}

function candName(c: SRCandidate): string {
  const s = styleLabel(c);
  return s ? `${PARTY_NAMES[c.party]} (${s})` : PARTY_NAMES[c.party];
}

const pct = (x: number) => `${(x * 100).toFixed(1)}%`;

export function ScenarioCard(props: Props) {
  const { index, candidates, partyOrder, aCode, bCode, aCand, bCand, aColor, bColor,
    office, raceLabel, h2h, ec, groups, coalitionLabel, canRemove, onChangeA, onChangeB, onRemove } = props;

  const agg = aggregateFaceoff(groups);

  return (
    <Card className="p-4 space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">Scenario {index + 1}</h3>
        {canRemove && (
          <button type="button" onClick={onRemove}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            aria-label={`Remove scenario ${index + 1}`}>Remove</button>
        )}
      </div>

      <div className="flex items-start gap-2">
        <CandidatePicker candidates={candidates} partyOrder={partyOrder} value={aCode} onChange={onChangeA} />
        <span className="text-xs text-muted-foreground font-medium shrink-0 pt-2">vs</span>
        <CandidatePicker candidates={candidates} partyOrder={partyOrder} value={bCode} onChange={onChangeB} />
      </div>

      {/* Headline faceoff — the two-party split, each side labeled in-bar. */}
      <div className="space-y-1.5">
        <div className="flex items-baseline justify-between text-sm gap-2">
          <span className="font-medium truncate" style={{ color: aColor }}>{candName(aCand)} {agg.aPct.toFixed(0)}%</span>
          <span className="font-medium text-right truncate" style={{ color: bColor }}>{agg.bPct.toFixed(0)}% {candName(bCand)}</span>
        </div>
        <FaceoffBar f={agg} aColor={aColor} bColor={bColor} height={40} labels />
        <ToneLegend color={aColor} />
        {office !== 'presidency' && h2h && (
          <div className="flex items-center justify-between text-xs text-muted-foreground pt-0.5">
            <span>{raceLabel}</span>
            <span>
              <span className="px-1.5 py-0.5 rounded font-semibold"
                style={{ background: (h2h.winner === 'A' ? aColor : bColor) + '22', color: h2h.winner === 'A' ? aColor : bColor }}>
                {candName(h2h.winner === 'A' ? aCand : bCand)}
              </span>{' '}wins by {pct(h2h.margin)}
            </span>
          </div>
        )}
      </div>

      {office === 'presidency' && ec && (
        <Presidency ec={ec} aCand={aCand} bCand={bCand} aColor={aColor} bColor={bColor} />
      )}

      {/* Where the votes come from — numeric table, heatmapped per column in each party's color. */}
      <div className="pt-2 border-t border-border/50 space-y-1.5">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">Where the votes come from</div>
        <p className="text-[11px] text-muted-foreground -mt-0.5">
          {coalitionLabel}. Numbers are % of each group. <span className="font-medium text-foreground">Likely</span> already vote; <span className="font-medium text-foreground">Mobilize</span> = that side's voters who skip midterms; <span className="font-medium text-foreground">Persuade</span> = near-boundary voters who lean that side now but could be flipped either way.
        </p>
        <MicrotargetTable groups={groups} aColor={aColor} bColor={bColor} aParty={aCand.party} bParty={bCand.party} />
      </div>
    </Card>
  );
}

function TwoWayBar({ shareA, aColor, bColor }: { shareA: number; aColor: string; bColor: string }) {
  const a = Math.max(0, Math.min(1, shareA));
  return (
    <div className="flex h-7 rounded-md overflow-hidden text-xs font-semibold">
      <div className="flex items-center justify-start pl-2" style={{ width: `${a * 100}%`, background: aColor, color: getContrastText(aColor) }}>
        {a > 0.12 ? pct(a) : ''}
      </div>
      <div className="flex items-center justify-end pr-2" style={{ width: `${(1 - a) * 100}%`, background: bColor, color: getContrastText(bColor) }}>
        {1 - a > 0.12 ? pct(1 - a) : ''}
      </div>
    </div>
  );
}

function Presidency({ ec, aCand, bCand, aColor, bColor }: {
  ec: ECResult; aCand: SRCandidate; bCand: SRCandidate; aColor: string; bColor: string;
}) {
  const total = ec.evA + ec.evB;
  const winnerLabel = ec.winner === 'A' ? candName(aCand) : ec.winner === 'B' ? candName(bCand) : 'No majority';
  const winColor = ec.winner === 'A' ? aColor : ec.winner === 'B' ? bColor : '#6b7280';
  return (
    <div className="space-y-3 pt-1 border-t border-border/50">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium" style={{ color: aColor }}>{candName(aCand)} · {ec.evA}</span>
        <span className="font-medium text-right" style={{ color: bColor }}>{ec.evB} · {candName(bCand)}</span>
      </div>
      <div className="relative">
        <TwoWayBar shareA={total ? ec.evA / total : 0.5} aColor={aColor} bColor={bColor} />
        <div className="absolute top-0 bottom-0 w-px bg-slate-900" style={{ left: `${(ec.needed / total) * 100}%` }} title={`${ec.needed} to win`} />
      </div>
      <div className="text-xs text-muted-foreground">
        <span className="px-1.5 py-0.5 rounded font-semibold" style={{ background: winColor + '22', color: winColor }}>{winnerLabel}</span>
        {ec.winner !== 'tie' ? ` reaches ${ec.needed}` : ` — ${ec.evA}–${ec.evB}, neither reaches ${ec.needed}`}
      </div>
      <PresidencyGrid ec={ec} aColor={aColor} bColor={bColor} />
    </div>
  );
}
