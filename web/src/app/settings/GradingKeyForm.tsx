"use client";

import { KeyRound, Trash2 } from "lucide-react";
import { useActionState, useTransition } from "react";
import { Notice } from "@/components/Notice";
import { Spinner } from "@/components/QuestionCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Grading } from "@/lib/api";
import type { KeyState } from "./actions";

/**
 * The Learner's own Gemini key for grading written answers: save, replace or remove it. The key
 * is never shown again after saving, only its last four characters. A key saved earlier for
 * another provider (NVIDIA) isn't shown: the Learner is asked for a Gemini key, which replaces it.
 */
export function GradingKeyForm({
  grading,
  saveAction,
  removeAction,
}: {
  grading: Grading;
  saveAction: (previous: KeyState, form: FormData) => Promise<KeyState>;
  removeAction: () => Promise<void>;
}) {
  const [state, formAction, pending] = useActionState(saveAction, null);
  const [removing, startRemoving] = useTransition();
  const key = grading.key?.provider === "gemini" ? grading.key : null;

  return (
    <div className="space-y-4 rounded-2xl border bg-card p-5 shadow-xs">
      <p className="text-sm text-muted-foreground" role="status">
        {key
          ? "Your written answers are graded with your own Gemini key."
          : "Set your own Gemini key below to grade your written answers with it."}
      </p>

      {key && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-muted/40 px-4 py-3 text-sm">
          <span className="flex items-center gap-2">
            <KeyRound aria-hidden className="size-4 text-primary" />
            <span>
              Gemini key ending <code>{key.key_hint}</code> · {key.model}
            </span>
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={removing}
            onClick={() => startRemoving(() => removeAction())}
          >
            {removing ? <Spinner /> : <Trash2 aria-hidden />}
            Remove key
          </Button>
        </div>
      )}

      {grading.keys_enabled ? (
        <form action={formAction} className="space-y-3">
          <div className="space-y-1.5">
            <label htmlFor="api-key" className="text-sm font-semibold">
              {key ? "Replace your Gemini API key" : "Gemini API key"}
            </label>
            <Input
              id="api-key"
              name="api_key"
              type="password"
              autoComplete="off"
              spellCheck={false}
              placeholder="Paste your Gemini API key"
              className="h-10 bg-background font-mono"
            />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="model" className="text-sm font-semibold">
              Model <span className="font-normal text-muted-foreground">(optional)</span>
            </label>
            <Input
              id="model"
              name="model"
              autoComplete="off"
              spellCheck={false}
              placeholder={grading.default_model}
              defaultValue={key?.model ?? grading.default_model}
              className="h-10 bg-background font-mono"
            />
          </div>
          <Button type="submit" size="lg" className="px-4" disabled={pending}>
            {pending ? <Spinner /> : <KeyRound aria-hidden />}
            Save key
          </Button>
          {state && (
            <Notice tone={state.ok ? "success" : "error"} role="status">
              {state.message}
            </Notice>
          )}
        </form>
      ) : (
        <Notice tone="warning" role="note">
          This server can&apos;t store keys yet: the Admin needs to set <code>LLM_KEY_SECRET</code>{" "}
          on the API.
        </Notice>
      )}
    </div>
  );
}
