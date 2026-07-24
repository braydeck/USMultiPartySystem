import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { CandidatePicker } from './CandidatePicker';
import { PresidencyGrid } from './PresidencyGrid';
import { FaceoffBar, ToneLegend } from './FaceoffBar';
import { MicrotargetTable } from './MicrotargetTable';
import { aggregateFaceoff, type ElectionCycle } from './faceoff';
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
  cycle: ElectionCycle;
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
    office, cycle, raceLabel, h2h, ec, groups, coalitionLabel: _coalitionLabel, canRemove, onChangeA, onChangeB, onRemove } = props;

  const [aMobRate, setAMobRate] = useState(0);
  const [bMobRate, setBMobRate] = useState(0);

  const agg = aggregateFaceoff(groups, cycle, aMobRate, bMobRate);

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

      {/* Projected result among likely voters */}
      <div className="space-y-1.5">
        <div className="flex items-baseline justify-between text-xs text-muted-foreground">
          <span className="font-medium" style={{ color: aColor }}>{candName(aCand)}</span>
          <span className="font-medium" style={{ color: bColor }}>{candName(bCand)}</span>
        </div>
        <EffectiveVoteBar aPct={agg.aLikelyPct} aColor={aColor} bColor={bColor} />
        <div className="flex items-baseline justify-between text-[11px]">
          {office !== 'presidency' && h2h ? (
            <>
              <span className="text-muted-foreground">{raceLabel}</span>
              <span>
                <span className="px-1.5 py-0.5 rounded font-semibold"
                  style={{ background: (h2h.winner === 'A' ? aColor : bColor) + '22', color: h2h.winner === 'A' ? aColor : bColor }}>
                  {candName(h2h.winner === 'A' ? aCand : bCand)}
                </span>{' '}
                <span className="text-muted-foreground">wins by {pct(h2h.margin)}</span>
              </span>
            </>
          ) : (
            <span className="text-muted-foreground">
              If everyone voted: <span style={{ color: aColor }} className="font-medium">{agg.aPct.toFixed(0)}%</span>
              {' / '}
              <span style={{ color: bColor }} className="font-medium">{agg.bPct.toFixed(0)}%</span>
            </span>
          )}
        </div>
      </div>

      {/* Mobilization — turnout scenario modeling */}
      <div className="space-y-2 pt-2 border-t border-border/40">
        <div>
          <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">Turnout mobilization</div>
          <p className="text-[10px] text-muted-foreground mt-0.5">
            Each slider converts unlikely voters into active ones, shifting the projected result above.
          </p>
        </div>
        <div className="flex items-center gap-4">
          <MobSlider label={aCand.party} color={aColor} value={aMobRate} onChange={setAMobRate} />
          <MobSlider label={bCand.party} color={bColor} value={bMobRate} onChange={setBMobRate} />
        </div>
      </div>

      {office === 'presidency' && ec && (
        <Presidency ec={ec} aCand={aCand} bCand={bCand} aColor={aColor} bColor={bColor} />
      )}

      {/* Where the votes come from — numeric table, heatmapped per column in each party's color. */}
      <div className="pt-2 border-t border-border/50 space-y-1.5">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">Where the votes come from</div>
        <p className="text-[11px] text-muted-foreground -mt-0.5">
          Each cluster's electorate splits into three pools.{' '}
          <span className="font-medium text-foreground">Likely</span>: reliable turnout.{' '}
          <span className="font-medium text-foreground">Mobilize</span>: aligned but dormant—the gap between support and showing up.{' '}
          <span className="font-medium text-foreground">Persuade</span>: near the ideological boundary between candidates.
        </p>
        <div className="space-y-1">
          <div className="flex items-baseline justify-between text-[11px]">
            <span className="text-muted-foreground">Full population: <span style={{ color: aColor }} className="font-semibold">{agg.aPct.toFixed(0)}% {aCand.party}</span></span>
            <span style={{ color: bColor }} className="font-semibold">{bCand.party} {agg.bPct.toFixed(0)}%</span>
          </div>
          <FaceoffBar f={agg} aColor={aColor} bColor={bColor} height={22} />
          <ToneLegend color={aColor} />
        </div>
        <MicrotargetTable groups={groups} cycle={cycle} aMobRate={aMobRate} bMobRate={bMobRate} aColor={aColor} bColor={bColor} aParty={aCand.party} bParty={bCand.party} />
      </div>
    </Card>
  );
}

function EffectiveVoteBar({ aPct, aColor, bColor }: { aPct: number; aColor: string; bColor: string }) {
  const a = Math.max(0, Math.min(100, aPct));
  return (
    <div className="flex rounded-md overflow-hidden border border-border" style={{ height: 32 }}>
      <div className="flex items-center justify-start pl-2 text-xs font-semibold transition-all duration-150"
        style={{ width: `${a}%`, background: aColor, color: getContrastText(aColor) }}>
        {a > 12 ? `${a.toFixed(0)}%` : ''}
      </div>
      <div className="flex items-center justify-end pr-2 text-xs font-semibold transition-all duration-150"
        style={{ width: `${100 - a}%`, background: bColor, color: getContrastText(bColor) }}>
        {100 - a > 12 ? `${(100 - a).toFixed(0)}%` : ''}
      </div>
    </div>
  );
}

function MobSlider({ label, color, value, onChange }: {
  label: string; color: string; value: number; onChange: (v: number) => void;
}) {
  return (
    <div className="flex-1 flex items-center gap-2">
      <label className="text-[10px] font-semibold uppercase tracking-wider shrink-0" style={{ color }}>
        {label} mobilize
      </label>
      <input
        type="range" min={0} max={1} step={0.01} value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="flex-1 h-1.5 accent-current cursor-pointer"
        style={{ color }}
      />
      <span className="text-[10px] tabular-nums text-muted-foreground w-7 text-right">
        {(value * 100).toFixed(0)}%
      </span>
    </div>
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
