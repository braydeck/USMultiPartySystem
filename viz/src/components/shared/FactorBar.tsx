import { FACTOR_LABELS, FACTOR_POLES } from '../../constants/parties';
import { bamForZ, BAM_TEXT_LOW, BAM_TEXT_HIGH } from '../../lib/bam';
import { CHART_TYPE } from '../../constants/typography';

interface Props {
  factor: string;
  value: number; // z-score, roughly -2.5 to +2.5
  marker?: number; // optional respondent position (same z-scale) rendered as a dot
}

// Diverging from a centered zero: bam colour scale — teal (low pole) → magenta (high pole).
export function FactorBar({ factor, value, marker }: Props) {
  const label = FACTOR_LABELS[factor] ?? factor;
  const poles = FACTOR_POLES[factor];
  const isHigh = value >= 0;
  const barPct = Math.min((Math.abs(value) / 2.5) * 50, 50);
  const markerLeft = marker === undefined
    ? null
    : 50 + (Math.max(-2.5, Math.min(2.5, marker)) / 2.5) * 50;
  const mixed = Math.abs(value) < 0.3;
  const color = bamForZ(value);
  const textColor = mixed ? '#6b7280' : (isHigh ? BAM_TEXT_HIGH : BAM_TEXT_LOW);

  return (
    <div className="mb-2">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-muted-foreground">{label}</span>
        <span style={{ color: textColor }} className="font-mono font-semibold">
          {value >= 0 ? '+' : ''}{value.toFixed(2)}
        </span>
      </div>
      <div className="relative h-2.5 bg-muted rounded-full overflow-hidden">
        {isHigh ? (
          <div className="absolute top-0 h-full rounded-r-full transition-all"
            style={{ left: '50%', width: `${barPct}%`, backgroundColor: color }} />
        ) : (
          <div className="absolute top-0 h-full rounded-l-full transition-all"
            style={{ left: `${50 - barPct}%`, width: `${barPct}%`, backgroundColor: color }} />
        )}
        <div className="absolute top-0 left-1/2 w-px h-full bg-slate-400" />
        {markerLeft !== null && (
          <div
            className="absolute top-1/2 w-3 h-3 rounded-full border-2 border-white shadow-sm -translate-x-1/2 -translate-y-1/2"
            style={{ left: `${markerLeft}%`, backgroundColor: '#0f172a' }}
            title="You"
          />
        )}
      </div>
      {poles && (
        <div className="flex justify-between text-muted-foreground mt-0.5" style={{ fontSize: CHART_TYPE.smallTick }}>
          <span>{poles.low}</span>
          <span>{poles.high}</span>
        </div>
      )}
    </div>
  );
}
