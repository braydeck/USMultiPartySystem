import { Card } from '@/components/ui/card';
import { CandidatePicker } from './CandidatePicker';
import { PresidencyGrid } from './PresidencyGrid';
import type { SRCandidate, H2HResult, ECResult } from '../../lib/singleRace';
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
  canRemove: boolean;
  onChangeA: (code: string) => void;
  onChangeB: (code: string) => void;
  onRemove: () => void;
}

function candName(c: SRCandidate): string {
  const s = styleLabel(c);
  return s ? `${PARTY_NAMES[c.party]} (${s})` : PARTY_NAMES[c.party];
}

function pct(x: number): string {
  return `${(x * 100).toFixed(1)}%`;
}

export function ScenarioCard(props: Props) {
  const { index, candidates, partyOrder, aCode, bCode, aCand, bCand, aColor, bColor,
    office, raceLabel, h2h, ec, canRemove, onChangeA, onChangeB, onRemove } = props;

  return (
    <Card className="p-4 space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">
          Scenario {index + 1}
        </h3>
        {canRemove && (
          <button
            type="button"
            onClick={onRemove}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            aria-label={`Remove scenario ${index + 1}`}
          >
            Remove
          </button>
        )}
      </div>

      <div className="flex items-start gap-2">
        <CandidatePicker candidates={candidates} partyOrder={partyOrder} value={aCode} onChange={onChangeA} />
        <span className="text-xs text-muted-foreground font-medium shrink-0 pt-2">vs</span>
        <CandidatePicker candidates={candidates} partyOrder={partyOrder} value={bCode} onChange={onChangeB} />
      </div>

      {office !== 'presidency' && h2h && (
        <SingleRace h2h={h2h} aCand={aCand} bCand={bCand} aColor={aColor} bColor={bColor} raceLabel={raceLabel} />
      )}

      {office === 'presidency' && ec && (
        <Presidency ec={ec} aCand={aCand} bCand={bCand} aColor={aColor} bColor={bColor} />
      )}
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

function SingleRace({ h2h, aCand, bCand, aColor, bColor, raceLabel }: {
  h2h: H2HResult; aCand: SRCandidate; bCand: SRCandidate; aColor: string; bColor: string; raceLabel: string;
}) {
  const winner = h2h.winner === 'A' ? aCand : bCand;
  const winColor = h2h.winner === 'A' ? aColor : bColor;
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium" style={{ color: aColor }}>{candName(aCand)}</span>
        <span className="font-medium text-right" style={{ color: bColor }}>{candName(bCand)}</span>
      </div>
      <TwoWayBar shareA={h2h.shareA} aColor={aColor} bColor={bColor} />
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{raceLabel}</span>
        <span>
          <span className="px-1.5 py-0.5 rounded font-semibold" style={{ background: winColor + '22', color: winColor }}>
            {candName(winner)}
          </span>
          {' '}wins by {pct(h2h.margin)}
        </span>
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
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium" style={{ color: aColor }}>{candName(aCand)} · {ec.evA}</span>
        <span className="font-medium text-right" style={{ color: bColor }}>{ec.evB} · {candName(bCand)}</span>
      </div>
      <div className="relative">
        <TwoWayBar shareA={total ? ec.evA / total : 0.5} aColor={aColor} bColor={bColor} />
        {/* 270 threshold marker */}
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
