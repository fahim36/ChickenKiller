"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";
import { Inline } from "@/components/Inline";
import { AnsweredQuestionDetail } from "@/components/MissedQuestions";
import type { AnsweredQuestion, QuizQuestion, Retake, RetakeResult } from "@/lib/api";

interface RetakeState {
  id: string;
  question: QuizQuestion;
  /** The last wrong sibling, shown with its Explanation. */
  explained: AnsweredQuestion | null;
  done: boolean;
}

type AnswerAction = (retakeId: string, answer: string | null) => Promise<RetakeResult>;

/**
 * The Retakes of a passed Lesson Quiz: for each Missed Question, a sibling Question on the same
 * Concept. A wrong answer shows that sibling's Explanation and the API offers another sibling;
 * once every Retake is correct the Lesson is Completed and the next one is Unlocked.
 */
export function RetakeFlow({
  retakes,
  stackId,
  answerAction,
}: {
  retakes: Retake[];
  stackId: string;
  answerAction: AnswerAction;
}) {
  const [states, setStates] = useState<RetakeState[]>(() =>
    retakes.map((r) => ({ id: r.id, question: r.question, explained: null, done: false })),
  );
  const [completed, setCompleted] = useState(false);

  function answered(result: RetakeResult) {
    setStates((current) =>
      current.map((s) =>
        s.id !== result.retake_id
          ? s
          : result.correct
            ? { ...s, explained: null, done: true }
            : { ...s, explained: result.question, question: result.next_question ?? s.question },
      ),
    );
    if (result.lesson_completed) setCompleted(true);
  }

  if (completed) {
    return (
      <div role="status" className="notice">
        <p>Every Retake is correct: this Lesson is Completed and the next one is Unlocked.</p>
        <p>
          <Link href={`/stacks/${stackId}`}>Back to the Week map</Link>
        </p>
      </div>
    );
  }

  return (
    <section className="retakes">
      <h2>Retakes</h2>
      <p className="muted">
        Answer a sibling Question on the same Concept for each Missed Question. The Lesson is
        Completed once every Retake is correct.
      </p>
      <ol className="quiz">
        {states.map((s) => (
          <li key={s.id}>
            {s.done ? (
              <p className="mark mark-correct">Correct</p>
            ) : (
              <RetakeForm state={s} answerAction={answerAction} onAnswered={answered} />
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}

function RetakeForm({
  state,
  answerAction,
  onAnswered,
}: {
  state: RetakeState;
  answerAction: AnswerAction;
  onAnswered: (result: RetakeResult) => void;
}) {
  const [answer, setAnswer] = useState<{ questionId: string; choice: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [failed, setFailed] = useState(false);
  const q = state.question;
  const chosen = answer?.questionId === q.id ? answer.choice : null;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setFailed(false);
    setSubmitting(true);
    try {
      onAnswered(await answerAction(state.id, chosen));
    } catch {
      setFailed(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit}>
      {state.explained && (
        <div className="retake-explained">
          <p className="mark mark-missed">Not quite. Read the Explanation, then try this one.</p>
          <AnsweredQuestionDetail question={state.explained} />
        </div>
      )}
      <fieldset>
        <legend>
          <Inline text={q.prompt} />
        </legend>
        {q.choices.map((c) => (
          <label key={c.id} className="choice">
            <input
              type="radio"
              name={`retake-${state.id}`}
              value={c.id}
              checked={chosen === c.id}
              onChange={() => setAnswer({ questionId: q.id, choice: c.id })}
            />{" "}
            <Inline text={c.text} />
          </label>
        ))}
      </fieldset>
      {failed && (
        <p role="alert" className="notice notice-error">
          Couldn&apos;t submit your Retake. Try again.
        </p>
      )}
      <button type="submit" disabled={submitting}>
        Submit Retake
      </button>
    </form>
  );
}
