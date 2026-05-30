import { useState } from 'react';
import type { QuizQuestion as QuizQuestionType, ClusterProfile, VoteModelRow } from '../types';
import { QuizQuestion } from '../components/quiz/QuizQuestion';
import { QuizProgress } from '../components/quiz/QuizProgress';
import { QuizResult } from '../components/quiz/QuizResult';
import { scoreQuiz } from '../utils/quizScoring';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface Props {
  questions: QuizQuestionType[];
  clusters: ClusterProfile[];
  houseVotes: VoteModelRow[];
}

export function QuizTab({ questions, clusters, houseVotes }: Props) {
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [current, setCurrent] = useState(0);
  const [result, setResult] = useState<{ clusterId: string; topScore: number; secondScore: number } | null>(null);

  function handleSelect(value: number) {
    setAnswers(prev => ({ ...prev, [current]: value }));
  }

  function handleNext() {
    if (current < questions.length - 1) {
      setCurrent(c => c + 1);
    } else {
      const scores = scoreQuiz(questions, answers);
      setResult({
        clusterId: scores[0].clusterId,
        topScore: scores[0].score,
        secondScore: scores[1]?.score ?? 0,
      });
    }
  }

  function handleBack() {
    if (current > 0) setCurrent(c => c - 1);
  }

  function handleRetake() {
    setAnswers({});
    setCurrent(0);
    setResult(null);
  }

  if (result) {
    const cluster = clusters.find(c => c.id === result.clusterId);
    if (!cluster) return null;
    return (
      <div className="space-y-8">
        <div>
          <h2 className="text-2xl font-bold text-foreground mb-1">Your Political Profile</h2>
          <p className="text-muted-foreground text-sm">Based on your quiz answers, here's which party you align with most.</p>
        </div>
        <QuizResult
          cluster={cluster}
          topScore={result.topScore}
          secondScore={result.secondScore}
          houseVotes={houseVotes}
          onRetake={handleRetake}
        />
      </div>
    );
  }

  const q = questions[current];
  const hasAnswer = answers[current] !== undefined;

  return (
    <div className="space-y-8 max-w-xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-1">Who Are You?</h2>
        <p className="text-muted-foreground text-sm">
          10 questions to find which of the 9 parties best matches your political values.
        </p>
      </div>

      <QuizProgress current={current + 1} total={questions.length} />

      <Card className="p-6">
        <QuizQuestion
          question={q.question}
          domain={q.domain}
          selected={answers[current] ?? null}
          onSelect={handleSelect}
        />
      </Card>

      <div className="flex justify-between">
        <Button
          onClick={handleBack}
          disabled={current === 0}
          variant="secondary"
        >
          Back
        </Button>
        <Button
          onClick={handleNext}
          disabled={!hasAnswer}
          variant="default"
        >
          {current === questions.length - 1 ? 'See Results' : 'Next'}
        </Button>
      </div>
    </div>
  );
}
