"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";
import { Inline } from "@/components/Inline";
import { AnsweredQuestionDetail } from "@/components/MissedQuestions";
import { ResultCard } from "@/components/ResultCard";
import { WrittenAnswer } from "@/components/WrittenAnswer";
import type {
  ChallengeAnswerResult,
  ChallengeOutcome,
  ChallengeQuestion,
  DailyChallenge,
  GradingFailed,
  QuizQuestion,
} from "@/lib/api";

export type AnswerChallengeAction = (
  questionId: string,
  answer: string | null,
) => Promise<ChallengeAnswerResult | GradingFailed>;

const OUTCOME_LABELS: Record<ChallengeOutcome, string> = {
  correct: "Correct",
  wrong: "Wrong",
  ungraded: "Ungraded: no point",
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
      <section className="challenge">
        <Result
          result={shown}
          maxAnswerChars={challenge.max_answer_chars}
          answerAction={answerAction}
        />
        <button type="button" onClick={() => setShown(null)}>
          {pending ? "Next Question" : "See your score"}
        </button>
      </section>
    );
  }

  if (pending) {
    return (
      <section className="challenge">
        {challenge.status === "not_started" && (
          <p className="muted">
            {questions.length} Questions. Only your first answer to each Question counts.
          </p>
        )}
        <p className="muted">
          Question {questions.indexOf(pending) + 1} of {questions.length}
        </p>
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
    <section className="challenge" aria-label="Your score">
      {challenge.status === "finished" && (
        <p className="mark">
          Played: {challenge.score}/{challenge.out_of}
        </p>
      )}
      {challenge.result_card && <ResultCard text={challenge.result_card} />}
      <ol className="challenge-summary">
        {challenge.questions.map((q) => (
          <li key={q.id}>
            {q.outcome === null ? (
              <>
                <p>
                  <Inline text={q.prompt} />
                </p>
                {q.retired && <Retired question={q} stackId={stackId} />}
              </>
            ) : (
              <>
                <p>
                  <strong>{OUTCOME_LABELS[q.outcome]}</strong>
                </p>
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
      <p>
        <button type="button" onClick={onReplay}>
          Replay
        </button>{" "}
        <span className="small muted">
          For learning: it changes nothing about your score, Streak or Missed Questions.
        </span>
      </p>
    </section>
  );
}

/**
 * Why a Question was retired, and where its replacement is: the first released Challenge that
 * asks it, in the Stack's Archive. A replacement no released Challenge asks yet has no link.
 */
function Retired({ question, stackId }: { question: ChallengeQuestion; stackId: string }) {
  const replacement = question.replaced_by;
  return (
    <p className="small muted">
      Retired{question.retired_reason ? `: ${question.retired_reason}` : "."} It can&apos;t be
      answered and isn&apos;t scored.
      {replacement &&
        (replacement.challenge_number !== null ? (
          <>
            {" "}
            Its replacement is in{" "}
            <Link
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
    <section className="challenge">
      <p className="muted">
        Replay · Question {position + 1} of {questions.length}
      </p>
      {shown ? (
        <>
          <Result result={shown} maxAnswerChars={maxAnswerChars} answerAction={answerAction} />
          <button
            type="button"
            onClick={() => {
              setShown(null);
              if (isLast) onDone();
              else setPosition((p) => p + 1);
            }}
          >
            {isLast ? "Finish replay" : "Next Question"}
          </button>
        </>
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
    <div>
      {ungraded ? (
        <p role="alert" className="notice notice-error">
          Your answer couldn&apos;t be graded, so it earns no point toward your score. You can
          resubmit it for feedback.
        </p>
      ) : (
        <Mark outcome={result.outcome} />
      )}
      {!result.counted && (
        <p className="small muted">
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
  if (outcome === "correct") return <p className="mark mark-correct">Correct</p>;
  if (outcome === "wrong") {
    return <p className="mark mark-missed">Not quite. Read the Explanation.</p>;
  }
  return <p className="mark mark-missed">Couldn&apos;t be graded.</p>;
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
      <div className="resubmitted">
        <Mark outcome={graded.outcome} />
        {graded.question.feedback && <p className="feedback">{graded.question.feedback}</p>}
        <p className="small muted">Feedback only: this answer earns no point.</p>
      </div>
    );
  }
  return (
    <form onSubmit={submit}>
      <WrittenAnswer
        question={question}
        value={answer}
        maxLength={maxAnswerChars}
        onChange={setAnswer}
        idPrefix="resubmit"
      />
      {message && (
        <p role="alert" className="notice notice-error">
          {message}
        </p>
      )}
      <button type="submit" disabled={submitting || answer.trim() === ""}>
        {submitting ? "Grading…" : "Resubmit for feedback"}
      </button>
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
  const [answer, setAnswer] = useState("");
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
    <form onSubmit={submit}>
      <fieldset>
        <legend>
          <Inline text={q.prompt} />
        </legend>
        {written ? (
          <WrittenAnswer
            question={q}
            value={answer}
            maxLength={maxAnswerChars}
            onChange={setAnswer}
            idPrefix={idPrefix}
          />
        ) : (
          q.choices.map((c) => (
            <label key={c.id} className="choice">
              <input
                type="radio"
                name={`${idPrefix}-${q.id}`}
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
          Couldn&apos;t send your answer. Try again.
        </p>
      )}
      {gradingFailed && (
        <p role="alert" className="notice notice-error">
          {gradingFailed}
        </p>
      )}
      <button type="submit" disabled={submitting || answer.trim() === ""}>
        {submitting ? (written ? "Grading…" : "Checking…") : "Submit answer"}
      </button>
      {submitting && written && (
        <span className="small muted"> Grading takes about ten seconds.</span>
      )}
    </form>
  );
}
