import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { SHIFT_AXES } from '../../lib/singleRace';
import { FACTOR_POLES, FACTOR_LABELS } from '../../constants/parties';

const RANGE = 0.75; // ± population SD
const STEP = 0.05;

interface Props {
  opinionSigma: number[];
  turnoutSigma: number[];
  setOpinionSigma: (v: number[]) => void;
  setTurnoutSigma: (v: number[]) => void;
  essFraction: number;
}

function fmt(v: number): string {
  return `${v >= 0 ? '+' : ''}${v.toFixed(2)}σ`;
}

function AxisSlider({ factor, value, onChange }: {
  factor: string; value: number; onChange: (v: number) => void;
}) {
  const poles = FACTOR_POLES[factor];
  return (
    <div className="space-y-0.5">
      <div className="flex items-center justify-between text-[11px] text-muted-foreground">
        <span>{poles.low}</span>
        <span className="font-medium text-foreground tabular-nums">{value === 0 ? '—' : fmt(value)}</span>
        <span>{poles.high}</span>
      </div>
      <input
        type="range"
        min={-RANGE}
        max={RANGE}
        step={STEP}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        aria-label={FACTOR_LABELS[factor]}
        className="w-full accent-slate-700"
      />
    </div>
  );
}

function Group({ title, blurb, sigma, setSigma, footer }: {
  title: string; blurb: string; sigma: number[]; setSigma: (v: number[]) => void; footer?: React.ReactNode;
}) {
  const setAxis = (idx: number, v: number) => {
    const next = sigma.slice();
    next[idx] = v;
    setSigma(next);
  };
  const active = SHIFT_AXES.some(a => sigma[a.idx] !== 0);
  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between gap-2">
        <div>
          <h4 className="text-sm font-semibold">{title}</h4>
          <p className="text-[11px] text-muted-foreground">{blurb}</p>
        </div>
        {active && (
          <button type="button" onClick={() => setSigma([0, 0, 0, 0, 0])}
            className="text-[11px] text-muted-foreground hover:text-foreground shrink-0">Reset</button>
        )}
      </div>
      <div className="space-y-2.5">
        {SHIFT_AXES.map(a => (
          <AxisSlider key={a.factor} factor={a.factor} value={sigma[a.idx]} onChange={v => setAxis(a.idx, v)} />
        ))}
      </div>
      {footer}
    </div>
  );
}

export function ElectorateShift({ opinionSigma, turnoutSigma, setOpinionSigma, setTurnoutSigma, essFraction }: Props) {
  const [open, setOpen] = useState(false);
  const anyActive = SHIFT_AXES.some(a => opinionSigma[a.idx] !== 0 || turnoutSigma[a.idx] !== 0);

  return (
    <Card className="p-4">
      <button type="button" onClick={() => setOpen(o => !o)} aria-expanded={open}
        className="w-full flex items-center justify-between gap-2">
        <div className="text-left">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">
            Shift the electorate {anyActive && <span className="text-foreground normal-case tracking-normal font-normal">· active</span>}
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Model a different electorate. Zero = today's electorate.
          </p>
        </div>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ transform: open ? 'rotate(180deg)' : undefined }}><path d="M6 9l6 6 6-6" /></svg>
      </button>
      {open && (
        <div className="mt-4 grid gap-6 md:grid-cols-2">
          <Group
            title="Opinion"
            blurb="The public changes its mind. Moves swing voters; committed partisans hold. Only bites where the two candidates differ."
            sigma={opinionSigma}
            setSigma={setOpinionSigma}
          />
          <Group
            title="Turnout"
            blurb="A different mix turns out. Re-weights who shows up toward each pole."
            sigma={turnoutSigma}
            setSigma={setTurnoutSigma}
            footer={
              <p className="text-[11px] text-muted-foreground pt-1">
                Effective electorate: {(essFraction * 100).toFixed(0)}% of today's
                {essFraction < 0.5 && ' — leaning on a thin slice'}
              </p>
            }
          />
        </div>
      )}
    </Card>
  );
}
