import { useState } from 'react';
import type { QuizQuestion as QuizQuestionType, ClusterProfile, VoteModelRow } from '../types';
import { QuizQuestion } from '../components/quiz/QuizQuestion';
import { QuizProgress } from '../components/quiz/QuizProgress';
import { QuizResult } from '../components/quiz/QuizResult';
import { scoreQuiz } from '../utils/quizScoring';

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
          <h2 className="text-2xl font-bold text-slate-900 mb-1">Your Political Profile</h2>
          <p className="text-slate-500 text-sm">Based on your quiz answers, here's which party you align with most.</p>
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
        <h2 className="text-2xl font-bold text-slate-900 mb-1">Who Are You?</h2>
        <p className="text-slate-500 text-sm">
          10 questions to find which of the 9 parties best matches your political values.
        </p>
      </div>

      <QuizProgress current={current + 1} total={questions.length} />

      <div className="bg-white rounded-xl p-6 border border-slate-200">
        <QuizQuestion
          question={q.question}
          domain={q.domain}
          selected={answers[current] ?? null}
          onSelect={handleSelect}
        />
      </div>

      <div className="flex justify-between">
        <button
          onClick={handleBack}
          disabled={current === 0}
          className="px-5 py-2 rounded bg-slate-200 text-slate-700 font-medium disabled:opacity-40 hover:bg-slate-300 transition-colors"
        >
          Back
        </button>
        <button
          onClick={handleNext}
          disabled={!hasAnswer}
          className="px-5 py-2 rounded bg-indigo-600 text-white font-medium disabled:opacity-40 hover:bg-indigo-500 transition-colors"
        >
          {current === questions.length - 1 ? 'See Results' : 'Next'}
        </button>
      </div>
    </div>
  );
}
