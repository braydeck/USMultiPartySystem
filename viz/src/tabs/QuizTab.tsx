import { useState } from 'react';
import type { QuizQuestion as QuizQuestionType, ClusterProfile, VoteModelRow, HouseSeat } from '../types';
import { QuizQuestion } from '../components/quiz/QuizQuestion';
import { QuizProgress } from '../components/quiz/QuizProgress';
import { QuizResult } from '../components/quiz/QuizResult';
import { scoreQuiz } from '../utils/quizScoring';
import { useUrlState } from '../hooks/useUrlState';
import { F5_ORDER } from '../constants/parties';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface Props {
  questions: QuizQuestionType[];
  clusters: ClusterProfile[];
  houseVotes: VoteModelRow[];
  houseSeats: HouseSeat[];
}

export function QuizTab({ questions, clusters, houseVotes, houseSeats }: Props) {
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [current, setCurrent] = useState(0);
  const [scored, setScored] = useState<{ topScore: number; secondScore: number } | null>(null);
  // Result party lives in the URL so it can be deep-linked / shared (?result=STY).
  const [resultParty, setResultParty] = useUrlState<string>('result', '', {
    allowed: [...F5_ORDER],
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
      const scores = scoreQuiz(questions, answers);
      const top = clusters.find(c => c.id === scores[0].clusterId);
      setScored({ topScore: scores[0].score, secondScore: scores[1]?.score ?? 0 });
      if (top) setResultParty(top.party);
    }
  }

  function handleBack() {
    if (current > 0) setCurrent(c => c - 1);
  }

  function handleRetake() {
    setAnswers({});
    setCurrent(0);
    setScored(null);
    setResultParty('');
  }

  // Result view — either just taken (scored) or arrived via a shared ?result=CODE link.
  if (resultParty) {
    const cluster = clusters.find(c => c.party === resultParty);
    if (cluster) {
      const isShared = !scored;
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
            topScore={scored?.topScore}
            secondScore={scored?.secondScore}
            shared={isShared}
            houseVotes={houseVotes}
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
          {questions.length} questions to find which of the 9 parties best matches your political values.
        </p>
      </div>

      <QuizProgress current={current + 1} total={questions.length} />

      <Card className="p-6">
        <QuizQuestion
          question={q.question}
          domain={q.domain}
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
