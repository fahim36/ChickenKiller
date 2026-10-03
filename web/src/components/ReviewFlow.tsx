"use client";

import { ArrowRight, PartyPopper, SkipForward } from "lucide-react";
import { type FormEvent, useState } from "react";
import { AnsweredQuestionDetail } from "@/components/MissedQuestions";
import { Notice } from "@/components/Notice";
import {
  Mark,
  QuestionAnswer,
  QuestionCard,
  Spinner,
  StepProgress,
} from "@/components/QuestionCard";
import { Button } from "@/components/ui/button";
import { submittedAnswer } from "@/lib/answers";
import type {
  Answer,
  GradingFailed,
  ReviewAnswerResult,
  ReviewQuestion,
  ReviewSet,
} from "@/lib/api";

export type AnswerReviewAction = (
  stackId: string,
  questionId: string,
  answer: Answer,
) => Promise<ReviewAnswerResult | GradingFailed>;

/**
 * A Review set, answered one Question at a time in the order the API gives, each on its own
 * Stack. Each answer is marked straight away: a right one says so, a wrong one shows the
 * Question's correct answer or Model Answer, the grader's feedback (written), the
 * Explanation and its Sources before moving on. Any Question can be skipped: Review is optional. If grading
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
      <div
        role="status"
        className="flex flex-col items-center gap-4 rounded-2xl border bg-card px-6 py-10 text-center shadow-xs"
      >
        <span className="flex size-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <PartyPopper aria-hidden className="size-7" />
        </span>
        <p className="font-heading text-xl font-semibold">
          Set done: {right} of {answered} right.
        </p>
        <p>
          {/* A full page load, so the server draws the next set. */}
          <Button asChild size="lg" className="px-4">
            <a href="/review">
              Next set
              <ArrowRight aria-hidden />
            </a>
          </Button>
        </p>
      </div>
    );
  }

  return (
    <section className="space-y-4">
      <StepProgress
        label={`${question.stack_name} · Question ${position + 1} of ${questions.length}`}
        step={position}
        total={questions.length}
      />
      {outcome ? (
        <div className="space-y-5">
          {outcome.correct ? (
            <Mark correct className="rounded-xl bg-success/10 px-4 py-3 text-base">
              Correct
            </Mark>
          ) : (
            <>
              <Mark correct={false} className="rounded-xl bg-destructive/10 px-4 py-3 text-base">
                Not quite. Read the Explanation before moving on.
              </Mark>
              <AnsweredQuestionDetail question={outcome.question} />
            </>
          )}
          <Button type="button" size="lg" className="px-4" onClick={next}>
            {isLast ? "Finish" : "Next Question"}
            <ArrowRight aria-hidden />
          </Button>
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
  const [answer, setAnswer] = useState<Answer>(null);
  const [submitting, setSubmitting] = useState(false);
  const [failed, setFailed] = useState(false);
  const [gradingFailed, setGradingFailed] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setFailed(false);
    setGradingFailed(null);
    setSubmitting(true);
    try {
      const outcome = await answerAction(q.stack_id, q.id, submittedAnswer(answer));
      if ("code" in outcome) setGradingFailed(outcome.message);
      else onAnswered(outcome);
    } catch {
      setFailed(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <QuestionCard prompt={q.prompt}>
        <QuestionAnswer
          question={q}
          name={`review-${q.id}`}
          idPrefix="review"
          value={answer}
          maxLength={maxAnswerChars}
          onChange={setAnswer}
        />
      </QuestionCard>
      {failed && (
        <Notice tone="error" role="alert">
          Couldn&apos;t submit your answer. Try again, or skip this Question.
        </Notice>
      )}
      {gradingFailed && (
        <Notice tone="error" role="alert">
          {gradingFailed}
        </Notice>
      )}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" size="lg" className="px-4" disabled={submitting}>
          {submitting && <Spinner />}
          {submitting ? "Grading…" : gradingFailed ? "Submit again" : "Submit answer"}
        </Button>{" "}
        <Button type="button" variant="ghost" size="lg" onClick={onSkip} disabled={submitting}>
          <SkipForward aria-hidden />
          Skip
        </Button>
      </div>
    </form>
  );
}
