import { Button } from '@/components/ui/button';

interface Props {
  question: string;
  domain: string;
  selected: number | null;
  onSelect: (v: number) => void;
}

const OPTIONS = [
  { value: 1, label: 'Strongly Agree' },
  { value: 0.75, label: 'Agree' },
  { value: 0.5, label: 'Neutral' },
  { value: 0.25, label: 'Disagree' },
  { value: 0, label: 'Strongly Disagree' },
];

export function QuizQuestion({ question, domain, selected, onSelect }: Props) {
  return (
    <div aria-live="polite">
      <div className="text-xs text-muted-foreground uppercase tracking-widest mb-2">{domain}</div>
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
