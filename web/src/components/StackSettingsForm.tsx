"use client";

import { useActionState, useState, useSyncExternalStore } from "react";
import type { Settings, StackSummary } from "@/lib/api";

/** What the save action reports back: nothing on success (it navigates away), or why not. */
export type SettingsState = { error: string } | null;

const noSubscription = () => () => {};

/** A browser-only value: null while rendering on the server, so hydration matches. */
function useBrowserValue<T>(read: () => T): T | null {
  return useSyncExternalStore(noSubscription, read, () => null);
}

function browserTimeZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

let timeZoneNames: string[] | undefined;
function knownTimeZones(): string[] {
  // Suggestions only: the API checks the name against the IANA database.
  timeZoneNames ??= Intl.supportedValuesOf("timeZone");
  return timeZoneNames;
}

/**
 * Pick the Active Stack and time zone: the onboarding screen, and settings later. Without
 * `current` the time zone starts as the browser's.
 */
export function StackSettingsForm({
  stacks,
  action,
  submitLabel,
  current,
}: {
  stacks: StackSummary[];
  action: (previous: SettingsState, form: FormData) => Promise<SettingsState>;
  submitLabel: string;
  current?: Settings;
}) {
  const [state, formAction, pending] = useActionState(action, null);
  const detected = useBrowserValue(browserTimeZone);
  const suggestions = useBrowserValue(knownTimeZones);
  const [typed, setTyped] = useState<string | null>(null);
  const timeZone = typed ?? current?.time_zone ?? detected ?? "";
  const onlyStack = stacks.length === 1 ? stacks[0].id : undefined;

  return (
    <form action={formAction} className="settings">
      <fieldset>
        <legend>Stack</legend>
        <ul className="cards">
          {stacks.map((s) => (
            <li key={s.id}>
              <label className="card choice">
                <span>
                  <input
                    type="radio"
                    name="active_stack_id"
                    value={s.id}
                    required
                    defaultChecked={s.id === (current?.active_stack_id ?? onlyStack)}
                  />{" "}
                  <strong>{s.name}</strong>
                </span>
                <span className="muted">{s.summary}</span>
              </label>
            </li>
          ))}
        </ul>
      </fieldset>

      <label htmlFor="time-zone" className="field-label">
        Time zone
      </label>
      <p className="muted small" id="time-zone-help">
        Your Daily Review follows the calendar day where you are.
      </p>
      <input
        id="time-zone"
        name="time_zone"
        type="text"
        list="time-zones"
        required
        autoComplete="off"
        spellCheck={false}
        aria-describedby="time-zone-help"
        value={timeZone}
        onChange={(event) => setTyped(event.target.value)}
      />
      <datalist id="time-zones">
        {suggestions?.map((name) => (
          <option key={name} value={name} />
        ))}
      </datalist>

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
