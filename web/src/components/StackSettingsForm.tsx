"use client";

import { Check, Layers } from "lucide-react";
import { useActionState } from "react";
import { Notice } from "@/components/Notice";
import { Spinner } from "@/components/QuestionCard";
import { Button } from "@/components/ui/button";
import type { StackSummary } from "@/lib/api";

/** What the save action reports back: nothing on success (it navigates away), or why not. */
export type SettingsState = { error: string } | null;

/**
 * Pick the Active Stacks, one or more: the onboarding screen, and settings later. `current`
 * are the Learner's Active Stacks, ticked to start with; a lone Stack is ticked too. An
 * unticked Stack is deactivated on save, and keeps its progress.
 */
export function StackSettingsForm({
  stacks,
  action,
  submitLabel,
  current = [],
}: {
  stacks: StackSummary[];
  action: (previous: SettingsState, form: FormData) => Promise<SettingsState>;
  submitLabel: string;
  current?: string[];
}) {
  const [state, formAction, pending] = useActionState(action, null);
  const ticked = current.length > 0 ? current : stacks.length === 1 ? [stacks[0].id] : [];

  return (
    <form action={formAction} className="space-y-6">
      <fieldset className="space-y-3">
        <legend className="mb-3 text-sm font-semibold tracking-wide text-muted-foreground uppercase">
          Stacks
        </legend>
        <ul className="grid gap-3 sm:grid-cols-2">
          {stacks.map((s) => (
            <li key={s.id} className="flex">
              <label className="group relative flex w-full cursor-pointer gap-4 rounded-2xl border bg-card p-5 shadow-xs transition-colors hover:border-primary/50 has-checked:border-primary has-checked:bg-accent/50 has-checked:ring-1 has-checked:ring-primary has-focus-visible:ring-3 has-focus-visible:ring-ring/40">
                <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <Layers aria-hidden className="size-5" />
                </span>
                <span className="min-w-0 flex-1 space-y-1">
                  <span className="flex items-start justify-between gap-2">
                    <span>
                      <input
                        type="checkbox"
                        name="stack_ids"
                        value={s.id}
                        defaultChecked={ticked.includes(s.id)}
                        className="sr-only"
                      />{" "}
                      <strong className="font-heading font-semibold">{s.name}</strong>
                    </span>
                    <span
                      aria-hidden
                      className="flex size-5 shrink-0 items-center justify-center rounded-md border bg-background text-transparent group-has-checked:border-primary group-has-checked:bg-primary group-has-checked:text-primary-foreground"
                    >
                      <Check className="size-3.5" strokeWidth={3} />
                    </span>
                  </span>
                  <span className="block text-sm text-muted-foreground">{s.summary}</span>
                </span>
              </label>
            </li>
          ))}
        </ul>
      </fieldset>

      <div>
        <Button type="submit" size="lg" className="px-5" disabled={pending}>
          {pending && <Spinner />}
          {submitLabel}
        </Button>
      </div>
      {state?.error && (
        <Notice tone="error" role="alert">
          {state.error}
        </Notice>
      )}
    </form>
  );
}
