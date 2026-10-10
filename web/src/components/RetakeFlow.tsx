"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { type FormEvent, useState } from "react";
import { AnsweredQuestionDetail } from "@/components/MissedQuestions";
import { Notice } from "@/components/Notice";
import { Mark, QuestionAnswer, QuestionCard, Spinner } from "@/components/QuestionCard";
import { Button } from "@/components/ui/button";
import { submittedAnswer } from "@/lib/answers";
import type {
  Answer,
  AnsweredQuestion,
  GradingFailed,
  QuizQuestion,
  Retake,
  RetakeResult,
  RetakeNotice,
} from "@/lib/api";

interface RetakeState {
  id: string;
  question: QuizQuestion;
  /** How many times this Retake has been answered wrongly: a new ask starts a fresh form. */
  tries: number;
  /** The last wrong sibling, shown with its Explanation. */
  explained: AnsweredQuestion | null;
  done: boolean;
  waived?: boolean;
}

export type AnswerRetakeAction = (
  retakeId: string,
  answer: Answer,
  questionId: string,
) => Promise<RetakeResult | GradingFailed>;

/**
 * The Retakes of a passed Lesson Quiz: for each Missed Question, a sibling Question on the same
 * Concept, of any type. A wrong answer shows that sibling's Explanation (and the
 * grader's feedback on a written one) and the API offers another sibling; once every Retake is
 * correct the Lesson is Completed and the next one is Unlocked. If grading fails, nothing was
 * counted and the Learner submits again.
 */
export function RetakeFlow({
  retakes,
  stackId,
  maxAnswerChars,
  answerAction,
  notices = [],
}: {
  retakes: Retake[];
  stackId: string;
  /** The longest written answer the API accepts. */
  maxAnswerChars: number;
  answerAction: AnswerRetakeAction;
  notices?: RetakeNotice[];
}) {
  const [states, setStates] = useState<RetakeState[]>(() =>
    retakes.map((r) => ({ id: r.id, question: r.question, tries: 0, explained: null, done: false })),
  );
  const [completed, setCompleted] = useState(false);
  const [messages, setMessages] = useState(notices);

  function answered(result: RetakeResult) {
    setMessages(result.notices ?? []);
    setStates((current) =>
      current.map((s) =>
        (result.notices ?? []).some((n) => n.retake_id === s.id && n.waived)
          ? { ...s, explained: null, done: true, waived: true }
          : s.id !== result.retake_id
          ? s
          : result.correct || result.waived
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
      <Notice tone="success" role="status" className="mt-8 text-base">
        <RetakeNotices notices={messages} />
        <p>Every Retake is resolved: this Lesson is Completed and the next one is Unlocked.</p>
        <p>
          <Button asChild variant="outline" className="no-underline!">
            <Link href={`/stacks/${stackId}`}>
              <ArrowLeft aria-hidden />
              Back to the Week map
            </Link>
          </Button>
        </p>
      </Notice>
    );
  }

  return (
    <section className="mt-10 space-y-4">
      <h2 className="font-heading text-lg font-semibold tracking-tight">Retakes</h2>
      <RetakeNotices notices={messages} />
      <p className="text-sm text-muted-foreground">
        Answer a sibling Question on the same Concept for each Missed Question. The Lesson is
        Completed once every Retake is correct.
      </p>
      <ol className="space-y-5">
        {states.map((s) => (
          <li key={s.id}>
            {s.done ? (
              <Mark correct className="rounded-2xl border border-success/30 bg-success/8 px-5 py-4 text-base">
                {s.waived ? "Retake waived" : "Correct"}
              </Mark>
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
  const [answer, setAnswer] = useState<Answer>(null);
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
      const outcome = await answerAction(state.id, submittedAnswer(answer), q.id);
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
      {state.explained && (
        <div className="space-y-3">
          <Mark correct={false} className="rounded-xl bg-destructive/10 px-4 py-3">
            Not quite. Read the Explanation, then try this one.
          </Mark>
          <AnsweredQuestionDetail question={state.explained} />
        </div>
      )}
      <QuestionCard prompt={q.prompt}>
        <QuestionAnswer
          question={q}
          name={`retake-${state.id}`}
          idPrefix={`retake-${state.id}`}
          value={answer}
          maxLength={maxAnswerChars}
          onChange={setAnswer}
        />
      </QuestionCard>
      {failed && (
        <Notice tone="error" role="alert">
          Couldn&apos;t submit your Retake. Try again.
        </Notice>
      )}
      {gradingFailed && (
        <Notice tone="error" role="alert">
          {gradingFailed}
        </Notice>
      )}
      <Button type="submit" size="lg" className="px-4" disabled={submitting}>
        {submitting && <Spinner />}
        {submitting ? "Grading…" : gradingFailed ? "Submit again" : "Submit Retake"}
      </Button>
    </form>
  );
}

export function RetakeNotices({ notices = [] }: { notices?: RetakeNotice[] }) {
  return notices.length > 0 ? (
    <div className="space-y-2" aria-label="Retake content changes">
      {notices.map((notice) => <p key={notice.retake_id}>{notice.message}</p>)}
    </div>
  ) : null;
}
