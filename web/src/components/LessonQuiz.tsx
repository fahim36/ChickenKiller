"use client";

import { ArrowLeft, RotateCcw } from "lucide-react";
import Link from "next/link";
import { type FormEvent, useState } from "react";
import { MissedQuestions } from "@/components/MissedQuestions";
import { Notice } from "@/components/Notice";
import { Mark, QuestionAnswer, QuestionCard, Spinner } from "@/components/QuestionCard";
import { type AnswerRetakeAction, RetakeFlow, RetakeNotices } from "@/components/RetakeFlow";
import { Button } from "@/components/ui/button";
import { isAnswered } from "@/lib/answers";
import type {
  Answer,
  GradingFailed,
  LessonQuiz as Quiz,
  LessonQuizResult,
  QuizAnswers,
} from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * A Lesson Quiz: multiple-choice Questions answered by picking one choice, multiple-select ones
 * by ticking every correct choice, and legacy written ones in a text box. Submitting sends the
 * answers through `submitAction`; the API scores them (a multiple-select answer is right only
 * when the ticks are exactly the correct choices; written answers are graded against their Model
 * Answers), and this shows the score, whether it met the Pass Mark, which Questions were missed,
 * the grader's feedback on each written answer and, for each Missed Question, the answers, the
 * Explanation, the Sources and the Materials.
 * Unanswered Questions are left out, so they count as missed.
 *
 * If grading fails, nothing was counted: the answers stay as they are and the Learner can
 * submit again. After a pass with Missed Questions come their Retakes (`answerRetakeAction`);
 * below the Pass Mark the Learner takes a fresh Lesson Quiz.
 */
export function LessonQuiz({
  quiz,
  stackId,
  submitAction,
  answerRetakeAction,
}: {
  quiz: Quiz;
  stackId: string;
  submitAction: (answers: QuizAnswers) => Promise<LessonQuizResult | GradingFailed>;
  answerRetakeAction: AnswerRetakeAction;
}) {
  const [answers, setAnswers] = useState<QuizAnswers>({});
  const [result, setResult] = useState<LessonQuizResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [failed, setFailed] = useState(false);
  const [gradingFailed, setGradingFailed] = useState<string | null>(null);
  const marks = new Map(result?.questions.map((q) => [q.id, q] as const));
  const answeredCount = quiz.questions.filter((q) => isAnswered(answers[q.id])).length;

  function answer(questionId: string, value: Answer) {
    setAnswers((current) => ({ ...current, [questionId]: value }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setFailed(false);
    setGradingFailed(null);
    setSubmitting(true);
    // A blank written answer, or no ticks, is left out, like an unpicked choice.
    const given = Object.fromEntries(
      Object.entries(answers).filter(([, value]) => isAnswered(value)),
    );
    try {
      const outcome = await submitAction(given);
      if ("code" in outcome) setGradingFailed(outcome.message);
      else setResult(outcome);
    } catch {
      setFailed(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      {result && <ScoreBanner result={result} stackId={stackId} />}

      <form onSubmit={submit} className="space-y-5">
        <ol className="space-y-5">
          {quiz.questions.map((q, i) => {
            const mark = marks.get(q.id);
            return (
              <li key={q.id}>
                <QuestionCard
                  prompt={q.prompt}
                  number={i + 1}
                  disabled={result !== null}
                  className={cn(
                    mark?.correct === true && "border-success/40",
                    mark?.correct === false && "border-destructive/40",
                  )}
                >
                  <QuestionAnswer
                    question={q}
                    name={q.id}
                    value={answers[q.id]}
                    maxLength={quiz.max_answer_chars}
                    onChange={(value) => answer(q.id, value)}
                  />
                  {mark && (
                    <Mark correct={mark.correct} className="pt-1">
                      {mark.correct ? "Correct" : "Missed"}
                    </Mark>
                  )}
                  {mark?.feedback && (
                    <p className="rounded-xl bg-muted px-3 py-2 text-sm text-muted-foreground">
                      {mark.feedback}
                    </p>
                  )}
                </QuestionCard>
              </li>
            );
          })}
        </ol>

        {failed && (
          <Notice tone="error" role="alert">
            Couldn&apos;t submit your answers. Try again.
          </Notice>
        )}
        {gradingFailed && (
          <Notice tone="error" role="alert">
            {gradingFailed}
          </Notice>
        )}
        <div
          className={cn(
            "z-10 flex flex-wrap items-center justify-between gap-3 rounded-2xl border bg-card/95 p-3 pl-5 backdrop-blur",
            result === null && "sticky bottom-4 shadow-lg",
          )}
        >
          <span className="text-sm text-muted-foreground tabular-nums" aria-hidden>
            {result === null
              ? `${answeredCount} of ${quiz.questions.length} answered`
              : "Answers submitted"}
          </span>
          <Button type="submit" size="lg" className="px-4" disabled={submitting || result !== null}>
            {submitting && <Spinner />}
            {submitting ? "Grading…" : gradingFailed ? "Submit again" : "Submit answers"}
          </Button>
        </div>
      </form>

      {result && <MissedQuestions missed={result.missed} />}
      {result && result.next_step !== "retakes" && <RetakeNotices notices={result.notices} />}
      {result && result.next_step === "retakes" && (
        <RetakeFlow
          retakes={result.retakes}
          notices={result.notices}
          stackId={stackId}
          maxAnswerChars={quiz.max_answer_chars}
          answerAction={answerRetakeAction}
        />
      )}
    </>
  );
}

/** The score, whether it passed, and what to do next. */
function ScoreBanner({ result, stackId }: { result: LessonQuizResult; stackId: string }) {
  return (
    <div
      role="status"
      className={cn(
        "mb-6 space-y-4 rounded-2xl border p-5 sm:p-6",
        result.passed
          ? "border-success/30 bg-success/8 text-foreground"
          : "border-destructive/30 bg-destructive/8 text-foreground",
      )}
    >
      <div className="flex items-center gap-4">
        <span
          aria-hidden
          className={cn(
            "flex size-14 shrink-0 items-center justify-center rounded-2xl font-heading text-lg font-semibold tabular-nums",
            result.passed ? "bg-success text-white" : "bg-destructive text-white",
          )}
        >
          {result.percent}%
        </span>
        <p className="text-sm leading-relaxed sm:text-base">
          You scored {result.correct} of {result.total} ({result.percent}%).{" "}
          {outcome(result)}
        </p>
      </div>
      <p className="flex flex-wrap gap-2">
        {!result.passed && (
          <>
            <Button asChild>
              <a href={`/stacks/${stackId}/lessons/${result.lesson_id}/quiz`}>
                <RotateCcw aria-hidden />
                Take a fresh Lesson Quiz
              </a>
            </Button>{" "}
          </>
        )}
        <Button asChild variant="outline">
          <Link href={`/stacks/${stackId}`}>
            <ArrowLeft aria-hidden />
            Back to the Week map
          </Link>
        </Button>
      </p>
    </div>
  );
}

function outcome(result: LessonQuizResult): string {
  switch (result.next_step) {
    case "completed":
      return "Passed: this Lesson is Completed and the next one is Unlocked.";
    case "retakes":
      return "Passed. Read the Explanations, then Retake each Missed Question to complete this Lesson.";
    case "fresh_quiz":
      return `Not passed: the Pass Mark is ${result.pass_mark}%. Read the Explanations, then take a fresh Lesson Quiz.`;
  }
}
