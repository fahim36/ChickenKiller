"use client";

import { useActionState } from "react";

export type InviteState = { ok: boolean; message: string } | null;

export function InviteForm({
  action,
}: {
  action: (previous: InviteState, form: FormData) => Promise<InviteState>;
}) {
  const [state, formAction, pending] = useActionState(action, null);

  return (
    <form action={formAction} className="invite">
      <label htmlFor="invite-email">Email address</label>
      <div className="invite-row">
        <input id="invite-email" name="email" type="email" required autoComplete="off" />
        <button type="submit" disabled={pending}>
          Invite
        </button>
      </div>
      {state && (
        <p role="status" className={state.ok ? "notice" : "notice notice-error"}>
          {state.message}
        </p>
      )}
    </form>
  );
}
