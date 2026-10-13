"use client";

import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Clock3,
  RotateCcw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Inline } from "@/components/Inline";
import { useRef, useState } from "react";
import { abandonPlacement, savePlacement, submitPlacement } from "./actions";
import type { PlacementAttempt } from "./types";

function PlacementText({ text }: { text: string }) {
  return text.split(/```[\w+-]*\n([\s\S]*?)```/g).map((part, index) =>
    index % 2 ? (
      <code
        key={index}
        className="my-2 block overflow-x-auto whitespace-pre-wrap rounded bg-muted p-3 text-sm"
      >
        {part}
      </code>
    ) : (
      <Inline key={index} text={part} />
    ),
  );
}

export function PlacementPractice({
  initial,
  lessonTitles = {},
}: {
  initial: PlacementAttempt;
  lessonTitles?: Record<string, string>;
}) {
  const [attempt, setAttempt] = useState(initial);
  const [answers, setAnswers] = useState(initial.responses);
  const answersRef = useRef(initial.responses);
  const queue = useRef(Promise.resolve());
  const dirty = useRef(new Set<string>());
  const [pending, setPending] = useState(0);
  const [error, setError] = useState("");
  const [unsaved, setUnsaved] = useState(false);
  const answered = Object.values(answers).filter((answer) =>
    Array.isArray(answer) ? answer.length > 0 : Boolean(answer),
  ).length;
  const lessonIds = [...new Set(attempt.questions.map((q) => q.lesson))];
  const lessonTitle = (id: string) =>
    lessonTitles[id] ?? `Lesson ${lessonIds.indexOf(id) + 1}`;

  function save(question: string, answer: string | string[] | null) {
    const next = { ...answersRef.current, [question]: answer };
    answersRef.current = next;
    setAnswers(next);
    dirty.current.add(question);
    setUnsaved(true);
    setPending((n) => n + 1);
    queue.current = queue.current.then(async () => {
      try {
        const result = await savePlacement(attempt.id, question, answer);
        if (result.state !== "open") setAttempt(result);
        if (answersRef.current[question] === answer)
          dirty.current.delete(question);
        if (dirty.current.size === 0) {
          setError("");
          setUnsaved(false);
        }
      } catch {
        setError(
          "Some answers could not be saved. Retry before leaving this page.",
        );
      } finally {
        setPending((n) => n - 1);
      }
    });
  }

  async function abandon() {
    try {
      const result = await abandonPlacement(attempt.id);
      setAttempt(result);
    } catch {
      setError("Could not abandon this attempt. Try again.");
    }
  }

  async function submit() {
    setPending((n) => n + 1);
    try {
      setAttempt(await submitPlacement(attempt.id));
    } catch {
      setError(
        "Could not submit. Your saved answers remain available; try again.",
      );
    } finally {
      setPending((n) => n - 1);
    }
  }

  return (
    <div className="min-w-0 space-y-6 break-words">
      <div className="rounded-2xl border bg-card p-5 shadow-xs sm:p-6">
        <p className="flex items-center gap-2 text-sm font-medium">
          <ShieldCheck aria-hidden className="size-4 text-primary" />
          Your knowledge, your pace
        </p>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
          Self-assessment: answer without outside help. No timer. Answers save
          automatically; correctness appears after submission.
        </p>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm">
          <span className="flex items-center gap-2 text-muted-foreground">
            <Clock3 aria-hidden className="size-4" />
            Untimed self-assessment
          </span>
          <p
            role="status"
            className={cn(
              "rounded-full px-3 py-1 text-xs font-medium",
              error
                ? "bg-destructive/10 text-destructive"
                : "bg-success/10 text-success-foreground",
            )}
          >
            {pending
              ? "Saving answers…"
              : error
                ? "Unsaved answers"
                : "Answers saved"}
          </p>
        </div>
        {attempt.state === "open" && (
          <div className="mt-5 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="font-medium">Your progress</span>
              <span className="text-muted-foreground">
                {answered} of {attempt.questions.length} answered
              </span>
            </div>
            <progress
              aria-label="Answered questions"
              value={answered}
              max={attempt.questions.length}
              className="h-2 w-full overflow-hidden rounded-full accent-primary"
            />
          </div>
        )}
      </div>
      {error && (
        <div
          role="alert"
          className="rounded-2xl border border-destructive/30 bg-destructive/5 p-5 text-sm"
        >
          <p>{error}</p>
          <Button
            className="mt-3"
            variant="outline"
            type="button"
            onClick={() => {
              for (const question of dirty.current)
                save(question, answersRef.current[question] ?? null);
            }}
          >
            Retry saving
          </Button>
        </div>
      )}
      {attempt.state === "submitted" && attempt.result ? (
        <div className="space-y-6">
          <section
            className={cn(
              "rounded-3xl border p-6 shadow-xs sm:p-8",
              attempt.result.passed
                ? "border-success/25 bg-linear-to-br from-success/10 via-card to-background"
                : "border-primary/20 bg-linear-to-br from-primary/10 via-card to-background",
            )}
          >
            <div className="mb-4 flex items-center gap-3">
              <span className="flex size-12 items-center justify-center rounded-2xl bg-background shadow-xs">
                {attempt.result.passed ? (
                  <CheckCircle2
                    aria-hidden
                    className="size-6 text-success-foreground"
                  />
                ) : (
                  <Sparkles aria-hidden className="size-6 text-primary" />
                )}
              </span>
              <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                Your placement result
              </p>
            </div>
            <h2 className="font-heading text-3xl font-semibold tracking-tight">
              {attempt.result.passed
                ? "Placement passed"
                : "Continue the Lesson path"}
            </h2>
            <p className="my-4 text-5xl font-semibold tracking-tight">
              {Math.round(
                (attempt.result.correct / attempt.result.total) * 100,
              )}
              <span className="text-2xl text-muted-foreground">%</span>
            </p>
            <p className="text-sm text-muted-foreground">
              {attempt.result.correct}/{attempt.result.total} correct. Passing
              requires 80% overall and in every Lesson.
            </p>
            <div className="my-6 grid gap-3 sm:grid-cols-2">
              {attempt.result.lessons.map((lesson) => (
                <p
                  key={lesson.lesson}
                  className="rounded-2xl border bg-background/70 p-4 text-sm"
                >
                  {lessonTitle(lesson.lesson)}: {lesson.correct}/{lesson.total}{" "}
                  · {lesson.passed ? "Passed" : "Below 80%"}
                </p>
              ))}
            </div>
            <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
              {attempt.result.passed
                ? "Previously incomplete Lessons are completed by placement."
                : "No additional Lessons were completed."}{" "}
              Misses are available in optional Review.
            </p>
            <Button asChild className="mt-5">
              <Link href="/review">
                Optional Review <ArrowRight aria-hidden />
              </Link>
            </Button>
          </section>
          <h2 className="font-heading text-xl font-semibold">
            Answers & explanations
          </h2>
          {attempt.questions.map((q) => (
            <section
              key={q.id}
              className="space-y-4 rounded-2xl border bg-card p-5 shadow-xs sm:p-6"
            >
              <h3 className="font-medium leading-relaxed">
                <PlacementText text={q.prompt} />
              </h3>
              <p
                className={cn(
                  "inline-flex rounded-full px-3 py-1 text-xs font-semibold",
                  attempt.result?.correct_questions[q.id]
                    ? "bg-success/10 text-success-foreground"
                    : "bg-destructive/10 text-destructive",
                )}
              >
                {attempt.result?.correct_questions[q.id]
                  ? "Correct"
                  : "Incorrect or unanswered"}
              </p>
              <p>
                Correct choices:{" "}
                {q.choices
                  .filter((c) => (q.answers ?? [q.answer]).includes(c.id))
                  .map((c) => c.text)
                  .join("; ")}
              </p>
              <p className="text-sm leading-relaxed text-muted-foreground">
                <PlacementText text={q.explanation ?? ""} />
              </p>
              {q.sources?.map((source) => (
                <p key={source.url}>
                  <a
                    className="text-sm font-medium text-primary underline underline-offset-4"
                    href={source.url}
                  >
                    {source.title}
                  </a>
                </p>
              ))}
            </section>
          ))}
        </div>
      ) : attempt.state !== "open" ? (
        <p className="rounded-2xl border bg-muted/50 p-6">
          {attempt.reason ?? "This attempt has finished."}
        </p>
      ) : (
        <>
          {attempt.questions.map((q, index) => (
            <fieldset
              key={q.id}
              className="min-w-0 space-y-4 rounded-2xl border bg-card p-5 shadow-xs sm:p-6"
            >
              <legend className="max-w-full px-2 text-base font-semibold leading-relaxed sm:text-lg">
                {index + 1}. <PlacementText text={q.prompt} />
              </legend>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {lessonTitle(q.lesson)} ·{" "}
                {q.type === "multiple_select"
                  ? "Select all that apply"
                  : "Choose one"}
              </p>
              {q.choices.map((choice) => {
                const current = answers[q.id];
                const checked = Array.isArray(current)
                  ? current.includes(choice.id)
                  : current === choice.id;
                return (
                  <label
                    key={choice.id}
                    className={cn(
                      "flex cursor-pointer items-start gap-3 rounded-xl border p-4 text-sm leading-relaxed transition-colors focus-within:ring-2 focus-within:ring-primary/50",
                      checked
                        ? "border-primary/50 bg-primary/8"
                        : "border-border bg-background hover:border-primary/30 hover:bg-muted/40",
                    )}
                  >
                    <input
                      type={q.type === "multiple_select" ? "checkbox" : "radio"}
                      name={q.id}
                      className="mt-1 size-4 shrink-0 accent-primary"
                      checked={checked}
                      onChange={() => {
                        const ticks = Array.isArray(current) ? current : [];
                        save(
                          q.id,
                          q.type === "multiple_select"
                            ? checked
                              ? ticks.filter((id) => id !== choice.id)
                              : [...ticks, choice.id]
                            : choice.id,
                        );
                      }}
                    />
                    <Inline text={choice.text} />
                  </label>
                );
              })}
              <Button
                variant="ghost"
                size="sm"
                type="button"
                onClick={() => save(q.id, null)}
              >
                <RotateCcw aria-hidden className="size-3.5" />
                Clear answer
              </Button>
            </fieldset>
          ))}
          <div className="rounded-2xl border bg-card p-6 shadow-xs">
            <Button
              size="lg"
              type="button"
              disabled={pending > 0 || unsaved}
              onClick={submit}
            >
              Submit placement
              <ArrowRight aria-hidden />
            </Button>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">
              Submission is final. Unanswered Questions count as incorrect. One
              submitted attempt is allowed per Week teaching revision.
            </p>
            <Button
              className="mt-5"
              variant="outline"
              type="button"
              disabled={pending > 0}
              onClick={abandon}
            >
              Abandon attempt
            </Button>
            <p className="mt-2 text-xs text-muted-foreground">
              Abandoning uses no submitted attempt, but viewed Questions remain
              seen.
            </p>
          </div>
        </>
      )}
      <Link
        className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground"
        href={`/stacks/${encodeURIComponent(attempt.stack_id)}`}
      >
        <ArrowLeft aria-hidden className="size-4" />
        Return to your Week map
      </Link>
    </div>
  );
}
