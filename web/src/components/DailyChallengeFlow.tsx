"use client";

import { ArrowRight, CircleCheck, CircleMinus, CircleX, RotateCcw, Trophy } from "lucide-react";
import Link from "next/link";
import { type FormEvent, useState } from "react";
import { Inline } from "@/components/Inline";
import { AnsweredQuestionDetail } from "@/components/MissedQuestions";
import { Notice } from "@/components/Notice";
import {
  Mark as MarkLine,
  QuestionAnswer,
  QuestionCard,
  Spinner,
  StepProgress,
} from "@/components/QuestionCard";
import { ResultCard } from "@/components/ResultCard";
import { Button } from "@/components/ui/button";
import { WrittenAnswer } from "@/components/WrittenAnswer";
import { isAnswered } from "@/lib/answers";
import type {
  Answer,
  ChallengeAnswerResult,
  ChallengeOutcome,
  ChallengeQuestion,
  DailyChallenge,
  GradingFailed,
  QuizQuestion,
} from "@/lib/api";
import { cn } from "@/lib/utils";

export type AnswerChallengeAction = (
  questionId: string,
  answer: Answer,
) => Promise<ChallengeAnswerResult | GradingFailed>;

const OUTCOME_LABELS: Record<ChallengeOutcome, string> = {
  correct: "Correct",
  wrong: "Wrong",
  ungraded: "Ungraded: no point",
};

const OUTCOME_ICONS = { correct: CircleCheck, wrong: CircleX, ungraded: CircleMinus };

const OUTCOME_STYLES: Record<ChallengeOutcome, string> = {
  correct: "text-success-foreground",
  wrong: "text-destructive",
  ungraded: "text-muted-foreground",
};

/**
 * A Daily Challenge, today's or one from the Archive, answered one Question at a time. The API scores only the first
 * answer to each Question; after each one the Learner sees the result, the Explanation and
 * every Source. A written answer takes a while to grade ("Grading…"). If grading a first answer
 * fails, that Question is ungraded (no point, ever) and the Learner can resubmit it for feedback
 * only. Once finished, the page sums up the score, with the Result Card to copy and share, and
 * offers a replay, which is marked the same way but changes nothing. A Retired Question is
 * skipped: it can't be answered. The summary shows its reason and links to its replacement, if
 * it has one (#19).
 */
export function DailyChallengeFlow({
  stackId,
  challenge: initial,
  answerAction,
}: {
  stackId: string;
  challenge: DailyChallenge;
  answerAction: AnswerChallengeAction;
}) {
  const [challenge, setChallenge] = useState(initial);
  const [shown, setShown] = useState<ChallengeAnswerResult | null>(null);
  const [replaying, setReplaying] = useState(false);
  const questions = challenge.questions;
  const pending = questions.find((q) => q.outcome === null && !q.retired);

  if (replaying) {
    return (
      <Replay
        questions={questions.filter((q) => !q.retired)}
        maxAnswerChars={challenge.max_answer_chars}
        answerAction={answerAction}
        onDone={() => setReplaying(false)}
      />
    );
  }

  if (shown) {
    return (
      <section className="space-y-5">
        <Result
          result={shown}
          maxAnswerChars={challenge.max_answer_chars}
          answerAction={answerAction}
        />
        <Button type="button" size="lg" className="px-4" onClick={() => setShown(null)}>
          {pending ? "Next Question" : "See your score"}
          <ArrowRight aria-hidden />
        </Button>
      </section>
    );
  }

  if (pending) {
    return (
      <section className="space-y-4">
        {challenge.status === "not_started" && (
          <p className="text-sm text-muted-foreground">
            {questions.length} Questions. Only your first answer to each Question counts.
          </p>
        )}
        <StepProgress
          label={`Question ${questions.indexOf(pending) + 1} of ${questions.length}`}
          step={questions.indexOf(pending)}
          total={questions.length}
        />
        <QuestionForm
          key={pending.id}
          question={pending}
          maxAnswerChars={challenge.max_answer_chars}
          answerAction={answerAction}
          onAnswered={(result) => {
            setChallenge(result.challenge);
            setShown(result);
          }}
        />
      </section>
    );
  }

  return (
    <Summary
      stackId={stackId}
      challenge={challenge}
      answerAction={answerAction}
      onReplay={() => setReplaying(true)}
    />
  );
}

/**
 * A finished Challenge: the score, its Result Card, each Question's first try, and the replay. A
 * Retired Question shows why it was retired and links to its replacement.
 */
function Summary({
  stackId,
  challenge,
  answerAction,
  onReplay,
}: {
  stackId: string;
  challenge: DailyChallenge;
  answerAction: AnswerChallengeAction;
  onReplay: () => void;
}) {
  return (
    <section className="space-y-6" aria-label="Your score">
      {challenge.status === "finished" && (
        <div className="flex items-center gap-4 rounded-2xl border bg-card p-5 shadow-xs">
          <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-streak/15 text-streak">
            <Trophy aria-hidden className="size-6" />
          </span>
          <div>
            <p className="font-heading text-2xl font-semibold tabular-nums">
              Played: {challenge.score}/{challenge.out_of}
            </p>
            <p className="text-sm text-muted-foreground">Only your first try counts.</p>
          </div>
        </div>
      )}
      {challenge.result_card && <ResultCard text={challenge.result_card} />}
      <ol className="space-y-4">
        {challenge.questions.map((q, i) => (
          <li key={q.id} className="space-y-3">
            {q.outcome === null ? (
              <div className="space-y-2 rounded-2xl border border-dashed bg-card/50 p-5">
                <p className="font-medium">
                  <Inline text={q.prompt} />
                </p>
                {q.retired && <Retired question={q} stackId={stackId} />}
              </div>
            ) : (
              <>
                <OutcomeHeading outcome={q.outcome} number={i + 1} />
                {q.retired && <Retired question={q} stackId={stackId} />}
                {q.answered && <AnsweredQuestionDetail question={q.answered} />}
                {q.outcome === "ungraded" && q.answered && (
                  <Resubmit
                    question={q}
                    response={q.answered.response}
                    maxAnswerChars={challenge.max_answer_chars}
                    answerAction={answerAction}
                  />
                )}
              </>
            )}
          </li>
        ))}
      </ol>
      <div className="flex flex-wrap items-center gap-3 rounded-2xl border bg-muted/40 p-4">
        <Button type="button" variant="outline" onClick={onReplay}>
          <RotateCcw aria-hidden />
          Replay
        </Button>{" "}
        <span className="text-sm text-muted-foreground">
          For learning: it changes nothing about your score, Streak or Missed Questions.
        </span>
      </div>
    </section>
  );
}

/** "Question 1" and how its first try went, above that Question in the summary. */
function OutcomeHeading({ outcome, number }: { outcome: ChallengeOutcome; number: number }) {
  const Icon = OUTCOME_ICONS[outcome];
  return (
    <p className={cn("flex items-center gap-2 text-sm font-semibold", OUTCOME_STYLES[outcome])}>
      <Icon aria-hidden className="size-4" />
      <span className="sr-only">Question {number}: </span>
      <strong>{OUTCOME_LABELS[outcome]}</strong>
    </p>
  );
}

/**
 * Why a Question was retired, and where its replacement is: the first released Challenge that
 * asks it, in the Stack's Archive. A replacement no released Challenge asks yet has no link.
 */
function Retired({ question, stackId }: { question: ChallengeQuestion; stackId: string }) {
  const replacement = question.replaced_by;
  return (
    <p className="rounded-xl bg-muted px-3 py-2 text-sm text-muted-foreground">
      Retired{question.retired_reason ? `: ${question.retired_reason}` : "."} It can&apos;t be
      answered and isn&apos;t scored.
      {replacement &&
        (replacement.challenge_number !== null ? (
          <>
            {" "}
            Its replacement is in{" "}
            <Link
              className="font-medium text-foreground underline underline-offset-4 hover:text-primary"
              href={`/stacks/${encodeURIComponent(stackId)}/archive/${replacement.challenge_number}`}
            >
              {replacement.challenge_label}
            </Link>
            .
          </>
        ) : (
          " A newer Question replaces it."
        ))}
    </p>
  );
}

/** A replay: every Question that can be answered, marked and explained, counting for nothing. */
function Replay({
  questions,
  maxAnswerChars,
  answerAction,
  onDone,
}: {
  questions: ChallengeQuestion[];
  maxAnswerChars: number;
  answerAction: AnswerChallengeAction;
  onDone: () => void;
}) {
  const [position, setPosition] = useState(0);
  const [shown, setShown] = useState<ChallengeAnswerResult | null>(null);
  const question = questions[position];
  const isLast = position + 1 >= questions.length;

  if (!question) return null;
  return (
    <section className="space-y-4">
      <StepProgress
        label={`Replay · Question ${position + 1} of ${questions.length}`}
        step={position}
        total={questions.length}
      />
      {shown ? (
        <div className="space-y-5">
          <Result result={shown} maxAnswerChars={maxAnswerChars} answerAction={answerAction} />
          <Button
            type="button"
            size="lg"
            className="px-4"
            onClick={() => {
              setShown(null);
              if (isLast) onDone();
              else setPosition((p) => p + 1);
            }}
          >
            {isLast ? "Finish replay" : "Next Question"}
            <ArrowRight aria-hidden />
          </Button>
        </div>
      ) : (
        <QuestionForm
          key={`replay-${question.id}`}
          question={question}
          maxAnswerChars={maxAnswerChars}
          answerAction={answerAction}
          onAnswered={setShown}
          idPrefix="replay"
        />
      )}
    </section>
  );
}

/** One answer's result: the mark, then the correct answer, Explanation and every Source. */
function Result({
  result,
  maxAnswerChars,
  answerAction,
}: {
  result: ChallengeAnswerResult;
  maxAnswerChars: number;
  answerAction: AnswerChallengeAction;
}) {
  const { question } = result;
  const ungraded = result.counted && result.outcome === "ungraded";
  return (
    <div className="space-y-4">
      {ungraded ? (
        <Notice tone="error" role="alert">
          Your answer couldn&apos;t be graded, so it earns no point toward your score. You can
          resubmit it for feedback.
        </Notice>
      ) : (
        <Mark outcome={result.outcome} />
      )}
      {!result.counted && (
        <p className="text-sm text-muted-foreground">
          A replay changes no score, Streak or Missed Question: only your first answer counts.
        </p>
      )}
      <AnsweredQuestionDetail question={question} />
      {ungraded && (
        <Resubmit
          question={question}
          response={question.response}
          maxAnswerChars={maxAnswerChars}
          answerAction={answerAction}
        />
      )}
    </div>
  );
}

function Mark({ outcome }: { outcome: ChallengeOutcome }) {
  if (outcome === "correct") {
    return (
      <MarkLine correct className="rounded-xl bg-success/10 px-4 py-3 text-base">
        Correct
      </MarkLine>
    );
  }
  if (outcome === "wrong") {
    return (
      <MarkLine correct={false} className="rounded-xl bg-destructive/10 px-4 py-3 text-base">
        Not quite. Read the Explanation.
      </MarkLine>
    );
  }
  return (
    <MarkLine correct={false} className="rounded-xl bg-destructive/10 px-4 py-3 text-base">
      Couldn&apos;t be graded.
    </MarkLine>
  );
}

/**
 * Resubmitting an ungraded written answer: graded for feedback only. If it can't be graded
 * either, the Learner can send it again.
 */
function Resubmit({
  question,
  response,
  maxAnswerChars,
  answerAction,
}: {
  question: QuizQuestion;
  response: string | null;
  maxAnswerChars: number;
  answerAction: AnswerChallengeAction;
}) {
  const [answer, setAnswer] = useState(response ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [graded, setGraded] = useState<ChallengeAnswerResult | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    setSubmitting(true);
    try {
      const outcome = await answerAction(question.id, answer);
      if ("code" in outcome) setMessage(outcome.message);
      else setGraded(outcome);
    } catch {
      setMessage("Couldn't send your answer. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (graded) {
    return (
      <div className="space-y-2 rounded-2xl border bg-card p-5">
        <Mark outcome={graded.outcome} />
        {graded.question.feedback && <p className="text-sm">{graded.question.feedback}</p>}
        <p className="text-sm text-muted-foreground">Feedback only: this answer earns no point.</p>
      </div>
    );
  }
  return (
    <form onSubmit={submit} className="space-y-3 rounded-2xl border bg-card p-5">
      <WrittenAnswer
        question={question}
        value={answer}
        maxLength={maxAnswerChars}
        onChange={setAnswer}
        idPrefix="resubmit"
      />
      {message && (
        <Notice tone="error" role="alert">
          {message}
        </Notice>
      )}
      <Button type="submit" disabled={submitting || answer.trim() === ""}>
        {submitting && <Spinner />}
        {submitting ? "Grading…" : "Resubmit for feedback"}
      </Button>
    </form>
  );
}

function QuestionForm({
  question: q,
  maxAnswerChars,
  answerAction,
  onAnswered,
  idPrefix = "challenge",
}: {
  question: ChallengeQuestion;
  maxAnswerChars: number;
  answerAction: AnswerChallengeAction;
  onAnswered: (result: ChallengeAnswerResult) => void;
  idPrefix?: string;
}) {
  const [answer, setAnswer] = useState<Answer>(null);
  const [submitting, setSubmitting] = useState(false);
  const [failed, setFailed] = useState(false);
  const [gradingFailed, setGradingFailed] = useState<string | null>(null);
  const written = q.type === "written";

  async function submit(event: FormEvent) {
    event.preventDefault();
    setFailed(false);
    setGradingFailed(null);
    setSubmitting(true);
    try {
      const outcome = await answerAction(q.id, answer);
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
          name={`${idPrefix}-${q.id}`}
          idPrefix={idPrefix}
          value={answer}
          maxLength={maxAnswerChars}
          onChange={setAnswer}
        />
      </QuestionCard>
      {failed && (
        <Notice tone="error" role="alert">
          Couldn&apos;t send your answer. Try again.
        </Notice>
      )}
      {gradingFailed && (
        <Notice tone="error" role="alert">
          {gradingFailed}
        </Notice>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <Button
          type="submit"
          size="lg"
          className="px-4"
          disabled={submitting || !isAnswered(answer)}
        >
          {submitting && <Spinner />}
          {submitting ? (written ? "Grading…" : "Checking…") : "Submit answer"}
        </Button>
        {submitting && written && (
          <span className="text-sm text-muted-foreground"> Grading takes about ten seconds.</span>
        )}
      </div>
    </form>
  );
}
