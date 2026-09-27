"use client";

import { Send } from "lucide-react";
import { useActionState } from "react";
import { Notice } from "@/components/Notice";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export type InviteState = { ok: boolean; message: string } | null;

export function InviteForm({
  action,
}: {
  action: (previous: InviteState, form: FormData) => Promise<InviteState>;
}) {
  const [state, formAction, pending] = useActionState(action, null);

  return (
    <form action={formAction} className="space-y-3 rounded-2xl border bg-card p-5 shadow-xs">
      <label htmlFor="invite-email" className="text-sm font-semibold">
        Email address
      </label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <Input
          id="invite-email"
          name="email"
          type="email"
          required
          autoComplete="off"
          placeholder="name@example.com"
          className="h-10 flex-1 bg-background text-base"
        />
        <Button type="submit" size="lg" className="h-10 px-4" disabled={pending}>
          <Send aria-hidden />
          Invite
        </Button>
      </div>
      {state && (
        <Notice tone={state.ok ? "success" : "error"} role="status">
          {state.message}
        </Notice>
      )}
    </form>
  );
}
