"use client";

import { useActionState } from "react";
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
    <form action={formAction} className="settings">
      <fieldset>
        <legend>Stacks</legend>
        <ul className="cards">
          {stacks.map((s) => (
            <li key={s.id}>
              <label className="card choice">
                <span>
                  <input
                    type="checkbox"
                    name="stack_ids"
                    value={s.id}
                    defaultChecked={ticked.includes(s.id)}
                  />{" "}
                  <strong>{s.name}</strong>
                </span>
                <span className="muted">{s.summary}</span>
              </label>
            </li>
          ))}
        </ul>
      </fieldset>

      <div className="actions">
        <button type="submit" disabled={pending}>
          {submitLabel}
        </button>
      </div>
      {state?.error && (
        <p role="alert" className="notice notice-error">
          {state.error}
        </p>
      )}
    </form>
  );
}
