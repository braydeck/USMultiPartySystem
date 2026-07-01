import { useState } from 'react';
import type { QuizQuestion as QuizQuestionType, ClusterProfile, HouseSeat } from '../types';
import { QuizQuestion } from '../components/quiz/QuizQuestion';
import { QuizProgress } from '../components/quiz/QuizProgress';
import { QuizResult, type RankEntry } from '../components/quiz/QuizResult';
import { classifyQuiz, type SpreadRow } from '../utils/quizScoring';
import { useUrlState } from '../hooks/useUrlState';
import { F5_ORDER_WFP } from '../constants/parties';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface Props {
  questions: QuizQuestionType[];
  clusters: ClusterProfile[];
  houseSeats: HouseSeat[];
  spreads: SpreadRow[];
}

export function QuizTab({ questions, clusters, houseSeats, spreads }: Props) {
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [current, setCurrent] = useState(0);
  const [ranking, setRanking] = useState<RankEntry[] | null>(null);
  // Result party lives in the URL so it can be deep-linked / shared (?result=STY).
  const [resultParty, setResultParty] = useUrlState<string>('result', '', {
    allowed: [...F5_ORDER_WFP],
    push: true,
  });

  const seatsById: Record<string, number> = Object.fromEntries(
    houseSeats.map(h => [String(h.party), h.national])
  );

  function handleSelect(value: number) {
    setAnswers(prev => ({ ...prev, [current]: value }));
  }

  function handleNext() {
    if (current < questions.length - 1) {
      setCurrent(c => c + 1);
    } else {
      const scores = classifyQuiz(questions, answers, spreads);
      const top: RankEntry[] = scores.slice(0, 4).map(s => {
        const cl = clusters.find(c => c.id === s.clusterId);
        return { party: cl?.party ?? '', partyName: cl?.partyName ?? '', prob: s.prob };
      });
      setRanking(top);
      if (top[0].party) setResultParty(top[0].party);
    }
  }

  function handleBack() {
    if (current > 0) setCurrent(c => c - 1);
  }

  function handleRetake() {
    setAnswers({});
    setCurrent(0);
    setRanking(null);
    setResultParty('');
  }

  // Result view — either just taken (ranking set) or arrived via a shared ?result=CODE link.
  if (resultParty) {
    const cluster = clusters.find(c => c.party === resultParty);
    if (cluster) {
      const isShared = !ranking;
      return (
        <div className="space-y-8">
          <div>
            <h2 className="text-2xl font-bold text-foreground mb-1">
              {isShared ? 'A Political Profile' : 'Your Political Profile'}
            </h2>
            <p className="text-muted-foreground text-sm">
              {isShared
                ? "Someone shared this result. Here's the party. Take the quiz yourself to find yours."
                : "Based on your answers, here's the party you align with most."}
            </p>
          </div>
          <QuizResult
            cluster={cluster}
            seats={seatsById[cluster.id] ?? 0}
            shared={isShared}
            ranking={ranking ?? undefined}
            onRetake={handleRetake}
          />
        </div>
      );
    }
  }

  const q = questions[current];
  const hasAnswer = answers[current] !== undefined;

  return (
    <div className="space-y-8 max-w-xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-1">Which Party Are You?</h2>
        <p className="text-muted-foreground text-sm">
          {questions.length} questions to find which of the 10 parties best matches your political values.
        </p>
      </div>

      <QuizProgress current={current + 1} total={questions.length} />

      <Card className="p-6">
        <QuizQuestion
          question={q.question}
          domain={q.domain}
          section={q.section}
          instruction={q.instruction}
          selected={answers[current] ?? null}
          onSelect={handleSelect}
          options={q.options}
        />
      </Card>

      <div className="flex justify-between">
        <Button onClick={handleBack} disabled={current === 0} variant="secondary">
          Back
        </Button>
        <Button onClick={handleNext} disabled={!hasAnswer} variant="default">
          {current === questions.length - 1 ? 'See Results' : 'Next'}
        </Button>
      </div>
    </div>
  );
}
