"use client";

import { Check, X } from "lucide-react";
import { useTransition } from "react";
import { Spinner } from "@/components/QuestionCard";
import { Button } from "@/components/ui/button";

/** Accept or reject one draft. */
export function DraftActions({
  id,
  action,
}: {
  id: number;
  action: (id: number, status: "accepted" | "rejected") => Promise<void>;
}) {
  const [pending, start] = useTransition();
  return (
    <div className="flex gap-2">
      <Button size="sm" disabled={pending} onClick={() => start(() => action(id, "accepted"))}>
        {pending ? <Spinner /> : <Check aria-hidden />}
        Accept
      </Button>
      <Button
        size="sm"
        variant="outline"
        disabled={pending}
        onClick={() => start(() => action(id, "rejected"))}
      >
        <X aria-hidden />
        Reject
      </Button>
    </div>
  );
}
