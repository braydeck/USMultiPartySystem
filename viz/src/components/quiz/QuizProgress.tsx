interface Props {
  current: number;
  total: number;
}

export function QuizProgress({ current, total }: Props) {
  const pct = (current / total) * 100;
  return (
    <div className="mb-6" aria-live="polite" aria-atomic="true">
      <span className="sr-only">Question {current} of {total}</span>
      <div className="flex justify-between text-xs text-muted-foreground mb-1">
        <span>Question {current} of {total}</span>
        <span>{Math.round(pct)}%</span>
      </div>
      <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-teal-500 rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
