"use client";

import { Trash2 } from "lucide-react";
import { useState, useTransition } from "react";
import { Spinner } from "@/components/QuestionCard";
import { Button } from "@/components/ui/button";

/** Delete a Stack being built, after a second click to confirm: its drafts go with it. */
export function DeleteStackRequest({
  stackId,
  name,
  action,
}: {
  stackId: string;
  name: string;
  action: (stackId: string) => Promise<void>;
}) {
  const [confirming, setConfirming] = useState(false);
  const [pending, startTransition] = useTransition();

  if (!confirming) {
    return (
      <Button
        type="button"
        variant="outline"
        size="sm"
        aria-label={`Delete ${name}`}
        onClick={() => setConfirming(true)}
      >
        <Trash2 aria-hidden />
        Delete
      </Button>
    );
  }
  return (
    <span className="flex flex-wrap items-center gap-2 text-sm" role="group">
      <span>Delete {name} and all its drafts?</span>
      <Button
        type="button"
        variant="destructive"
        size="sm"
        disabled={pending}
        onClick={() => startTransition(() => action(stackId))}
      >
        {pending ? <Spinner /> : <Trash2 aria-hidden />}
        Delete for good
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        disabled={pending}
        onClick={() => setConfirming(false)}
      >
        Keep it
      </Button>
    </span>
  );
}
