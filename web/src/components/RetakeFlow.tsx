"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";
import { Inline } from "@/components/Inline";
import { AnsweredQuestionDetail } from "@/components/MissedQuestions";
import { WrittenAnswer } from "@/components/WrittenAnswer";
import type {
  AnsweredQuestion,
  GradingFailed,
  QuizQuestion,
  Retake,
  RetakeResult,
} from "@/lib/api";

interface RetakeState {
  id: string;
  question: QuizQuestion;
  /** How many times this Retake has been answered wrongly: a new ask starts a fresh form. */
  tries: number;
  /** The last wrong sibling, shown with its Explanation. */
  explained: AnsweredQuestion | null;
  done: boolean;
}

export type AnswerRetakeAction = (
  retakeId: string,
  answer: string | null,
) => Promise<RetakeResult | GradingFailed>;

/**
 * The Retakes of a passed Lesson Quiz: for each Missed Question, a sibling Question on the same
 * Concept, multiple choice or written. A wrong answer shows that sibling's Explanation (and the
 * grader's feedback on a written one) and the API offers another sibling; once every Retake is
 * correct the Lesson is Completed and the next one is Unlocked. If grading fails, nothing was
 * counted and the Learner submits again.
 */
export function RetakeFlow({
  retakes,
  stackId,
  maxAnswerChars,
  answerAction,
}: {
  retakes: Retake[];
  stackId: string;
  /** The longest written answer the API accepts. */
  maxAnswerChars: number;
  answerAction: AnswerRetakeAction;
}) {
  const [states, setStates] = useState<RetakeState[]>(() =>
    retakes.map((r) => ({ id: r.id, question: r.question, tries: 0, explained: null, done: false })),
  );
  const [completed, setCompleted] = useState(false);

  function answered(result: RetakeResult) {
    setStates((current) =>
      current.map((s) =>
        s.id !== result.retake_id
          ? s
          : result.correct
            ? { ...s, explained: null, done: true }
            : {
                ...s,
                tries: s.tries + 1,
                explained: result.question,
                question: result.next_question ?? s.question,
              },
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
              <RetakeForm
                key={s.tries}
                state={s}
                maxAnswerChars={maxAnswerChars}
                answerAction={answerAction}
                onAnswered={answered}
              />
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}

function RetakeForm({
  state,
  maxAnswerChars,
  answerAction,
  onAnswered,
}: {
  state: RetakeState;
  maxAnswerChars: number;
  answerAction: AnswerRetakeAction;
  onAnswered: (result: RetakeResult) => void;
}) {
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [failed, setFailed] = useState(false);
  const [gradingFailed, setGradingFailed] = useState<string | null>(null);
  const q = state.question;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setFailed(false);
    setGradingFailed(null);
    setSubmitting(true);
    try {
      const outcome = await answerAction(state.id, answer.trim() === "" ? null : answer);
      if ("code" in outcome) setGradingFailed(outcome.message);
      else onAnswered(outcome);
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
        {q.type === "written" ? (
          <WrittenAnswer
            question={q}
            value={answer}
            maxLength={maxAnswerChars}
            onChange={setAnswer}
            idPrefix={`retake-${state.id}`}
          />
        ) : (
          q.choices.map((c) => (
            <label key={c.id} className="choice">
              <input
                type="radio"
                name={`retake-${state.id}`}
                value={c.id}
                checked={answer === c.id}
                onChange={() => setAnswer(c.id)}
              />{" "}
              <Inline text={c.text} />
            </label>
          ))
        )}
      </fieldset>
      {failed && (
        <p role="alert" className="notice notice-error">
          Couldn&apos;t submit your Retake. Try again.
        </p>
      )}
      {gradingFailed && (
        <p role="alert" className="notice notice-error">
          {gradingFailed}
        </p>
      )}
      <button type="submit" disabled={submitting}>
        {submitting ? "Grading…" : gradingFailed ? "Submit again" : "Submit Retake"}
      </button>
    </form>
  );
}
