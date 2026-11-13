import { Button } from '@/components/ui/button';
import { FACTOR_LABELS, FACTOR_POLES } from '../../constants/parties';
import { bamForZ } from '../../lib/bam';

// Short, readable labels: a fresh visitor won't know "SO/ID/RT/PC". Full factor names stay on
// the button tooltips and the chart axes.
export const AXIS_WORD: Record<string, string> = {
  party: 'Party', F1: 'Security', F2: 'Distrust', F4: 'Traditionalism', F5: 'Econ. Right', seats: 'Seats',
};

export function ControlSection({ label, options, value, onChange }: {
  label: string;
  options: readonly string[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-start gap-1.5">
      <span className="w-12 shrink-0 pt-1 text-xs text-muted-foreground font-semibold">{label}</span>
      <div className="flex flex-wrap gap-1">
        {options.map(opt => (
          <Button key={opt} onClick={() => onChange(opt)}
            title={opt === 'seats' ? 'Seats' : opt === 'party' ? 'Party color' : (FACTOR_LABELS[opt] ?? opt)}
            variant={value === opt ? 'default' : 'secondary'} size="sm" className="px-2 h-6 flex-none">
            {AXIS_WORD[opt] ?? opt}
          </Button>
        ))}
      </div>
    </div>
  );
}

/** Size picker. Equal size and a size dimension are mutually exclusive: with equal size on, no
 *  dimension is highlighted, and picking a dimension turns equal size off. */
export function SizeControl({ options, value, equal, onChange, onEqualChange }: {
  options: readonly string[];
  value: string;
  equal: boolean;
  onChange: (v: string) => void;
  onEqualChange: (v: boolean) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <ControlSection label="Size" options={options} value={equal ? '' : value}
        onChange={v => { onChange(v); onEqualChange(false); }} />
      <Button onClick={() => onEqualChange(!equal)} variant={equal ? 'default' : 'secondary'}
        size="sm" className="px-2 h-6">
        {equal ? '⊙ Equal size' : '○ Equal size'}
      </Button>
    </div>
  );
}

/** Colour picker with the diverging legend, labelled by the chosen factor's two poles. */
export function ColorControl({ options, value, onChange }: {
  options: readonly string[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1">
      <ControlSection label="Color" options={options} value={value} onChange={onChange} />
      {value !== 'party' && (
        <div className="flex items-center gap-1 pl-[3.375rem]">
          <span className="text-4xs text-muted-foreground">{FACTOR_POLES[value]?.low}</span>
          <div className="h-1.5 w-14 rounded-full"
            style={{ background: `linear-gradient(to right, ${bamForZ(-2.5)}, ${bamForZ(0)}, ${bamForZ(2.5)})` }} />
          <span className="text-4xs text-muted-foreground">{FACTOR_POLES[value]?.high}</span>
        </div>
      )}
    </div>
  );
}
