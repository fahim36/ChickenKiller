"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";
import { Inline } from "@/components/Inline";
import { AnsweredQuestionDetail } from "@/components/MissedQuestions";
import { WrittenAnswer } from "@/components/WrittenAnswer";
import type { GradingFailed, QuizQuestion, ReviewAnswerResult, ReviewRound } from "@/lib/api";

export type AnswerReviewAction = (
  questionId: string,
  answer: string | null,
) => Promise<ReviewAnswerResult | GradingFailed>;

/**
 * A Review Round, answered one Question at a time in the order the API gives. Each answer is
 * marked straight away: a right one says so, a wrong one shows the Question's correct answer
 * or Model Answer, the grader's feedback (written) and the Explanation before moving on. The
 * last answer finishes the round. If grading fails, nothing was counted and the Learner submits
 * again.
 */
export function ReviewRoundFlow({
  round,
  stackId,
  answerAction,
}: {
  round: ReviewRound;
  stackId: string;
  answerAction: AnswerReviewAction;
}) {
  const [position, setPosition] = useState(0);
  const [outcome, setOutcome] = useState<ReviewAnswerResult | null>(null);
  const [right, setRight] = useState(() => round.results.filter((r) => r.correct).length);
  const [finished, setFinished] = useState(false);
  const question = round.remaining[position];

  function answered(result: ReviewAnswerResult) {
    setOutcome(result);
    if (result.correct) setRight((n) => n + 1);
  }

  function next() {
    const isLast = outcome?.round.state === "finished" || position + 1 >= round.remaining.length;
    setOutcome(null);
    if (isLast) setFinished(true);
    else setPosition((p) => p + 1);
  }

  if (finished || !question) {
    return (
      <div role="status" className="notice">
        <p>
          Review Round {round.number} is done: {right} of {round.total} right.
        </p>
        <p>
          <Link href={`/stacks/${stackId}`}>Back to the Week map</Link>
        </p>
      </div>
    );
  }

  const isLast = outcome?.round.state === "finished" || position + 1 >= round.remaining.length;
  return (
    <section className="review-round">
      <p className="muted">
        Question {round.answered + position + 1} of {round.total}
      </p>
      {outcome ? (
        <div>
          {outcome.correct ? (
            <p className="mark mark-correct">Correct</p>
          ) : (
            <>
              <p className="mark mark-missed">Not quite. Read the Explanation before moving on.</p>
              <AnsweredQuestionDetail question={outcome.question} />
            </>
          )}
          <button type="button" onClick={next}>
            {isLast ? "Finish" : "Next Question"}
          </button>
        </div>
      ) : (
        <QuestionForm
          key={question.id}
          question={question}
          maxAnswerChars={round.max_answer_chars}
          answerAction={answerAction}
          onAnswered={answered}
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
}: {
  question: QuizQuestion;
  maxAnswerChars: number;
  answerAction: AnswerReviewAction;
  onAnswered: (result: ReviewAnswerResult) => void;
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
      const outcome = await answerAction(q.id, answer.trim() === "" ? null : answer);
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
          Couldn&apos;t submit your answer. Try again.
        </p>
      )}
      {gradingFailed && (
        <p role="alert" className="notice notice-error">
          {gradingFailed}
        </p>
      )}
      <button type="submit" disabled={submitting}>
        {submitting ? "Grading…" : gradingFailed ? "Submit again" : "Submit answer"}
      </button>
    </form>
  );
}
