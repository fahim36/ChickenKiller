"use client";

import { Plus } from "lucide-react";
import { useActionState } from "react";
import { Notice } from "@/components/Notice";
import { Spinner } from "@/components/QuestionCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { StackRequestState } from "../actions";

const FIELDS: {
  name: string;
  label: string;
  hint?: string;
  placeholder?: string;
  required?: boolean;
  long?: boolean;
}[] = [
  {
    name: "name",
    label: "Name",
    placeholder: "Data Engineer",
    required: true,
  },
  {
    name: "id",
    label: "Id",
    hint: "Lower-case words joined by hyphens. It is permanent.",
    placeholder: "data-engineer",
    required: true,
  },
  {
    name: "summary",
    label: "Summary",
    hint: "One line: what the Stack prepares for.",
    placeholder: "Pipelines, warehouses and streaming, for data engineering interviews.",
    required: true,
  },
  {
    name: "audience",
    label: "Who it is for",
    placeholder: "Backend developers moving into data.",
  },
  {
    name: "notes",
    label: "Notes for Claude",
    hint: "Topics to cover or skip, tools to use, anything the plan should know.",
    long: true,
  },
];

/** The Add a Stack form: what the Stack is, for Claude to plan it from. */
export function NewStackForm({
  action,
}: {
  action: (previous: StackRequestState, form: FormData) => Promise<StackRequestState>;
}) {
  const [state, formAction, pending] = useActionState(action, null);
  const value = (name: string, fallback = "") => state?.values[name] ?? fallback;

  return (
    <form action={formAction} className="space-y-5 rounded-2xl border bg-card p-5 shadow-xs">
      {FIELDS.map((f) => (
        <div key={f.name} className="space-y-1.5">
          <label htmlFor={`stack-${f.name}`} className="text-sm font-semibold">
            {f.label}
            {!f.required && <span className="font-normal text-muted-foreground"> (optional)</span>}
          </label>
          {f.long ? (
            <Textarea
              id={`stack-${f.name}`}
              name={f.name}
              defaultValue={value(f.name)}
              rows={4}
              className="bg-background"
            />
          ) : (
            <Input
              id={`stack-${f.name}`}
              name={f.name}
              required={f.required}
              autoComplete="off"
              defaultValue={value(f.name)}
              placeholder={f.placeholder}
              className="h-10 bg-background"
            />
          )}
          {f.hint && <p className="text-xs text-muted-foreground">{f.hint}</p>}
        </div>
      ))}
      <div className="space-y-1.5">
        <label htmlFor="stack-weeks" className="text-sm font-semibold">
          Weeks
        </label>
        <Input
          id="stack-weeks"
          name="weeks"
          type="number"
          min={1}
          max={52}
          defaultValue={value("weeks", "12")}
          className="h-10 w-28 bg-background"
        />
      </div>

      {state?.error && (
        <Notice tone="error" role="alert">
          {state.error}
        </Notice>
      )}
      <Button type="submit" size="lg" disabled={pending}>
        {pending ? <Spinner /> : <Plus aria-hidden />}
        Request the Stack
      </Button>
    </form>
  );
}
