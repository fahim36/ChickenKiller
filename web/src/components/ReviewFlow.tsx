"use client";

import { type FormEvent, useState } from "react";
import { Inline } from "@/components/Inline";
import { AnsweredQuestionDetail } from "@/components/MissedQuestions";
import { WrittenAnswer } from "@/components/WrittenAnswer";
import type { GradingFailed, ReviewAnswerResult, ReviewQuestion, ReviewSet } from "@/lib/api";

export type AnswerReviewAction = (
  stackId: string,
  questionId: string,
  answer: string | null,
) => Promise<ReviewAnswerResult | GradingFailed>;

/**
 * A Review set, answered one Question at a time in the order the API gives, each on its own
 * Stack. Each answer is marked straight away: a right one says so, a wrong one shows the
 * Question's correct answer or Model Answer, the grader's feedback (written) and the
 * Explanation before moving on. Any Question can be skipped: Review is optional. If grading
 * fails, nothing was counted and the Learner submits again. After the last one, "Next set"
 * loads the page again, which draws a fresh set.
 */
export function ReviewFlow({
  reviewSet,
  answerAction,
}: {
  reviewSet: ReviewSet;
  answerAction: AnswerReviewAction;
}) {
  const [position, setPosition] = useState(0);
  const [outcome, setOutcome] = useState<ReviewAnswerResult | null>(null);
  const [right, setRight] = useState(0);
  const [answered, setAnswered] = useState(0);
  const questions = reviewSet.questions;
  const question = questions[position];
  const isLast = position + 1 >= questions.length;

  function marked(result: ReviewAnswerResult) {
    setOutcome(result);
    setAnswered((n) => n + 1);
    if (result.correct) setRight((n) => n + 1);
  }

  function next() {
    setOutcome(null);
    setPosition((p) => p + 1);
  }

  if (!question) {
    return (
      <div role="status" className="notice">
        <p>
          Set done: {right} of {answered} right.
        </p>
        <p>
          {/* A full page load, so the server draws the next set. */}
          <a className="button" href="/review">
            Next set
          </a>
        </p>
      </div>
    );
  }

  return (
    <section className="review">
      <p className="muted">
        {question.stack_name} · Question {position + 1} of {questions.length}
      </p>
      {outcome ? (
        <div>
          {outcome.correct ? (
            <p className="mark mark-correct">Correct</p>
          ) : (
            <>
              <p className="mark mark-missed">Not quite. Read the Explanation before moving on.</p>
              <AnsweredQuestionDetail question={outcome.question} />
              {/* Sources (#15): show the Question's Sources here, after its Explanation. */}
            </>
          )}
          <button type="button" onClick={next}>
            {isLast ? "Finish" : "Next Question"}
          </button>
        </div>
      ) : (
        <QuestionForm
          key={`${question.stack_id}/${question.id}`}
          question={question}
          maxAnswerChars={reviewSet.max_answer_chars}
          answerAction={answerAction}
          onAnswered={marked}
          onSkip={next}
        />
      )}
    </section>
  );
}

function QuestionForm({
  question: q,
  maxAnswerChars,
  answerAction,
  onAnswered,
  onSkip,
}: {
  question: ReviewQuestion;
  maxAnswerChars: number;
  answerAction: AnswerReviewAction;
  onAnswered: (result: ReviewAnswerResult) => void;
  onSkip: () => void;
}) {
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [failed, setFailed] = useState(false);
  const [gradingFailed, setGradingFailed] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setFailed(false);
    setGradingFailed(null);
    setSubmitting(true);
    try {
      const outcome = await answerAction(q.stack_id, q.id, answer.trim() === "" ? null : answer);
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
            idPrefix="review"
          />
        ) : (
          q.choices.map((c) => (
            <label key={c.id} className="choice">
              <input
                type="radio"
                name={`review-${q.id}`}
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
          Couldn&apos;t submit your answer. Try again, or skip this Question.
        </p>
      )}
      {gradingFailed && (
        <p role="alert" className="notice notice-error">
          {gradingFailed}
        </p>
      )}
      <button type="submit" disabled={submitting}>
        {submitting ? "Grading…" : gradingFailed ? "Submit again" : "Submit answer"}
      </button>{" "}
      <button type="button" className="secondary" onClick={onSkip} disabled={submitting}>
        Skip
      </button>
    </form>
  );
}
