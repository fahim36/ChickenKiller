"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";
import { Inline } from "@/components/Inline";
import type { LessonQuiz as Quiz, LessonQuizResult, QuizAnswers } from "@/lib/api";

/**
 * A Lesson Quiz: its Questions, each answered by picking one choice. Submitting sends the
 * answers through `submitAction`; the API scores them, and this shows the score, whether it met
 * the Pass Mark, and which Questions were missed. Unanswered Questions are left out, so they
 * count as missed.
 */
export function LessonQuiz({
  quiz,
  stackId,
  submitAction,
}: {
  quiz: Quiz;
  stackId: string;
  submitAction: (answers: QuizAnswers) => Promise<LessonQuizResult>;
}) {
  const [answers, setAnswers] = useState<QuizAnswers>({});
  const [result, setResult] = useState<LessonQuizResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [failed, setFailed] = useState(false);
  const correct = new Map(result?.questions.map((q) => [q.id, q.correct] as const));

  async function submit(event: FormEvent) {
    event.preventDefault();
    setFailed(false);
    setSubmitting(true);
    try {
      setResult(await submitAction(answers));
    } catch {
      setFailed(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <ol className="quiz">
        {quiz.questions.map((q) => (
          <li key={q.id}>
            <fieldset disabled={result !== null}>
              <legend>
                <Inline text={q.prompt} />
              </legend>
              {q.choices.map((c) => (
                <label key={c.id} className="choice">
                  <input
                    type="radio"
                    name={q.id}
                    value={c.id}
                    checked={answers[q.id] === c.id}
                    onChange={() => setAnswers((current) => ({ ...current, [q.id]: c.id }))}
                  />{" "}
                  <Inline text={c.text} />
                </label>
              ))}
              {correct.has(q.id) && (
                <p className={correct.get(q.id) ? "mark mark-correct" : "mark mark-missed"}>
                  {correct.get(q.id) ? "Correct" : "Missed"}
                </p>
              )}
            </fieldset>
          </li>
        ))}
      </ol>

      {failed && (
        <p role="alert" className="notice notice-error">
          Couldn&apos;t submit your answers. Try again.
        </p>
      )}
      <button type="submit" disabled={submitting || result !== null}>
        Submit answers
      </button>

      {result && (
        <div role="status" className={`notice ${result.passed ? "" : "notice-error"}`}>
          <p>
            You scored {result.correct} of {result.total} ({result.percent}%).{" "}
            {result.passed
              ? "Passed: this Lesson is Completed and the next one is Unlocked."
              : `Not passed: the Pass Mark is ${result.pass_mark}%.`}
          </p>
          <p>
            {!result.passed && (
              <>
                <a href={`/stacks/${stackId}/lessons/${result.lesson_id}/quiz`}>
                  Take a fresh Lesson Quiz
                </a>{" "}
                ·{" "}
              </>
            )}
            <Link href={`/stacks/${stackId}`}>Back to the Week map</Link>
          </p>
        </div>
      )}
    </form>
  );
}
