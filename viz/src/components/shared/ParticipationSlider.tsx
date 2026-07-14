export const GAP_STOPS = [0, 25, 50, 75, 100] as const;

interface Props {
  /** % of the inter-force turnout gap that has closed (one of GAP_STOPS). */
  value: number;
  onChange: (v: number) => void;
}

/** Gap-compression slider: observed 2024 turnout (0%) → full parity (100%).
 *  Sweeps how much each force's turnout gap closes; the datasets are precomputed
 *  per stop, so this snaps to the 5 GAP_STOPS. */
export function ParticipationSlider({ value, onChange }: Props) {
  const idx = Math.max(0, GAP_STOPS.indexOf(value as typeof GAP_STOPS[number]));
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted-foreground uppercase tracking-widest">Participation</span>
      <div className="flex flex-col gap-0.5 w-[150px]">
        <input
          type="range" min={0} max={GAP_STOPS.length - 1} step={1} value={idx}
          onChange={e => onChange(GAP_STOPS[Number(e.target.value)])}
          className="w-full accent-indigo-600 cursor-pointer"
          aria-label="Turnout gap closed"
        />
        <div className="flex justify-between text-[9px] text-muted-foreground leading-none">
          <span>Observed</span>
          <span className="font-semibold text-foreground">{value === 100 ? 'Parity' : `${value}%`}</span>
          <span>Parity</span>
        </div>
      </div>
    </div>
  );
}
