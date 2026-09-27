"use client";

import { CircleCheck, CircleX, LoaderCircle } from "lucide-react";
import type { ReactNode } from "react";
import { Inline } from "@/components/Inline";
import { cn } from "@/lib/utils";

/**
 * A Question to answer: its prompt as the `legend` of a `fieldset` (so the choices are one named
 * group), then whatever answers it. Used by the Lesson Quiz, Retakes, Review and Daily Challenges.
 */
export function QuestionCard({
  prompt,
  number,
  disabled,
  children,
  className,
}: {
  prompt: string;
  number?: number;
  disabled?: boolean;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("rounded-2xl border bg-card p-5 shadow-xs sm:p-6", className)}>
      <fieldset disabled={disabled} className="min-w-0 space-y-3">
        <legend className="mb-4 flex w-full gap-3 text-base leading-snug font-semibold sm:text-lg">
          {number !== undefined && (
            <span
              aria-hidden
              className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary"
            >
              {number}
            </span>
          )}
          <span className="min-w-0">
            <Inline text={prompt} />
          </span>
        </legend>
        {children}
      </fieldset>
    </div>
  );
}

/**
 * A multiple-choice Question's choices, as native radio buttons dressed as cards: the picked one
 * is highlighted, and the keyboard works as for any radio group.
 */
export function AnswerChoices({
  name,
  choices,
  value,
  onChange,
}: {
  name: string;
  choices: { id: string; text: string }[];
  value: string | null | undefined;
  onChange: (choiceId: string) => void;
}) {
  return (
    <div className="grid gap-2">
      {choices.map((c, i) => (
        <label
          key={c.id}
          className="group relative flex cursor-pointer items-start gap-3 rounded-xl border bg-background px-4 py-3 text-sm transition-colors hover:border-primary/50 hover:bg-accent/40 has-checked:border-primary has-checked:bg-accent has-focus-visible:ring-3 has-focus-visible:ring-ring/40 has-disabled:cursor-default has-disabled:opacity-70 sm:text-base"
        >
          <input
            type="radio"
            name={name}
            value={c.id}
            checked={value === c.id}
            onChange={() => onChange(c.id)}
            className="peer sr-only"
          />
          <span
            aria-hidden
            className="flex size-6 shrink-0 items-center justify-center rounded-md border bg-card text-xs font-semibold text-muted-foreground transition-colors peer-checked:border-primary peer-checked:bg-primary peer-checked:text-primary-foreground"
          >
            {String.fromCharCode(65 + i)}
          </span>
          <span className="min-w-0 pt-px">
            <Inline text={c.text} />
          </span>
        </label>
      ))}
    </div>
  );
}

/** "Correct" or a miss, shown under an answered Question. */
export function Mark({
  correct,
  children,
  className,
}: {
  correct: boolean;
  children: ReactNode;
  className?: string;
}) {
  const Icon = correct ? CircleCheck : CircleX;
  return (
    <p
      className={cn(
        "flex items-center gap-2 text-sm font-semibold",
        correct ? "text-success-foreground" : "text-destructive",
        className,
      )}
    >
      <Icon aria-hidden className="size-4 shrink-0" />
      <span>{children}</span>
    </p>
  );
}

/** A spinner for a button that is waiting on the server. */
export function Spinner() {
  return <LoaderCircle aria-hidden className="size-4 animate-spin" />;
}

/**
 * "Question 2 of 3" and a bar showing how far through a set the Learner is. `step` counts from
 * 0; the bar fills up to and including the current Question.
 */
export function StepProgress({
  label,
  step,
  total,
}: {
  label: string;
  step: number;
  total: number;
}) {
  const percent = total === 0 ? 0 : Math.round(((step + 1) / total) * 100);
  return (
    <div className="mb-4 space-y-2">
      <p className="text-sm font-medium text-muted-foreground">{label}</p>
      <div aria-hidden className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-500"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
