import { Button } from '@/components/ui/button';

interface Props<T extends string> {
  label?: string;
  value: T;
  onChange: (v: T) => void;
  options: readonly T[];
  labels: Record<T, string>;
  size?: 'sm' | 'default';
}

export function ToggleGroup<T extends string>({ label, value, onChange, options, labels, size = 'sm' }: Props<T>) {
  return (
    <div className="flex items-center gap-2">
      {label && <span className="text-xs text-muted-foreground uppercase tracking-widest">{label}</span>}
      <div className="flex gap-1">
        {options.map(o => (
          <Button key={o} onClick={() => onChange(o)}
            variant={value === o ? 'default' : 'secondary'} size={size}>
            {labels[o]}
          </Button>
        ))}
      </div>
    </div>
  );
}
