import { Button } from '@/components/ui/button';
import { FIELD_LABEL } from '../../constants/typography';

interface Option { value: number; label: string }

interface Props {
  question: string;
  domain: string;
  section?: string;
  instruction?: string;
  selected: number | null;
  onSelect: (v: number) => void;
  options?: Option[];
}

const DEFAULT_OPTIONS: Option[] = [
  { value: 1, label: 'Strongly Agree' },
  { value: 0.75, label: 'Agree' },
  { value: 0.5, label: 'Neutral' },
  { value: 0.25, label: 'Disagree' },
  { value: 0, label: 'Strongly Disagree' },
];

export function QuizQuestion({ question, domain, section, instruction, selected, onSelect, options }: Props) {
  const OPTIONS = options ?? DEFAULT_OPTIONS;
  return (
    <div aria-live="polite">
      <div className={`${FIELD_LABEL} mb-1`}>
        {section ?? domain}{section && domain ? ` · ${domain}` : ''}
      </div>
      {instruction && <div className="text-sm text-muted-foreground mb-3">{instruction}</div>}
      <h3 className="text-xl font-semibold text-foreground mb-6 leading-snug">{question}</h3>
      <div className="flex flex-col gap-2">
        {OPTIONS.map(opt => (
          <Button
            key={opt.value}
            onClick={() => onSelect(opt.value)}
            variant={selected === opt.value ? 'default' : 'outline'}
            className="justify-start px-4 py-3"
          >
            {opt.label}
          </Button>
        ))}
      </div>
    </div>
  );
}
