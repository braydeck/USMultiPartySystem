import { Button, buttonVariants } from '@/components/ui/button';
import { StateLink } from './StateLink';
import { FIELD_LABEL } from '../../constants/typography';

interface Props<T extends string> {
  label?: string;
  value: T;
  onChange: (v: T) => void;
  options: readonly T[];
  labels: Record<T, string>;
  size?: 'sm' | 'default';
  /** When set, render each option as a real link to this URL so it supports "open in new tab". */
  hrefFor?: (v: T) => string;
}

export function ToggleGroup<T extends string>({ label, value, onChange, options, labels, size = 'sm', hrefFor }: Props<T>) {
  return (
    <div className="flex items-center gap-2">
      {label && <span className={FIELD_LABEL}>{label}</span>}
      <div className="flex gap-1">
        {options.map(o => {
          const variant = value === o ? 'default' : 'secondary';
          if (hrefFor) {
            return (
              <StateLink key={o} href={hrefFor(o)} onNavigate={() => onChange(o)}
                className={buttonVariants({ variant, size })}>
                {labels[o]}
              </StateLink>
            );
          }
          return (
            <Button key={o} onClick={() => onChange(o)} variant={variant} size={size}>
              {labels[o]}
            </Button>
          );
        })}
      </div>
    </div>
  );
}
